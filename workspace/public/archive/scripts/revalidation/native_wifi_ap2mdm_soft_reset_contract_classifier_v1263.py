#!/usr/bin/env python3
"""V1263 host-only AP2MDM soft-reset contract classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1263-ap2mdm-soft-reset-contract-classifier")
DEFAULT_V1262 = Path("tmp/wifi/v1262-gpiochip-line-info-live/manifest.json")
DEFAULT_V1239 = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_V1242 = Path("tmp/wifi/v1242-late-per-proxy-response-sampler-live/manifest.json")
DEFAULT_V1243 = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json")


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1262", type=Path, default=DEFAULT_V1262)
    parser.add_argument("--v1239", type=Path, default=DEFAULT_V1239)
    parser.add_argument("--v1242", type=Path, default=DEFAULT_V1242)
    parser.add_argument("--v1243", type=Path, default=DEFAULT_V1243)
    parser.add_argument("command", choices=("run", "plan"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"exists": False, "path": str(path)}
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(path), "json_error": str(exc)}
    data["_exists"] = True
    data["_path"] = str(path)
    return data


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def analyze(v1262: dict[str, Any], v1239: dict[str, Any], v1242: dict[str, Any], v1243: dict[str, Any]) -> dict[str, Any]:
    line = v1262.get("analysis", {})
    line_kernel_owned = line.get("line_flag_kernel") == "1"
    line_consumer = str(line.get("line_consumer", ""))
    line_is_soft_reset = line_consumer == "AP2MDM_SOFT_RESET"
    line_info_ready = as_bool(line.get("ready")) and as_bool(line.get("lineinfo_ok"))
    v1239_decision = str(v1239.get("decision", ""))
    v1242_decision = str(v1242.get("decision", ""))
    v1243_decision = str(v1243.get("decision", ""))
    no_gpio142_response = (
        "before-gpio142-pcie-wlfw" in v1239_decision and
        "mdm2ap-silent" in v1242_decision and
        "mdm2ap-silent" in v1243_decision
    )
    direct_line_request_rejected = line_info_ready and line_kernel_owned and line_is_soft_reset
    return {
        "v1262_path": v1262.get("_path", v1262.get("path", "")),
        "v1239_path": v1239.get("_path", v1239.get("path", "")),
        "v1242_path": v1242.get("_path", v1242.get("path", "")),
        "v1243_path": v1243.get("_path", v1243.get("path", "")),
        "v1262_decision": v1262.get("decision", "missing"),
        "v1239_decision": v1239.get("decision", "missing"),
        "v1242_decision": v1242.get("decision", "missing"),
        "v1243_decision": v1243.get("decision", "missing"),
        "line_info_ready": line_info_ready,
        "line_offset": line.get("line_offset", ""),
        "line_global": line.get("line_global", ""),
        "line_flags": line.get("line_flags", ""),
        "line_flag_kernel": line.get("line_flag_kernel", ""),
        "line_flag_is_out": line.get("line_flag_is_out", ""),
        "line_consumer": line_consumer,
        "line_kernel_owned": line_kernel_owned,
        "line_is_soft_reset": line_is_soft_reset,
        "zero_markers_ok": as_bool(line.get("all_zero_markers_ok")),
        "no_gpio142_response_evidence": no_gpio142_response,
        "direct_line_request_rejected": direct_line_request_rejected,
        "safe_next_gate": "read-only ext-mdm/AP2MDM contract observer; no userspace GPIO line request",
    }


def build_checks(command: str, analysis: dict[str, Any], manifests: dict[str, dict[str, Any]]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no evidence loaded for mutation", "run classifier")]
    return [
        Check("v1262-line-info", "pass" if manifests["v1262"].get("_exists") and analysis["line_info_ready"] else "blocked", "blocker", f"decision={analysis['v1262_decision']} ready={analysis['line_info_ready']}", "rerun V1262 if missing"),
        Check("kernel-owned-soft-reset", "pass" if analysis["line_kernel_owned"] and analysis["line_is_soft_reset"] else "blocked", "blocker", f"flags={analysis['line_flags']} kernel={analysis['line_flag_kernel']} consumer={analysis['line_consumer']}", "do not decide line request until line ownership is known"),
        Check("prior-powerup-gap", "pass" if analysis["no_gpio142_response_evidence"] else "warn", "warning", f"v1239={analysis['v1239_decision']} v1242={analysis['v1242_decision']} v1243={analysis['v1243_decision']}", "refresh powerup-gap evidence only if needed"),
        Check("direct-userspace-line-request", "pass" if analysis["direct_line_request_rejected"] else "blocked", "blocker", "reject direct GPIO line request/hold when GPIOLINE_FLAG_KERNEL is set", "select read-only ext-mdm observer next"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1263-ap2mdm-soft-reset-contract-plan-ready", True, "plan-only; no live command executed", "run host-only classifier")
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return ("v1263-ap2mdm-soft-reset-contract-blocked", False, "blocked by " + ", ".join(blockers), "fix missing evidence before selecting next gate")
    return (
        "v1263-kernel-owned-soft-reset-line-request-rejected",
        True,
        "PMIC GPIO9 is kernel-owned by AP2MDM_SOFT_RESET; direct userspace line request/hold is not the next safe path",
        analysis["safe_next_gate"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["line_offset", analysis["line_offset"]],
        ["line_global", analysis["line_global"]],
        ["line_flags", analysis["line_flags"]],
        ["line_flag_kernel", analysis["line_flag_kernel"]],
        ["line_consumer", analysis["line_consumer"]],
        ["direct_line_request_rejected", analysis["direct_line_request_rejected"]],
        ["no_gpio142_response_evidence", analysis["no_gpio142_response_evidence"]],
        ["safe_next_gate", analysis["safe_next_gate"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    return "\n".join([
        "# V1263 AP2MDM Soft-reset Contract Classifier",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Evidence",
        "",
        f"- V1262: `{analysis['v1262_path']}`",
        f"- V1239: `{analysis['v1239_path']}`",
        f"- V1242: `{analysis['v1242_path']}`",
        f"- V1243: `{analysis['v1243_path']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    manifests = {
        "v1262": load_json(args.v1262),
        "v1239": load_json(args.v1239),
        "v1242": load_json(args.v1242),
        "v1243": load_json(args.v1243),
    }
    analysis = analyze(manifests["v1262"], manifests["v1239"], manifests["v1242"], manifests["v1243"])
    checks = build_checks(args.command, analysis, manifests)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "device_mutations": False,
        "live_command_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"gpio_line_request_executed: {manifest['gpio_line_request_executed']}")
    print(f"pmic_write_executed: {manifest['pmic_write_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
