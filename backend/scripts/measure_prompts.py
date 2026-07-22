"""Measure prompt length + token count per sport (Sprint 16C).

Prints a table of character length and a whitespace-word token estimate for every
registered sport's perception and adjudicator prompt, plus the total source size of
the four `sports/<sport>/prompts.py` files. Run it against the pre-refactor tree
(`git stash`) and the post-refactor tree to produce the before/after comparison the
sprint asks for — it is offline and imports nothing that needs a network or key.

    cd backend && python scripts/measure_prompts.py

Note on tokens: we deliberately do NOT use `tiktoken` (that is OpenAI's tokenizer
and mis-counts for Claude). This is a relative before/after measure, so a stable
whitespace-word estimate is sufficient; the character count is exact.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rules.sport_config import supported_sports
from sports import get_sport

_PROMPT_FILES = [
    "sports/basketball/prompts.py",
    "sports/soccer/prompts.py",
    "sports/hockey/prompts.py",
    "sports/lacrosse/prompts.py",
]


def _tokens(text: str) -> int:
    """Whitespace-word token estimate (stable, tokenizer-free)."""
    return len(text.split())


def main() -> None:
    sports = sorted(supported_sports())
    rows: list[tuple[str, int, int]] = []
    total_chars = total_tokens = 0
    print(f"{'prompt':<28}{'chars':>8}{'~tokens':>10}")
    print("-" * 46)
    for name in sports:
        sport = get_sport(name)
        for kind, text in (
            (f"{name} perception", sport.perception_prompt()),
            (f"{name} adjudicator", sport.adjudicator_prompt()),
        ):
            c, t = len(text), _tokens(text)
            total_chars += c
            total_tokens += t
            rows.append((kind, c, t))
            print(f"{kind:<28}{c:>8}{t:>10}")
    print("-" * 46)
    print(f"{'TOTAL (8 prompts)':<28}{total_chars:>8}{total_tokens:>10}")

    src_chars = 0
    here = os.path.join(os.path.dirname(__file__), "..")
    for rel in _PROMPT_FILES:
        with open(os.path.join(here, rel), encoding="utf-8") as fh:
            src_chars += len(fh.read())
    print(f"\nSource size of 4 sport prompts.py files: {src_chars} chars")


if __name__ == "__main__":
    main()
