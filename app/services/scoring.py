import math
from datetime import datetime

from googleapiclient.discovery import build
from sqlmodel import Session, select, col

from app.config import settings
from app.models import Channel, Keyword, KeywordScore, Video


def get_youtube_service():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def score_keywords(session: Session, channel_id: int) -> int:
    """Score keywords relative to YOUR channel.

    For each keyword, searches YouTube and analyzes the top 5 ranking videos:
    - How big are the channels ranking for this? (subscriber comparison)
    - How many views do the top results get? (demand signal)
    - Can YOUR channel realistically compete? (size ratio)

    Formula:
      opportunity = (demand × 0.3) + (beatable × 0.4) + (affinity × 0.3)

    Where:
      demand    = normalized search volume (how many people search this)
      beatable  = how weak the current competition is relative to YOUR channel
      affinity  = how well this keyword fits your existing content

    Costs ~200 quota units per keyword (1 search.list + 1 videos.list batch).
    Capped at 30 keywords per run (~6,000 units).
    Returns number of keywords scored."""

    channel = session.exec(
        select(Channel).where(Channel.id == channel_id)
    ).first()
    if not channel:
        return 0

    keywords = session.exec(select(Keyword)).all()
    if not keywords:
        return 0

    youtube = get_youtube_service()

    # Your channel stats — the baseline
    my_subs = max(channel.subscriber_count, 1)
    my_videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()
    my_avg_views = 1
    if my_videos:
        total_views = sum(v.views for v in my_videos)
        my_avg_views = max(total_views // len(my_videos), 1)

    # Only analyze keywords that haven't been scored yet (competition == 0)
    needs_analysis = [kw for kw in keywords if kw.competition == 0.0]
    already_scored = [kw for kw in keywords if kw.competition > 0.0]

    # Cap at 30 per run to save quota
    needs_analysis = needs_analysis[:30]

    # Analyze competition for each keyword
    for kw in needs_analysis:
        comp_data = _analyze_search_results(youtube, kw.term, my_subs, my_avg_views)
        kw.competition = round(comp_data["competition"], 4)
        kw.updated_at = datetime.utcnow()

    if needs_analysis:
        session.commit()

    # Only score keywords that have real competition data
    keywords = session.exec(
        select(Keyword).where(Keyword.competition > 0.0)
    ).all()
    if not keywords:
        return 0

    # Normalize volume
    max_volume = max(kw.volume_proxy for kw in keywords) if keywords else 1
    if max_volume == 0:
        max_volume = 1

    channel_terms = _get_channel_keyword_set(session, channel_id)

    scored = 0
    for kw in keywords:
        demand = kw.volume_proxy / max_volume
        beatable = 1.0 - min(kw.competition, 1.0)
        affinity = _calculate_affinity(kw.term, channel_terms)

        opportunity = (demand * 0.3) + (beatable * 0.4) + (affinity * 0.3)

        # Upsert
        existing = session.exec(
            select(KeywordScore).where(
                KeywordScore.keyword_id == kw.id,
                KeywordScore.channel_id == channel_id,
            )
        ).first()

        if existing:
            existing.score = round(opportunity, 4)
            existing.volume_component = round(demand, 4)
            existing.competition_component = round(beatable, 4)
            existing.affinity = round(affinity, 4)
            existing.scored_at = datetime.utcnow()
        else:
            ks = KeywordScore(
                keyword_id=kw.id,
                channel_id=channel_id,
                score=round(opportunity, 4),
                volume_component=round(demand, 4),
                competition_component=round(beatable, 4),
                affinity=round(affinity, 4),
            )
            session.add(ks)

        scored += 1

    session.commit()
    return scored


def _analyze_search_results(youtube, keyword: str, my_subs: int, my_avg_views: int) -> dict:
    """Search YouTube for a keyword and analyze who's ranking.

    Returns competition as 0-1 where:
      0 = tiny channels ranking, you can easily beat them
      1 = huge channels dominating, very hard to compete

    Logic:
    - Search top 5 videos for this keyword
    - Get their channel subscriber counts and view counts
    - Compare their avg subs to YOUR subs
    - Compare their avg views to YOUR avg views
    - If the top results are from channels your size or smaller → low competition
    - If the top results are from channels 100x your size → high competition
    """
    try:
        # Step 1: Search for videos (100 quota units)
        search_resp = youtube.search().list(
            part="snippet",
            q=keyword,
            type="video",
            maxResults=5,
            relevanceLanguage="en",
        ).execute()

        items = search_resp.get("items", [])
        if not items:
            return {"competition": 0.5}

        # Collect video IDs and channel IDs
        video_ids = [item["id"]["videoId"] for item in items]
        channel_ids = list(set(item["snippet"]["channelId"] for item in items))

        # Step 2: Get video stats (1 quota unit — batch)
        videos_resp = youtube.videos().list(
            part="statistics",
            id=",".join(video_ids),
        ).execute()

        competitor_views = []
        for v in videos_resp.get("items", []):
            stats = v.get("statistics", {})
            competitor_views.append(int(stats.get("viewCount", 0)))

        # Step 3: Get channel stats (1 quota unit — batch)
        channels_resp = youtube.channels().list(
            part="statistics",
            id=",".join(channel_ids),
        ).execute()

        competitor_subs = []
        for ch in channels_resp.get("items", []):
            stats = ch.get("statistics", {})
            competitor_subs.append(int(stats.get("subscriberCount", 0)))

        if not competitor_subs:
            return {"competition": 0.5}

        # Calculate competition relative to MY channel
        avg_comp_subs = sum(competitor_subs) / len(competitor_subs)
        avg_comp_views = sum(competitor_views) / len(competitor_views) if competitor_views else 0

        # Sub ratio: how much bigger are competitors vs me?
        # ratio = 1 means same size, ratio = 100 means they're 100x bigger
        sub_ratio = avg_comp_subs / my_subs

        # View ratio: how many views do their videos get vs mine?
        view_ratio = avg_comp_views / my_avg_views if my_avg_views > 0 else 1

        # Convert ratios to 0-1 competition score using log scale
        # log10(1) = 0 → same size = 0.0 competition
        # log10(10) = 1 → 10x bigger = moderate
        # log10(100) = 2 → 100x bigger = high
        # log10(1000) = 3 → 1000x bigger = very high
        # We cap at log10(10000) = 4

        sub_score = min(math.log10(max(sub_ratio, 1)) / 4, 1.0)
        view_score = min(math.log10(max(view_ratio, 1)) / 4, 1.0)

        # Blend: subscribers matter more (they indicate channel authority)
        competition = (sub_score * 0.6) + (view_score * 0.4)

        return {"competition": min(competition, 1.0)}

    except Exception:
        return {"competition": 0.5}


def get_scored_keywords(session: Session, channel_id: int) -> list[dict]:
    """Get all scored keywords for a channel, sorted by opportunity (highest score first)."""
    scores = session.exec(
        select(KeywordScore)
        .where(KeywordScore.channel_id == channel_id)
        .order_by(col(KeywordScore.score).desc())
    ).all()

    results = []
    for ks in scores:
        keyword = session.exec(
            select(Keyword).where(Keyword.id == ks.keyword_id)
        ).first()
        if keyword:
            # Difficulty label based on competition component
            # competition_component is (1 - competition), so higher = easier
            if ks.competition_component >= 0.6:
                difficulty = "Easy"
            elif ks.competition_component >= 0.3:
                difficulty = "Medium"
            else:
                difficulty = "Hard"

            results.append({
                "keyword": keyword,
                "score": ks,
                "difficulty": difficulty,
            })

    return results


def _get_channel_keyword_set(session: Session, channel_id: int) -> set[str]:
    """Build a set of terms that appear in the channel's video titles, tags, descriptions."""
    videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()

    terms = set()
    for v in videos:
        for word in v.title.lower().split():
            word = word.strip(".,!?()[]\"'")
            if len(word) > 2:
                terms.add(word)
        for tag in v.tags.split(","):
            tag = tag.strip().lower()
            if tag:
                terms.add(tag)

    return terms


def _calculate_affinity(keyword_term: str, channel_terms: set[str]) -> float:
    """Calculate how closely a keyword relates to the channel's existing content.
    Returns 0.0-1.0 based on word overlap."""
    if not channel_terms:
        return 0.5

    words = keyword_term.lower().split()
    if not words:
        return 0.0

    matches = sum(1 for w in words if w in channel_terms)
    return matches / len(words)
