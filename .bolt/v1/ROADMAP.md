# Roadmap — V1

## Phase 1: Foundation
**Goal:** Project skeleton — FastAPI app, SQLite database, models, basic dashboard shell
**Requirements:**
- R1: FastAPI app with config/settings (Pydantic BaseSettings, .env)
- R2: SQLModel database + all tables (channels, videos, keywords, keyword_scores, competitors, reports, metadata_templates)
- R3: Jinja2/HTMX/Tailwind base layout with channel URL input form
- R4: Google OAuth setup guide page
**Success:** App runs, paste a YouTube URL, channel resolves and saves to DB

## Phase 2: Channel Data
**Goal:** Connect to YouTube APIs and pull real channel + video data
**Requirements:**
- R1: YouTube Data API v3 integration (channel info, video list, tags)
- R2: YouTube Analytics API via OAuth (search terms, retention, traffic sources, revenue)
- R3: Dashboard shows channel stats + video table
**Success:** Paste your channel URL → see real analytics data in the dashboard

## Phase 3: Trend Engine
**Goal:** Keyword research and trend detection across all 3 layers
**Requirements:**
- R1: YouTube autocomplete scraping + keyword extraction from channel videos
- R2: Google Keyword Planner integration (seasonal volume)
- R3: Google Trends scraping with graceful fallback
- R4: Autocomplete tracking over time (store snapshots, show rising/falling)
**Success:** Search a niche term → see volume proxy, seasonal pattern, trending direction

## Phase 4: Competitors & Scoring
**Goal:** Auto-discover competitors and score all keywords
**Requirements:**
- R1: Competitor auto-discovery (search niche keywords → harvest channels)
- R2: Manual competitor add
- R3: Competitor tracking dashboard (their new videos, tags, view velocity)
- R4: Keyword scoring engine (volume × 0.4 + competition × 0.4 + affinity × 0.2)
**Success:** Dashboard shows ranked competitors + scored keyword table sorted by opportunity

## Phase 5: Metadata & Reports
**Goal:** Generate ready-to-use video metadata and niche reports
**Requirements:**
- R1: Metadata generator (title, description, tags from top keywords)
- R2: Copy-paste UI + JSON export
- R3: Niche report combining all data sources
- R4: "Suggested next video" recommendation
**Success:** Click "Generate metadata" → get complete SEO-optimized title/description/tags + downloadable JSON

## Phase 6: Polish & Deploy
**Goal:** Edge cases, UX polish, deployment readiness
**Requirements:**
- R1: Background task progress indicators
- R2: Quota usage tracking/warnings
- R3: Multi-user onboarding flow (easy OAuth for others)
- R4: Error handling + rate limit resilience
- R5: Deployment docs
**Success:** Another creator can clone, set up credentials, and use the app end-to-end
