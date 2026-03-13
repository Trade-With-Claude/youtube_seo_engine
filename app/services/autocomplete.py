import json
import time
from datetime import datetime

import httpx


def get_youtube_suggestions(query: str, language: str = "en") -> list[str]:
    """Get YouTube autocomplete suggestions for a query.
    Uses the unofficial YouTube suggest endpoint."""
    url = "https://clients1.google.com/complete/search"
    params = {
        "client": "youtube",
        "q": query,
        "hl": language,
        "ds": "yt",
    }

    try:
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()

        # Response is JSONP: window.google.ac.h([...])
        text = response.text
        # Extract the JSON array from the JSONP wrapper
        start = text.index("(")
        end = text.rindex(")")
        data = json.loads(text[start + 1:end])

        suggestions = []
        if len(data) > 1 and isinstance(data[1], list):
            for item in data[1]:
                if isinstance(item, list) and len(item) > 0:
                    suggestions.append(item[0])

        return suggestions

    except Exception:
        return []


def get_suggestions_batch(queries: list[str], delay: float = 1.5) -> dict[str, list[str]]:
    """Get autocomplete suggestions for multiple queries with rate limiting."""
    results = {}
    for query in queries:
        results[query] = get_youtube_suggestions(query)
        if delay > 0:
            time.sleep(delay)
    return results
