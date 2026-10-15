"""Model metadata tests (no live database)."""

from __future__ import annotations

from db.models import Article, Region, RegionDailyStat, Source


def test_region_daily_stats_composite_pk() -> None:
    pk = {col.name for col in RegionDailyStat.__table__.primary_key.columns}
    assert pk == {"region_id", "date", "score_version"}


def test_article_snippet_capped_at_300() -> None:
    snippet = Article.__table__.c.snippet
    assert snippet.type.length == 300


def test_source_type_and_region_level_constraints_exist() -> None:
    source_names = {ck.name for ck in Source.__table__.constraints if ck.name}
    region_names = {ck.name for ck in Region.__table__.constraints if ck.name}
    assert "ck_sources_source_type" in source_names
    assert "ck_regions_level" in region_names
