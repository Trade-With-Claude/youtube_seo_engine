from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.services.seo_scoring import score_all_videos, get_seo_scores

router = APIRouter(prefix="/seo", tags=["seo"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def seo_dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    channel_id = request.query_params.get("channel_id")

    selected_channel = None
    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    seo_data = []
    if selected_channel:
        seo_data = get_seo_scores(session, selected_channel.id)

    return templates.TemplateResponse("seo.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "seo_data": seo_data,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/score")
def trigger_scoring(request: Request, session: Session = Depends(get_session)):
    channel_id = request.query_params.get("channel_id")
    cid = int(channel_id) if channel_id else None

    if not cid:
        return RedirectResponse(url="/seo?error=No channel selected", status_code=303)

    try:
        count = score_all_videos(session, cid)
        msg = f"Scored {count} videos"
    except Exception as e:
        return RedirectResponse(url=f"/seo?error={str(e)}&channel_id={channel_id}", status_code=303)

    return RedirectResponse(url=f"/seo?message={msg}&channel_id={channel_id}", status_code=303)
