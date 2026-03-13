import json
import random
from datetime import datetime

from sqlmodel import Session, select, col

from app.models import (
    Channel,
    Keyword,
    KeywordScore,
    MetadataTemplate,
    Video,
)

# Title templates — {primary}, {secondary}, {tertiary} get replaced with keywords
_TITLE_TEMPLATES = [
    "{primary} | {secondary} for Deep Focus",
    "{primary}: {secondary} & {tertiary}",
    "{primary} — {secondary} for Relaxation & Focus",
    "{secondary} with {primary} | {tertiary}",
    "{primary} for {secondary} | Deep {tertiary}",
    "{primary} | {secondary} — Powerful {tertiary}",
    "{secondary} & {primary}: {tertiary} Session",
    "Deep {primary} | {secondary} for {tertiary}",
    "{primary} Music for {secondary} & {tertiary}",
    "{primary} | {secondary} — Release {tertiary}",
    "{secondary}: {primary} for Deep {tertiary}",
    "{primary} & {secondary} | Calm {tertiary}",
]


def generate_metadata(session: Session, channel_id: int) -> list[dict]:
    """Generate fresh title, description, and tags suggestions.
    Each click gives different combinations by shuffling keywords and templates."""

    channel = session.exec(
        select(Channel).where(Channel.id == channel_id)
    ).first()
    if not channel:
        return []

    # Get scored keywords — ONLY those with real competition data
    # (keywords with competition=0 were never analyzed and would pollute results)
    analyzed_keyword_ids = [
        kw.id for kw in session.exec(
            select(Keyword).where(Keyword.competition > 0.0)
        ).all()
    ]

    if not analyzed_keyword_ids:
        return []

    top_scores = session.exec(
        select(KeywordScore)
        .where(
            KeywordScore.channel_id == channel_id,
            KeywordScore.keyword_id.in_(analyzed_keyword_ids),
        )
        .order_by(col(KeywordScore.score).desc())
        .limit(20)
    ).all()

    if not top_scores:
        return []

    top_keywords = []
    for ks in top_scores:
        kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
        if kw:
            top_keywords.append({"keyword": kw, "score": ks})

    if len(top_keywords) < 3:
        return []

    # Get traffic data to know what actually works
    traffic_winners = _get_traffic_winners(session, channel_id)

    # Get existing titles to avoid duplicates
    existing_titles = set()
    existing = session.exec(
        select(MetadataTemplate).where(MetadataTemplate.channel_id == channel_id)
    ).all()
    for mt in existing:
        existing_titles.add(mt.suggested_title.lower())

    # Generate 5 unique suggestions
    suggestions = []
    attempts = 0
    max_attempts = 30

    while len(suggestions) < 5 and attempts < max_attempts:
        attempts += 1
        s = _generate_one_title(top_keywords, traffic_winners)
        if s and s["title"].lower() not in existing_titles:
            existing_titles.add(s["title"].lower())
            suggestions.append(s)

    # Save to DB
    for s in suggestions:
        mt = MetadataTemplate(
            channel_id=channel_id,
            keyword_id=s.get("primary_keyword_id"),
            suggested_title=s["title"],
            suggested_description=s["description"],
            suggested_tags=json.dumps(s["tags"]),
        )
        session.add(mt)

    session.commit()
    return suggestions


def _generate_one_title(top_keywords: list[dict], traffic_winners: list[str]) -> dict | None:
    """Generate a single title by picking random keywords and a random template."""

    # Pick 3 keywords with weighted randomness (higher score = more likely)
    weights = [item["score"].score for item in top_keywords]
    total = sum(weights)
    if total == 0:
        return None
    weights = [w / total for w in weights]

    picked_indices = set()
    picked = []
    for _ in range(3):
        for _ in range(20):  # retry to get unique picks
            idx = random.choices(range(len(top_keywords)), weights=weights, k=1)[0]
            if idx not in picked_indices:
                picked_indices.add(idx)
                picked.append(top_keywords[idx])
                break

    if len(picked) < 3:
        picked = random.sample(top_keywords, min(3, len(top_keywords)))

    primary = picked[0]["keyword"].term.title()
    secondary = picked[1]["keyword"].term.title()
    tertiary = picked[2]["keyword"].term.title()

    # Pick a random template
    template = random.choice(_TITLE_TEMPLATES)
    title = template.format(primary=primary, secondary=secondary, tertiary=tertiary)

    # Boost: if a traffic winner isn't in the title yet, try to include it
    if traffic_winners:
        winner = random.choice(traffic_winners[:5])
        if winner.lower() not in title.lower() and len(title) < 50:
            title = f"{title} | {winner.title()}"

    # Trim if too long
    if len(title) > 70:
        title = title[:67].rsplit(" ", 1)[0] + "..."

    # Build description and tags
    all_terms = [picked[i]["keyword"].term for i in range(len(picked))]
    description = _build_description(all_terms, traffic_winners)
    tags = _build_tags(all_terms, [item["keyword"].term for item in top_keywords])

    # Determine strategy label
    scores = [picked[i]["score"] for i in range(len(picked))]
    avg_beatable = sum(s.competition_component for s in scores) / len(scores)
    avg_demand = sum(s.volume_component for s in scores) / len(scores)

    if avg_beatable > 0.6:
        strategy = "Easy to Rank"
    elif avg_demand > 0.3:
        strategy = "High Demand"
    else:
        strategy = "Niche Opportunity"

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "primary_keyword_id": picked[0]["keyword"].id,
        "strategy": strategy,
    }


def _get_traffic_winners(session: Session, channel_id: int) -> list[str]:
    """Get keywords that actually drive the most views on this channel."""
    videos = session.exec(
        select(Video)
        .where(Video.channel_id == channel_id)
        .order_by(col(Video.views).desc())
        .limit(5)
    ).all()

    # Extract common words from top-performing video titles
    word_views = {}
    for v in videos:
        words = v.title.lower().split()
        for w in words:
            clean = w.strip(".,!?()[]\"'|—:-")
            if len(clean) > 3:
                word_views[clean] = word_views.get(clean, 0) + v.views

    sorted_words = sorted(word_views.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:10]]


def get_saved_metadata(session: Session, channel_id: int) -> list[dict]:
    """Get all saved metadata suggestions for a channel."""
    templates = session.exec(
        select(MetadataTemplate)
        .where(MetadataTemplate.channel_id == channel_id)
        .order_by(col(MetadataTemplate.created_at).desc())
    ).all()

    results = []
    for mt in templates:
        keyword = None
        if mt.keyword_id:
            keyword = session.exec(
                select(Keyword).where(Keyword.id == mt.keyword_id)
            ).first()

        tags = []
        if mt.suggested_tags:
            try:
                tags = json.loads(mt.suggested_tags)
            except json.JSONDecodeError:
                tags = []

        results.append({
            "id": mt.id,
            "title": mt.suggested_title,
            "description": mt.suggested_description,
            "tags": tags,
            "keyword": keyword,
            "saved": mt.saved,
            "created_at": mt.created_at,
        })

    return results


def _build_description(main_terms: list[str], traffic_winners: list[str]) -> str:
    """Build a YouTube description optimized for SEO."""
    all_terms = list(dict.fromkeys(main_terms + traffic_winners[:3]))
    keyword_text = ", ".join(t.lower() for t in all_terms[:6])

    return (
        f"Discover {main_terms[0].lower()} designed to help you focus, relax, and find calm. "
        f"This session features {keyword_text}.\n\n"
        f"Perfect for deep work, study sessions, meditation, or simply unwinding after a long day.\n\n"
        f"Keywords: {keyword_text}\n\n"
        f"#{'  #'.join(t.replace(' ', '') for t in all_terms[:8])}"
    )


def _build_tags(main_terms: list[str], all_keyword_terms: list[str]) -> list[str]:
    """Build a tag list optimized for YouTube SEO (max 500 chars total)."""
    tags = []
    for t in main_terms + all_keyword_terms:
        tag = t.lower()
        if tag not in tags:
            tags.append(tag)

    total = 0
    trimmed = []
    for tag in tags:
        if total + len(tag) + 1 > 480:
            break
        trimmed.append(tag)
        total += len(tag) + 1

    return trimmed
