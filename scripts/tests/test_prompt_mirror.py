"""The vendored research prompt must mirror the canonical one.

`scripts/album_research_v2.md` is what the poller actually sends;
`docs/editorial/album-research-prompt.md` is the canonical document a human
edits and pastes into the claude.ai Project. They are kept identical **over the
shared range** — the canonical file additionally carries a workspace-only
validation log behind an explicit marker, which must never reach the model.

Why a test: the parity was convention-only, and on 2026-07-30 the RFC was found
claiming the two files were byte-identical when they had never been (the
appendix). A silent drift here means the poller ships a prompt nobody reviewed —
the same failure class as the schema.sql mirror that drifted for five days.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDORED = ROOT / "scripts" / "album_research_v2.md"
CANONICAL = ROOT / "docs" / "editorial" / "album-research-prompt.md"
MARKER = "> Everything below is workspace record"


def test_vendored_prompt_is_the_canonical_prompts_shared_range():
    vendored = VENDORED.read_text(encoding="utf-8")
    canonical = CANONICAL.read_text(encoding="utf-8")
    assert canonical.startswith(vendored), (
        "vendored prompt and canonical prompt have drifted over the shared range — "
        "re-sync before the poller sends an unreviewed prompt"
    )


def test_the_workspace_only_appendix_never_reaches_the_model():
    assert MARKER in CANONICAL.read_text(encoding="utf-8"), "appendix marker moved"
    assert MARKER not in VENDORED.read_text(encoding="utf-8"), (
        "the validation log is workspace record, not prompt text"
    )
