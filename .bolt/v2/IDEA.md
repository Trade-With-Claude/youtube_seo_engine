# YouTube SEO Engine — v2

## What's New
Advanced analytics, real-time trend detection, and competitive intelligence inspired by TubeBuddy/VidIQ. V2 turns the SEO engine from a research tool into a proactive optimization system.

## Why
V1 built the foundation — channel data, basic keyword scoring, metadata generation, and competitor tracking. But it lacks real-time velocity metrics (VPH), channel-relative keyword difficulty, publish timing optimization, proactive trend alerts, subscriber source insights, and deeper competitive tag analysis. These are the features that make tools like TubeBuddy and VidIQ indispensable for serious creators.

## Key Changes
1. **Views Per Hour (VPH)** — poll video stats periodically, calculate velocity, spot algorithm-boosted content in your niche. VidIQ's signature metric.
2. **Channel-Relative Keyword Difficulty** — weight keyword scores by your channel's actual authority/size/watch time so recommendations are realistic. Inspired by MorningFame.
3. **Best Time to Publish** — heat map from YouTube Analytics data showing when your audience is most active, by day and hour.
4. **Trend Velocity Alerts** — detect keywords rising faster than baseline in autocomplete tracking. Proactive notifications instead of manual checking.
5. **Subscriber Source Tracking** — which videos and keywords actually drive subscriptions. Uses YouTube Analytics API.
6. **Enhanced SEO Scoring** — more granular video optimization score (title length, keyword placement, description quality, tag count, thumbnail presence) with actionable fix-it recommendations.
7. **Competitor Tag Sniping** — extract all competitor tags, find most-used tags per channel, show tag overlap/gaps with your channel.
8. **A/B Testing** — rotate title/thumbnail variants on published videos, measure CTR differences over time via YouTube API.

## Lessons from v1
- OAuth flow was tricky — PKCE flow state management between requests needed careful handling
- YouTube Data API quota (10K/day) is tight — aggressive caching is essential
- Autocomplete API is free but unofficial — needs resilient error handling
- Simple scoring formula works but needs channel context to be actionable
- Copy-paste metadata is useful but AI generation (via external LLM) would be even better

## Notes
- AI metadata generation handled externally (copy context into Claude) — no need to build LLM integration
- VPH requires periodic polling — budget ~2-5 quota units per poll, batch efficiently
- A/B testing requires YouTube API write access (already have OAuth with update scope)
- All features degrade gracefully if API quota is exhausted
- New DB tables needed: vph_snapshots, ab_tests, trend_alerts, seo_scores
