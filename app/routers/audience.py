from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel, OAuthToken, Video
from app.services.audience import get_audience_activity, get_subscriber_sources

router = APIRouter(prefix="/audience", tags=["audience"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def audience_dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    channel_id = request.query_params.get("channel_id")

    selected_channel = None
    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    oauth_token = None
    activity_data = None
    subscriber_data = None

    if selected_channel:
        oauth_token = session.exec(
            select(OAuthToken).where(OAuthToken.channel_id == selected_channel.id)
        ).first()

        if oauth_token:
            try:
                activity_data = get_audience_activity(oauth_token)
            except Exception as e:
                activity_data = {"has_data": False, "error": str(e)}

            try:
                subscriber_data = get_subscriber_sources(oauth_token)
                # Enrich video data with titles
                if subscriber_data and subscriber_data.get("by_video"):
                    for item in subscriber_data["by_video"]:
                        video = session.exec(
                            select(Video).where(Video.youtube_id == item["video_id"])
                        ).first()
                        item["title"] = video.title if video else item["video_id"]
            except Exception as e:
                subscriber_data = {"has_data": False, "error": str(e)}

    return templates.TemplateResponse("audience.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "oauth_connected": oauth_token is not None,
        "activity": activity_data,
        "subscribers": subscriber_data,
        "error": request.query_params.get("error"),
    })
