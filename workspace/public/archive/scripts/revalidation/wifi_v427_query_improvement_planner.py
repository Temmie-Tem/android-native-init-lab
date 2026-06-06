#!/usr/bin/env python3
"""V427 host-only planner for native Wi-Fi service-query improvement.

V427 consumes V426/V425/V423 evidence and classifies whether the current target
matches prove live hwservice registration or only VINTF/declaration surface.
It does not run ADB, start daemons, mutate the device, or perform Wi-Fi
bring-up.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_hwservice_inventory_v423 import TARGETED_WAIT_TARGETS


DEFAULT_OUT_DIR = Path("tmp/wifi/v427-query-improvement-planner")
DEFAULT_V426_PATTERN = "v426-service-surface-run*"
FETCH_NULL_RE = re.compile(r'Warning: Skipping "(?P<target>[^"]+)": cannot be fetched from service manager \\(null\\)')
FETCH_ERROR_RE = re.compile(r'Warning: Skipping "(?P<target>[^"]+)": (?P<reason>.*)')
LITERAL_STATUS_WORDS = {"alive", "registered;dead", "declared"}


@dataclass
class TargetStatus:
    target: str
    line_present: bool
    warning_present: bool
    null_fetch_warning: bool
    status_token: str
    interpretation: str
    evidence: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v426-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_manifest(pattern: str) -> Path | None:
    candidates = sorted(repo_path("tmp/wifi").glob(pattern), key=lambda path: path.stat().st_mtime)
    for candidate in reversed(candidates):
        manifest = candidate / "manifest.json"
        if manifest.exists():
            return manifest
    return None


def choose_v426_manifest(args: argparse.Namespace) -> Path | None:
    if args.v426_manifest:
        return repo_path(args.v426_manifest)
    return latest_manifest(DEFAULT_V426_PATTERN)


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": ""}
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def v425_manifest_from_v426(v426: dict[str, Any]) -> Path | None:
    text = (((v426.get("inputs") or {}).get("v425_manifest")) or "").strip()
    return Path(text) if text else None


def v423_dir_from_v425(v425_path: Path | None) -> Path | None:
    if v425_path is None:
        return None
    return v425_path.parent / "v423-android-hwservice-bootcomplete-run"


def command_texts(v423_dir: Path | None) -> dict[str, str]:
    if v423_dir is None:
        return {}
    return {
        "lshal_binderized": read_text(v423_dir / "commands" / "lshal-binderized-neat.txt"),
        "lshal_wifi_filter": read_text(v423_dir / "commands" / "lshal-wifi-filter.txt"),
        "service_list": read_text(v423_dir / "commands" / "service-list-wifi.txt"),
        "processes": read_text(v423_dir / "commands" / "service-processes.txt"),
        "props": read_text(v423_dir / "commands" / "identity-props.txt"),
    }


def collect_target_status(texts: dict[str, str]) -> list[TargetStatus]:
    combined_lshal = texts.get("lshal_binderized", "") + "\n" + texts.get("lshal_wifi_filter", "")
    statuses: list[TargetStatus] = []
    for target in TARGETED_WAIT_TARGETS:
        evidence = [line.strip() for line in combined_lshal.splitlines() if target in line]
        warning_lines = [line for line in evidence if line.startswith("Warning:")]
        null_warning = any("cannot be fetched from service manager (null)" in line for line in warning_lines)
        status_token = ""
        for line in evidence:
            tokens = line.split()
            for token in tokens:
                if token in LITERAL_STATUS_WORDS:
                    status_token = token
                    break
            if status_token:
                break
        if null_warning:
            interpretation = "declared-or-listed-but-get-null"
        elif status_token == "alive":
            interpretation = "alive-registered"
        elif status_token == "registered;dead":
            interpretation = "registered-dead"
        elif status_token == "declared":
            interpretation = "declared-only"
        elif evidence:
            interpretation = "present-without-explicit-status"
        else:
            interpretation = "not-present"
        statuses.append(TargetStatus(
            target=target,
            line_present=bool(evidence),
            warning_present=bool(warning_lines),
            null_fetch_warning=null_warning,
            status_token=status_token,
            interpretation=interpretation,
            evidence=evidence[:12],
        ))
    return statuses


def improvement_options(v426: dict[str, Any], target_statuses: list[TargetStatus]) -> list[dict[str, Any]]:
    all_null = all(status.null_fetch_warning for status in target_statuses)
    all_present = all(status.line_present for status in target_statuses)
    v426_decision = v426.get("decision")
    options = [
        {
            "id": "v428-explicit-lshal-status-columns",
            "rank": 1,
            "decision": "recommended",
            "reason": "V425 output has target rows, but current columns do not include explicit service status and all targets have get-null warnings" if all_null else "explicit service-status columns are still the lowest-risk next probe",
            "native_scope": "add helper/runner mode for /system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c under the existing composite namespace",
            "android_scope": "optional Android handoff read-only mirror using the same explicit columns after sys.boot_completed=1",
            "mutations": "service-manager/HAL start-only only if using existing bounded composite path; no scan/connect/link-up",
        },
        {
            "id": "v428-vintf-only-control",
            "rank": 2,
            "decision": "recommended-control",
            "reason": "AOSP lshal separates VINTF manifest rows from binderized services; VINTF-only output can prove declaration surface without waiting on hwservicemanager registration",
            "native_scope": "run /system/bin/lshal list --types=vintf --neat -V -S -i as a no-HAL-start control",
            "android_scope": "compare with V425 VINTF grep and Android lshal output",
            "mutations": "read-only command only",
        },
        {
            "id": "android-managed-runtime-pivot",
            "rank": 3,
            "decision": "defer",
            "reason": "if explicit status still shows declared/get-null and Android framework owns supplicant/services, Wi-Fi control may need Android-managed runtime rather than native service-manager recreation",
            "native_scope": "none until V428 proves service status",
            "android_scope": "read-only Android framework state mapping before any enable/scan/connect",
            "mutations": "deferred",
        },
    ]
    if v426_decision != "v426-native-registration-surface-gap" or not all_present:
        options[0]["decision"] = "blocked"
        options[0]["reason"] = "V426 does not yet prove all target rows are present"
    return options


def decide(v426: dict[str, Any], target_statuses: list[TargetStatus], options: list[dict[str, Any]]) -> tuple[str, bool, str]:
    if not v426.get("present"):
        return "v427-missing-v426-evidence", False, "V426 manifest is missing"
    if v426.get("decision") != "v426-native-registration-surface-gap":
        return "v427-waiting-for-native-gap-evidence", True, f"V426 decision is {v426.get('decision')}"
    if all(status.null_fetch_warning for status in target_statuses):
        return "v427-explicit-status-query-needed", True, "target rows are present but all have get-null warnings; explicit lshal service-status/VINTF split is the next minimal read-only improvement"
    if any(status.interpretation == "alive-registered" for status in target_statuses):
        return "v427-registration-alive-evidence-present", True, "at least one target has explicit alive status; next step can narrow native parity"
    if any(option["decision"] == "recommended" for option in options):
        return "v427-query-improvement-plan-ready", True, "query improvement options are ready"
    return "v427-query-improvement-review-needed", True, "manual review required"


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v426_path = choose_v426_manifest(args)
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v427-query-improvement-planner-plan-ready",
        "pass": True,
        "reason": "host-only query improvement planner is ready",
        "host": collect_host_metadata(),
        "inputs": {
            "v426_manifest": str(v426_path) if v426_path else "",
            "v426_present": bool(v426_path and v426_path.exists()),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_planner(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v426_path = choose_v426_manifest(args)
    v426 = load_json(v426_path)
    v425_path = v425_manifest_from_v426(v426)
    v425 = load_json(v425_path)
    v423_dir = v423_dir_from_v425(v425_path)
    texts = command_texts(v423_dir)
    target_statuses = collect_target_status(texts)
    options = improvement_options(v426, target_statuses)
    decision, pass_ok, reason = decide(v426, target_statuses, options)
    source_notes = [
        {
            "source": "AOSP ListCommand.cpp",
            "url": "https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp",
            "relevant_lines": "fetchBinderized list/get and get-null warning; fetchManifestHals DECLARED rows; -V/-S/--types option descriptions",
        }
    ]
    parsed = {
        "target_statuses": [asdict(status) for status in target_statuses],
        "improvement_options": options,
        "source_notes": source_notes,
        "v426_native_gaps": (v426.get("parsed") or {}).get("native_gaps", []),
    }
    store.write_json("query-improvement-plan.json", parsed)
    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "v426_manifest": v426.get("path", ""),
            "v426_decision": v426.get("decision"),
            "v426_pass": v426.get("pass"),
            "v425_manifest": str(v425_path) if v425_path else "",
            "v425_decision": v425.get("decision"),
            "v425_pass": v425.get("pass"),
            "v423_evidence_dir": str(v423_dir) if v423_dir else "",
        },
        "parsed": parsed,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    statuses = manifest.get("parsed", {}).get("target_statuses", [])
    status_rows = [
        [
            status["target"],
            "yes" if status["line_present"] else "no",
            "yes" if status["null_fetch_warning"] else "no",
            status["status_token"] or "-",
            status["interpretation"],
        ]
        for status in statuses
    ]
    option_rows = [
        [
            str(option["rank"]),
            option["id"],
            option["decision"],
            option["reason"],
        ]
        for option in manifest.get("parsed", {}).get("improvement_options", [])
    ]
    gap_rows = [[gap] for gap in manifest.get("parsed", {}).get("v426_native_gaps", [])]
    return "\n".join(
        [
            "# V427 Query Improvement Planner",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Target Status",
            "",
            markdown_table(["target", "line", "get-null", "status", "interpretation"], status_rows if status_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Improvement Options",
            "",
            markdown_table(["rank", "option", "decision", "reason"], option_rows if option_rows else [["-", "-", "-", "-"]]),
            "",
            "## Native Gaps",
            "",
            markdown_table(["gap"], gap_rows if gap_rows else [["-"]]),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = run_plan(args, store) if args.command == "plan" else run_planner(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
