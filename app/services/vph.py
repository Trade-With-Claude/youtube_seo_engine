from datetime import datetime

from sqlmodel import Session, select, col

from app.models import Video, VphSnapshot
from app.services.youtube_api import get_youtube_service


def poll_vph(session: Session, channel_id: int | None = None) -> int:
    """Fetch current view counts for all tracked videos and store snapshots.
    Returns the number of snapshots created."""
    query = select(Video)
    if channel_id:
        query = query.where(Video.channel_id == channel_id)

    videos = session.exec(query).all()
    if not videos:
        return 0

    youtube = get_youtube_service()
    video_ids = [v.youtube_id for v in videos]
    video_map = {v.youtube_id: v for v in videos}

    count = 0
    # Batch in groups of 50 (YouTube API limit)
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        response = youtube.videos().list(
            part="statistics",
            id=",".join(batch),
        ).execute()

        for item in response.get("items", []):
            yt_id = item["id"]
            views = int(item["statistics"].get("viewCount", 0))
            video = video_map.get(yt_id)
            if not video:
                continue

            # Also update the video's cached view count
            video.views = views

            snapshot = VphSnapshot(
                video_id=video.id,
                views=views,
                polled_at=datetime.utcnow(),
            )
            session.add(snapshot)
            count += 1

    session.commit()
    return count


def calculate_vph(session: Session, video_id: int) -> float | None:
    """Calculate views per hour for a video based on the last 2 snapshots.
    Returns None if fewer than 2 snapshots exist."""
    snapshots = session.exec(
        select(VphSnapshot)
        .where(VphSnapshot.video_id == video_id)
        .order_by(col(VphSnapshot.polled_at).desc())
        .limit(2)
    ).all()

    if len(snapshots) < 2:
        return None

    latest = snapshots[0]
    previous = snapshots[1]

    delta_views = latest.views - previous.views
    delta_hours = (latest.polled_at - previous.polled_at).total_seconds() / 3600

    if delta_hours <= 0:
        return 0.0

    return round(delta_views / delta_hours, 1)


def get_vph_for_videos(session: Session, channel_id: int | None = None) -> list[dict]:
    """Get VPH data for all videos, optionally filtered by channel."""
    query = select(Video)
    if channel_id:
        query = query.where(Video.channel_id == channel_id)

    videos = session.exec(query).all()
    results = []

    for video in videos:
        vph = calculate_vph(session, video.id)

        # Get last polled time
        latest_snapshot = session.exec(
            select(VphSnapshot)
            .where(VphSnapshot.video_id == video.id)
            .order_by(col(VphSnapshot.polled_at).desc())
            .limit(1)
        ).first()

        results.append({
            "video": video,
            "vph": vph,
            "last_polled": latest_snapshot.polled_at if latest_snapshot else None,
            "snapshot_count": len(session.exec(
                select(VphSnapshot).where(VphSnapshot.video_id == video.id)
            ).all()),
        })

    # Sort by VPH descending (None values last)
    results.sort(key=lambda x: x["vph"] if x["vph"] is not None else -1, reverse=True)
    return results
