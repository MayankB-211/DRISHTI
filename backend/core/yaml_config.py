"""Load repo YAML. Used by seed.py and the pipeline — not by the API at runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.config import get_config_dir

REGION_LEVELS = frozenset({"world", "continent", "bloc", "country", "state"})
SOURCE_TYPES = frozenset({"independent", "state_affiliated", "commentary", "aggregator"})
SOURCE_KINDS = frozenset({"rss", "gdelt", "youtube"})


def _read(name: str) -> Any:
    path = get_config_dir() / name
    if not path.is_file():
        raise FileNotFoundError(f"config file not found: {path.name}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if data is not None else {}


def load_settings_yaml() -> dict[str, Any]:
    data = _read("settings.yaml")
    if not isinstance(data, dict):
        raise ValueError("settings.yaml must be a mapping")
    return data


def load_channels() -> list[dict[str, Any]]:
    data = _read("channels.yaml")
    channels = data.get("channels", []) if isinstance(data, dict) else []
    if channels is None:
        return []
    if not isinstance(channels, list):
        raise ValueError("channels.yaml: 'channels' must be a list")
    return channels


def load_sources() -> list[dict[str, Any]]:
    data = _read("sources.yaml")
    sources = data.get("sources", []) if isinstance(data, dict) else []
    if not isinstance(sources, list):
        raise ValueError("sources.yaml: 'sources' must be a list")
    for source in sources:
        kind = source.get("kind")
        source_type = source.get("source_type")
        if kind not in SOURCE_KINDS:
            raise ValueError(f"source {source.get('id')!r} has invalid kind {kind!r}")
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"source {source.get('id')!r} has invalid source_type {source_type!r}")
    return sources


def flatten_regions(
    nodes: list[dict[str, Any]] | None = None,
    parent_id: str | None = None,
) -> list[dict[str, Any]]:
    """Turn the nested regions.yaml tree into a parent-before-child flat list."""
    if nodes is None:
        data = _read("regions.yaml")
        nodes = data.get("regions", []) if isinstance(data, dict) else []
    if not isinstance(nodes, list):
        raise ValueError("regions.yaml: 'regions' must be a list")

    rows: list[dict[str, Any]] = []
    for node in nodes:
        region_id = node["id"]
        level = node["level"]
        if level not in REGION_LEVELS:
            raise ValueError(f"region {region_id!r} has invalid level {level!r}")
        row = {
            "id": region_id,
            "parent_id": node.get("parent_id", parent_id),
            "level": level,
            "iso_code": node.get("iso_code"),
            "gdelt_code": node.get("gdelt_code"),
            "name": node["name"],
            "lat": node.get("lat"),
            "lon": node.get("lon"),
            "is_active": bool(node.get("is_active", True)),
            "keywords": list(node.get("keywords") or []),
        }
        rows.append(row)
        children = node.get("children") or []
        rows.extend(flatten_regions(children, parent_id=region_id))
    return rows


def config_dir() -> Path:
    return get_config_dir()
