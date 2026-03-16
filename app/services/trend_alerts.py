from datetime import datetime, timedelta

from sqlmodel import Session, select, col

from app.models import AutocompleteSnapshot, Keyword, TrendAlert


def detect_trends(session: Session, lookback_days: int = 14, threshold: float = 0.3) -> int:
    """Compare autocomplete snapshots across time periods to detect rising/falling keywords.

    For each tracked keyword query:
    - Get average position in recent period (last 7 days)
    - Get average position in previous period (7-14 days ago)
    - Calculate velocity = (old_position - new_position) / old_position
      Positive velocity = rising (moved up in autocomplete)
      Negative velocity = falling (moved down)
    - Flag keywords with |velocity| > threshold

    Also detects "spikes" — keywords that appear in recent snapshots
    but were absent in the previous period.

    Returns number of new alerts created.
    """
    now = datetime.utcnow()
    mid_point = now - timedelta(days=lookback_days // 2)
    old_start = now - timedelta(days=lookback_days)

    # Get all unique queries we've tracked
    all_snapshots = session.exec(
        select(AutocompleteSnapshot)
        .where(AutocompleteSnapshot.snapshot_date >= old_start)
    ).all()

    if not all_snapshots:
        return 0

    # Group by (query, suggestion) and split into recent vs old
    recent_data = {}  # {suggestion: [positions]}
    old_data = {}     # {suggestion: [positions]}

    for snap in all_snapshots:
        key = snap.suggestion.lower().strip()
        if not key:
            continue

        if snap.snapshot_date >= mid_point:
            recent_data.setdefault(key, []).append(snap.position)
        else:
            old_data.setdefault(key, []).append(snap.position)

    count = 0

    # Detect rising/falling
    for suggestion, recent_positions in recent_data.items():
        avg_recent = sum(recent_positions) / len(recent_positions)

        if suggestion in old_data:
            old_positions = old_data[suggestion]
            avg_old = sum(old_positions) / len(old_positions)

            if avg_old == 0:
                continue

            # Lower position number = higher rank, so invert for velocity
            # velocity > 0 means rising (moved from position 8 to position 3)
            velocity = (avg_old - avg_recent) / avg_old

            if abs(velocity) < threshold:
                continue

            alert_type = "rising" if velocity > 0 else "falling"
        else:
            # New keyword that wasn't in old period = spike
            alert_type = "spike"
            velocity = 1.0
            avg_old = 0

        # Find matching keyword in DB
        keyword = session.exec(
            select(Keyword).where(Keyword.term == suggestion)
        ).first()

        if not keyword:
            # Try partial match
            keyword = session.exec(
                select(Keyword).where(Keyword.term.contains(suggestion))
            ).first()

        if not keyword:
            continue

        # Check if we already have a recent alert for this keyword + type
        existing = session.exec(
            select(TrendAlert).where(
                TrendAlert.keyword_id == keyword.id,
                TrendAlert.alert_type == alert_type,
                TrendAlert.created_at >= mid_point,
            )
        ).first()

        if existing:
            continue

        alert = TrendAlert(
            keyword_id=keyword.id,
            alert_type=alert_type,
            velocity=round(velocity, 3),
            baseline=round(avg_old, 1),
            message=_build_message(suggestion, alert_type, velocity),
            seen=False,
        )
        session.add(alert)
        count += 1

    session.commit()
    return count


def get_trend_alerts(session: Session, include_seen: bool = False) -> list[dict]:
    """Get all trend alerts, newest first."""
    query = select(TrendAlert).order_by(col(TrendAlert.created_at).desc())
    if not include_seen:
        query = query.where(TrendAlert.seen == False)

    alerts = session.exec(query).all()

    results = []
    for alert in alerts:
        keyword = session.exec(
            select(Keyword).where(Keyword.id == alert.keyword_id)
        ).first()

        results.append({
            "alert": alert,
            "keyword": keyword,
        })

    return results


def mark_alert_seen(session: Session, alert_id: int) -> bool:
    """Mark an alert as seen."""
    alert = session.exec(
        select(TrendAlert).where(TrendAlert.id == alert_id)
    ).first()
    if not alert:
        return False
    alert.seen = True
    session.commit()
    return True


def _build_message(suggestion: str, alert_type: str, velocity: float) -> str:
    """Build a human-readable alert message."""
    if alert_type == "spike":
        return f'"{suggestion}" just appeared in autocomplete — new trending topic'
    elif alert_type == "rising":
        pct = abs(round(velocity * 100))
        return f'"{suggestion}" is rising — moved up {pct}% in autocomplete rankings'
    else:
        pct = abs(round(velocity * 100))
        return f'"{suggestion}" is falling — dropped {pct}% in autocomplete rankings'
