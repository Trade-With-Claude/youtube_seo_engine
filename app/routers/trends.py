from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Channel, Keyword
from app.services.autocomplete import get_youtube_suggestions
from app.services.keywords import extract_keywords_from_videos

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/trends")
def trends_page(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    keywords = session.exec(select(Keyword).order_by(Keyword.volume_proxy.desc())).all()

    # Get autocomplete results if a search query was submitted
    search_query = request.query_params.get("q", "")
    suggestions = []
    if search_query:
        suggestions = get_youtube_suggestions(search_query)

    return templates.TemplateResponse("trends.html", {
        "request": request,
        "channels": channels,
        "keywords": keywords[:100],
        "search_query": search_query,
        "suggestions": suggestions,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
    })


@router.post("/trends/extract-keywords/{channel_id}")
def extract_keywords(channel_id: int, session: Session = Depends(get_session)):
    channel = session.exec(select(Channel).where(Channel.id == channel_id)).first()
    if not channel:
        return RedirectResponse(url="/trends?error=Channel not found", status_code=303)

    count = extract_keywords_from_videos(session, channel_id)

    return RedirectResponse(
        url=f"/trends?message=Extracted {count} new keywords from '{channel.name}'",
        status_code=303,
    )


@router.get("/trends/search")
def search_autocomplete(request: Request, q: str = ""):
    """HTMX endpoint for live autocomplete search."""
    if not q or len(q) < 2:
        return templates.TemplateResponse("components/suggestions.html", {
            "request": request,
            "suggestions": [],
            "query": q,
        })

    suggestions = get_youtube_suggestions(q)
    return templates.TemplateResponse("components/suggestions.html", {
        "request": request,
        "suggestions": suggestions,
        "query": q,
    })
