#!/usr/bin/env python3
"""WSTA48 redacted aggregation for WSTA42/WSTA43/WSTA45 result JSON.

This is a host-only operator surface.  It reads private run artifacts only when
the operator supplies explicit paths, then emits an allowlisted summary suitable
for reports or handoff notes.  Raw public URLs, confirm tokens, SSIDs, PSKs, and
public-url scratch paths are fail-closed by a final redaction guard.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta43_orchestrated_native_uplink_dpublic as wsta43  # noqa: E402
import run_wsta45_appliance_operator as wsta45  # noqa: E402


REPO_ROOT = wsta43.REPO_ROOT
PASS_SUFFIX = "-pass"
FORBIDDEN_LITERAL_VALUES = (
    wsta25.NATIVE_CONFIRM_TOKEN,
    wsta43.PUBLIC_CONFIRM_TOKEN,
)
FORBIDDEN_TEXT_PATTERNS = (
    "trycloudflare.com",
    "public-url.txt",
    "ssid=",
    "psk=",
)
FORBIDDEN_TEXT_PATTERN_LABELS = (
    "cloudflare-domain",
    "public-url-scratch-path",
    "ssid-assignment",
    "psk-assignment",
)
FORBIDDEN_REGEX = (
    re.compile(r"https?://[^\s\"']+", re.IGNORECASE),
)
FORBIDDEN_REGEX_LABELS = ("http-url",)


def rel(path: Path) -> str:
    return wsta43.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_utc_stamp(value: Any) -> _dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def elapsed_sec(started_utc: Any, ended_utc: Any) -> float | None:
    started = parse_utc_stamp(started_utc)
    ended = parse_utc_stamp(ended_utc)
    if not started or not ended:
        return None
    return round((ended - started).total_seconds(), 3)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def discover_result_files(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        path = item if item.is_absolute() else REPO_ROOT / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("wsta*_result.json")))
        else:
            raise FileNotFoundError(path)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in sorted(files):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def result_kind(path: Path, payload: dict[str, Any]) -> str:
    name = path.name
    scope = str(payload.get("scope") or "")
    if name == "wsta45_result.json" or "WSTA45" in scope:
        return "wsta45"
    if name == "wsta43_result.json" or "WSTA43" in scope:
        return "wsta43"
    if name == "wsta42_result.json" or "WSTA42" in scope:
        return "wsta42"
    return "unknown"


def unknown_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": payload.get("decision"),
        "run_dir": payload.get("run_dir"),
        "gate_decision": payload.get("gate_decision"),
        "checks": {
            key: value
            for key, value in dict(payload.get("checks") or {}).items()
            if isinstance(value, (bool, int, float, type(None)))
        },
        "safety": {
            key: value
            for key, value in dict(payload.get("safety") or {}).items()
            if isinstance(value, (bool, int, float, str, type(None)))
        },
    }


def safe_public_summary(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "wsta45":
        return wsta45.public_summary(payload)
    if kind == "wsta43":
        return wsta43.public_summary(payload)
    if kind == "wsta42":
        return {
            **wsta43.summarize_wsta42(payload),
            "safety": payload.get("safety", {}),
        }
    return unknown_summary(payload)


def summarize_result(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    kind = result_kind(path, payload)
    started = payload.get("started_utc")
    ended = payload.get("ended_utc")
    decision = payload.get("decision")
    return {
        "path": rel(path.resolve()),
        "kind": kind,
        "decision": decision,
        "pass": isinstance(decision, str) and decision.endswith(PASS_SUFFIX),
        "started_utc": started,
        "ended_utc": ended,
        "elapsed_sec": elapsed_sec(started, ended),
        "summary": safe_public_summary(kind, payload),
    }


def redaction_findings(payload: Any) -> list[str]:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    lowered = text.lower()
    findings: list[str] = []
    for value in FORBIDDEN_LITERAL_VALUES:
        if value and value in text:
            findings.append("forbidden-confirm-token-value")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern in lowered:
            findings.append(f"forbidden-text:{pattern}")
    for regex in FORBIDDEN_REGEX:
        if regex.search(text):
            findings.append(f"forbidden-regex:{regex.pattern}")
    return sorted(set(findings))


def build_aggregate(inputs: list[Path]) -> dict[str, Any]:
    files = discover_result_files(inputs)
    entries = [summarize_result(path, load_json(path)) for path in files]
    decisions: dict[str, int] = {}
    for entry in entries:
        decision = str(entry.get("decision") or "missing")
        decisions[decision] = decisions.get(decision, 0) + 1
    aggregate: dict[str, Any] = {
        "scope": "WSTA48 redacted WSTA result aggregation",
        "generated_utc": utc_stamp(),
        "input_count": len(inputs),
        "result_count": len(entries),
        "all_pass": bool(entries) and all(bool(entry.get("pass")) for entry in entries),
        "decisions": dict(sorted(decisions.items())),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "entries": entries,
    }
    findings = redaction_findings(aggregate)
    if findings:
        aggregate["redaction_guard"] = {"ok": False, "findings": findings}
        raise ValueError(json.dumps(aggregate["redaction_guard"], sort_keys=True))
    aggregate["redaction_guard"] = {
        "ok": True,
        "forbidden_literals_checked": len([value for value in FORBIDDEN_LITERAL_VALUES if value]),
        "forbidden_text_patterns_checked": list(FORBIDDEN_TEXT_PATTERN_LABELS),
        "forbidden_regex_checked": list(FORBIDDEN_REGEX_LABELS),
    }
    return aggregate


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, help="Result JSON file or run directory.")
    parser.add_argument("--output", type=Path, help="Optional output JSON path.")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        aggregate = build_aggregate(list(args.input or []))
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta48-redacted-aggregate-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    if args.output:
        output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(json.dumps(aggregate, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
