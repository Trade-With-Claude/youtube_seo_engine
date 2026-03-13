import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def parse_youtube_url(url: str) -> dict:
    """Parse a YouTube channel URL and extract the identifier.

    Supports:
      - https://youtube.com/@handle
      - https://youtube.com/channel/UC...
      - https://youtube.com/c/CustomName
      - @handle (bare)
      - UC... (bare channel ID)
    """
    url = url.strip()

    # Bare handle
    if url.startswith("@"):
        return {"handle": url, "youtube_id": "", "type": "handle"}

    # Bare channel ID
    if url.startswith("UC") and len(url) == 24:
        return {"handle": "", "youtube_id": url, "type": "channel_id"}

    # Full URL
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # /@handle
    match = re.match(r"^/@([\w.-]+)", path)
    if match:
        return {"handle": f"@{match.group(1)}", "youtube_id": "", "type": "handle"}

    # /channel/UC...
    match = re.match(r"^/channel/(UC[\w-]+)", path)
    if match:
        return {"handle": "", "youtube_id": match.group(1), "type": "channel_id"}

    # /c/CustomName
    match = re.match(r"^/c/([\w.-]+)", path)
    if match:
        return {"handle": f"@{match.group(1)}", "youtube_id": "", "type": "custom"}

    return {"handle": "", "youtube_id": "", "type": "unknown"}


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "channels": channels,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/channel")
def add_channel(channel_url: str = Form(...), session: Session = Depends(get_session)):
    parsed = parse_youtube_url(channel_url)

    if parsed["type"] == "unknown":
        return RedirectResponse(
            url="/?error=Could not parse that URL. Try a YouTube channel URL like https://youtube.com/@handle",
            status_code=303,
        )

    # Check for duplicates
    youtube_id = parsed["youtube_id"]
    handle = parsed["handle"]

    if youtube_id:
        existing = session.exec(select(Channel).where(Channel.youtube_id == youtube_id)).first()
    elif handle:
        existing = session.exec(select(Channel).where(Channel.handle == handle)).first()
    else:
        existing = None

    if existing:
        return RedirectResponse(url="/?error=Channel already added", status_code=303)

    channel = Channel(
        youtube_id=youtube_id or handle,  # Use handle as temporary ID until API resolves
        handle=handle,
        url=channel_url.strip(),
        name=handle or youtube_id,  # Placeholder name until API fetch
    )
    session.add(channel)
    session.commit()

    return RedirectResponse(url="/?message=Channel added successfully", status_code=303)
