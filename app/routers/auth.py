import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import Channel, OAuthToken
from app.services.analytics import SCOPES

router = APIRouter(prefix="/auth")


def _create_flow() -> Flow:
    """Create a Google OAuth flow from our app settings."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


@router.get("/start")
def auth_start(request: Request, channel_id: int = 0):
    """Start the OAuth flow — redirects to Google consent screen."""
    flow = _create_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=str(channel_id),
    )
    return RedirectResponse(authorization_url)


@router.get("/callback")
def auth_callback(
    request: Request,
    code: str,
    state: str = "0",
    session: Session = Depends(get_session),
):
    """Handle the OAuth callback from Google."""
    flow = _create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    channel_id = int(state) if state.isdigit() else 0

    # If no channel specified, find the first one or create a placeholder
    if channel_id == 0:
        channel = session.exec(select(Channel)).first()
        if channel:
            channel_id = channel.id

    if channel_id == 0:
        return RedirectResponse(url="/?error=No channel found. Add a channel first.", status_code=303)

    # Mark channel as own (since user authenticated with their Google account)
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if channel:
        channel.is_own = True

    # Upsert OAuth token
    existing_token = session.exec(
        select(OAuthToken).where(OAuthToken.channel_id == channel_id)
    ).first()

    if existing_token:
        existing_token.access_token = creds.token
        existing_token.refresh_token = creds.refresh_token or existing_token.refresh_token
        existing_token.scopes = json.dumps(list(creds.scopes or []))
        existing_token.expiry = creds.expiry
        existing_token.updated_at = datetime.utcnow()
    else:
        token = OAuthToken(
            channel_id=channel_id,
            access_token=creds.token,
            refresh_token=creds.refresh_token or "",
            scopes=json.dumps(list(creds.scopes or [])),
            expiry=creds.expiry,
        )
        session.add(token)

    session.commit()

    return RedirectResponse(
        url=f"/?message=YouTube Analytics connected successfully&channel_id={channel_id}",
        status_code=303,
    )
