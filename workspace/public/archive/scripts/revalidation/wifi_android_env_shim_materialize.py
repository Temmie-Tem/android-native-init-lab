#!/usr/bin/env python3
"""Materialize a host-side Android-env Wi-Fi shim dry-run model."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import stat
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir


DEFAULT_V219_MANIFEST = Path("tmp/wifi/v219-native-android-env-shim/manifest.json")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
DEFAULT_V222_MANIFEST = Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json")
DEFAULT_V223_MANIFEST = Path("tmp/wifi/v223-recovery-rollback-policy/manifest.json")

ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bresetprop\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\breboot\b|\bpoweroff\b", re.IGNORECASE),
    re.compile(r">\s*/sys/|>\s*/proc/sys/|>\s*/config/", re.IGNORECASE),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v224-android-env-shim-materialize"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--vendor-root", type=Path, default=None)
    parser.add_argument("--v219-manifest", type=Path, default=DEFAULT_V219_MANIFEST)
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--v222-manifest", type=Path, default=DEFAULT_V222_MANIFEST)
    parser.add_argument("--v223-manifest", type=Path, default=DEFAULT_V223_MANIFEST)
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


def normalize_vendor_root(path: Path | None) -> tuple[Path | None, str]:
    if path is None:
        return None, "not-provided"
    root = repo_path(path)
    try:
        info = root.lstat()
    except FileNotFoundError:
        return root, "missing"
    if stat.S_ISLNK(info.st_mode):
        return root, "symlink-root-denied"
    if not stat.S_ISDIR(info.st_mode):
        return root, "not-directory"
    return root.resolve(), "ok"


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def rows_by_status(rows: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("status") == status]


def rows_by_category(rows: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("category") == category]


def build_alias_plan(v219_rows: list[dict[str, Any]], vendor_root_status: str, v222: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "system-vendor-alias-plan",
        "status": "source-required" if v222.get("decision") != "vendor-root-ready" else "ready",
        "source_vendor_root_status": vendor_root_status,
        "mappings": [
            {
                "android_path": "/system/vendor",
                "native_target": "<vendor-root>",
                "mode": "dry-run-only",
                "persistent": False,
            },
            {
                "android_path": "/vendor",
                "native_target": "<vendor-root>",
                "mode": "dry-run-only",
                "persistent": False,
            },
        ],
        "source_rows": rows_by_category(v219_rows, "mount-path"),
    }


def build_static_properties(v219_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": "static-properties",
        "status": "evidence-only",
        "mutation_allowed": False,
        "denied_operations": ["setprop", "ctl.start", "ctl.restart", "class_start"],
        "source_rows": rows_by_category(v219_rows, "property"),
    }


def build_groups_capabilities(v219_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": "groups-capabilities",
        "status": "dry-run-model",
        "persistent_passwd_group_mutation": False,
        "execution_model": "root-only-temporary-or-future-explicit-group-table",
        "source_rows": rows_by_category(v219_rows, "user-capability"),
    }


def build_log_policy(v219_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": "log-policy",
        "status": "ready",
        "directory_mode": "0700",
        "file_mode": "0600",
        "redaction_required": True,
        "source_rows": rows_by_category(v219_rows, "logging-evidence"),
    }


def build_health_capture_plan(v219_rows: list[dict[str, Any]], v223: dict[str, Any]) -> dict[str, Any]:
    policy = v223.get("policy") if isinstance(v223.get("policy"), dict) else {}
    return {
        "name": "health-capture-plan",
        "status": "ready" if v223.get("decision") == "reboot-recovery-accepted" else "blocked",
        "preflight_requirements": policy.get("preflight_requirements", []),
        "stop_conditions": policy.get("stop_conditions", []),
        "post_reboot_verification": policy.get("post_reboot_verification", []),
        "source_rows": rows_by_category(v219_rows, "recovery-rollback"),
    }


def build_materialization(v219: dict[str, Any],
                          v221: dict[str, Any],
                          v222: dict[str, Any],
                          v223: dict[str, Any],
                          vendor_root_status: str) -> dict[str, Any]:
    rows = [row for row in v219.get("shim_matrix", []) if isinstance(row, dict)]
    blocked_rows = rows_by_status(rows, "blocked")
    shim_required_rows = rows_by_status(rows, "shim-required")
    return {
        "status_counts": status_counts(rows),
        "shim_required_rows": shim_required_rows,
        "blocked_rows": blocked_rows,
        "host_evidence_required_rows": rows_by_status(rows, "host-evidence-required"),
        "artifacts": {
            "system_vendor_alias_plan": build_alias_plan(rows, vendor_root_status, v222),
            "static_properties": build_static_properties(rows),
            "groups_capabilities": build_groups_capabilities(rows),
            "log_policy": build_log_policy(rows),
            "health_capture_plan": build_health_capture_plan(rows, v223),
        },
        "input_decisions": {
            "v219": v219.get("decision"),
            "v221": v221.get("decision"),
            "v222": v222.get("decision"),
            "v223": v223.get("decision"),
        },
        "source_vendor_root_status": vendor_root_status,
        "blocked_policy": {
            "blocked_rows_remain_blocked": True,
            "daemon_execution": "denied",
            "property_mutation": "denied",
            "qmi_pdr_ssr_writes": "denied",
            "wifi_credentials": "denied",
            "active_network": "denied",
        },
    }


def decide(v219: dict[str, Any],
           v222: dict[str, Any],
           v223: dict[str, Any],
           vendor_root_status: str,
           materialization: dict[str, Any]) -> tuple[str, str, bool]:
    if v219.get("decision") != "shim-plan-partial":
        return "manual-review-required", "v219 shim plan is not in expected partial state", False
    if v223.get("decision") != "reboot-recovery-accepted":
        return "manual-review-required", "v223 recovery policy is not accepted", False
    if not materialization["shim_required_rows"]:
        return "manual-review-required", "v219 has no shim-required rows to materialize", False
    if any(row.get("status") != "blocked" for row in materialization["blocked_rows"]):
        return "manual-review-required", "blocked rows changed unexpectedly", False
    if v222.get("decision") != "vendor-root-ready" or vendor_root_status != "ok":
        return "shim-source-required", "dry-run artifacts generated but source vendor root remains required", True
    return "shim-dryrun-ready", "dry-run shim materialization is ready for v225 gate integration", True


def write_shim_root(store: EvidenceStore, materialization: dict[str, Any]) -> None:
    shim_root = store.mkdir("shim-root")
    ensure_private_dir(shim_root)
    artifacts = materialization["artifacts"]
    store.write_json("shim-root/system-vendor-alias-plan.json", artifacts["system_vendor_alias_plan"])
    store.write_json("shim-root/static-properties.json", artifacts["static_properties"])
    store.write_json("shim-root/groups-capabilities.json", artifacts["groups_capabilities"])
    store.write_json("shim-root/log-policy.json", artifacts["log_policy"])
    store.write_json("shim-root/health-capture-plan.json", artifacts["health_capture_plan"])


def build_summary(manifest: dict[str, Any]) -> str:
    materialization = manifest["materialization"]
    artifact_rows = [
        [name, str(value.get("status")), str(len(value.get("source_rows", [])))]
        for name, value in materialization["artifacts"].items()
    ]
    blocked_rows = [
        [row.get("category", ""), row.get("item", ""), row.get("action", "")]
        for row in materialization["blocked_rows"]
    ]
    lines = [
        "# v224 Android-Env Shim Dry-Run Materialization",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- vendor_root_status: `{manifest['vendor_root_status']}`",
        "",
        "## Artifact Summary",
        "",
        markdown_table(["artifact", "status", "source rows"], artifact_rows),
        "",
        "## Blocked Rows Kept Blocked",
        "",
        markdown_table(["category", "item", "action"], blocked_rows or [["none", "none", "none"]]),
        "",
        "## Guardrails",
        "",
    ]
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `shim-source-required` is a successful dry-run result while v222 has no source vendor root.",
        "- This output is host-side evidence only and is not copied to the device.",
        "- Daemon execution and active Wi-Fi remain blocked.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v219 = load_json(args.v219_manifest)
    v221 = load_json(args.v221_manifest)
    v222 = load_json(args.v222_manifest)
    v223 = load_json(args.v223_manifest)
    vendor_root, vendor_root_status = normalize_vendor_root(args.vendor_root)

    materialization = build_materialization(v219, v221, v222, v223, vendor_root_status)
    decision, reason, pass_ok = decide(v219, v222, v223, vendor_root_status, materialization)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "android-env-shim-dryrun-materialization",
        "vendor_root": str(vendor_root) if vendor_root else None,
        "vendor_root_status": vendor_root_status,
        "inputs": {
            "v219_manifest": str(repo_path(args.v219_manifest)),
            "v221_manifest": str(repo_path(args.v221_manifest)),
            "v222_manifest": str(repo_path(args.v222_manifest)),
            "v223_manifest": str(repo_path(args.v223_manifest)),
        },
        "materialization": materialization,
        "guardrails": [
            "no live device commands by default",
            "no vendor binary execution",
            "no device writes",
            "no world-readable evidence output",
            "no Android property mutation",
            "no QMI/PDR/SSR writes",
            "no binder/HAL publication",
            "no Wi-Fi credential collection",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    write_shim_root(store, materialization)
    store.write_json("manifest.json", manifest)
    store.write_json("shim-materialization.json", materialization)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
