import json
from collections import Counter

from sqlmodel import Session, select

from app.models import Channel, Competitor, Video


def analyze_competitor_tags(session: Session, channel_id: int) -> dict:
    """Extract and analyze tags from competitor videos vs your channel.

    Returns:
    - competitor_tags: {channel_name: {tag: count}} — most-used tags per competitor
    - your_tags: set of your channel's tags
    - overlap: tags both you and competitors use
    - gaps: tags competitors use that you don't (sorted by frequency)
    - your_unique: tags you use that competitors don't
    - overlap_percentage: how much your tags overlap with competitor tags
    """
    # Get your channel's tags
    your_videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()
    your_tags = _extract_tags_from_videos(your_videos)

    # Get competitors
    competitors = session.exec(
        select(Competitor).where(Competitor.source_channel_id == channel_id)
    ).all()

    if not competitors:
        return {
            "competitor_tags": {},
            "your_tags": your_tags,
            "overlap": set(),
            "gaps": [],
            "your_unique": your_tags,
            "overlap_percentage": 0,
            "has_data": False,
        }

    # Collect tags per competitor
    competitor_tags = {}
    all_competitor_tags = Counter()

    for comp in competitors:
        channel = session.exec(
            select(Channel).where(Channel.id == comp.competitor_channel_id)
        ).first()
        if not channel:
            continue

        videos = session.exec(
            select(Video).where(Video.channel_id == channel.id)
        ).all()

        channel_tags = _extract_tags_from_videos(videos)
        if channel_tags:
            tag_counts = Counter(channel_tags)
            competitor_tags[channel.name] = dict(tag_counts.most_common(20))
            all_competitor_tags.update(channel_tags)

    # Calculate overlap and gaps
    all_comp_tag_set = set(all_competitor_tags.keys())
    overlap = your_tags & all_comp_tag_set
    gaps = all_comp_tag_set - your_tags
    your_unique = your_tags - all_comp_tag_set

    # Sort gaps by competitor frequency (most used first)
    gaps_sorted = sorted(
        [(tag, all_competitor_tags[tag]) for tag in gaps],
        key=lambda x: -x[1]
    )

    # Overlap percentage
    if all_comp_tag_set:
        overlap_pct = round(len(overlap) / len(all_comp_tag_set) * 100, 1)
    else:
        overlap_pct = 0

    return {
        "competitor_tags": competitor_tags,
        "your_tags": your_tags,
        "overlap": overlap,
        "gaps": gaps_sorted[:30],  # Top 30 missing tags
        "your_unique": your_unique,
        "overlap_percentage": overlap_pct,
        "has_data": bool(competitor_tags),
    }


def _extract_tags_from_videos(videos: list) -> set:
    """Extract unique lowercase tags from a list of videos."""
    tags = set()
    for video in videos:
        if not video.tags:
            continue
        try:
            tag_list = json.loads(video.tags) if video.tags.startswith("[") else [t.strip() for t in video.tags.split(",")]
        except (json.JSONDecodeError, ValueError):
            tag_list = []

        for tag in tag_list:
            clean = tag.strip().lower()
            if clean and len(clean) > 1:
                tags.add(clean)

    return tags
