"""YAML config loader tests. No database and no secrets."""

from __future__ import annotations

from core.yaml_config import flatten_regions, load_channels, load_settings_yaml, load_sources


def test_region_tree_has_world_asia_eu_and_no_states() -> None:
    rows = flatten_regions()
    by_id = {row["id"]: row for row in rows}
    assert "world" in by_id
    assert by_id["world"]["parent_id"] is None
    assert by_id["world"]["level"] == "world"
    assert by_id["india"]["parent_id"] == "asia"
    assert by_id["india"]["iso_code"] == "IN"
    assert by_id["india"]["gdelt_code"] == "IN"
    # GDELT uses FIPS, which differs from ISO for China / Russia / Germany.
    assert by_id["china"]["iso_code"] == "CN"
    assert by_id["china"]["gdelt_code"] == "CH"
    assert by_id["russia"]["iso_code"] == "RU"
    assert by_id["russia"]["gdelt_code"] == "RS"
    assert by_id["germany"]["iso_code"] == "DE"
    assert by_id["germany"]["gdelt_code"] == "GM"
    assert by_id["united_states"]["parent_id"] == "world"
    assert by_id["european_union"]["level"] == "bloc"
    assert by_id["france"]["parent_id"] == "european_union"
    assert all(row["level"] != "state" for row in rows)
    # 1 world + 1 asia + 11 asia children + US + EU + 27 members + Russia
    assert len(rows) == 1 + 1 + 11 + 1 + 1 + 27 + 1


def test_parent_rows_appear_before_children() -> None:
    rows = flatten_regions()
    seen: set[str] = set()
    for row in rows:
        if row["parent_id"] is not None:
            assert row["parent_id"] in seen
        seen.add(row["id"])


def test_channels_list_is_empty_stub() -> None:
    assert load_channels() == []


def test_settings_yaml_score_version() -> None:
    data = load_settings_yaml()
    assert data["score_version"] == "score_v1"
    assert data["retention"]["raw_articles_days"] == 14


def test_sources_include_gdelt_and_inactive_rss() -> None:
    sources = load_sources()
    by_id = {row["id"]: row for row in sources}
    assert by_id["gdelt_doc"]["kind"] == "gdelt"
    assert by_id["gdelt_doc"]["is_active"] is True
    assert by_id["youtube_stub"]["is_active"] is False
    rss = [row for row in sources if row["kind"] == "rss"]
    assert rss, "expected placeholder RSS rows"
    assert all(row["is_active"] is False for row in rss)
    assert all(row["url"] in (None, "") for row in rss)
