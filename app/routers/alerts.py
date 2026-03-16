from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel
from app.services.trend_alerts import detect_trends, get_trend_alerts, mark_alert_seen
from app.services.tag_analysis import analyze_competitor_tags

router = APIRouter(prefix="/alerts", tags=["alerts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def alerts_dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    channel_id = request.query_params.get("channel_id")
    show_seen = request.query_params.get("show_seen") == "1"

    selected_channel = None
    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    # Get trend alerts
    trend_alerts = get_trend_alerts(session, include_seen=show_seen)

    # Get tag analysis
    tag_data = None
    if selected_channel:
        tag_data = analyze_competitor_tags(session, selected_channel.id)

    return templates.TemplateResponse("alerts.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "trend_alerts": trend_alerts,
        "tag_data": tag_data,
        "show_seen": show_seen,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/detect")
def trigger_detection(request: Request, session: Session = Depends(get_session)):
    channel_id = request.query_params.get("channel_id")
    try:
        count = detect_trends(session)
        msg = f"Detected {count} new trend alerts"
    except Exception as e:
        redirect = f"/alerts?error={str(e)}"
        if channel_id:
            redirect += f"&channel_id={channel_id}"
        return RedirectResponse(url=redirect, status_code=303)

    redirect = f"/alerts?message={msg}"
    if channel_id:
        redirect += f"&channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/seen/{alert_id}")
def mark_seen(alert_id: int, request: Request, session: Session = Depends(get_session)):
    mark_alert_seen(session, alert_id)
    channel_id = request.query_params.get("channel_id")
    redirect = "/alerts"
    if channel_id:
        redirect += f"?channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)
