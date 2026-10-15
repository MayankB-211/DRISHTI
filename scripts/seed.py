#!/usr/bin/env python3
"""Idempotent YAML → Postgres sync.

Run from repo root via `make seed`, or:
    cd backend && python ../scripts/seed.py

The API never reads these YAML files at runtime.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core.logging import configure_logging  # noqa: E402
from core.yaml_config import flatten_regions, load_sources  # noqa: E402
from db.models import Region, Source  # noqa: E402
from db.session import get_session_factory  # noqa: E402

log = logging.getLogger("seed")

# Columns the seed is allowed to overwrite. Operational fields (last_success_at,
# last_error, last_article_count) are owned by the pipeline.
SOURCE_SYNC_FIELDS = ("name", "kind", "url", "country_iso", "language", "source_type", "is_active")
REGION_SYNC_FIELDS = (
    "parent_id",
    "level",
    "iso_code",
    "gdelt_code",
    "name",
    "lat",
    "lon",
    "is_active",
)


def upsert_regions(session: Session, rows: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    seen: set[str] = set()
    for row in rows:
        region_id = row["id"]
        seen.add(region_id)
        existing = session.get(Region, region_id)
        values = {field: row[field] for field in REGION_SYNC_FIELDS}
        if existing is None:
            session.add(Region(id=region_id, **values))
            inserted += 1
        else:
            changed = False
            for field, value in values.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                updated += 1
    # Deactivate regions that disappeared from YAML rather than deleting (FKs).
    yaml_ids = seen
    extras = session.scalars(select(Region).where(Region.id.not_in(yaml_ids))).all()
    deactivated = 0
    for extra in extras:
        if extra.is_active:
            extra.is_active = False
            deactivated += 1
    if deactivated:
        log.info("deactivated_regions", extra={"count": deactivated})
    return inserted, updated


def upsert_sources(session: Session, rows: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    seen: set[str] = set()
    for row in rows:
        source_id = row["id"]
        seen.add(source_id)
        existing = session.get(Source, source_id)
        values = {field: row.get(field) for field in SOURCE_SYNC_FIELDS}
        if values["language"] is None:
            values["language"] = "en"
        if existing is None:
            session.add(Source(id=source_id, **values))
            inserted += 1
        else:
            changed = False
            for field, value in values.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                updated += 1
    extras = session.scalars(select(Source).where(Source.id.not_in(seen))).all()
    deactivated = 0
    for extra in extras:
        if extra.is_active:
            extra.is_active = False
            deactivated += 1
    if deactivated:
        log.info("deactivated_sources", extra={"count": deactivated})
    return inserted, updated


def run() -> None:
    configure_logging()
    factory = get_session_factory(pooled=False)
    session = factory()
    try:
        regions = flatten_regions()
        sources = load_sources()
        r_ins, r_upd = upsert_regions(session, regions)
        s_ins, s_upd = upsert_sources(session, sources)
        session.commit()
        n_regions = len(session.scalars(select(Region.id)).all())
        n_sources = len(session.scalars(select(Source.id)).all())
        n_active_sources = len(
            session.scalars(select(Source.id).where(Source.is_active.is_(True))).all()
        )
        log.info(
            "seed_complete",
            extra={
                "regions_inserted": r_ins,
                "regions_updated": r_upd,
                "regions_total": n_regions,
                "sources_inserted": s_ins,
                "sources_updated": s_upd,
                "sources_total": n_sources,
                "sources_active": n_active_sources,
            },
        )
        print(
            f"seed ok: regions={n_regions} (ins={r_ins} upd={r_upd}) "
            f"sources={n_sources} active={n_active_sources} (ins={s_ins} upd={s_upd})"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
