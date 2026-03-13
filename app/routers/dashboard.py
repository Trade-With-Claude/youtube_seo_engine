import re
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel, Video
from app.services.youtube_api import resolve_channel, fetch_videos

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def parse_youtube_url(url: str) -> dict:
    """Parse a YouTube channel URL and extract the identifier."""
    url = url.strip()

    if url.startswith("@"):
        return {"handle": url, "youtube_id": "", "type": "handle"}

    if url.startswith("UC") and len(url) == 24:
        return {"handle": "", "youtube_id": url, "type": "channel_id"}

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    match = re.match(r"^/@([\w.-]+)", path)
    if match:
        return {"handle": f"@{match.group(1)}", "youtube_id": "", "type": "handle"}

    match = re.match(r"^/channel/(UC[\w-]+)", path)
    if match:
        return {"handle": "", "youtube_id": match.group(1), "type": "channel_id"}

    match = re.match(r"^/c/([\w.-]+)", path)
    if match:
        return {"handle": f"@{match.group(1)}", "youtube_id": "", "type": "custom"}

    return {"handle": "", "youtube_id": "", "type": "unknown"}


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    # Get videos for the first channel (or selected one)
    channel_id = request.query_params.get("channel_id")
    videos = []
    selected_channel = None

    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    if selected_channel:
        videos = session.exec(
            select(Video).where(Video.channel_id == selected_channel.id)
        ).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "videos": videos,
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

    # Resolve channel via YouTube API
    identifier = parsed["youtube_id"] or parsed["handle"]
    channel_data = resolve_channel(identifier)

    if not channel_data:
        return RedirectResponse(
            url="/?error=Channel not found on YouTube. Check the URL and try again.",
            status_code=303,
        )

    # Check for duplicates
    existing = session.exec(
        select(Channel).where(Channel.youtube_id == channel_data["youtube_id"])
    ).first()
    if existing:
        return RedirectResponse(url="/?error=Channel already added", status_code=303)

    channel = Channel(
        youtube_id=channel_data["youtube_id"],
        name=channel_data["name"],
        handle=channel_data["handle"],
        url=channel_url.strip(),
        description=channel_data["description"],
        subscriber_count=channel_data["subscriber_count"],
        video_count=channel_data["video_count"],
        fetched_at=datetime.utcnow(),
    )
    session.add(channel)
    session.commit()
    session.refresh(channel)

    return RedirectResponse(
        url=f"/?message=Channel '{channel.name}' added successfully&channel_id={channel.id}",
        status_code=303,
    )


@router.post("/channel/{channel_id}/fetch-videos")
def fetch_channel_videos(channel_id: int, session: Session = Depends(get_session)):
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if not channel:
        return RedirectResponse(url="/?error=Channel not found", status_code=303)

    video_data_list = fetch_videos(channel.youtube_id, max_results=50)

    count = 0
    for vdata in video_data_list:
        # Skip if already exists
        existing = session.exec(
            select(Video).where(Video.youtube_id == vdata["youtube_id"])
        ).first()
        if existing:
            continue

        video = Video(
            channel_id=channel.id,
            youtube_id=vdata["youtube_id"],
            title=vdata["title"],
            description=vdata["description"],
            tags=vdata["tags"],
            views=vdata["views"],
            likes=vdata["likes"],
            comments_count=vdata["comments_count"],
            published_at=vdata["published_at"],
            fetched_at=datetime.utcnow(),
        )
        session.add(video)
        count += 1

    session.commit()

    return RedirectResponse(
        url=f"/?message=Fetched {count} new videos for '{channel.name}'&channel_id={channel.id}",
        status_code=303,
    )


@router.get("/setup")
def setup_guide(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})
