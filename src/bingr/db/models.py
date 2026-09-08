"""SQLAlchemy ORM models for the Bingr database.

Tables: m3u_sources (imported playlists), channels (normalised channel records),
m3u_channels (many-to-many link), feeds (iptv-org feed metadata).
All models use SQLAlchemy 2.0-style mapped_column with DeclarativeBase.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(UTC).isoformat()


class M3USource(Base):
    __tablename__ = "m3u_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    input_url: Mapped[str | None] = mapped_column(String(500))
    input_file: Mapped[str | None] = mapped_column(String(500))
    path: Mapped[str | None] = mapped_column(String(500))
    m3u_provided_epg_url: Mapped[str | None] = mapped_column(Text)
    channel_count: Mapped[int | None] = mapped_column()
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(30), default=utcnow, onupdate=utcnow)

    channels = relationship("M3UChannel", back_populates="source", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(100), index=True)

    tvg_prefix: Mapped[str | None] = mapped_column(String(100))
    tvg_suffix: Mapped[str | None] = mapped_column(String(50), index=True)
    tvg_ids: Mapped[list[str] | None] = mapped_column(JSON)
    titles: Mapped[list[str] | None] = mapped_column(JSON)
    clean_titles: Mapped[list[str] | None] = mapped_column(JSON)
    display_name: Mapped[str | None] = mapped_column(String(300), index=True)
    tvg_names: Mapped[list[str] | None] = mapped_column(JSON)
    country: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    group_titles: Mapped[list[str] | None] = mapped_column(JSON)
    tvg_logos: Mapped[list[str] | None] = mapped_column(JSON)
    resolutions: Mapped[list[str] | None] = mapped_column(JSON)
    flags: Mapped[list[str] | None] = mapped_column(JSON)
    m3u_provided_uris: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    matched_feed_id: Mapped[str | None] = mapped_column(String(50))
    canonical_name: Mapped[str | None] = mapped_column(String(200))
    alt_names: Mapped[list[str] | None] = mapped_column(JSON)
    categories: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    website: Mapped[str | None] = mapped_column(String(500))
    visit_count: Mapped[int] = mapped_column(default=0)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(30), default=utcnow, onupdate=utcnow)

    m3u_links = relationship("M3UChannel", back_populates="channel", cascade="all, delete-orphan")
    feeds = relationship("Feed", back_populates="channel", cascade="all, delete-orphan")
    watch_sessions = relationship("WatchSession", back_populates="channel", cascade="all, delete-orphan")


class M3UChannel(Base):
    __tablename__ = "m3u_channels"
    __table_args__ = (UniqueConstraint("channel_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(ForeignKey("m3u_sources.id", ondelete="CASCADE"))
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(30), default=utcnow, onupdate=utcnow)

    channel = relationship("Channel", back_populates="m3u_links")
    source = relationship("M3USource", back_populates="channels")


class Feed(Base):
    __tablename__ = "feeds"
    __table_args__ = (UniqueConstraint("channel_id", "feed_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    feed_id: Mapped[str | None] = mapped_column(String(50))
    feed_name: Mapped[str | None] = mapped_column(String(100))
    format: Mapped[str | None] = mapped_column(String(20), index=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    broadcast_area: Mapped[list[str] | None] = mapped_column(JSON)
    languages: Mapped[list[str] | None] = mapped_column(JSON)
    streams: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(30), default=utcnow, onupdate=utcnow)

    channel = relationship("Channel", back_populates="feeds")


Index("idx_feed_broadcast", func.json_extract(Feed.broadcast_area, "$[0]"))


class WatchSession(Base):
    __tablename__ = "watch_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[str] = mapped_column(String(30), index=True)
    ended_at: Mapped[str] = mapped_column(String(30), index=True)
    duration_seconds: Mapped[int] = mapped_column(default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)

    channel = relationship("Channel", back_populates="watch_sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shared: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)


class Settings(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(30), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(30), default=utcnow, onupdate=utcnow)
