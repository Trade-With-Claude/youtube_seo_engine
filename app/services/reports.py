from sqlmodel import Session, select, col

from app.models import (
    Channel,
    Competitor,
    Keyword,
    KeywordScore,
    Video,
)
from app.services.keywords import get_keyword_traffic


def generate_niche_report(session: Session, channel_id: int) -> dict | None:
    """Generate a full niche report combining all data sources."""

    channel = session.exec(
        select(Channel).where(Channel.id == channel_id)
    ).first()
    if not channel:
        return None

    # --- Channel Overview ---
    videos = session.exec(
        select(Video)
        .where(Video.channel_id == channel_id)
        .order_by(col(Video.views).desc())
    ).all()

    total_views = sum(v.views for v in videos)
    avg_views = total_views // len(videos) if videos else 0
    top_videos = videos[:5]

    # --- Keyword Landscape ---
    traffic = get_keyword_traffic(session, channel_id)[:15]

    # Top opportunities (only analyzed keywords)
    analyzed_ids = [
        kw.id for kw in session.exec(
            select(Keyword).where(Keyword.competition > 0.0)
        ).all()
    ]
    opportunities = []
    if analyzed_ids:
        scores = session.exec(
            select(KeywordScore)
            .where(
                KeywordScore.channel_id == channel_id,
                KeywordScore.keyword_id.in_(analyzed_ids),
            )
            .order_by(col(KeywordScore.score).desc())
            .limit(10)
        ).all()
        for ks in scores:
            kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
            if kw:
                opportunities.append({"keyword": kw, "score": ks})

    # Keyword gaps: high demand but low beatable (hard to rank — aspirational)
    gaps = []
    if analyzed_ids:
        gap_scores = session.exec(
            select(KeywordScore)
            .where(
                KeywordScore.channel_id == channel_id,
                KeywordScore.keyword_id.in_(analyzed_ids),
            )
            .order_by(col(KeywordScore.volume_component).desc())
            .limit(20)
        ).all()
        for ks in gap_scores:
            if ks.competition_component < 0.3:  # Hard to beat
                kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
                if kw:
                    gaps.append({"keyword": kw, "score": ks})
        gaps = gaps[:5]

    # --- Competitors ---
    competitors_data = []
    comps = session.exec(
        select(Competitor).where(Competitor.source_channel_id == channel_id)
    ).all()
    for comp in comps:
        comp_channel = session.exec(
            select(Channel).where(Channel.id == comp.competitor_channel_id)
        ).first()
        if comp_channel:
            competitors_data.append(comp_channel)

    # --- Content Strategy ---
    strategy = _build_strategy(channel, videos, traffic, opportunities, gaps)

    return {
        "channel": channel,
        "total_views": total_views,
        "avg_views": avg_views,
        "video_count": len(videos),
        "top_videos": top_videos,
        "traffic_keywords": traffic,
        "opportunities": opportunities,
        "gaps": gaps,
        "competitors": competitors_data,
        "strategy": strategy,
        "analyzed_keyword_count": len(analyzed_ids),
        "total_keyword_count": len(session.exec(select(Keyword)).all()),
    }


def _build_strategy(channel, videos, traffic, opportunities, gaps) -> list[str]:
    """Generate content strategy insights from the data."""
    tips = []

    # What's working
    if traffic:
        top_term = traffic[0]["keyword"].term
        top_views = traffic[0]["total_views"]
        tips.append(
            f"Your strongest keyword is \"{top_term}\" with {top_views:,} total views. "
            f"Keep using it — it's proven to attract your audience."
        )

    # Best opportunities
    if opportunities:
        best = opportunities[0]
        beatable_pct = int(best["score"].competition_component * 100)
        tips.append(
            f"Your best opportunity is \"{best['keyword'].term}\" — "
            f"{beatable_pct}% beatable for your channel size. "
            f"Prioritize this in your next video title."
        )

    # Gaps to watch
    if gaps:
        gap_terms = ", ".join(f"\"{g['keyword'].term}\"" for g in gaps[:3])
        tips.append(
            f"High-demand keywords you can't rank for yet: {gap_terms}. "
            f"As your channel grows, these become opportunities."
        )

    # Video frequency insight
    if videos:
        total_views = sum(v.views for v in videos)
        avg = total_views // len(videos)
        best_video = videos[0]
        if best_video.views > avg * 5:
            tips.append(
                f"Your top video (\"{best_video.title[:50]}...\") has "
                f"{best_video.views:,} views — {best_video.views // max(avg, 1)}x your average. "
                f"Study what made it work and replicate the formula."
            )

    # Channel size context
    if channel.subscriber_count < 5000:
        tips.append(
            f"At {channel.subscriber_count:,} subs, focus on niche long-tail keywords "
            f"where bigger channels don't compete. Avoid generic terms like \"music\" or \"meditation\"."
        )

    return tips


def generate_video_suggestions(session: Session, channel_id: int) -> list[dict]:
    """Generate 3-5 concrete video ideas based on all available data."""

    channel = session.exec(
        select(Channel).where(Channel.id == channel_id)
    ).first()
    if not channel:
        return []

    # Get top opportunities
    analyzed_ids = [
        kw.id for kw in session.exec(
            select(Keyword).where(Keyword.competition > 0.0)
        ).all()
    ]
    if not analyzed_ids:
        return []

    scores = session.exec(
        select(KeywordScore)
        .where(
            KeywordScore.channel_id == channel_id,
            KeywordScore.keyword_id.in_(analyzed_ids),
        )
        .order_by(col(KeywordScore.score).desc())
        .limit(15)
    ).all()

    # Get traffic winners
    traffic = get_keyword_traffic(session, channel_id)
    traffic_terms = {t["keyword"].term.lower() for t in traffic[:10]}

    # Get best-performing video patterns
    videos = session.exec(
        select(Video)
        .where(Video.channel_id == channel_id)
        .order_by(col(Video.views).desc())
        .limit(5)
    ).all()

    proven_words = set()
    for v in videos:
        for w in v.title.lower().split():
            clean = w.strip(".,!?()[]\"'|—:-")
            if len(clean) > 3:
                proven_words.add(clean)

    suggestions = []
    used_keywords = set()

    for ks in scores:
        if len(suggestions) >= 5:
            break

        kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
        if not kw or kw.term.lower() in used_keywords:
            continue
        # Skip single generic words
        if len(kw.term.split()) < 2 and kw.term.lower() in {"music", "adhd", "sleep", "meditation", "audio", "brain", "calm", "deep", "stress"}:
            continue

        used_keywords.add(kw.term.lower())

        # Find a complementary keyword
        complement = _find_complement(kw, scores, used_keywords, session)

        # Build reasoning
        reasons = []
        beatable = int(ks.competition_component * 100)
        demand = int(ks.volume_component * 100)

        if beatable >= 50:
            reasons.append(f"{beatable}% beatable for your channel")
        if demand >= 10:
            reasons.append(f"good search demand ({demand}%)")
        if kw.term.lower() in traffic_terms:
            reasons.append("already proven on your channel")
        if any(w in proven_words for w in kw.term.lower().split()):
            reasons.append("matches your top-performing video patterns")

        if not reasons:
            reasons.append("strong opportunity score")

        # Build title
        if complement:
            title = f"{kw.term.title()} | {complement.term.title()}"
            target_kws = [kw.term, complement.term]
        else:
            title = kw.term.title()
            target_kws = [kw.term]

        if len(title) > 70:
            title = title[:67].rsplit(" ", 1)[0] + "..."

        suggestions.append({
            "title": title,
            "target_keywords": target_kws,
            "reasoning": " + ".join(reasons),
            "opportunity_score": int(ks.score * 100),
        })

    return suggestions


def _find_complement(primary_kw, all_scores, used, session) -> "Keyword | None":
    """Find a keyword that complements the primary one."""
    primary_words = set(primary_kw.term.lower().split())

    for ks in all_scores:
        kw = session.exec(select(Keyword).where(Keyword.id == ks.keyword_id)).first()
        if not kw or kw.term.lower() in used or kw.id == primary_kw.id:
            continue
        kw_words = set(kw.term.lower().split())
        # Good complement: adds new words
        if kw_words - primary_words:
            return kw
    return None
