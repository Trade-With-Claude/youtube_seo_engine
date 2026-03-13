from trendspy import Trends


def get_interest_over_time(keyword: str, timeframe: str = "today 12-m") -> dict:
    """Get Google Trends interest over time for a keyword.
    Returns timeline data + related queries, or error info on failure."""
    try:
        tr = Trends()
        df = tr.interest_over_time(keyword, timeframe=timeframe)

        if df is None or df.empty:
            return {"error": "No data returned"}

        # Build timeline from dataframe
        timeline = []
        for idx, row in df.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            value = int(row.iloc[0]) if len(row) > 0 else 0
            timeline.append({"date": date_str, "value": value})

        # Get related queries
        related = []
        try:
            related_df = tr.related_queries(keyword)
            if related_df is not None and not related_df.empty:
                for _, row in related_df.head(10).iterrows():
                    query = row.iloc[0] if len(row) > 0 else ""
                    if query:
                        related.append(str(query))
        except Exception:
            pass

        return {
            "timeline": timeline,
            "related_queries": related,
        }

    except Exception as e:
        return {"error": str(e)}
