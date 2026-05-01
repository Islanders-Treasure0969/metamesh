"""Shared helpers for generator backends (dbt, semantic layer, ...).

Pure helpers - no MCP dependency. Anything that operates on the
JSON-LD documents and is reusable across multiple output formats
lives here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EXT_NAMESPACES: tuple[str, ...] = ("dv", "kimball")
NAMING_STRATEGIES = frozenset({"as_is", "dv_lower", "snake"})


def load_jsonld_dir(path: Path) -> list[dict[str, Any]]:
    """Load every ``*.jsonld`` file in a directory, sorted by filename."""
    if not path.exists():
        return []
    docs: list[dict[str, Any]] = []
    for p in sorted(path.glob("*.jsonld")):
        with open(p, encoding="utf-8") as f:
            docs.append(json.load(f))
    return docs


def snake(name: str) -> str:
    """PascalCase / camelCase -> snake_case. Already-snake passes through."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def model_name(doc: dict[str, Any], *, oid: str, naming: str) -> str:
    """Resolve the dbt-style model name for a Concept or Relationship."""
    if naming == "as_is":
        return oid
    if naming == "dv_lower":
        for key in ("dv:hub", "dv:link"):
            v = doc.get(key)
            if isinstance(v, str) and v:
                return v.lower()
        return snake(oid)
    if naming == "snake":
        return snake(oid)
    raise ValueError(f"unknown naming strategy: {naming!r}")


def validate_naming(naming: str) -> None:
    if naming not in NAMING_STRATEGIES:
        raise ValueError(
            f"unknown naming strategy: {naming!r}. allowed: {sorted(NAMING_STRATEGIES)}"
        )


def label_for_lang(values: Any, lang: str) -> str | None:
    """Pick a value from a SKOS-style multilingual list by @language tag."""
    if values is None:
        return None
    if isinstance(values, str):
        return values
    if isinstance(values, dict):
        if values.get("@language") == lang:
            return values.get("@value")
        return values.get("@value")
    if isinstance(values, list):
        for v in values:
            if isinstance(v, dict) and v.get("@language") == lang:
                return v.get("@value")
    return None


def split_alt_labels(values: Any) -> tuple[list[str], list[str]]:
    """Split skos:altLabel array into (ja_list, en_list)."""
    if not values:
        return [], []
    if isinstance(values, dict):
        values = [values]
    ja = [v["@value"] for v in values if isinstance(v, dict) and v.get("@language") == "ja"]
    en = [v["@value"] for v in values if isinstance(v, dict) and v.get("@language") == "en"]
    return ja, en


def attach_extension_meta(*, doc: dict[str, Any], meta: dict[str, Any]) -> None:
    """Lift ``dv:`` / ``kimball:`` properties into a nested meta dict."""
    for ns in EXT_NAMESPACES:
        prefix = ns + ":"
        ext: dict[str, Any] = {}
        for k, v in doc.items():
            if k.startswith(prefix):
                ext[k[len(prefix):]] = v
        if ext:
            meta[ns] = ext
