from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.services.competitors import (
    add_competitor_manual,
    discover_competitors,
    get_competitors_with_data,
)
from app.services.youtube_api import resolve_channel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/competitors")
def competitors_page(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel).where(Channel.is_own == True)).all()
    if not channels:
        channels = session.exec(select(Channel)).all()

    selected_id = request.query_params.get("channel_id")
    selected_channel = None
    competitors_data = []

    if selected_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(selected_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    if selected_channel:
        competitors_data = get_competitors_with_data(session, selected_channel.id)

    return templates.TemplateResponse("competitors.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "competitors": competitors_data,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/competitors/discover/{channel_id}")
def discover(channel_id: int, session: Session = Depends(get_session)):
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if not channel:
        return RedirectResponse(url="/competitors?error=Channel not found", status_code=303)

    try:
        count = discover_competitors(session, channel_id)
    except Exception as e:
        error = str(e)[:200]
        if "quota" in error.lower():
            error = "YouTube API quota exceeded. Try again tomorrow."
        elif "forbidden" in error.lower() or "key" in error.lower():
            error = "YouTube API key invalid or missing. Check your .env file."
        else:
            error = f"API error: {error}"
        return RedirectResponse(
            url=f"/competitors?error={error}&channel_id={channel_id}",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/competitors?message=Discovered {count} new competitors&channel_id={channel_id}",
        status_code=303,
    )


@router.post("/competitors/add/{channel_id}")
def add_manual(
    channel_id: int,
    competitor_url: str = Form(...),
    session: Session = Depends(get_session),
):
    # Resolve the competitor channel
    from app.routers.dashboard import parse_youtube_url

    parsed = parse_youtube_url(competitor_url)
    identifier = parsed.get("youtube_id") or parsed.get("handle")

    if not identifier or parsed["type"] == "unknown":
        return RedirectResponse(
            url=f"/competitors?error=Could not parse that URL&channel_id={channel_id}",
            status_code=303,
        )

    try:
        channel_data = resolve_channel(identifier)
    except Exception as e:
        return RedirectResponse(
            url=f"/competitors?error=API error: {str(e)[:100]}&channel_id={channel_id}",
            status_code=303,
        )
    if not channel_data:
        return RedirectResponse(
            url=f"/competitors?error=Channel not found on YouTube&channel_id={channel_id}",
            status_code=303,
        )

    # Get or create the competitor channel
    from datetime import datetime

    existing = session.exec(
        select(Channel).where(Channel.youtube_id == channel_data["youtube_id"])
    ).first()

    if not existing:
        existing = Channel(
            youtube_id=channel_data["youtube_id"],
            name=channel_data["name"],
            handle=channel_data["handle"],
            description=channel_data["description"][:500],
            subscriber_count=channel_data["subscriber_count"],
            video_count=channel_data["video_count"],
            fetched_at=datetime.utcnow(),
        )
        session.add(existing)
        session.flush()

    added = add_competitor_manual(session, channel_id, existing.id)

    if added:
        msg = f"Added '{existing.name}' as competitor"
    else:
        msg = f"'{existing.name}' is already a competitor"

    return RedirectResponse(
        url=f"/competitors?message={msg}&channel_id={channel_id}",
        status_code=303,
    )
