#!/usr/bin/env python3
"""V854 host-only eSoC actor parity classifier.

V853 proved the Android lower eSoC actor contract: `pm-service` holds
`/dev/subsys_esoc0` and `/dev/subsys_modem`, while `mdm_helper` and child `ks`
hold `/dev/esoc-0`. This classifier reconciles that with prior native
subsys/PeripheralManager/mdm_helper attempts and selects the next safe native
gate without contacting the device.
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
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v854-esoc-actor-parity-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v854-esoc-actor-parity-classifier.txt")
DEFAULT_V853_MANIFEST = Path("tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json")
DEFAULT_V849_REPORT = Path("docs/reports/NATIVE_INIT_V849_SUBSYS_ESOC0_WAIT_STATE_SAMPLER_2026-05-25.md")
DEFAULT_V840_REPORT = Path("docs/reports/NATIVE_INIT_V840_PROVIDER_FIRST_PREARMED_LISTENER_2026-05-25.md")
DEFAULT_V764_REPORT = Path("docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md")
DEFAULT_V853_REPORT = Path("docs/reports/NATIVE_INIT_V853_ANDROID_ESOC_ACTOR_HANDOFF_2026-05-25.md")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: Any
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v853-manifest", type=Path, default=DEFAULT_V853_MANIFEST)
    parser.add_argument("--v849-report", type=Path, default=DEFAULT_V849_REPORT)
    parser.add_argument("--v840-report", type=Path, default=DEFAULT_V840_REPORT)
    parser.add_argument("--v764-report", type=Path, default=DEFAULT_V764_REPORT)
    parser.add_argument("--v853-report", type=Path, default=DEFAULT_V853_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(payload, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    payload.setdefault("exists", True)
    payload.setdefault("path", str(resolved))
    return payload


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def nested(data: Any, *keys: Any) -> Any:
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def grep_lines(text: str, pattern: str, limit: int = 40) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            rows.append(line.strip())
        if len(rows) >= limit:
            break
    return rows


def contains_all(text: str, values: list[str]) -> bool:
    return all(value in text for value in values)


def summarize_v853(v853: dict[str, Any], report_text: str) -> dict[str, Any]:
    summary = v853.get("android_summary") if isinstance(v853.get("android_summary"), dict) else {}
    nodes = summary.get("nodes") if isinstance(summary.get("nodes"), dict) else {}
    holder_lines = "\n".join(summary.get("holder_lines") or [])
    process_lines = "\n".join(summary.get("process_lines") or [])
    ueventd_lines = "\n".join(summary.get("ueventd_lines") or [])
    selinux_lines = "\n".join(summary.get("selinux_lines") or [])
    combined = "\n".join([holder_lines, process_lines, ueventd_lines, selinux_lines, report_text])
    return {
        "path": v853.get("path"),
        "exists": bool(v853.get("exists")),
        "decision": v853.get("decision"),
        "pass": bool(v853.get("pass")),
        "reason": v853.get("reason"),
        "nodes": {
            "dev_esoc_0": bool(nodes.get("dev_esoc_0")),
            "dev_subsys_esoc0": bool(nodes.get("dev_subsys_esoc0")),
            "dev_subsys_modem": "/dev/subsys_modem" in report_text or "/dev/subsys_modem" in combined,
            "dev_wlan": bool(nodes.get("dev_wlan")),
            "dev_qcwlanstate": bool(nodes.get("dev_qcwlanstate")),
        },
        "holders": {
            "mdm_helper_esoc": "mdm_helper" in holder_lines and "/dev/esoc-0" in holder_lines,
            "ks_esoc": "comm=ks" in holder_lines and "/dev/esoc-0" in holder_lines,
            "pm_service_subsys_esoc0": "pm-service" in holder_lines and "/dev/subsys_esoc0" in holder_lines,
            "pm_service_subsys_modem": "pm-service" in holder_lines and "/dev/subsys_modem" in holder_lines,
            "holder_count": int(summary.get("holder_count") or 0),
            "focused_lines": summary.get("holder_lines") or [],
        },
        "ueventd": {
            "dev_esoc_0_rule": contains_all(ueventd_lines, ["/dev/esoc-0", "0660", "root", "radio"]),
            "dev_subsys_rule": contains_all(ueventd_lines, ["/dev/subsys_*", "0640", "system", "system"]),
            "dev_wlan_rule": contains_all(ueventd_lines, ["/dev/wlan", "0660", "wifi", "wifi"]),
            "focused_lines": grep_lines(ueventd_lines, r"/dev/(esoc|subsys|wlan)|vendor\.per_mgr|vendor\.mdm_helper|rmt_storage|tftp_server|cnss", limit=60),
        },
        "selinux": {
            "vendor_esoc_device": "vendor_esoc_device" in selinux_lines,
            "vendor_ssr_device": "vendor_ssr_device" in selinux_lines,
            "vendor_mdm_helper_exec": "vendor_mdm_helper_exec" in selinux_lines,
            "vendor_per_mgr_exec": "vendor_per_mgr_exec" in selinux_lines,
            "focused_lines": grep_lines(selinux_lines, r"esoc|subsys|mdm_helper|ks|pm-service|vendor_per_mgr|vendor_mdm_helper|vendor_ssr", limit=60),
        },
    }


def summarize_prior(v849_text: str, v840_text: str, v764_text: str) -> dict[str, Any]:
    joined = "\n".join([v849_text, v840_text, v764_text])
    return {
        "v849": {
            "present": bool(v849_text),
            "manual_subsys_open_blocked": contains_all(v849_text, ["mdm_subsys_powerup", "D-state"]),
            "no_wlfw": "no MHI/WLFW/BDF" in v849_text or "WLFW/BDF" in v849_text,
            "focused_lines": grep_lines(v849_text, r"mdm_subsys_powerup|D-state|subsys_esoc0|wait_for_err_ready|MHI|WLFW|wlan0", limit=24),
        },
        "v840": {
            "present": bool(v840_text),
            "provider_first_attempted": "PeripheralManager" in v840_text,
            "still_uninit": "UNINIT" in v840_text or "uninit" in v840_text,
            "no_wlfw": any(
                needle in v840_text
                for needle in (
                    "no WLFW",
                    "WLFW/BDF/wlan0",
                    "WLFW/service69/BDF/wlan0 absent",
                    "WLFW/BDF/firmware-ready/`wlan0` | absent",
                )
            ),
            "focused_lines": grep_lines(v840_text, r"PeripheralManager|UNINIT|WLFW|BDF|wlan0|provider-first", limit=24),
        },
        "v764": {
            "present": bool(v764_text),
            "mdm_helper_started_no_progress": contains_all(v764_text, ["mdm_helper", "mdm3", "OFFLINING"]) and ("WLFW" in v764_text),
            "focused_lines": grep_lines(v764_text, r"mdm_helper|OFFLINING|WLFW|BDF|wlan0|service180", limit=24),
        },
        "joined_evidence_present": bool(joined),
    }


def candidate_matrix(v853: dict[str, Any], prior: dict[str, Any]) -> list[dict[str, str]]:
    mdm_helper_contract = v853["holders"]["mdm_helper_esoc"] and v853["holders"]["ks_esoc"]
    pm_contract = v853["holders"]["pm_service_subsys_esoc0"] and v853["holders"]["pm_service_subsys_modem"]
    node_contract = v853["nodes"]["dev_esoc_0"] and v853["nodes"]["dev_subsys_esoc0"]
    rule_contract = v853["ueventd"]["dev_esoc_0_rule"] and v853["ueventd"]["dev_subsys_rule"]
    return [
        {
            "candidate": "repeat manual /dev/subsys_esoc0 open",
            "classification": "reject",
            "reason": "V849 already blocks in mdm_subsys_powerup and Android uses a broader actor contract.",
        },
        {
            "candidate": "repeat mdm_helper alone",
            "classification": "reject",
            "reason": "V764/V746 showed mdm_helper start without mdm3/WLFW progress; V853 shows mdm_helper also depends on /dev/esoc-0 and child ks.",
        },
        {
            "candidate": "repeat provider-first PeripheralManager without node parity",
            "classification": "reject",
            "reason": "V840 did not produce WLAN-PD/WLFW; V853 now proves exact /dev/subsys_* and /dev/esoc-0 node/FD contracts are the missing discriminator.",
        },
        {
            "candidate": "native Android node/ueventd parity preflight",
            "classification": "select-next" if node_contract and rule_contract else "blocked",
            "reason": "Recreate only Android-equivalent node metadata and verify service preconditions before any actor open/ioctl.",
        },
        {
            "candidate": "pm-service start-only with Android node parity",
            "classification": "prepare-after-next" if pm_contract else "blocked",
            "reason": "Only justified after node parity confirms the native surface can match Android without side effects.",
        },
        {
            "candidate": "mdm_helper + ks eSoC contract replay",
            "classification": "prepare-after-pm" if mdm_helper_contract else "blocked",
            "reason": "Android holds /dev/esoc-0 through mdm_helper and ks, but replaying it before pm-service/subsys parity would skip a proven dependency.",
        },
        {
            "candidate": "GPIO 135 / PMIC GPIO 9 direct manipulation",
            "classification": "forbidden-now",
            "reason": "Still lower-risk to exhaust Android actor parity before GPIO/sysfs/debugfs writes.",
        },
    ]


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    v853 = analysis["v853"]
    prior = analysis["prior"]
    checks = [
        Check(
            "v853-input",
            "pass" if v853["pass"] and v853["decision"] == "v853-android-esoc-actor-surface-captured" else "blocked",
            "blocker",
            {"decision": v853["decision"], "pass": v853["pass"]},
            "rerun V853 handoff if the actor evidence is missing",
        ),
        Check(
            "android-node-contract",
            "pass" if v853["nodes"]["dev_esoc_0"] and v853["nodes"]["dev_subsys_esoc0"] and v853["nodes"]["dev_subsys_modem"] else "blocked",
            "blocker",
            v853["nodes"],
            "capture all Android eSoC/subsys nodes before native parity selection",
        ),
        Check(
            "android-holder-contract",
            "pass" if v853["holders"]["mdm_helper_esoc"] and v853["holders"]["ks_esoc"] and v853["holders"]["pm_service_subsys_esoc0"] and v853["holders"]["pm_service_subsys_modem"] else "blocked",
            "blocker",
            v853["holders"],
            "capture exact FD holders before native actor replay",
        ),
        Check(
            "android-policy-contract",
            "pass" if v853["ueventd"]["dev_esoc_0_rule"] and v853["ueventd"]["dev_subsys_rule"] and v853["selinux"]["vendor_esoc_device"] and v853["selinux"]["vendor_ssr_device"] else "blocked",
            "blocker",
            {"ueventd": v853["ueventd"], "selinux": v853["selinux"]},
            "capture Android node permissions and labels before native parity",
        ),
        Check(
            "prior-retry-closures",
            "pass" if prior["v849"]["manual_subsys_open_blocked"] and prior["v840"]["provider_first_attempted"] and prior["v764"]["mdm_helper_started_no_progress"] else "warn",
            "risk",
            prior,
            "use prior closures to avoid blind repeat of known non-progressing paths",
        ),
    ]
    return checks


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v853_payload = load_json(args.v853_manifest)
    v853_report = read_text(args.v853_report)
    v849_report = read_text(args.v849_report)
    v840_report = read_text(args.v840_report)
    v764_report = read_text(args.v764_report)
    v853_summary = summarize_v853(v853_payload, v853_report)
    prior = summarize_prior(v849_report, v840_report, v764_report)
    analysis = {
        "inputs": {
            "v853_manifest": str(repo_path(args.v853_manifest)),
            "v853_report": str(repo_path(args.v853_report)),
            "v849_report": str(repo_path(args.v849_report)),
            "v840_report": str(repo_path(args.v840_report)),
            "v764_report": str(repo_path(args.v764_report)),
        },
        "v853": v853_summary,
        "prior": prior,
        "candidate_matrix": candidate_matrix(v853_summary, prior),
        "forbidden_executed": {
            "device_commands": False,
            "service_start": False,
            "raw_esoc_open": False,
            "subsys_char_open": False,
            "subsystem_write": False,
            "gpio_sysfs_debugfs_write": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_route": False,
            "external_ping": False,
            "boot_or_partition_write": False,
        },
    }
    return analysis


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v854-esoc-actor-parity-plan-ready",
            True,
            "plan-only; no evidence classified",
            "run the host-only V854 classifier",
        )
    blockers = [check for check in checks if check.status == "blocked" and check.severity == "blocker"]
    if blockers:
        names = ",".join(check.name for check in blockers)
        return (
            "v854-esoc-actor-parity-inputs-incomplete",
            False,
            f"required evidence incomplete: {names}",
            "repair missing V853/V849/V840/V764 evidence before selecting a live gate",
        )
    return (
        "v854-esoc-actor-parity-selects-node-contract-preflight",
        True,
        "Android node, holder, policy, and prior retry evidence select native node/ueventd parity preflight as the next safe gate",
        "implement V855 native Android eSoC/subsys node parity preflight; no actor open/ioctl yet",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    checks = manifest.get("checks") or []
    v853 = analysis.get("v853") or {}
    prior = analysis.get("prior") or {}
    matrix = analysis.get("candidate_matrix") or []
    check_rows = [[item["name"], item["status"], item["severity"], json.dumps(item["detail"], ensure_ascii=False, sort_keys=True), item["next_step"]] for item in checks]
    matrix_rows = [[item["candidate"], item["classification"], item["reason"]] for item in matrix]
    holder_rows = [[line] for line in (v853.get("holders") or {}).get("focused_lines", [])]
    prior_rows = [
        ["v849", json.dumps((prior.get("v849") or {}).get("focused_lines", []), ensure_ascii=False)],
        ["v840", json.dumps((prior.get("v840") or {}).get("focused_lines", []), ensure_ascii=False)],
        ["v764", json.dumps((prior.get("v764") or {}).get("focused_lines", []), ensure_ascii=False)],
    ]
    return "\n".join([
        "# V854 eSoC Actor Parity Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next_step"], check_rows) if check_rows else "- none",
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason"], matrix_rows) if matrix_rows else "- none",
        "",
        "## Android Holder Lines",
        "",
        markdown_table(["line"], holder_rows) if holder_rows else "- none",
        "",
        "## Prior Closure Lines",
        "",
        markdown_table(["source", "focused_lines"], prior_rows),
        "",
        "## Guardrails",
        "",
        "- Host-only classifier; no bridge, ADB, QRTR socket, or device command.",
        "- No node creation/open/ioctl, GPIO/sysfs/debugfs write, service start, module load/unload, boot write, partition write, HAL, scan/connect, DHCP/routes, credentials, or external ping.",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    analysis = classify(args) if args.command == "run" else {
        "inputs": {
            "v853_manifest": str(repo_path(args.v853_manifest)),
            "v853_report": str(repo_path(args.v853_report)),
            "v849_report": str(repo_path(args.v849_report)),
            "v840_report": str(repo_path(args.v840_report)),
            "v764_report": str(repo_path(args.v764_report)),
        },
        "v853": {},
        "prior": {},
        "candidate_matrix": [],
        "forbidden_executed": {},
    }
    checks = build_checks(analysis) if args.command == "run" else []
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(repo_path(args.out_dir)),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "raw_esoc_open_executed": False,
        "subsys_char_open_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "gpio_write_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"raw_esoc_open_executed: {manifest['raw_esoc_open_executed']}")
    print(f"subsys_char_open_executed: {manifest['subsys_char_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
