# YouTube SEO Engine

## Project Name
YouTube SEO Engine

## Description
Web-based SEO research engine and metadata optimizer for YouTube music channels. Connects to YouTube Analytics via OAuth for deep channel insights, scrapes competitor data, detects trends, scores keywords, and generates ready-to-use video metadata.

## Repository
youtube_seo_engine

## Users
- Primary: channel owner (ADHD music / binaural beats, ~1,200 subs, in YouTube Partner Program)
- Secondary: any YouTube creator who pastes their channel URL
- Single-user focused but multi-user friendly

## UX
- Simple web dashboard
- Entry point: paste a YouTube channel URL → app does the rest
- Copy-paste metadata output in UI + JSON export for automation pipeline

## Architecture
- **Backend:** Python + FastAPI
- **Frontend:** Jinja2 + HTMX (server-rendered HTML fragments, no build step)
- **Styling:** Tailwind CSS via CDN
- **Database:** SQLite + SQLModel (WAL mode, sync), migrations via Alembic
- **Background tasks:** FastAPI BackgroundTasks (no extra infra)
- **Auth:** Google OAuth for YouTube Analytics API (one-time setup, guided in-app)
- **No paid dependencies** — all free APIs and tools

## Data Sources
- **YouTube Analytics API** (OAuth) — private channel data: search terms, revenue, retention, demographics, traffic sources. Revenue requires YPP membership (primary user has it).
- **YouTube Data API v3** — public channel/video data (free, 10K quota/day). Reads = 1 unit, search.list = 100 units (~100 searches/day). Cache aggressively.
- **YouTube autocomplete API** — real-time keyword suggestions (free, no key, unofficial). Track over time to build own trend curves.
- **Google Keyword Planner API** — free with Google Ads account (no spend needed). Monthly search volume + seasonal breakdowns. Not YouTube-specific but highly correlated for music/focus content.
- **Google Trends scraping** — lightweight custom scraping (not pytrends, which is dead). Bonus layer, graceful fallback if it breaks.
- **Competitor scraping** — titles, tags, descriptions, view velocity via YouTube Data API (public data)

## Trend Detection Strategy (3 layers)
1. **YouTube autocomplete tracking** (foundation) — poll daily/weekly, track keyword position/frequency over time. Builds own trend curves. Free, YouTube-specific, gets smarter over time.
2. **Google Keyword Planner** (immediate seasonal data) — monthly volume breakdowns from day one. Free with Google Ads account.
3. **Google Trends scraping** (bonus) — seasonal patterns, keyword comparison. Fragile but useful. Graceful fallback if blocked.

## Core Features (v1)
1. **Channel Analytics** — connect via OAuth, pull real traffic/revenue/retention data
2. **Competitor Intelligence** — auto-discover similar channels (search niche keywords → harvest channel IDs) + manual add, track their content over time
3. **Trend Detection** — 3-layer system: autocomplete tracking + Keyword Planner + Google Trends scraping
4. **Custom Keyword Scoring** — formula: Score = (volume_proxy × 0.4) + ((1 - competition) × 0.4) + (channel_affinity × 0.2). Hardcoded weights to start.
5. **Metadata Generation** — title, description, tags from keyword research. Copy-paste in UI + JSON export
6. **Niche Reports** — periodic summary combining all data sources into actionable recommendations

## Data Model (SQLite)
- `channels` — id, youtube_id, name, url, subscriber_count, video_count, fetched_at
- `videos` — id, channel_id FK, youtube_id, title, description, tags, views, published_at
- `keywords` — id, term, volume_proxy, competition, trend_data_json
- `keyword_scores` — id, keyword_id FK, channel_id FK, score, affinity, scored_at
- `competitors` — id, source_channel_id FK, competitor_channel_id FK, similarity_score
- `reports` — id, channel_id FK, created_at, report_json
- `metadata_templates` — id, keyword_id FK, suggested_title, suggested_description, suggested_tags

## Technical Constraints
- **Quota**: 10K units/day on YouTube Data API. search.list = 100 units. Cache everything, minimize search calls.
- **Autocomplete**: unofficial endpoint, could break. Abstract behind a service layer for easy swap.
- **OAuth consent**: "External" apps in testing mode capped at 100 users. Full verification requires Google review.
- **Google Trends scraping**: fragile, may get blocked. Non-critical, graceful fallback.

## Project Structure
```
youtube_seo_engine/
├── app/
│   ├── main.py              # FastAPI app, startup events
│   ├── config.py            # Settings (Pydantic BaseSettings)
│   ├── database.py          # SQLModel engine, session, init_db
│   ├── models.py            # SQLModel table models
│   ├── routers/
│   │   ├── dashboard.py     # HTML routes (Jinja2 + HTMX)
│   │   └── api.py           # JSON API routes
│   ├── services/
│   │   ├── youtube_api.py   # YouTube Data API v3
│   │   ├── analytics.py     # YouTube Analytics API
│   │   ├── autocomplete.py  # YouTube autocomplete scraping
│   │   ├── trends.py        # Google Trends + Keyword Planner
│   │   ├── competitors.py   # Competitor discovery & tracking
│   │   ├── scoring.py       # Keyword scoring engine
│   │   └── metadata.py      # Metadata generation
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, favicon
├── tests/
├── .env
└── requirements.txt
```

## Channel Context
- ADHD music / meditation / binaural beats niche
- ~1,200 subs, one video at 115K views
- ~€10/month passive income, no uploads in 3-4 years
- Channel is in YouTube Partner Program (revenue data accessible)
- Old workflow took 2 days per video — this project automates the SEO/metadata part

## Ecosystem
- 1 of 3 sub-projects inside youtube-autopilot (others: visual engine, upload pipeline)
- SEO engine output feeds into both other projects
- Metadata JSON export consumed by upload pipeline
