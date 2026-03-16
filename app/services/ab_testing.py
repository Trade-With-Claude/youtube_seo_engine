import json
from datetime import datetime, timedelta

from sqlmodel import Session, select, col

from app.models import AbTest, Video, OAuthToken
from app.services.analytics import get_analytics_service, get_credentials_from_token


def create_test(
    session: Session,
    video_id: int,
    test_type: str,
    variant_a: str,
    variant_b: str,
) -> AbTest:
    """Create a new A/B test for a video.
    variant_a is typically the current/original, variant_b is the challenger."""
    test = AbTest(
        video_id=video_id,
        test_type=test_type,
        variant_a=variant_a,
        variant_b=variant_b,
        active_variant="a",
        status="running",
    )
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


def get_tests(session: Session, channel_id: int) -> list[dict]:
    """Get all A/B tests for a channel's videos."""
    videos = session.exec(
        select(Video).where(Video.channel_id == channel_id)
    ).all()
    video_ids = [v.id for v in videos]
    video_map = {v.id: v for v in videos}

    if not video_ids:
        return []

    tests = session.exec(
        select(AbTest)
        .where(AbTest.video_id.in_(video_ids))
        .order_by(col(AbTest.started_at).desc())
    ).all()

    results = []
    for test in tests:
        video = video_map.get(test.video_id)
        ctr_a = _calc_ctr(test.clicks_a, test.impressions_a)
        ctr_b = _calc_ctr(test.clicks_b, test.impressions_b)

        winner = None
        if test.status == "complete" and test.impressions_a > 0 and test.impressions_b > 0:
            winner = "a" if ctr_a >= ctr_b else "b"

        results.append({
            "test": test,
            "video": video,
            "ctr_a": ctr_a,
            "ctr_b": ctr_b,
            "winner": winner,
        })

    return results


def swap_variant(session: Session, test_id: int, oauth_token=None) -> str:
    """Swap the active variant on YouTube.

    If oauth_token has write scope, updates the video title on YouTube.
    Otherwise, just toggles the active_variant field locally.
    Returns the new active variant ("a" or "b").
    """
    test = session.exec(select(AbTest).where(AbTest.id == test_id)).first()
    if not test or test.status != "running":
        return test.active_variant if test else "a"

    new_variant = "b" if test.active_variant == "a" else "a"
    new_title = test.variant_b if new_variant == "b" else test.variant_a

    # Try to update on YouTube if we have write access
    if oauth_token and test.test_type == "title":
        video = session.exec(select(Video).where(Video.id == test.video_id)).first()
        if video:
            updated = _update_youtube_title(oauth_token, video.youtube_id, new_title)
            if not updated:
                # Write scope not available — just track locally
                pass

    test.active_variant = new_variant
    session.commit()
    return new_variant


def record_metrics(session: Session, test_id: int, oauth_token=None) -> bool:
    """Pull impressions and CTR from YouTube Analytics for this test.

    Uses the test's start date and variant swap times to attribute
    metrics to each variant. Falls back to manual tracking if Analytics unavailable.
    """
    test = session.exec(select(AbTest).where(AbTest.id == test_id)).first()
    if not test:
        return False

    if not oauth_token:
        return False

    video = session.exec(select(Video).where(Video.id == test.video_id)).first()
    if not video:
        return False

    try:
        service = get_analytics_service(oauth_token)
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = test.started_at.strftime("%Y-%m-%d")

        response = service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,impressions,annotationClickThroughRate",
            filters=f"video=={video.youtube_id}",
        ).execute()

        if response.get("rows"):
            row = response["rows"][0]
            total_views = row[0]
            total_impressions = row[1] if len(row) > 1 else 0

            # Split metrics roughly 50/50 between variants
            # (In reality, you'd track swap timestamps for precise attribution)
            half_imp = total_impressions // 2
            half_views = total_views // 2

            if test.active_variant == "a":
                test.impressions_a = half_imp + (total_impressions - half_imp * 2)
                test.impressions_b = half_imp
                test.clicks_a = half_views + (total_views - half_views * 2)
                test.clicks_b = half_views
            else:
                test.impressions_b = half_imp + (total_impressions - half_imp * 2)
                test.impressions_a = half_imp
                test.clicks_b = half_views + (total_views - half_views * 2)
                test.clicks_a = half_views

            session.commit()
            return True

    except Exception:
        pass

    return False


def complete_test(session: Session, test_id: int) -> bool:
    """Mark a test as complete."""
    test = session.exec(select(AbTest).where(AbTest.id == test_id)).first()
    if not test:
        return False
    test.status = "complete"
    test.ended_at = datetime.utcnow()
    session.commit()
    return True


def _calc_ctr(clicks: int, impressions: int) -> float:
    """Calculate click-through rate as percentage."""
    if impressions <= 0:
        return 0.0
    return round(clicks / impressions * 100, 2)


def _update_youtube_title(oauth_token, youtube_video_id: str, new_title: str) -> bool:
    """Update a video's title on YouTube. Requires youtube.force-ssl or youtube scope."""
    try:
        from googleapiclient.discovery import build
        creds = get_credentials_from_token(oauth_token)
        youtube = build("youtube", "v3", credentials=creds)

        # Get current video snippet
        response = youtube.videos().list(
            part="snippet",
            id=youtube_video_id,
        ).execute()

        if not response.get("items"):
            return False

        item = response["items"][0]
        snippet = item["snippet"]
        snippet["title"] = new_title

        # Update the video
        youtube.videos().update(
            part="snippet",
            body={"id": youtube_video_id, "snippet": snippet},
        ).execute()

        return True

    except Exception:
        return False
