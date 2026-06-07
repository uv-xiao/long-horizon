from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # Python 3.10 fallback for the small TOML subset we write.
    tomllib = None


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        return _parse_simple_toml(path.read_text(encoding="utf-8"))
    with path.open("rb") as fh:
        return tomllib.load(fh)


def toml_dumps(data: dict[str, Any]) -> str:
    lines: list[str] = []
    scalars: dict[str, Any] = {}
    tables: dict[str, dict[str, Any]] = {}
    arrays: dict[str, list[dict[str, Any]]] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            tables[key] = value
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            arrays[key] = value
        else:
            scalars[key] = value
    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_value(value)}")
    if scalars and (tables or arrays):
        lines.append("")
    for name, table in tables.items():
        lines.append(f"[{name}]")
        for key, value in table.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    for name, items in arrays.items():
        for item in items:
            lines.append(f"[[{name}]]")
            for key, value in item.items():
                lines.append(f"{key} = {_toml_value(value)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def _parse_simple_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] = data
    array_name: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            array_name = line[2:-2].strip()
            data.setdefault(array_name, [])
            item: dict[str, Any] = {}
            data[array_name].append(item)
            current = item
            continue
        if line.startswith("[") and line.endswith("]"):
            array_name = None
            name = line[1:-1].strip()
            data.setdefault(name, {})
            current = data[name]
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = _parse_simple_value(value.strip())
    return data


def _parse_simple_value(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_simple_value(part.strip()) for part in _split_simple_array(inner)]
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    try:
        return int(value)
    except ValueError:
        return value


def _split_simple_array(inner: str) -> list[str]:
    parts: list[str] = []
    buf = ""
    in_str = False
    escape = False
    for ch in inner:
        if ch == "\\" and in_str:
            escape = not escape
            buf += ch
            continue
        if ch == '"' and not escape:
            in_str = not in_str
        if ch == "," and not in_str:
            parts.append(buf)
            buf = ""
        else:
            parts.append(ch) if False else None
            buf += ch
        escape = False
    if buf:
        parts.append(buf)
    return parts


def write_toml(path: Path, data: dict[str, Any]) -> None:
    write_text(path, toml_dumps(data))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def copy_file(src: Path, dst: Path) -> None:
    ensure_dir(dst.parent)
    dst.write_bytes(src.read_bytes())
