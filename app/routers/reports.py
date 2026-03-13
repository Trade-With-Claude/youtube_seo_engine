from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.services.reports import generate_niche_report, generate_video_suggestions

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/report")
def report_page(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel).where(Channel.is_own == True)).all()
    if not channels:
        channels = session.exec(select(Channel)).all()

    selected_channel = channels[0] if channels else None
    report = None
    video_suggestions = []

    if selected_channel:
        report = generate_niche_report(session, selected_channel.id)
        video_suggestions = generate_video_suggestions(session, selected_channel.id)

    return templates.TemplateResponse("report.html", {
        "request": request,
        "selected_channel": selected_channel,
        "report": report,
        "video_suggestions": video_suggestions,
    })
