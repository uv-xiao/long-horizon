from __future__ import annotations

from pathlib import Path


def next_numeric_id(prefix: str, existing_count: int) -> str:
    return f"{prefix}_{existing_count + 1:06d}"


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())
