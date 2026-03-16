from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, JSON, Column


class Channel(SQLModel, table=True):
    __tablename__ = "channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    youtube_id: str = Field(unique=True, index=True)
    name: str = ""
    url: str = ""
    handle: str = ""
    subscriber_count: int = 0
    video_count: int = 0
    description: str = ""
    is_own: bool = False
    fetched_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Video(SQLModel, table=True):
    __tablename__ = "videos"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="channels.id", index=True)
    youtube_id: str = Field(unique=True, index=True)
    title: str = ""
    description: str = ""
    tags: str = ""  # JSON string
    views: int = 0
    likes: int = 0
    comments_count: int = 0
    duration: str = ""
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None


class Keyword(SQLModel, table=True):
    __tablename__ = "keywords"

    id: Optional[int] = Field(default=None, primary_key=True)
    term: str = Field(unique=True, index=True)
    volume_proxy: float = 0.0
    competition: float = 0.0
    trend_data_json: str = ""  # JSON string: snapshots over time
    source: str = ""  # "autocomplete", "analytics", "manual"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class KeywordScore(SQLModel, table=True):
    __tablename__ = "keyword_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    keyword_id: int = Field(foreign_key="keywords.id", index=True)
    channel_id: int = Field(foreign_key="channels.id", index=True)
    score: float = 0.0
    volume_component: float = 0.0
    competition_component: float = 0.0
    affinity: float = 0.0
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class Competitor(SQLModel, table=True):
    __tablename__ = "competitors"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_channel_id: int = Field(foreign_key="channels.id", index=True)
    competitor_channel_id: int = Field(foreign_key="channels.id", index=True)
    similarity_score: float = 0.0
    discovered_via: str = ""  # "auto" or "manual"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="channels.id", index=True)
    report_json: str = ""  # Full report as JSON
    report_type: str = "niche"  # "niche", "competitor", "trend"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AutocompleteSnapshot(SQLModel, table=True):
    __tablename__ = "autocomplete_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    suggestion: str = ""
    position: int = 0  # Rank in the autocomplete results (1-based)
    snapshot_date: datetime = Field(default_factory=datetime.utcnow)


class OAuthToken(SQLModel, table=True):
    __tablename__ = "oauth_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="channels.id", index=True)
    access_token: str = ""
    refresh_token: str = ""
    token_uri: str = "https://oauth2.googleapis.com/token"
    scopes: str = ""  # JSON string
    expiry: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class VphSnapshot(SQLModel, table=True):
    __tablename__ = "vph_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True)
    views: int = 0
    polled_at: datetime = Field(default_factory=datetime.utcnow)


class SeoScore(SQLModel, table=True):
    __tablename__ = "seo_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True)
    score: float = 0.0  # 0-100
    title_score: float = 0.0
    description_score: float = 0.0
    tags_score: float = 0.0
    recommendations: str = ""  # JSON string
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class TrendAlert(SQLModel, table=True):
    __tablename__ = "trend_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    keyword_id: int = Field(foreign_key="keywords.id", index=True)
    alert_type: str = ""  # "rising", "falling", "spike"
    velocity: float = 0.0  # rate of change
    baseline: float = 0.0
    message: str = ""
    seen: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AbTest(SQLModel, table=True):
    __tablename__ = "ab_tests"

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="videos.id", index=True)
    test_type: str = ""  # "title", "thumbnail"
    variant_a: str = ""
    variant_b: str = ""
    impressions_a: int = 0
    impressions_b: int = 0
    clicks_a: int = 0
    clicks_b: int = 0
    active_variant: str = "a"  # which is currently live
    status: str = "running"  # "running", "paused", "complete"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


class MetadataTemplate(SQLModel, table=True):
    __tablename__ = "metadata_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(foreign_key="channels.id", index=True)
    keyword_id: Optional[int] = Field(default=None, foreign_key="keywords.id")
    suggested_title: str = ""
    suggested_description: str = ""
    suggested_tags: str = ""  # JSON string
    saved: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
