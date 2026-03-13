import json
from datetime import datetime

from googleapiclient.discovery import build

from app.config import settings


def get_youtube_service():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def resolve_channel(handle_or_id: str) -> dict | None:
    """Resolve a YouTube handle or channel ID to full channel data."""
    youtube = get_youtube_service()

    # Try forHandle first (for @handle format)
    handle = handle_or_id.lstrip("@")
    request = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        forHandle=handle,
    )
    response = request.execute()

    if not response.get("items"):
        # Try as channel ID
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=handle_or_id,
        )
        response = request.execute()

    if not response.get("items"):
        return None

    item = response["items"][0]
    snippet = item["snippet"]
    stats = item["statistics"]
    content = item["contentDetails"]

    return {
        "youtube_id": item["id"],
        "name": snippet.get("title", ""),
        "handle": snippet.get("customUrl", ""),
        "description": snippet.get("description", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist_id": content["relatedPlaylists"]["uploads"],
        "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
    }


def fetch_videos(channel_id: str, max_results: int = 50) -> list[dict]:
    """Fetch a channel's videos using playlistItems + videos.list (saves quota vs search)."""
    youtube = get_youtube_service()

    # Step 1: Get channel's uploads playlist ID
    ch_request = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    )
    ch_response = ch_request.execute()
    if not ch_response.get("items"):
        return []

    uploads_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Step 2: Get video IDs from uploads playlist
    video_ids = []
    page_token = None
    while len(video_ids) < max_results:
        pl_request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_id,
            maxResults=min(50, max_results - len(video_ids)),
            pageToken=page_token,
        )
        pl_response = pl_request.execute()
        for item in pl_response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        page_token = pl_response.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        return []

    # Step 3: Get video details in batches of 50
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        v_request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(batch),
        )
        v_response = v_request.execute()
        for item in v_response.get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            published = snippet.get("publishedAt", "")
            published_dt = None
            if published:
                published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

            videos.append({
                "youtube_id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "tags": json.dumps(snippet.get("tags", [])),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments_count": int(stats.get("commentCount", 0)),
                "published_at": published_dt,
            })

    return videos
