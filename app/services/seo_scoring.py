import json
from datetime import datetime

from sqlmodel import Session, select, col

from app.models import Channel, Keyword, KeywordScore, SeoScore, Video


def score_video_seo(session: Session, video_id: int) -> dict | None:
    """Score a video's SEO optimization on a 0-100 scale.
    Grades title, description, and tags individually with actionable recommendations."""

    video = session.exec(select(Video).where(Video.id == video_id)).first()
    if not video:
        return None

    # Get channel keywords for relevance checking
    channel_keywords = _get_channel_keywords(session, video.channel_id)

    title_result = _score_title(video.title, channel_keywords)
    desc_result = _score_description(video.description, channel_keywords)
    tags_result = _score_tags(video.tags, channel_keywords)

    # Weighted overall: title 40%, description 30%, tags 30%
    overall = (title_result["score"] * 0.4) + (desc_result["score"] * 0.3) + (tags_result["score"] * 0.3)
    overall = round(overall, 1)

    recommendations = title_result["recommendations"] + desc_result["recommendations"] + tags_result["recommendations"]

    # Upsert score
    existing = session.exec(
        select(SeoScore).where(SeoScore.video_id == video_id)
    ).first()

    if existing:
        existing.score = overall
        existing.title_score = title_result["score"]
        existing.description_score = desc_result["score"]
        existing.tags_score = tags_result["score"]
        existing.recommendations = json.dumps(recommendations)
        existing.scored_at = datetime.utcnow()
    else:
        seo_score = SeoScore(
            video_id=video_id,
            score=overall,
            title_score=title_result["score"],
            description_score=desc_result["score"],
            tags_score=tags_result["score"],
            recommendations=json.dumps(recommendations),
        )
        session.add(seo_score)

    session.commit()

    return {
        "video": video,
        "overall": overall,
        "title_score": title_result["score"],
        "description_score": desc_result["score"],
        "tags_score": tags_result["score"],
        "recommendations": recommendations,
    }


def score_all_videos(session: Session, channel_id: int) -> int:
    """Score all videos for a channel. Returns count of videos scored."""
    videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()

    count = 0
    for video in videos:
        result = score_video_seo(session, video.id)
        if result:
            count += 1

    return count


def get_seo_scores(session: Session, channel_id: int) -> list[dict]:
    """Get all SEO scores for a channel's videos, sorted by score ascending (worst first)."""
    videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()

    results = []
    for video in videos:
        seo_score = session.exec(
            select(SeoScore).where(SeoScore.video_id == video.id)
        ).first()

        recommendations = []
        if seo_score and seo_score.recommendations:
            try:
                recommendations = json.loads(seo_score.recommendations)
            except json.JSONDecodeError:
                pass

        results.append({
            "video": video,
            "seo_score": seo_score,
            "recommendations": recommendations,
        })

    # Sort: scored videos first (worst score first), then unscored
    results.sort(key=lambda x: x["seo_score"].score if x["seo_score"] else 999)
    return results


def _get_channel_keywords(session: Session, channel_id: int) -> list[str]:
    """Get top keyword terms for the channel."""
    scores = session.exec(
        select(KeywordScore)
        .where(KeywordScore.channel_id == channel_id)
        .order_by(col(KeywordScore.score).desc())
        .limit(30)
    ).all()

    terms = []
    for ks in scores:
        kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
        if kw:
            terms.append(kw.term.lower())

    return terms


def _score_title(title: str, keywords: list[str]) -> dict:
    """Score title on 0-100. Checks length, keyword presence, power words."""
    score = 0.0
    recommendations = []
    title_lower = title.lower()

    # Length (0-30 points)
    length = len(title)
    if 40 <= length <= 60:
        score += 30  # ideal
    elif 30 <= length <= 70:
        score += 20
    elif length > 0:
        score += 10
    if length < 30:
        recommendations.append({"area": "title", "priority": "high", "tip": f"Title is too short ({length} chars). Aim for 40-60 characters."})
    elif length > 70:
        recommendations.append({"area": "title", "priority": "medium", "tip": f"Title is long ({length} chars). YouTube may truncate it. Aim for under 60."})

    # Keyword presence (0-40 points)
    keyword_hits = 0
    for kw in keywords[:10]:
        if kw in title_lower:
            keyword_hits += 1
    if keyword_hits >= 3:
        score += 40
    elif keyword_hits >= 2:
        score += 30
    elif keyword_hits >= 1:
        score += 20
    else:
        score += 0
        if keywords:
            recommendations.append({"area": "title", "priority": "high", "tip": f"No tracked keywords found in title. Consider adding: {', '.join(keywords[:3])}"})

    if keyword_hits == 1:
        recommendations.append({"area": "title", "priority": "medium", "tip": f"Only 1 keyword in title. Try to include 2-3 relevant terms."})

    # Power words / engagement (0-15 points)
    power_words = ["best", "ultimate", "powerful", "deep", "intense", "calm", "relaxing",
                   "focus", "study", "sleep", "healing", "meditation", "hours", "hz"]
    power_hits = sum(1 for w in power_words if w in title_lower)
    if power_hits >= 2:
        score += 15
    elif power_hits >= 1:
        score += 10
    else:
        recommendations.append({"area": "title", "priority": "low", "tip": "Consider adding a power word (deep, powerful, calm, healing) to boost CTR."})

    # Separator usage (0-15 points) — pipes, dashes, colons help readability
    if "|" in title or "—" in title or ":" in title or "-" in title:
        score += 15
    else:
        recommendations.append({"area": "title", "priority": "low", "tip": "Use separators (|, —, :) to improve readability."})

    return {"score": min(score, 100), "recommendations": recommendations}


def _score_description(description: str, keywords: list[str]) -> dict:
    """Score description on 0-100. Checks length, keyword usage, structure."""
    score = 0.0
    recommendations = []
    desc_lower = description.lower()

    # Length (0-35 points)
    length = len(description)
    if length >= 500:
        score += 35
    elif length >= 200:
        score += 25
    elif length >= 50:
        score += 15
    elif length > 0:
        score += 5
    else:
        score += 0

    if length < 200:
        recommendations.append({"area": "description", "priority": "high", "tip": f"Description is too short ({length} chars). Aim for 500+ characters with keywords naturally woven in."})
    elif length < 500:
        recommendations.append({"area": "description", "priority": "medium", "tip": f"Description could be longer ({length} chars). 500+ chars helps YouTube understand your content."})

    # Keyword presence (0-35 points)
    keyword_hits = 0
    for kw in keywords[:10]:
        if kw in desc_lower:
            keyword_hits += 1
    if keyword_hits >= 4:
        score += 35
    elif keyword_hits >= 2:
        score += 25
    elif keyword_hits >= 1:
        score += 15
    else:
        if keywords:
            recommendations.append({"area": "description", "priority": "high", "tip": f"No tracked keywords in description. Include: {', '.join(keywords[:3])}"})

    # First 150 chars matter most (YouTube shows this in search)
    first_150 = desc_lower[:150]
    first_keyword_hit = any(kw in first_150 for kw in keywords[:5])
    if first_keyword_hit:
        score += 10
    else:
        if keywords:
            recommendations.append({"area": "description", "priority": "medium", "tip": "Put your main keyword in the first 1-2 sentences — YouTube shows this in search results."})

    # Hashtags (0-10 points)
    if "#" in description:
        score += 10
    else:
        recommendations.append({"area": "description", "priority": "low", "tip": "Add 3-5 hashtags at the end of your description."})

    # Links / timestamps (0-10 points)
    has_links = "http" in desc_lower or "www" in desc_lower
    has_timestamps = any(c.isdigit() and ":" in description for c in description)
    if has_links or has_timestamps:
        score += 10
    else:
        recommendations.append({"area": "description", "priority": "low", "tip": "Add timestamps or links to boost engagement signals."})

    return {"score": min(score, 100), "recommendations": recommendations}


def _score_tags(tags_str: str, keywords: list[str]) -> dict:
    """Score tags on 0-100. Checks count, relevance, variety."""
    score = 0.0
    recommendations = []

    # Parse tags
    try:
        tags = json.loads(tags_str) if tags_str.startswith("[") else [t.strip() for t in tags_str.split(",") if t.strip()]
    except (json.JSONDecodeError, ValueError):
        tags = []

    tag_count = len(tags)
    tags_lower = [t.lower() for t in tags]

    # Count (0-35 points)
    if tag_count >= 10:
        score += 35
    elif tag_count >= 5:
        score += 25
    elif tag_count >= 1:
        score += 15
    else:
        score += 0

    if tag_count == 0:
        recommendations.append({"area": "tags", "priority": "high", "tip": "No tags! Add 10-15 relevant tags to help YouTube categorize your video."})
    elif tag_count < 5:
        recommendations.append({"area": "tags", "priority": "high", "tip": f"Only {tag_count} tags. Aim for 10-15 tags covering your main topics."})
    elif tag_count < 10:
        recommendations.append({"area": "tags", "priority": "medium", "tip": f"{tag_count} tags is decent. Try to reach 10-15 for better coverage."})

    # Keyword overlap (0-40 points)
    overlap = 0
    for kw in keywords[:10]:
        if any(kw in t for t in tags_lower):
            overlap += 1
    if overlap >= 4:
        score += 40
    elif overlap >= 2:
        score += 25
    elif overlap >= 1:
        score += 15
    else:
        if keywords:
            recommendations.append({"area": "tags", "priority": "high", "tip": f"Tags don't match your tracked keywords. Add: {', '.join(keywords[:3])}"})

    # Tag length variety (0-15 points) — mix of short and long-tail
    short_tags = [t for t in tags if len(t.split()) <= 2]
    long_tags = [t for t in tags if len(t.split()) >= 3]
    if short_tags and long_tags:
        score += 15
    elif tags:
        score += 8
        if not long_tags:
            recommendations.append({"area": "tags", "priority": "medium", "tip": "Add some long-tail tags (3+ words) like 'binaural beats for studying'."})

    # Total characters (0-10 points) — YouTube allows 500 chars
    total_chars = sum(len(t) for t in tags)
    if total_chars >= 300:
        score += 10
    elif total_chars >= 100:
        score += 5
    else:
        if tag_count > 0:
            recommendations.append({"area": "tags", "priority": "low", "tip": f"Only using {total_chars}/500 tag characters. You have room for more tags."})

    return {"score": min(score, 100), "recommendations": recommendations}
