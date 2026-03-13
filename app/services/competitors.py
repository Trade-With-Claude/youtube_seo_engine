from datetime import datetime

from googleapiclient.discovery import build
from sqlmodel import Session, select

from app.config import settings
from app.models import Channel, Competitor, Keyword, Video


def get_youtube_service():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def discover_competitors(session: Session, channel_id: int, max_keywords: int = 5) -> int:
    """Discover competitor channels by searching YouTube for the channel's top keywords.
    Returns the number of new competitors found."""
    youtube = get_youtube_service()

    # Get top keywords for this channel
    keywords = session.exec(
        select(Keyword).order_by(Keyword.volume_proxy.desc()).limit(max_keywords)
    ).all()

    if not keywords:
        return 0

    # Get the source channel to exclude it
    source_channel = session.exec(
        select(Channel).where(Channel.id == channel_id)
    ).first()
    if not source_channel:
        return 0

    discovered_channel_ids = set()
    count = 0

    for kw in keywords:
        # Search YouTube for channels matching this keyword
        # Each search.list costs 100 quota units — limit to top keywords
        try:
            response = youtube.search().list(
                part="snippet",
                q=kw.term,
                type="channel",
                maxResults=5,
                relevanceLanguage="en",
            ).execute()
        except Exception:
            continue

        for item in response.get("items", []):
            yt_channel_id = item["snippet"]["channelId"]

            # Skip self
            if yt_channel_id == source_channel.youtube_id:
                continue

            # Skip already discovered in this run
            if yt_channel_id in discovered_channel_ids:
                continue
            discovered_channel_ids.add(yt_channel_id)

            # Check if channel already exists in DB
            existing_channel = session.exec(
                select(Channel).where(Channel.youtube_id == yt_channel_id)
            ).first()

            if not existing_channel:
                # Fetch full channel data
                ch_response = youtube.channels().list(
                    part="snippet,statistics",
                    id=yt_channel_id,
                ).execute()

                if not ch_response.get("items"):
                    continue

                ch_item = ch_response["items"][0]
                snippet = ch_item["snippet"]
                stats = ch_item["statistics"]

                existing_channel = Channel(
                    youtube_id=yt_channel_id,
                    name=snippet.get("title", ""),
                    handle=snippet.get("customUrl", ""),
                    description=snippet.get("description", "")[:500],
                    subscriber_count=int(stats.get("subscriberCount", 0)),
                    video_count=int(stats.get("videoCount", 0)),
                    fetched_at=datetime.utcnow(),
                )
                session.add(existing_channel)
                session.flush()

            # Check if competitor relationship already exists
            existing_comp = session.exec(
                select(Competitor).where(
                    Competitor.source_channel_id == channel_id,
                    Competitor.competitor_channel_id == existing_channel.id,
                )
            ).first()

            if not existing_comp:
                comp = Competitor(
                    source_channel_id=channel_id,
                    competitor_channel_id=existing_channel.id,
                    discovered_via="auto",
                )
                session.add(comp)
                count += 1

    session.commit()
    return count


def add_competitor_manual(session: Session, source_channel_id: int, competitor_channel_id: int) -> bool:
    """Manually add a competitor relationship. Returns True if new."""
    existing = session.exec(
        select(Competitor).where(
            Competitor.source_channel_id == source_channel_id,
            Competitor.competitor_channel_id == competitor_channel_id,
        )
    ).first()

    if existing:
        return False

    comp = Competitor(
        source_channel_id=source_channel_id,
        competitor_channel_id=competitor_channel_id,
        discovered_via="manual",
    )
    session.add(comp)
    session.commit()
    return True


def get_competitors_with_data(session: Session, channel_id: int) -> list[dict]:
    """Get all competitors for a channel with their channel data and latest video."""
    competitors = session.exec(
        select(Competitor).where(Competitor.source_channel_id == channel_id)
    ).all()

    results = []
    for comp in competitors:
        channel = session.exec(
            select(Channel).where(Channel.id == comp.competitor_channel_id)
        ).first()

        if not channel:
            continue

        # Get latest video if any
        latest_video = session.exec(
            select(Video)
            .where(Video.channel_id == channel.id)
            .order_by(Video.published_at.desc())
            .limit(1)
        ).first()

        results.append({
            "channel": channel,
            "competitor": comp,
            "latest_video": latest_video,
        })

    return results
