#!/usr/bin/env python3
"""V748 host-only classifier for the non-bind ICNSS/QCA power-up trigger."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v748-nonbind-powerup-trigger")
DEFAULT_V747_SOURCE = Path("tmp/wifi/latest-v747-qca6390-driver-binding-delta.txt")
DEFAULT_V746_SOURCE = Path("tmp/wifi/latest-v746-mdm-helper-sysmon-live.txt")
DEFAULT_V701_REPORT = Path("docs/reports/NATIVE_INIT_V701_PRE_WLFW_TRIGGER_CLASSIFIER_2026-05-24.md")
DEFAULT_V703_REPORT = Path("docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md")
DEFAULT_V716_REPORT = Path("docs/reports/NATIVE_INIT_V716_QCA_BIND_RECONCILIATION_2026-05-24.md")
DEFAULT_V727_REPORT = Path("docs/reports/NATIVE_INIT_V727_LOWER_PREREQ_2026-05-24.md")
DEFAULT_V728_REPORT = Path("docs/reports/NATIVE_INIT_V728_PRIVATE_VENDOR_ROOT_2026-05-24.md")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v747-source", type=Path, default=DEFAULT_V747_SOURCE)
    parser.add_argument("--v746-source", type=Path, default=DEFAULT_V746_SOURCE)
    parser.add_argument("--v701-report", type=Path, default=DEFAULT_V701_REPORT)
    parser.add_argument("--v703-report", type=Path, default=DEFAULT_V703_REPORT)
    parser.add_argument("--v716-report", type=Path, default=DEFAULT_V716_REPORT)
    parser.add_argument("--v727-report", type=Path, default=DEFAULT_V727_REPORT)
    parser.add_argument("--v728-report", type=Path, default=DEFAULT_V728_REPORT)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_manifest(source: Path) -> Path:
    path = repo_path(source)
    if path.is_file() and path.name != "manifest.json":
        text = path.read_text(encoding="utf-8").strip()
        if text:
            path = repo_path(Path(text))
    if path.is_dir():
        path = path / "manifest.json"
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8") if resolved.exists() else ""


def find_lines(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)]


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "pass"}
    return False


def v746_live(manifest: dict[str, Any]) -> dict[str, Any]:
    base = manifest.get("base_manifest")
    live = base.get("live") if isinstance(base, dict) else manifest.get("live")
    return live if isinstance(live, dict) else {}


def v746_marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = v746_live(manifest)
    markers = live.get("markers")
    counts = markers.get("counts") if isinstance(markers, dict) else {}
    if not isinstance(counts, dict):
        return {}
    return {str(key): int_value(value) for key, value in counts.items()}


def v747_checks(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for check in checks:
        if isinstance(check, dict) and isinstance(check.get("name"), str):
            result[str(check["name"])] = check
    return result


def report_signal(path: Path, text: str, patterns: dict[str, str]) -> dict[str, Any]:
    return {
        "path": str(repo_path(path)),
        "exists": repo_path(path).exists(),
        "signals": {
            name: find_lines(text, pattern)
            for name, pattern in patterns.items()
        },
    }


def build_signals(args: argparse.Namespace) -> dict[str, Any]:
    v701_text = read_text(args.v701_report)
    v703_text = read_text(args.v703_report)
    v716_text = read_text(args.v716_report)
    v727_text = read_text(args.v727_report)
    v728_text = read_text(args.v728_report)
    return {
        "v701": report_signal(args.v701_report, v701_text, {
            "cnss_cld80211_only": r"userspace reaches `cld80211`|cnss_daemon_cld80211=2|cld80211",
            "kernel_progression_gap": r"kernel/platform progression gap|ICNSS-QMI/WLFW/BDF/`wlan0` missing|MHI/WLFW progression|WLFW marker=0",
            "no_hal_connect": r"Wi-Fi bring-up remains unsafe|no `wlan0` exists",
        }),
        "v703": report_signal(args.v703_report, v703_text, {
            "android_icnss_netdev": r"/sys/devices/platform/soc/18800000\.qcom,icnss/net/",
            "android_wlfw_ready": r"icnss_qmi: QMI Server Connected|BDF file|WLAN FW is ready",
            "qca_bind_rejected": r"does not justify writing|bind`/`unbind|driver_override",
        }),
        "v716": report_signal(args.v716_report, v716_text, {
            "bind_unbind_blocked": r"not-bind-target|Do not write `bind`, `unbind`, or `driver_override`|target ICNSS-QMI/WLFW",
        }),
        "v727": report_signal(args.v727_report, v727_text, {
            "real_vendor_firmware_visible": r"wlanmdsp\.mbn|bdwlan\.bin|regdb\.bin|WCNSS_qcom_cfg\.ini",
            "wlan_static_surface": r"built-in/static|/sys/module/wlan exists|/proc/modules lacks `wlan`",
        }),
        "v728": report_signal(args.v728_report, v728_text, {
            "private_vendor_root_pass": r"private /vendor layout works|vendor_mount_source|context.target.exists=1",
            "vendor_gap_resolved_for_execns": r"real sda29 vendor has required Wi-Fi firmware|next gate is smallest safe modem ONLINE trigger proof",
        }),
    }


def signal_count(signals: dict[str, Any], section: str, name: str) -> int:
    section_data = signals.get(section) if isinstance(signals.get(section), dict) else {}
    nested = section_data.get("signals") if isinstance(section_data.get("signals"), dict) else {}
    lines = nested.get(name)
    return len(lines) if isinstance(lines, list) else 0


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(v747: dict[str, Any],
                 v746: dict[str, Any],
                 signals: dict[str, Any]) -> list[Check]:
    counts = v746_marker_counts(v746)
    v747_by_name = v747_checks(v747)
    mdm_helper_started = bool_value(v746.get("mdm_helper_start_executed"))
    no_lower_markers = all(counts.get(name, 0) == 0 for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd"))
    checks: list[Check] = []
    add_check(
        checks,
        "qca-bind-unbind-eliminated",
        "pass" if v747.get("decision") == "v747-qca-driver-link-gap-not-bind-target" else "blocked",
        "blocker",
        f"v747_decision={v747.get('decision')}",
        [str(v747.get("v716_manifest", ""))],
        "do not plan bind/unbind until this blocker is contradicted",
    )
    add_check(
        checks,
        "mdm-helper-eliminated",
        "pass" if mdm_helper_started and v746.get("decision") == "v746-mdm-helper-started-no-lower-progress" else "blocked",
        "blocker",
        f"v746_decision={v746.get('decision')} started={mdm_helper_started}",
        [str(v746.get("evidence_dir", ""))],
        "rerun V746 if mdm_helper did not actually start",
    )
    add_check(
        checks,
        "no-lower-marker-progress",
        "pass" if no_lower_markers else "blocked",
        "blocker",
        json.dumps({name: counts.get(name, 0) for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd")}, sort_keys=True),
        [],
        "if any marker advanced, stop and classify wlan0 readiness instead",
    )
    add_check(
        checks,
        "android-icnss-wlfw-reference",
        "pass" if signal_count(signals, "v703", "android_icnss_netdev") and signal_count(signals, "v703", "android_wlfw_ready") else "blocked",
        "blocker",
        f"netdev_lines={signal_count(signals, 'v703', 'android_icnss_netdev')} wlfw_lines={signal_count(signals, 'v703', 'android_wlfw_ready')}",
        [],
        "capture a narrow Android reference if this report is insufficient",
    )
    add_check(
        checks,
        "cnss-retry-eliminated",
        "pass" if signal_count(signals, "v701", "cnss_cld80211_only") and signal_count(signals, "v701", "kernel_progression_gap") else "blocked",
        "blocker",
        f"cld80211_lines={signal_count(signals, 'v701', 'cnss_cld80211_only')} gap_lines={signal_count(signals, 'v701', 'kernel_progression_gap')}",
        [],
        "do not retry the same CNSS/HAL path without a lower trigger",
    )
    add_check(
        checks,
        "vendor-namespace-eliminated",
        "pass" if signal_count(signals, "v727", "real_vendor_firmware_visible") and signal_count(signals, "v728", "private_vendor_root_pass") else "blocked",
        "blocker",
        f"firmware_lines={signal_count(signals, 'v727', 'real_vendor_firmware_visible')} private_vendor_lines={signal_count(signals, 'v728', 'private_vendor_root_pass')}",
        [],
        "repair private vendor root before lower trigger work if this fails",
    )
    add_check(
        checks,
        "wlan-module-load-eliminated",
        "pass" if signal_count(signals, "v727", "wlan_static_surface") else "blocked",
        "blocker",
        f"static_surface_lines={signal_count(signals, 'v727', 'wlan_static_surface')}",
        [],
        "do not plan insmod unless Android evidence proves a module path",
    )
    add_check(
        checks,
        "v747-check-coverage",
        "pass" if all(name in v747_by_name for name in (
            "v746-qca-child-unbound",
            "v746-no-mhi-wlfw-progress",
            "v716-bind-action-blocked-by-policy",
            "android-reference-usable",
        )) else "blocked",
        "blocker",
        "checks=" + ",".join(sorted(v747_by_name)),
        [],
        "refresh V747 classifier if expected checks are absent",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v748-nonbind-powerup-trigger-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V748 preflight",
        )
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v748-nonbind-powerup-trigger-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh source evidence before selecting the next gate",
        )
    if command == "preflight":
        return (
            "v748-nonbind-powerup-trigger-preflight-ready",
            True,
            "host-only source evidence is present and the candidate matrix is ready to run",
            "run V748 classifier and record the selected next gate",
        )
    return (
        "v748-icnss-qmi-wlfw-nonbind-trigger-selected",
        True,
        "bind/unbind, mdm_helper, repeated CNSS/HAL, vendor namespace, and wlan module load are eliminated; the remaining target is ICNSS-QMI/WLFW power-up trigger classification",
        "plan a read-only Android/native ICNSS-QMI/WLFW trigger capture before any live mutation",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    candidate_rows = [
        [name, data["status"], data["reason"]]
        for name, data in manifest.get("candidate_matrix", {}).items()
    ]
    return "\n".join([
        "# V748 Non-bind ICNSS/QCA Power-up Trigger Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "status", "reason"], candidate_rows) if candidate_rows else "- plan only",
        "",
        "## Source Evidence",
        "",
        markdown_table(["source", "path"], [
            ["v747", str(manifest.get("v747_manifest", ""))],
            ["v746", str(manifest.get("v746_manifest", ""))],
            ["v701_report", str(manifest.get("v701_report", ""))],
            ["v703_report", str(manifest.get("v703_report", ""))],
            ["v716_report", str(manifest.get("v716_report", ""))],
            ["v727_report", str(manifest.get("v727_report", ""))],
            ["v728_report", str(manifest.get("v728_report", ""))],
        ]),
        "",
        "## Guardrail",
        "",
        "- Do not write QCA6390 `bind`, `unbind`, or `driver_override`.",
        "- Do not start service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, or external ping.",
        "- The next unit must remain read-only unless it proves a specific non-bind trigger with cleanup.",
        "",
    ])


def build_candidate_matrix(checks: list[Check]) -> dict[str, dict[str, str]]:
    passed = {check.name for check in checks if check.status == "pass"}
    return {
        "qca6390_bind_unbind": {
            "status": "rejected" if "qca-bind-unbind-eliminated" in passed else "unproven",
            "reason": "V747/V716 classify the child driver-link gap as not a bind target.",
        },
        "mdm_helper": {
            "status": "rejected" if "mdm-helper-eliminated" in passed else "unproven",
            "reason": "V746 started mdm_helper safely after sysmon but no lower marker advanced.",
        },
        "repeat_cnss_or_hal": {
            "status": "rejected" if "cnss-retry-eliminated" in passed else "unproven",
            "reason": "Prior CNSS reaches cld80211 only; no ICNSS-QMI/WLFW/BDF/wlan0 progression.",
        },
        "vendor_namespace": {
            "status": "satisfied" if "vendor-namespace-eliminated" in passed else "unproven",
            "reason": "V727/V728 show real vendor firmware is available in the private exec namespace.",
        },
        "wlan_module_load": {
            "status": "rejected" if "wlan-module-load-eliminated" in passed else "unproven",
            "reason": "V727 treats wlan as static/built-in unless Android later proves a loadable module path.",
        },
        "icnss_qmi_wlfw_powerup": {
            "status": "selected" if not blocking_checks(checks) else "blocked",
            "reason": "Only remaining target before Wi-Fi HAL/connect is the non-bind ICNSS-QMI/WLFW power-up edge.",
        },
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v747_manifest = ""
    v746_manifest = ""
    v747: dict[str, Any] = {}
    v746: dict[str, Any] = {}
    signals: dict[str, Any] = {}
    checks: list[Check] = []
    if args.command != "plan":
        v747_path = resolve_manifest(args.v747_source)
        v746_path = resolve_manifest(args.v746_source)
        v747_manifest = str(v747_path)
        v746_manifest = str(v746_path)
        v747 = load_json(v747_path)
        v746 = load_json(v746_path)
        signals = build_signals(args)
        checks = build_checks(v747, v746, signals)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v748",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "v747_manifest": v747_manifest,
        "v746_manifest": v746_manifest,
        "v701_report": str(repo_path(args.v701_report)),
        "v703_report": str(repo_path(args.v703_report)),
        "v716_report": str(repo_path(args.v716_report)),
        "v727_report": str(repo_path(args.v727_report)),
        "v728_report": str(repo_path(args.v728_report)),
        "v747_decision": v747.get("decision"),
        "v746_decision": v746.get("decision"),
        "v746_marker_counts": v746_marker_counts(v746) if v746 else {},
        "signals": signals,
        "checks": [asdict(check) for check in checks],
        "candidate_matrix": build_candidate_matrix(checks) if checks else {},
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v748-nonbind-powerup-trigger.txt")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(str(store.run_dir.relative_to(repo_path("."))) + "\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
