import json
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings


SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_credentials_from_token(oauth_token) -> Credentials:
    """Build Google Credentials from our stored OAuthToken model."""
    creds = Credentials(
        token=oauth_token.access_token,
        refresh_token=oauth_token.refresh_token,
        token_uri=oauth_token.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=json.loads(oauth_token.scopes) if oauth_token.scopes else SCOPES,
    )
    if oauth_token.expiry:
        creds.expiry = oauth_token.expiry
    return creds


def get_analytics_service(oauth_token):
    """Build an authorized YouTube Analytics API service."""
    creds = get_credentials_from_token(oauth_token)
    return build("youtubeAnalytics", "v2", credentials=creds)


def get_top_search_terms(oauth_token, days: int = 90, max_results: int = 25) -> list[dict]:
    """Get top search terms driving traffic to the channel."""
    service = get_analytics_service(oauth_token)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = service.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched",
        dimensions="insightTrafficSourceDetail",
        filters="insightTrafficSourceType==YT_SEARCH",
        sort="-views",
        maxResults=max_results,
    ).execute()

    results = []
    for row in response.get("rows", []):
        results.append({
            "term": row[0],
            "views": row[1],
            "watch_time_minutes": round(row[2], 1),
        })
    return results


def get_traffic_sources(oauth_token, days: int = 90) -> list[dict]:
    """Get traffic source breakdown."""
    service = get_analytics_service(oauth_token)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = service.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched",
        dimensions="insightTrafficSourceType",
        sort="-views",
    ).execute()

    results = []
    for row in response.get("rows", []):
        results.append({
            "source": row[0],
            "views": row[1],
            "watch_time_minutes": round(row[2], 1),
        })
    return results


def get_revenue(oauth_token, days: int = 90) -> dict:
    """Get revenue data (requires YPP)."""
    service = get_analytics_service(oauth_token)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        response = service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="estimatedRevenue,views,estimatedMinutesWatched",
        ).execute()

        if response.get("rows"):
            row = response["rows"][0]
            return {
                "revenue": round(row[0], 2),
                "views": row[1],
                "watch_time_minutes": round(row[2], 1),
                "period_days": days,
            }
    except Exception:
        pass

    return {"revenue": 0, "views": 0, "watch_time_minutes": 0, "period_days": days}


def get_demographics(oauth_token, days: int = 90) -> list[dict]:
    """Get audience demographics (age + gender)."""
    service = get_analytics_service(oauth_token)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        response = service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            sort="-viewerPercentage",
        ).execute()

        results = []
        for row in response.get("rows", []):
            results.append({
                "age_group": row[0],
                "gender": row[1],
                "percentage": round(row[2], 1),
            })
        return results
    except Exception:
        return []
