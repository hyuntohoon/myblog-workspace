#!/usr/bin/env python3
"""Fail CI when workspace mirrors or active-plan RFC pointers drift."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ACTIVE_HEADING = "## Active"
TOP_LEVEL_HEADING_RE = re.compile(r"^##\s+")
TOP_LEVEL_ROW_RE = re.compile(r"^- \*\*(?P<name>[^*]+)\*\*")
DOCS_MARKDOWN_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(docs/[A-Za-z0-9_./-]+\.md)")
RFC_MARKER_RE = re.compile(
    r"<!--\s*rfc:\s*(?P<path>docs/rfcs/[A-Za-z0-9_.-]+\.md)\s*"
    r"\|\s*status:\s*(?P<status>[a-z-]+)\s*-->"
)
RFC_NONE_MARKER_RE = re.compile(r"<!--\s*rfc:\s*none\s*-->")
RFC_STATUS_RE = re.compile(r"^- \*\*Status\*\*:\s*(?P<status>.+?)\s*$", re.MULTILINE)
RFC_STATE_RE = re.compile(r"^(draft|accepted|in-progress|done|retired|reverted)\b")
CLOSED_RFC_STATES = {"done", "retired", "reverted"}


@dataclass(frozen=True)
class PlanRow:
    name: str
    line_number: int
    text: str


def _normalise_status(value: str) -> str:
    """Normalise harmless Markdown emphasis and whitespace, not status meaning."""
    return " ".join(value.replace("**", "").replace("`", "").split()).casefold()


def extract_active_rows(plan_text: str) -> list[PlanRow]:
    """Return top-level list items under ``## Active`` and their indented bodies.

    Unindented notes and blockquotes between rows are intentionally excluded: they
    are section commentary, not part of a top-level plan row.
    """
    lines = plan_text.splitlines()
    try:
        active_index = next(i for i, line in enumerate(lines) if line.strip() == ACTIVE_HEADING)
    except StopIteration as exc:
        raise ValueError(f"missing {ACTIVE_HEADING!r} section") from exc

    rows: list[PlanRow] = []
    index = active_index + 1
    while index < len(lines):
        line = lines[index]
        if TOP_LEVEL_HEADING_RE.match(line):
            break

        match = TOP_LEVEL_ROW_RE.match(line)
        if not match:
            index += 1
            continue

        row_lines = [line]
        row_line_number = index + 1
        index += 1
        while index < len(lines):
            continuation = lines[index]
            if TOP_LEVEL_HEADING_RE.match(continuation) or TOP_LEVEL_ROW_RE.match(continuation):
                break
            if continuation.startswith((" ", "\t")):
                row_lines.append(continuation)
                index += 1
                continue
            if not continuation:
                # Blank lines are formatting inside a list item only when followed
                # by another indented continuation. They carry no checkable text.
                lookahead = index + 1
                if lookahead < len(lines) and lines[lookahead].startswith((" ", "\t")):
                    index += 1
                    continue
            break

        rows.append(
            PlanRow(
                name=match.group("name"),
                line_number=row_line_number,
                text="\n".join(row_lines),
            )
        )

    return rows


def extract_markdown_paths(row: PlanRow) -> list[str]:
    """Extract repository-root ``docs/...md`` references in encounter order."""
    return list(dict.fromkeys(DOCS_MARKDOWN_PATH_RE.findall(row.text)))


def parse_rfc_status(rfc_text: str) -> str:
    match = RFC_STATUS_RE.search(rfc_text)
    if not match:
        raise ValueError("missing RFC '- **Status**:' header")
    status_text = _normalise_status(match.group("status"))
    state = RFC_STATE_RE.match(status_text)
    if not state:
        raise ValueError(f"unsupported RFC Status value: {match.group('status')!r}")
    return state.group(1)


def extract_rfc_markers(row: PlanRow) -> list[tuple[str, str]]:
    """Return explicit RFC path/state metadata from an Active plan row."""
    return [(match.group("path"), match.group("status")) for match in RFC_MARKER_RE.finditer(row.text)]


def validate_plan(root: Path, plan_path: Path | None = None) -> list[str]:
    """Return deterministic validation errors for the Active plan section."""
    plan_path = plan_path or root / "docs" / "plan.md"
    try:
        rows = extract_active_rows(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{plan_path}: {exc}"]

    errors: list[str] = []
    for row in rows:
        location = f"{plan_path}:{row.line_number} ({row.name})"
        markdown_paths = extract_markdown_paths(row)
        for relative_path in markdown_paths:
            if ".." in Path(relative_path).parts:
                errors.append(f"{location}: Markdown path may not traverse parents: {relative_path}")
                continue
            if relative_path == "docs/archive/done" or relative_path.startswith(
                "docs/archive/done/"
            ):
                errors.append(
                    f"{location}: active row references completed archive: {relative_path}"
                )
            if not (root / relative_path).is_file():
                errors.append(f"{location}: referenced Markdown file does not exist: {relative_path}")

        referenced_rfcs = {path for path in markdown_paths if path.startswith("docs/rfcs/")}
        markers = extract_rfc_markers(row)
        none_marker_count = len(RFC_NONE_MARKER_RE.findall(row.text))
        marker_paths = [path for path, _ in markers]
        duplicate_marker_paths = sorted(
            {path for path in marker_paths if marker_paths.count(path) > 1}
        )
        for duplicate_path in duplicate_marker_paths:
            errors.append(f"{location}: duplicate RFC metadata marker: {duplicate_path}")

        declaration_count = len(set(marker_paths)) + none_marker_count
        if declaration_count == 0:
            errors.append(
                f"{location}: Active row must declare one RFC owner or '<!-- rfc: none -->'"
            )
        elif declaration_count > 1:
            errors.append(f"{location}: Active row has multiple RFC ownership declarations")

        if none_marker_count and referenced_rfcs:
            errors.append(
                f"{location}: rfc:none row also references RFC paths: "
                f"{', '.join(sorted(referenced_rfcs))}"
            )

        identity_rfc = root / "docs" / "rfcs" / f"{row.name}.md"
        if none_marker_count and identity_rfc.is_file():
            errors.append(
                f"{location}: rfc:none is invalid because same-identity RFC exists: "
                f"{identity_rfc.relative_to(root)}"
            )

        if len(markers) == 1:
            owner_path, _ = markers[0]
            owner_name = Path(owner_path).stem
            if owner_name != row.name:
                errors.append(
                    f"{location}: RFC owner {owner_name!r} does not match row identity "
                    f"{row.name!r}"
                )

        missing_markers = (
            sorted(referenced_rfcs - set(marker_paths)) if declaration_count else []
        )
        for missing_path in missing_markers:
            errors.append(
                f"{location}: RFC reference lacks machine-readable path/status marker: "
                f"{missing_path}"
            )

        for marker_path, marker_status in markers:
            rfc_path = root / marker_path
            if not rfc_path.is_file():
                # The missing path has already produced the more direct error above.
                continue
            try:
                rfc_status = parse_rfc_status(rfc_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                errors.append(f"{location}: {marker_path}: {exc}")
                continue
            if marker_status != rfc_status:
                errors.append(
                    f"{location}: metadata status {marker_status!r} does not match "
                    f"RFC Status {rfc_status!r} in {marker_path}"
                )
            if rfc_status in CLOSED_RFC_STATES:
                errors.append(
                    f"{location}: Active row points to RFC with closed status "
                    f"{rfc_status!r}: {marker_path}"
                )

    return errors


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_bytes(canonical: Path, mirror: Path, label: str) -> list[str]:
    try:
        canonical_bytes = canonical.read_bytes()
        mirror_bytes = mirror.read_bytes()
    except OSError as exc:
        return [f"{label}: cannot read comparison input: {exc}"]
    if canonical_bytes == mirror_bytes:
        return []
    return [
        f"{label}: byte drift: {canonical} (sha256 {_digest(canonical)}) != "
        f"{mirror} (sha256 {_digest(mirror)})"
    ]


def validate_openapi(
    root: Path, backend_openapi: Path, music_openapi: Path, committed_openapi: Path
) -> list[str]:
    merge_script = root / "tools" / "merge_openapi.py"
    with tempfile.TemporaryDirectory(prefix="workspace-openapi-") as temp_dir:
        generated = Path(temp_dir) / "openapi.json"
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(merge_script),
                    str(backend_openapi),
                    str(music_openapi),
                    str(generated),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            return [f"OpenAPI merge failed: {detail.strip()}"]
        return compare_bytes(generated, committed_openapi, "merged OpenAPI contract")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1], help="workspace root"
    )
    parser.add_argument("--shared-schema", type=Path, required=True)
    parser.add_argument("--backend-openapi", type=Path, required=True)
    parser.add_argument("--music-openapi", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    errors = validate_plan(root)
    errors.extend(
        compare_bytes(
            root / "docs" / "contracts" / "schema.sql",
            args.shared_schema,
            "canonical SQL schema",
        )
    )
    errors.extend(
        validate_openapi(
            root,
            args.backend_openapi,
            args.music_openapi,
            root / "docs" / "contracts" / "openapi.json",
        )
    )

    if errors:
        print("workspace invariant check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("workspace invariants passed: plan/RFC pointers, schema mirror, merged OpenAPI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
