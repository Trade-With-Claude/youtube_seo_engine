# Roadmap — V2

## Phase 1: Data Layer & VPH
**Goal:** New DB tables + Views Per Hour tracking system
**Requirements:**
- R1: New tables — `vph_snapshots`, `seo_scores`, `trend_alerts`, `ab_tests`
- R2: VPH polling service — periodically fetch video stats, calculate views/hour delta
- R3: VPH dashboard section — show velocity for your videos + niche videos, sortable
**Success:** Videos show real-time VPH values, updated on each poll cycle

## Phase 2: Smart Scoring
**Goal:** Channel-relative keyword difficulty + enhanced SEO scoring
**Requirements:**
- R1: Upgrade scoring formula to factor in channel subscriber count, watch time, and existing rankings
- R2: Video SEO score — grade title length, keyword placement, description quality, tag count (0-100)
- R3: Actionable recommendations per video ("add keyword X to title", "description too short")
**Success:** Keyword scores reflect what YOUR channel can rank for. Each video has an SEO grade with fix-it tips.

## Phase 3: Audience Intelligence
**Goal:** Best time to publish + subscriber source tracking
**Requirements:**
- R1: Pull audience activity data from YouTube Analytics API (online times by day/hour)
- R2: Heat map UI showing optimal publish windows
- R3: Subscriber source report — which videos/keywords drive subscriptions
**Success:** Dashboard shows when to publish and which content drives growth

## Phase 4: Trend Alerts & Tags
**Goal:** Proactive trend detection + competitor tag deep-dive
**Requirements:**
- R1: Velocity detection on autocomplete tracking — flag keywords rising above baseline
- R2: Trend alerts UI — list of rising/falling keywords with sparklines
- R3: Competitor tag extraction — most-used tags per channel, tag overlap/gap analysis
**Success:** Get notified of trending keywords. See exactly what tags competitors use and what you're missing.

## Phase 5: A/B Testing & Polish
**Goal:** Title/thumbnail A/B testing + final polish
**Requirements:**
- R1: A/B test creation — pick a video, set two title or thumbnail variants
- R2: Rotation logic — swap variants via YouTube API, track impressions/CTR per variant
- R3: Results dashboard — show which variant wins with statistical confidence
- R4: Polish — loading states, error handling, quota warnings for new features
**Success:** Run an A/B test on a video title, see CTR difference after a test period.
