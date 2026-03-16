from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.services.vph import poll_vph, get_vph_for_videos

router = APIRouter(prefix="/vph", tags=["vph"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def vph_dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    channel_id = request.query_params.get("channel_id")

    selected_channel = None
    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    vph_data = []
    if selected_channel:
        vph_data = get_vph_for_videos(session, selected_channel.id)

    return templates.TemplateResponse("vph.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "vph_data": vph_data,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/poll")
def trigger_poll(
    request: Request,
    session: Session = Depends(get_session),
):
    channel_id = request.query_params.get("channel_id")
    cid = int(channel_id) if channel_id else None

    try:
        count = poll_vph(session, cid)
        msg = f"Polled {count} videos"
    except Exception as e:
        redirect = f"/vph?error={str(e)}"
        if channel_id:
            redirect += f"&channel_id={channel_id}"
        return RedirectResponse(url=redirect, status_code=303)

    redirect = f"/vph?message={msg}"
    if channel_id:
        redirect += f"&channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)
