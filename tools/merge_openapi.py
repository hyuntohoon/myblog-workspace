"""Merge myblog_backend/openapi.json and myblog_music/openapi.json into
docs/contracts/openapi.json.

Schema names are namespaced by service to prevent collisions:
  Backend_<name>  — from myblog_backend
  Music_<name>    — from myblog_music

All $ref values inside each spec are rewritten to use the new namespaced names
before merging. Paths are non-overlapping in production, so they are merged
as-is.

Usage:
    python tools/merge_openapi.py [backend.json music.json output.json]

Defaults (run from workspace root):
    myblog_backend/openapi.json
    myblog_music/openapi.json
    docs/contracts/openapi.json
"""
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_REF_PREFIX = "#/components/schemas/"


def _rewrite_refs(obj: Any, rename: dict[str, str]) -> Any:
    """Recursively rewrite all $ref values using the rename map."""
    if isinstance(obj, dict):
        return {
            k: (rename.get(v, v) if k == "$ref" else _rewrite_refs(v, rename))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_rewrite_refs(item, rename) for item in obj]
    return obj


def _namespace_spec(spec: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Return a copy of spec with all component schemas namespaced by prefix."""
    original_names = list((spec.get("components") or {}).get("schemas") or {})
    rename = {
        f"{SCHEMA_REF_PREFIX}{name}": f"{SCHEMA_REF_PREFIX}{prefix}{name}"
        for name in original_names
    }
    spec = _rewrite_refs(spec, rename)

    schemas = (spec.get("components") or {}).get("schemas") or {}
    spec["components"]["schemas"] = {
        f"{prefix}{name}": schema for name, schema in schemas.items()
    }
    return spec


def merge(backend_path: Path, music_path: Path, output_path: Path) -> None:
    backend = json.loads(backend_path.read_text())
    music = json.loads(music_path.read_text())

    backend = _namespace_spec(backend, "Backend_")
    music = _namespace_spec(music, "Music_")

    merged: dict = {
        "openapi": backend.get("openapi", "3.1.0"),
        "info": {
            "title": "MyBlog API",
            "version": backend.get("info", {}).get("version", "0.1.0"),
        },
        "paths": {},
        "components": {"schemas": {}},
    }

    # Merge paths — no collisions expected (backend: /api/posts /api/categories
    # /api/metrics /api/publish /health; music: /api/music/*)
    merged["paths"].update(backend.get("paths") or {})
    merged["paths"].update(music.get("paths") or {})

    # Merge schemas
    merged["components"]["schemas"].update(
        (backend.get("components") or {}).get("schemas") or {}
    )
    merged["components"]["schemas"].update(
        (music.get("components") or {}).get("schemas") or {}
    )

    # Merge any other component sections (securitySchemes, parameters, etc.)
    for section in ("securitySchemes", "parameters", "responses", "requestBodies"):
        b_section = (backend.get("components") or {}).get(section) or {}
        m_section = (music.get("components") or {}).get(section) or {}
        if b_section or m_section:
            combined = {**b_section, **m_section}
            merged["components"][section] = combined

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {output_path}  ({len(merged['paths'])} paths, "
          f"{len(merged['components']['schemas'])} schemas)")


if __name__ == "__main__":
    args = sys.argv[1:]
    root = Path(__file__).parent.parent
    backend_path = Path(args[0]) if len(args) > 0 else root / "myblog_backend/openapi.json"
    music_path   = Path(args[1]) if len(args) > 1 else root / "myblog_music/openapi.json"
    output_path  = Path(args[2]) if len(args) > 2 else root / "docs/contracts/openapi.json"

    merge(backend_path, music_path, output_path)
