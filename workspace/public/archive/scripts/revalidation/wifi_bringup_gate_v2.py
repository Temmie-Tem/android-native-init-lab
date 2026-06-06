#!/usr/bin/env python3
"""Evaluate lifecycle-aware Wi-Fi bring-up preflight gate v2."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V211_MANIFEST = Path("tmp/wifi/v211-firmware-path-policy/manifest.json")
DEFAULT_V212_MANIFEST = Path("tmp/wifi/v212-firmware-path-rollback/manifest.json")
DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V217_NATIVE_MANIFEST = Path("tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json")
DEFAULT_V218_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun/manifest.json")
DEFAULT_V219_MANIFEST = Path("tmp/wifi/v219-native-android-env-shim/manifest.json")

ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v220-bringup-gate-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v211-manifest", type=Path, default=DEFAULT_V211_MANIFEST)
    parser.add_argument("--v212-manifest", type=Path, default=DEFAULT_V212_MANIFEST)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v217-native-manifest", type=Path, default=DEFAULT_V217_NATIVE_MANIFEST)
    parser.add_argument("--v218-manifest", type=Path, default=DEFAULT_V218_MANIFEST)
    parser.add_argument("--v219-manifest", type=Path, default=DEFAULT_V219_MANIFEST)
    return parser.parse_args()


def validate_no_active_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv in NO_DEVICE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def gate_item(name: str,
              status: str,
              source: str,
              evidence: str,
              reason: str,
              next_action: str) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "source": source,
        "evidence": evidence,
        "reason": reason,
        "next_action": next_action,
    }


def risk_counts(manifest: dict[str, Any]) -> dict[str, int]:
    value = manifest.get("risk_summary")
    return value if isinstance(value, dict) else {}


def shim_status_counts(manifest: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in manifest.get("shim_matrix", []):
        if isinstance(row, dict):
            status = str(row.get("status"))
            counts[status] = counts.get(status, 0) + 1
    return counts


def daemon_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for daemon in manifest.get("daemons", []):
        if isinstance(daemon, dict):
            blockers.extend(str(blocker) for blocker in daemon.get("blockers", []))
    return sorted(set(blockers))


def build_gate(v210: dict[str, Any],
               v211: dict[str, Any],
               v212: dict[str, Any],
               v216: dict[str, Any],
               v217: dict[str, Any],
               v218: dict[str, Any],
               v219: dict[str, Any]) -> list[dict[str, str]]:
    vendor_ok = v210.get("decision") in {"asset-map-ready", "firmware-path-policy-needed"}
    firmware_policy_ok = v211.get("decision") in {"sysfs-path-update-needed", "path-policy-ready", "path-model-ready"}
    rollback_ok = v212.get("decision") == "path-rollback-pass"
    v217_risks = risk_counts(v217)
    dangerous = int(v217_risks.get("write-only-dangerous", 0)) + int(v217_risks.get("writable-unknown", 0))
    shim_counts = shim_status_counts(v219)
    blockers = daemon_blockers(v218)

    return [
        gate_item(
            "vendor_assets",
            "pass" if vendor_ok else "fail",
            "v210",
            str(v210.get("decision")),
            "vendor Wi-Fi/CNSS binaries and firmware are visible" if vendor_ok else "vendor asset evidence is missing",
            "keep read-only vendor asset evidence current",
        ),
        gate_item(
            "firmware_path",
            "pass" if firmware_policy_ok and rollback_ok else "fail",
            "v211/v212",
            f"policy={v211.get('decision')} rollback={v212.get('decision')}",
            "temporary firmware path policy has rollback evidence" if firmware_policy_ok and rollback_ok else "firmware path policy or rollback is incomplete",
            "keep path apply/readback/rollback as required preflight",
        ),
        gate_item(
            "service_replay",
            "pass" if v216.get("decision") == "replay-model-ready" else "fail",
            "v216",
            str(v216.get("decision")),
            "Android Wi-Fi/CNSS service chain is modeled",
            "do not execute services before later opt-in gate",
        ),
        gate_item(
            "icnss_recovery",
            "blocked" if dangerous else "pass",
            "v217",
            f"decision={v217.get('decision')} dangerous={dangerous}",
            "writable/recovery controls remain unsafe; reboot is only proven recovery" if dangerous else "no dangerous recovery control blocker",
            "either accept reboot-only recovery explicitly or produce a safer recovery proof",
        ),
        gate_item(
            "daemon_dryrun",
            "warn" if v218.get("decision") == "daemon-dryrun-partial" else ("pass" if v218.get("decision") == "daemon-dryrun-ready" else "fail"),
            "v218",
            f"decision={v218.get('decision')} blockers={','.join(blockers)}",
            "daemon visibility is mapped but ELF/library/recovery blockers remain" if v218.get("decision") == "daemon-dryrun-partial" else "daemon dry-run evidence state",
            "collect host-visible vendor root for ELF/library inspection before execution",
        ),
        gate_item(
            "shim_policy",
            "blocked" if shim_counts.get("blocked", 0) else ("warn" if v219.get("decision") == "shim-plan-partial" else "pass"),
            "v219",
            f"decision={v219.get('decision')} statuses={shim_counts}",
            "shim matrix still has blocked property/QMI/recovery/security areas" if shim_counts.get("blocked", 0) else "shim policy is bounded",
            "resolve or explicitly defer blocked shim items before v221 mutating experiment",
        ),
        gate_item(
            "security_exposure",
            "blocked",
            "v219/v224-pending",
            "credential collection denied; Wi-Fi exposure review pending",
            "pre-connect security and listener binding policy is not complete",
            "keep active network work blocked until v224 security review or earlier scan-only exposure gate",
        ),
    ]


def decide(items: list[dict[str, str]]) -> tuple[str, str, bool]:
    blocked = [item for item in items if item["status"] == "blocked"]
    failed = [item for item in items if item["status"] == "fail"]
    if failed:
        return "manual-review-required", f"gate has failed prerequisites: {', '.join(item['name'] for item in failed)}", False
    if blocked:
        return "no-go", f"gate has blocked prerequisites: {', '.join(item['name'] for item in blocked)}", True
    warnings = [item for item in items if item["status"] == "warn"]
    if warnings:
        return "no-go", f"gate has unresolved warnings: {', '.join(item['name'] for item in warnings)}", True
    return "go-scan-prep", "all lifecycle-aware preflight gates passed", True


def build_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [item["name"], item["status"], item["source"], item["reason"], item["next_action"]]
        for item in manifest["gate"]["items"]
    ]
    lines = [
        "# v220 Wi-Fi Bring-Up Preflight Gate v2",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "",
        "## Gate Items",
        "",
        markdown_table(["name", "status", "source", "reason", "next action"], rows),
        "",
        "## Interpretation",
        "",
        "- `no-go` is a valid successful gate result when blockers remain.",
        "- This gate does not approve daemon execution, rfkill writes, scan, or connect.",
        "- v221 must not proceed to controlled CNSS start while blocked items remain.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v210 = load_json(args.v210_manifest)
    v211 = load_json(args.v211_manifest)
    v212 = load_json(args.v212_manifest)
    v216 = load_json(args.v216_manifest)
    v217 = load_json(args.v217_native_manifest)
    v218 = load_json(args.v218_manifest)
    v219 = load_json(args.v219_manifest)

    items = build_gate(v210, v211, v212, v216, v217, v218, v219)
    decision, reason, pass_ok = decide(items)
    gate = {
        "items": items,
        "status_counts": {
            status: sum(1 for item in items if item["status"] == status)
            for status in ("pass", "warn", "fail", "blocked")
        },
    }
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {
            "v210_manifest": str(repo_path(args.v210_manifest)),
            "v211_manifest": str(repo_path(args.v211_manifest)),
            "v212_manifest": str(repo_path(args.v212_manifest)),
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v217_native_manifest": str(repo_path(args.v217_native_manifest)),
            "v218_manifest": str(repo_path(args.v218_manifest)),
            "v219_manifest": str(repo_path(args.v219_manifest)),
        },
        "gate": gate,
        "guardrails": [
            "no live device commands",
            "no daemon execution",
            "no service start",
            "no sysfs/debugfs writes",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("gate.json", gate)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
