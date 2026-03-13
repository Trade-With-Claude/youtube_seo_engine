import math

from googleapiclient.discovery import build

from app.config import settings


def get_youtube_service():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def test_title(title: str, my_subs: int, my_avg_views: int) -> dict:
    """Test a title against YouTube search results.

    Searches YouTube for the title, analyzes the top 10 results:
    - Who ranks for this? (channel names, sub counts)
    - How many views do those videos get?
    - Can YOUR channel compete?

    Returns a detailed analysis dict.
    """
    youtube = get_youtube_service()
    my_subs = max(my_subs, 1)
    my_avg_views = max(my_avg_views, 1)

    # Search YouTube for this title (100 quota units)
    search_resp = youtube.search().list(
        part="snippet",
        q=title,
        type="video",
        maxResults=10,
        relevanceLanguage="en",
    ).execute()

    items = search_resp.get("items", [])
    if not items:
        return {
            "verdict": "go",
            "verdict_text": "No competition found — this is a wide open niche!",
            "competitors": [],
            "avg_competitor_subs": 0,
            "avg_competitor_views": 0,
            "sub_ratio": 0,
            "title": title,
        }

    # Get video IDs and channel IDs
    video_ids = [item["id"]["videoId"] for item in items]
    channel_ids = list(set(item["snippet"]["channelId"] for item in items))

    # Get video stats (1 quota unit)
    videos_resp = youtube.videos().list(
        part="statistics",
        id=",".join(video_ids),
    ).execute()

    video_stats = {}
    for v in videos_resp.get("items", []):
        video_stats[v["id"]] = {
            "views": int(v["statistics"].get("viewCount", 0)),
            "likes": int(v["statistics"].get("likeCount", 0)),
        }

    # Get channel stats (1 quota unit)
    channels_resp = youtube.channels().list(
        part="snippet,statistics",
        id=",".join(channel_ids[:10]),
    ).execute()

    channel_stats = {}
    for ch in channels_resp.get("items", []):
        channel_stats[ch["id"]] = {
            "name": ch["snippet"].get("title", ""),
            "subs": int(ch["statistics"].get("subscriberCount", 0)),
        }

    # Build competitor list
    competitors = []
    for item in items:
        vid_id = item["id"]["videoId"]
        ch_id = item["snippet"]["channelId"]
        vid_title = item["snippet"]["title"]

        vid_data = video_stats.get(vid_id, {"views": 0, "likes": 0})
        ch_data = channel_stats.get(ch_id, {"name": "Unknown", "subs": 0})

        competitors.append({
            "title": vid_title,
            "channel_name": ch_data["name"],
            "channel_subs": ch_data["subs"],
            "views": vid_data["views"],
            "your_size": _size_comparison(ch_data["subs"], my_subs),
        })

    # Calculate averages
    comp_subs = [c["channel_subs"] for c in competitors if c["channel_subs"] > 0]
    comp_views = [c["views"] for c in competitors if c["views"] > 0]

    avg_subs = sum(comp_subs) // len(comp_subs) if comp_subs else 0
    avg_views = sum(comp_views) // len(comp_views) if comp_views else 0

    # How many competitors are your size or smaller?
    beatable_count = sum(1 for c in competitors if c["channel_subs"] <= my_subs * 3)
    total_count = len(competitors)

    # Sub ratio
    sub_ratio = avg_subs / my_subs if my_subs > 0 else 999

    # Verdict
    if sub_ratio <= 2:
        verdict = "go"
        verdict_text = "Great title! The channels ranking for this are your size or smaller. You can compete."
    elif sub_ratio <= 10:
        verdict = "maybe"
        verdict_text = (
            f"Possible. Competitors average {avg_subs:,} subs ({sub_ratio:.0f}x your size). "
            f"You might rank if your content is strong."
        )
    elif sub_ratio <= 50:
        verdict = "tough"
        verdict_text = (
            f"Tough. Competitors average {avg_subs:,} subs ({sub_ratio:.0f}x your size). "
            f"Consider adding a niche modifier to differentiate."
        )
    else:
        verdict = "skip"
        verdict_text = (
            f"Very competitive. Competitors average {avg_subs:,} subs ({sub_ratio:.0f}x your size). "
            f"Try a more specific/long-tail version of this title."
        )

    return {
        "verdict": verdict,
        "verdict_text": verdict_text,
        "competitors": competitors,
        "avg_competitor_subs": avg_subs,
        "avg_competitor_views": avg_views,
        "beatable_count": beatable_count,
        "total_count": total_count,
        "sub_ratio": sub_ratio,
        "title": title,
    }


def _size_comparison(their_subs: int, my_subs: int) -> str:
    if my_subs == 0:
        return "larger"
    ratio = their_subs / my_subs
    if ratio <= 0.5:
        return "much smaller"
    elif ratio <= 1.5:
        return "similar size"
    elif ratio <= 5:
        return "bigger"
    elif ratio <= 50:
        return "much bigger"
    else:
        return "way bigger"
