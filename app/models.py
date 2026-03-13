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
