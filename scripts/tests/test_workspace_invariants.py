from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_workspace_invariants import (  # noqa: E402
    PlanRow,
    compare_bytes,
    extract_active_rows,
    extract_markdown_paths,
    extract_rfc_markers,
    parse_rfc_status,
    validate_openapi,
    validate_plan,
)


class ActivePlanParserTests(unittest.TestCase):
    def test_extracts_only_top_level_active_rows_with_indented_bodies(self) -> None:
        plan = """# Plan

## Active

- **ONE** (`docs/rfcs/ONE.md`, draft) — first line
  continued with `docs/rfcs/TWO.md`.

> Section note mentioning `docs/archive/done/note.md` is not a row.

- **TWO** — second row.
  - nested detail remains part of TWO.

## Backlog

- **IGNORED** (`docs/rfcs/IGNORED.md`, draft)
"""
        rows = extract_active_rows(plan)
        self.assertEqual([row.name for row in rows], ["ONE", "TWO"])
        self.assertEqual(rows[0].line_number, 5)
        self.assertIn("continued", rows[0].text)
        self.assertNotIn("Section note", rows[0].text)
        self.assertIn("nested detail", rows[1].text)

    def test_missing_active_heading_is_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing '## Active'"):
            extract_active_rows("# Plan\n\n## Backlog\n")

    def test_extracts_only_explicit_docs_markdown_paths_and_deduplicates(self) -> None:
        row = PlanRow(
            "ONE",
            3,
            "- **ONE** `docs/rfcs/ONE.md` then [again](docs/rfcs/ONE.md) "
            "and `component-map.md` and `docs/contracts/schema.sql`.",
        )
        self.assertEqual(extract_markdown_paths(row), ["docs/rfcs/ONE.md"])


class PlanInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "docs" / "rfcs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_plan(self, active: str) -> Path:
        plan = self.root / "docs" / "plan.md"
        plan.write_text(f"# Plan\n\n## Active\n\n{active}\n\n## Backlog\n", encoding="utf-8")
        return plan

    def _write_rfc(self, name: str, status: str = "draft") -> None:
        (self.root / "docs" / "rfcs" / name).write_text(
            f"# Test\n\n- **Status**: {status}\n", encoding="utf-8"
        )

    def test_rfc_marker_with_matching_status_passes(self) -> None:
        self._write_rfc("ONE.md", "**draft**")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: draft -->"
        )
        self.assertEqual(validate_plan(self.root, plan), [])

    def test_rfc_marker_status_must_match_rfc_header(self) -> None:
        self._write_rfc("ONE.md", "accepted")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: draft -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("metadata status 'draft' does not match RFC Status 'accepted'", errors[0])

    def test_rfc_status_parser_accepts_descriptive_suffix(self) -> None:
        self._write_rfc("ONE.md", "**in-progress** — Step 2")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: in-progress -->"
        )
        self.assertEqual(validate_plan(self.root, plan), [])

    def test_rfc_reference_without_marker_fails_closed(self) -> None:
        self._write_rfc("ONE.md", "accepted")
        plan = self._write_plan(
            "- **ONE** (**draft; prose note**) — summary. → `docs/rfcs/ONE.md`."
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("must declare one RFC owner", errors[0])

    def test_every_active_row_requires_explicit_owner_or_none(self) -> None:
        plan = self._write_plan("- **ONE** — no RFC path and no declaration.")
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("must declare one RFC owner", errors[0])

    def test_rfc_owner_must_match_row_identity(self) -> None:
        self._write_rfc("TWO.md", "accepted")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/TWO.md | status: accepted -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("RFC owner 'TWO' does not match row identity 'ONE'", errors[0])

    def test_rfc_none_cannot_hide_an_rfc_reference(self) -> None:
        self._write_rfc("ONE.md", "draft")
        plan = self._write_plan(
            "- **ROW** — `docs/rfcs/ONE.md`\n"
            "  <!-- rfc: none -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("rfc:none row also references RFC paths" in error for error in errors))
        self.assertTrue(any("lacks machine-readable path/status marker" in error for error in errors))

    def test_rfc_none_cannot_hide_same_identity_rfc(self) -> None:
        self._write_rfc("ONE.md", "draft")
        plan = self._write_plan(
            "- **ONE** — path and owner marker were removed.\n"
            "  <!-- rfc: none -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("rfc:none is invalid because same-identity RFC exists", errors[0])

    def test_closed_rfc_status_is_rejected_from_active(self) -> None:
        self._write_rfc("ONE.md", "**retired** — no active steps")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: retired -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("Active row points to RFC with closed status 'retired'", errors[0])

    def test_duplicate_rfc_marker_fails(self) -> None:
        self._write_rfc("ONE.md", "draft")
        plan = self._write_plan(
            "- **ONE** — summary\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: draft -->\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: draft -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate RFC metadata marker", errors[0])

    def test_every_referenced_docs_markdown_path_must_exist(self) -> None:
        plan = self._write_plan(
            "- **ONE** — links `docs/rfcs/MISSING.md` and `docs/reviews/also-missing.md`."
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 3)
        self.assertEqual(sum("does not exist" in error for error in errors), 2)
        self.assertEqual(
            sum("must declare one RFC owner" in error for error in errors), 1
        )

    def test_active_row_must_not_reference_completed_archive(self) -> None:
        archived = self.root / "docs" / "archive" / "done" / "rfcs" / "ONE.md"
        archived.parent.mkdir(parents=True)
        archived.write_text("done", encoding="utf-8")
        plan = self._write_plan(
            f"- **ONE** — `{archived.relative_to(self.root)}`.\n"
            "  <!-- rfc: none -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("active row references completed archive", errors[0])

    def test_markdown_reference_cannot_escape_through_parent_segments(self) -> None:
        plan = self._write_plan(
            "- **ONE** — `docs/contracts/../../outside.md`.\n"
            "  <!-- rfc: none -->"
        )
        errors = validate_plan(self.root, plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("may not traverse parents", errors[0])

    def test_unindented_active_section_note_is_not_treated_as_a_row_reference(self) -> None:
        plan = self._write_plan(
            "- **ONE** — no RFC.\n"
            "  <!-- rfc: none -->\n\n"
            "> Historical note → `docs/archive/done/rfcs/OLD.md`.\n\n"
            "- **TWO** — no RFC.\n"
            "  <!-- rfc: none -->"
        )
        self.assertEqual(validate_plan(self.root, plan), [])

    def test_current_plan_shape_is_parseable_and_satisfies_plan_invariants(self) -> None:
        rows = extract_active_rows((ROOT / "docs" / "plan.md").read_text(encoding="utf-8"))
        self.assertGreater(len(rows), 1)
        self.assertEqual(rows[0].name, "SEC-system-hardening")
        self.assertEqual(validate_plan(ROOT), [])


class FileInvariantTests(unittest.TestCase):
    def test_byte_comparison_rejects_even_trailing_newline_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canonical = root / "canonical"
            mirror = root / "mirror"
            canonical.write_bytes(b"same\n")
            mirror.write_bytes(b"same")
            errors = compare_bytes(canonical, mirror, "test mirror")
            self.assertEqual(len(errors), 1)
            self.assertIn("byte drift", errors[0])

    def test_byte_comparison_accepts_identical_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canonical = root / "canonical"
            mirror = root / "mirror"
            canonical.write_bytes(b"same\n")
            mirror.write_bytes(b"same\n")
            self.assertEqual(compare_bytes(canonical, mirror, "test mirror"), [])

    def test_rfc_status_header_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing RFC"):
            parse_rfc_status("# No metadata\n")

    def test_rfc_marker_extraction_is_explicit(self) -> None:
        row = PlanRow(
            "ONE",
            3,
            "- **ONE** `docs/rfcs/ONE.md`\n"
            "  <!-- rfc: docs/rfcs/ONE.md | status: accepted -->",
        )
        self.assertEqual(
            extract_rfc_markers(row), [("docs/rfcs/ONE.md", "accepted")]
        )

    def test_openapi_is_regenerated_with_the_canonical_merge_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            backend = temp / "backend.json"
            music = temp / "music.json"
            committed = temp / "committed.json"
            backend.write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "info": {"version": "1.2.3"},
                        "paths": {"/api/a": {}},
                        "components": {"schemas": {"Thing": {"type": "string"}}},
                    }
                ),
                encoding="utf-8",
            )
            music.write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "paths": {"/api/music/a": {}},
                        "components": {"schemas": {"Thing": {"type": "integer"}}},
                    }
                ),
                encoding="utf-8",
            )
            expected = {
                "openapi": "3.1.0",
                "info": {"title": "MyBlog API", "version": "1.2.3"},
                "paths": {"/api/a": {}, "/api/music/a": {}},
                "components": {
                    "schemas": {
                        "Backend_Thing": {"type": "string"},
                        "Music_Thing": {"type": "integer"},
                    }
                },
            }
            committed.write_text(
                json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

            self.assertEqual(validate_openapi(ROOT, backend, music, committed), [])

            committed.write_text("{}\n", encoding="utf-8")
            errors = validate_openapi(ROOT, backend, music, committed)
            self.assertEqual(len(errors), 1)
            self.assertIn("merged OpenAPI contract: byte drift", errors[0])


if __name__ == "__main__":
    unittest.main()
