"""SQLAlchemy 2.0 models. Schema changes go through Alembic only."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all tables."""


class Region(Base):
    __tablename__ = "regions"
    __table_args__ = (
        CheckConstraint(
            "level IN ('world', 'continent', 'bloc', 'country', 'state')",
            name="ck_regions_level",
        ),
        Index("ix_regions_parent_id", "parent_id"),
        Index("ix_regions_iso_code", "iso_code"),
        Index("ix_regions_gdelt_code", "gdelt_code"),
        Index("ix_regions_level", "level"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    iso_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    gdelt_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped[Region | None] = relationship(remote_side="Region.id", back_populates="children")
    children: Mapped[list[Region]] = relationship(back_populates="parent")


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('rss', 'gdelt', 'youtube')",
            name="ck_sources_kind",
        ),
        CheckConstraint(
            "source_type IN ('independent', 'state_affiliated', 'commentary', 'aggregator')",
            name="ck_sources_source_type",
        ),
        Index("ix_sources_kind", "kind"),
        Index("ix_sources_is_active", "is_active"),
        Index("ix_sources_country_iso", "country_iso"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_iso: Mapped[str | None] = mapped_column(String(8), nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_article_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RawArticle(Base):
    __tablename__ = "raw_articles"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_articles_source_external"),
        Index("ix_raw_articles_fetched_at", "fetched_at"),
        Index("ix_raw_articles_source_id", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    source: Mapped[Source] = relationship()


class Cluster(Base):
    __tablename__ = "clusters"
    __table_args__ = (Index("ix_clusters_last_seen_at", "last_seen_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    top_terms: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outlet_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_articles_url_hash"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_cluster_id", "cluster_id"),
        Index("ix_articles_source_id", "source_id"),
        Index("ix_articles_dedup_group_id", "dedup_group_id"),
        Index("ix_articles_title_norm", "title_norm"),
        Index("ix_articles_raw_id", "raw_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("raw_articles.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    snippet: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"), nullable=True)
    dedup_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[Source] = relationship()
    raw: Mapped[RawArticle] = relationship()
    cluster: Mapped[Cluster | None] = relationship()
    regions: Mapped[list[ArticleRegion]] = relationship(back_populates="article")


class ArticleRegion(Base):
    __tablename__ = "article_regions"
    __table_args__ = (Index("ix_article_regions_region_id", "region_id"),)

    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), primary_key=True)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    article: Mapped[Article] = relationship(back_populates="regions")
    region: Mapped[Region] = relationship()


class RegionDailyStat(Base):
    __tablename__ = "region_daily_stats"
    __table_args__ = (
        Index("ix_region_daily_stats_date", "date"),
        Index("ix_region_daily_stats_heat_score", "heat_score"),
    )

    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    score_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_outlets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    region: Mapped[Region] = relationship()


class TrendingTopic(Base):
    __tablename__ = "trending_topics"
    __table_args__ = (
        Index("ix_trending_topics_computed_at", "computed_at"),
        Index("ix_trending_topics_scope_region_id", "scope_region_id"),
        Index("ix_trending_topics_cluster_id", "cluster_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_region_id: Mapped[str | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"), nullable=True)
    article_count_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outlet_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    momentum: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_version: Mapped[str] = mapped_column(String(32), nullable=False)
    top_article_ids: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    cluster: Mapped[Cluster | None] = relationship()
    scope_region: Mapped[Region | None] = relationship()


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (Index("ix_pipeline_runs_started_at", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    stage_timings: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    articles_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
