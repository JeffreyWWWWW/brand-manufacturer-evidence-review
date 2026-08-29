"""Deterministically validate evidence-review JSON/DOCX output names."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def expected_scope(payload: dict) -> str:
    report = payload.get("报告信息", {})
    explicit = report.get("项目名") or report.get("项目或品牌范围")
    if explicit:
        return str(explicit).strip()
    brands = payload.get("调查范围", {}).get("目标品牌", [])
    if len(brands) == 1:
        return str(brands[0].get("规范名称") or brands[0].get("原始名称")).strip()
    return f"{len(brands)}品牌"


def expected_names(payload: dict) -> tuple[str, str]:
    info = payload["报告信息"]
    date_value = str(info["调查日期"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
        raise ValueError(f"invalid investigation date: {date_value!r}")
    try:
        date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValueError(f"invalid investigation date: {date_value!r}") from exc
    compact_date = date_value.replace("-", "")
    scope = expected_scope(payload)
    if FORBIDDEN.search(scope) or scope.rstrip(" .") != scope or not scope:
        raise ValueError(f"invalid scope name: {scope!r}")
    return (
        f"{scope}_品牌权属与制造商证据底稿_{compact_date}.json",
        f"{scope}_品牌权属与制造商证据复核报告_{compact_date}.docx",
    )


def validate(payload_or_path: dict | Path, json_path: Path, docx_path: Path) -> None:
    payload = (
        json.loads(payload_or_path.read_text(encoding="utf-8"))
        if isinstance(payload_or_path, Path)
        else payload_or_path
    )
    expected_json, expected_docx = expected_names(payload)
    if json_path.name != expected_json:
        raise ValueError(f"JSON_FILENAME_MISMATCH expected={expected_json} actual={json_path.name}")
    if docx_path.name != expected_docx:
        raise ValueError(f"DOCX_FILENAME_MISMATCH expected={expected_docx} actual={docx_path.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("payload", type=Path)
    ap.add_argument("json_output", type=Path)
    ap.add_argument("docx_output", type=Path)
    args = ap.parse_args()
    try:
        validate(args.payload, args.json_output, args.docx_output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"OUTPUT_FILENAME_INVALID {exc}")
    print("OUTPUT_FILENAME_OK")
