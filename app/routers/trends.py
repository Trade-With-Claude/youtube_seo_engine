from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, col

from app.database import get_session
from app.models import AutocompleteSnapshot, Channel, Keyword
from app.services.autocomplete import get_youtube_suggestions
from app.services.keywords import extract_keywords_from_videos
from app.services.trends import get_interest_over_time

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/trends")
def trends_page(request: Request, session: Session = Depends(get_session)):
    channels = session.exec(select(Channel)).all()
    keywords = session.exec(
        select(Keyword).order_by(col(Keyword.volume_proxy).desc())
    ).all()

    search_query = request.query_params.get("q", "")
    suggestions = []
    trends_data = None

    if search_query:
        # Get YouTube autocomplete suggestions
        suggestions = get_youtube_suggestions(search_query)

        # Save autocomplete snapshot for tracking
        if suggestions:
            _save_snapshot(session, search_query, suggestions)

        # Get Google Trends data
        trends_data = get_interest_over_time(search_query)

    # Get trend indicators for keywords
    keyword_trends = _get_keyword_trends(session, keywords[:100])

    return templates.TemplateResponse("trends.html", {
        "request": request,
        "channels": channels,
        "keywords": keywords[:100],
        "keyword_trends": keyword_trends,
        "search_query": search_query,
        "suggestions": suggestions,
        "trends_data": trends_data,
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


def _save_snapshot(session: Session, query: str, suggestions: list[str]):
    """Save autocomplete suggestions as a snapshot for trend tracking."""
    for i, suggestion in enumerate(suggestions):
        snapshot = AutocompleteSnapshot(
            query=query,
            suggestion=suggestion,
            position=i + 1,
        )
        session.add(snapshot)
    session.commit()


def _get_keyword_trends(session: Session, keywords: list[Keyword]) -> dict[int, str]:
    """Determine rising/falling/stable for keywords based on autocomplete snapshots.
    Returns a dict of keyword_id -> trend direction."""
    trends = {}
    for kw in keywords:
        # Get latest two snapshots for this keyword
        snapshots = session.exec(
            select(AutocompleteSnapshot)
            .where(AutocompleteSnapshot.query == kw.term)
            .order_by(col(AutocompleteSnapshot.snapshot_date).desc())
            .limit(20)
        ).all()

        if len(snapshots) < 2:
            trends[kw.id] = "unknown"
            continue

        # Compare position across snapshots — lower position = more popular
        recent_positions = [s.position for s in snapshots[:10]]
        older_positions = [s.position for s in snapshots[10:]]

        if not older_positions:
            trends[kw.id] = "unknown"
            continue

        avg_recent = sum(recent_positions) / len(recent_positions)
        avg_older = sum(older_positions) / len(older_positions)

        if avg_recent < avg_older - 1:
            trends[kw.id] = "rising"
        elif avg_recent > avg_older + 1:
            trends[kw.id] = "falling"
        else:
            trends[kw.id] = "stable"

    return trends
