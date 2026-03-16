from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel, OAuthToken, Video
from app.services.ab_testing import create_test, get_tests, swap_variant, record_metrics, complete_test

router = APIRouter(prefix="/ab", tags=["ab"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def ab_dashboard(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    channel_id = request.query_params.get("channel_id")

    selected_channel = None
    if channel_id:
        selected_channel = session.exec(
            select(Channel).where(Channel.id == int(channel_id))
        ).first()
    elif channels:
        selected_channel = channels[0]

    tests = []
    videos = []
    if selected_channel:
        tests = get_tests(session, selected_channel.id)
        videos = session.exec(
            select(Video).where(Video.channel_id == selected_channel.id)
        ).all()

    return templates.TemplateResponse("ab.html", {
        "request": request,
        "channels": channels,
        "selected_channel": selected_channel,
        "tests": tests,
        "videos": videos,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/create")
def create_ab_test(
    request: Request,
    video_id: int = Form(...),
    variant_a: str = Form(...),
    variant_b: str = Form(...),
    session: Session = Depends(get_session),
):
    channel_id = request.query_params.get("channel_id")

    if not variant_a.strip() or not variant_b.strip():
        redirect = f"/ab?error=Both variants are required"
        if channel_id:
            redirect += f"&channel_id={channel_id}"
        return RedirectResponse(url=redirect, status_code=303)

    try:
        test = create_test(session, video_id, "title", variant_a.strip(), variant_b.strip())
        msg = f"A/B test created (ID: {test.id})"
    except Exception as e:
        redirect = f"/ab?error={str(e)}"
        if channel_id:
            redirect += f"&channel_id={channel_id}"
        return RedirectResponse(url=redirect, status_code=303)

    redirect = f"/ab?message={msg}"
    if channel_id:
        redirect += f"&channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{test_id}/swap")
def swap_ab_variant(test_id: int, request: Request, session: Session = Depends(get_session)):
    channel_id = request.query_params.get("channel_id")

    # Get oauth token if available
    oauth_token = None
    if channel_id:
        oauth_token = session.exec(
            select(OAuthToken).where(OAuthToken.channel_id == int(channel_id))
        ).first()

    new_variant = swap_variant(session, test_id, oauth_token)
    msg = f"Swapped to variant {new_variant.upper()}"

    redirect = f"/ab?message={msg}"
    if channel_id:
        redirect += f"&channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)


@router.post("/{test_id}/complete")
def complete_ab_test(test_id: int, request: Request, session: Session = Depends(get_session)):
    channel_id = request.query_params.get("channel_id")

    # Try to record final metrics
    if channel_id:
        oauth_token = session.exec(
            select(OAuthToken).where(OAuthToken.channel_id == int(channel_id))
        ).first()
        if oauth_token:
            record_metrics(session, test_id, oauth_token)

    complete_test(session, test_id)
    msg = "Test completed"

    redirect = f"/ab?message={msg}"
    if channel_id:
        redirect += f"&channel_id={channel_id}"
    return RedirectResponse(url=redirect, status_code=303)
