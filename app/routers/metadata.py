from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel, MetadataTemplate, Video
from app.services.metadata import generate_metadata, get_saved_metadata
from app.services.title_tester import test_title

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/metadata")
def metadata_page(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel).where(Channel.is_own == True)).all()
    if not channels:
        channels = session.exec(select(Channel)).all()

    selected_channel = channels[0] if channels else None
    current = []
    favorites = []

    if selected_channel:
        all_items = get_saved_metadata(session, selected_channel.id)
        favorites = [s for s in all_items if s.get("saved")]
        current = [s for s in all_items if not s.get("saved")]

    # Check for title test results in query params
    test_result = None
    test_title_q = request.query_params.get("test_title", "")

    return templates.TemplateResponse("metadata.html", {
        "request": request,
        "selected_channel": selected_channel,
        "current": current,
        "favorites": favorites,
        "test_title": test_title_q,
        "test_result": test_result,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/metadata/test-title/{channel_id}")
def test_title_route(
    channel_id: int,
    request: Request,
    title: str = Form(...),
    session: Session = Depends(get_session),
):
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if not channel:
        return RedirectResponse(url="/metadata?error=Channel not found", status_code=303)

    my_videos = session.exec(select(Video).where(Video.channel_id == channel_id)).all()
    my_avg_views = 1
    if my_videos:
        my_avg_views = max(sum(v.views for v in my_videos) // len(my_videos), 1)

    try:
        result = test_title(title, channel.subscriber_count, my_avg_views)
    except Exception as e:
        error = str(e)[:200]
        if "403" in error or "quota" in error.lower() or "exceeded" in error.lower():
            error = "YouTube API quota exceeded for today. Try again tomorrow (quota resets at midnight Pacific Time)."
        elif "forbidden" in error.lower() or "key" in error.lower():
            error = "YouTube API key invalid or missing. Check your .env file."
        else:
            error = f"Could not test title: {error}"
        return RedirectResponse(url=f"/metadata?error={error}", status_code=303)

    all_items = get_saved_metadata(session, channel_id)
    favorites = [s for s in all_items if s.get("saved")]
    current = [s for s in all_items if not s.get("saved")]

    return templates.TemplateResponse("metadata.html", {
        "request": request,
        "selected_channel": channel,
        "current": current,
        "favorites": favorites,
        "test_title": title,
        "test_result": result,
        "message": None,
        "error": None,
    })


@router.post("/metadata/generate/{channel_id}")
def generate(channel_id: int, session: Session = Depends(get_session)):
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if not channel:
        return RedirectResponse(url="/metadata?error=Channel not found", status_code=303)

    # Clear all unsaved suggestions first
    unsaved = session.exec(
        select(MetadataTemplate).where(
            MetadataTemplate.channel_id == channel_id,
            MetadataTemplate.saved == False,
        )
    ).all()
    for mt in unsaved:
        session.delete(mt)
    session.commit()

    # Generate fresh batch
    results = generate_metadata(session, channel_id)

    if not results:
        return RedirectResponse(
            url="/metadata?error=No scored keywords yet. Go to Trends and click 'Score Keywords' first.",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/metadata?message=Generated {len(results)} new title ideas",
        status_code=303,
    )


@router.post("/metadata/save/{template_id}")
def save_to_favorites(template_id: int, session: Session = Depends(get_session)):
    mt = session.exec(
        select(MetadataTemplate).where(MetadataTemplate.id == template_id)
    ).first()
    if mt:
        mt.saved = True
        session.commit()
    return RedirectResponse(url="/metadata", status_code=303)


@router.post("/metadata/unsave/{template_id}")
def remove_from_favorites(template_id: int, session: Session = Depends(get_session)):
    mt = session.exec(
        select(MetadataTemplate).where(MetadataTemplate.id == template_id)
    ).first()
    if mt:
        mt.saved = False
        session.commit()
    return RedirectResponse(url="/metadata", status_code=303)


@router.post("/metadata/delete/{template_id}")
def delete_suggestion(template_id: int, session: Session = Depends(get_session)):
    mt = session.exec(
        select(MetadataTemplate).where(MetadataTemplate.id == template_id)
    ).first()
    if mt:
        session.delete(mt)
        session.commit()
    return RedirectResponse(url="/metadata", status_code=303)
