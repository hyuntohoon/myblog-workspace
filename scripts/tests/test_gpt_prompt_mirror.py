"""The GPT worker's prompts must keep the retired Claude pollers' 의역 wording.

The owner compared models on the lyrics poller's frozen PROMPT_HEADER
(2026-10-08) and chose the GPT worker on that evidence. The worker's own
instruction text had silently diverged to a generic one-line English prompt,
so the comparison did not describe what would run. Read by AST: importing the
modules would pull in the backend and a database.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _assigned(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path.name}")


def _translation_rules(header: str) -> str:
    # The shared range ends where the old CLI header starts its JSON output contract;
    # the worker states that contract once, in gpt_plan_client.
    return header.split("출력은 오직 JSON 배열만")[0].strip()


def _first_lines(text: str, count: int) -> list[str]:
    return text.splitlines()[:count]


def test_lyrics_instructions_keep_the_frozen_paraphrase_rules():
    header = _translation_rules(_assigned(SCRIPTS / "lyrics_translate_poller.py", "PROMPT_HEADER"))
    instructions = _assigned(SCRIPTS / "gpt_translation_store.py", "INSTRUCTIONS")["lyrics"]
    assert _first_lines(instructions, 3)[:2] == _first_lines(header, 2)
    assert instructions.splitlines()[2].startswith(header.splitlines()[2])


def test_genius_instructions_keep_the_frozen_paraphrase_rules():
    header = _translation_rules(_assigned(SCRIPTS / "genius_translate_poller.py", "PROMPT_HEADER"))
    instructions = _assigned(SCRIPTS / "gpt_translation_store.py", "INSTRUCTIONS")["genius"]
    assert _first_lines(instructions, 3) == _first_lines(header, 3)
