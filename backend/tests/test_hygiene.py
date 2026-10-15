"""Repo-hygiene smoke tests. These do not hit the network or the database."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_requirements_lists_core_stack() -> None:
    """The pinned stack must stay light: no torch / spaCy / sentence-transformers."""
    text = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in (
        "fastapi",
        "sqlalchemy",
        "alembic",
        "pydantic",
        "psycopg",
        "scikit-learn",
        "rapidfuzz",
    ):
        assert package in text, f"expected {package} in requirements.txt"
    for banned in ("torch", "sentence-transformers", "spacy"):
        # Comments may mention these as omitted; the install line must not exist.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            assert banned not in stripped, f"banned heavy dep on install line: {stripped}"


def test_python_version_is_3_11_or_newer() -> None:
    """Render and local tooling both assume 3.11+ (Pydantic v2, FastAPI)."""
    assert sys.version_info >= (3, 11), f"need Python 3.11+, got {sys.version}"


def test_backend_entrypoints_exist() -> None:
    """Render and Alembic both assume these files live under backend/."""
    assert (BACKEND_ROOT / "main.py").exists()
    assert (BACKEND_ROOT / "alembic.ini").exists()
