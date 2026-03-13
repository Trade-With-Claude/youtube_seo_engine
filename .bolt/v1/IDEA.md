# YouTube SEO Engine

## The Idea
Automated SEO research engine + metadata optimizer for an ADHD music / binaural beats YouTube channel. Replaces TubeBuddy (and beats it) by connecting directly to your own channel data and feeding keyword insights straight into video metadata — no manual work.

## The Problem
- TubeBuddy gives generic suggestions, same for everyone in a niche
- Best features locked behind $50+/month paywalls
- TubeBuddy stops at suggestions — you still do everything manually
- No tool connects SEO research directly into metadata generation as one pipeline

## Key Features

### SEO Research (Step 1 — drives everything)

**Channel analytics (OAuth, YouTube Analytics API):**
- Your actual traffic sources, not estimates
- Exact search terms bringing people to YOUR videos
- Which videos get the most search traffic
- Keywords your 115K-view video ranks for
- Audience retention data — ideal video length
- Revenue per video — which content actually makes money
- Peak traffic days/times for your audience
- Real audience demographics

**Competitor intelligence (scraping, no API needed):**
- Track top channels in niche — titles, tags, descriptions they use
- Monitor which of their new videos blow up
- Spot trends before they peak
- Build a database over time to see patterns

**Trend detection:**
- YouTube autocomplete — what people are typing right now
- Google Trends — seasonal patterns (exam season = more "focus music" searches)
- Compare keywords against each other
- Trend timing — WHEN to post about a topic, not just what

**Custom scoring:**
- Weight keywords based on YOUR channel's history, not generic metrics
- Combine search volume + competition + your channel's strength in that topic

### Metadata Optimization (Step 6 — consumes SEO output)
- Title: combine track name + high-performing keywords from research
- Description: SEO template with dynamic keyword injection
- Tags: auto-generated from keyword research
- All filled from templates, minimal manual input

### Output Example
```
Niche Report — March 2026

TOP SEARCHES RIGHT NOW:
1. "adhd focus music 2026"        — high volume, low competition
2. "binaural beats studying"      — high volume, high competition
3. "adhd deep work music"         — medium volume, low competition ← sweet spot

YOUR CHANNEL INSIGHTS:
- Top search term: "binaural beats adhd" (68% of your traffic)
- Best performing length: 1h-2h videos
- Peak traffic days: Sunday-Tuesday

COMPETITOR MOVES:
- "ADHD Focus Zone" (50K subs) just posted "432hz ADHD" — gaining fast

SUGGESTED NEXT VIDEO:
Title: "ADHD Deep Work Music | 2 Hours Binaural Beats for Hyperfocus"
Tags: [auto-generated]
Best upload time: Sunday 6pm CET
```

## Stack / Tech Preferences
- **Python** — main language
- **YouTube Data API v3** — channel data + metadata (free, 10K quota/day)
- **YouTube Analytics API** — deep channel analytics (OAuth, free)
- **YouTube autocomplete API** — keyword scraping (free, no key needed)
- **Google Trends** — unofficial API, free
- All free tools, no paid dependencies

## Notes
- This is 1 of 3 sub-projects inside youtube-autopilot (others: visual engine, upload pipeline)
- SEO research comes FIRST in the workflow — keywords inform what music to make
- The output of this engine feeds into the other sub-projects (metadata for upload, topic for music)
- Channel context: ~1,200 subs, one video at 115K views, ~€10/month passive, no uploads in 3-4 years
