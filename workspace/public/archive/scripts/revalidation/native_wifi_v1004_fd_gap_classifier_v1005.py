#!/usr/bin/env python3
"""V1005 host-only classifier for the V1004 mdm_helper eSoC fd gap."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1005-v1004-fd-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1005-v1004-fd-gap-classifier.txt")

DEFAULT_V1000_DMESG = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt"
)
DEFAULT_V1000_PROCESS = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/process-fd.txt"
)
DEFAULT_V1000_GPIO = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/gpio.txt"
)
DEFAULT_V911_REPORT = Path("docs/reports/NATIVE_INIT_V911_MDM_HELPER_ESOC_FD_STALL_CLASSIFIER_2026-05-26.md")
DEFAULT_V1004_MANIFEST = Path("tmp/wifi/v1004-android-service-window-subsys-trigger-live/manifest.json")
DEFAULT_V1004_TRANSCRIPT = Path(
    "tmp/wifi/v1004-android-service-window-subsys-trigger-live/native/mdm-helper-cnss-before-esoc.txt"
)

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")

EVENT_PATTERNS: dict[str, str] = {
    "wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "wificond_start": r"init: starting service 'wificond'",
    "mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
    "esoc0_get": r"__subsystem_get\(\):\s+__subsystem_get:\s+esoc0 count:0",
    "wlfw_start": r"cnss-daemon wlfw_start:\s+Starting",
    "wlan_pd": r"service-notifier: .*msm/modem/wlan_pd",
    "icnss_qmi_connected": r"icnss_qmi:\s+QMI Server Connected",
    "bdf": r"BDF file\s*:",
    "wlan0": r"dev\s*:\s*wlan0\s*:\s*event|\bwlan0\b",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1000-dmesg", type=Path, default=DEFAULT_V1000_DMESG)
    parser.add_argument("--v1000-process", type=Path, default=DEFAULT_V1000_PROCESS)
    parser.add_argument("--v1000-gpio", type=Path, default=DEFAULT_V1000_GPIO)
    parser.add_argument("--v911-report", type=Path, default=DEFAULT_V911_REPORT)
    parser.add_argument("--v1004-manifest", type=Path, default=DEFAULT_V1004_MANIFEST)
    parser.add_argument("--v1004-transcript", type=Path, default=DEFAULT_V1004_TRANSCRIPT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_event(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if regex.search(line):
            return {
                "present": True,
                "line_number": line_number,
                "time": dmesg_time(line),
                "line": line,
            }
    return {"present": False, "line_number": None, "time": None, "line": ""}


def parse_events(dmesg: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(dmesg, pattern) for name, pattern in EVENT_PATTERNS.items()}


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = events.get(later, {}).get("time")
    earlier_time = events.get(earlier, {}).get("time")
    if not isinstance(later_time, int | float) or not isinstance(earlier_time, int | float):
        return None
    return round((float(later_time) - float(earlier_time)) * 1000.0, 3)


def manifest_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def bool_contract(contract: dict[str, str], key: str) -> bool:
    return contract.get(key) == "1"


def classify(args: argparse.Namespace) -> dict[str, Any]:
    dmesg = read_text(args.v1000_dmesg)
    process = read_text(args.v1000_process)
    gpio = read_text(args.v1000_gpio)
    v911 = read_text(args.v911_report)
    v1004_manifest = load_json(args.v1004_manifest)
    v1004_transcript = read_text(args.v1004_transcript)
    contract = manifest_contract(v1004_manifest)
    events = parse_events(dmesg)

    android_service_window_positive = all(
        events[name]["present"]
        for name in (
            "wifi_hal_legacy_start",
            "wifi_hal_ext_start",
            "wificond_start",
            "mdm_helper_start",
            "cnss_daemon_start",
            "esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi_connected",
        )
    )
    android_mdm_helper_fd = bool(re.search(r"PROC .*comm=mdm_helper.*\n(?:.*\n){0,80}.*?/dev/esoc-0", process))
    android_gpio_identity = "GPIO_DEBUG readable=1" in gpio and "gpio135" in gpio and "gpio142" in gpio
    native_prior_mdm_helper_fd = all(
        marker in v911 for marker in ("`fd_esoc0_count.window` | `1`", "worker thread wchan", "ESOC_WAIT_FOR_REQ")
    )
    v1004_actor_set_observed = all(
        bool_contract(contract, key)
        for key in (
            "service_manager_start_executed",
            "wifi_hal_start_executed",
            "wificond_start_executed",
            "mdm_helper_start_executed",
            "cnss_daemon_start_executed",
            "all_observable_at_timeout",
            "all_postflight_safe",
        )
    )
    v1004_fd_gate_closed = (
        v1004_manifest.get("decision") == "v1004-mdm-helper-esoc-fd-missing-no-trigger"
        and contract.get("mdm_helper_esoc0_fd_count") == "0"
        and contract.get("subsys_trigger_start_attempted") == "0"
        and contract.get("subsys_esoc0_open_attempted") == "0"
    )
    v1004_domain_correct = all(
        marker in v1004_transcript
        for marker in (
            "wifi_hal_composite_child.mdm_helper.selinux_exec.ok=1",
            "wifi_hal_composite_child.mdm_helper.selinux.exec=u:r:vendor_mdm_helper:s0",
        )
    )
    no_forbidden = all(
        v1004_manifest.get(key) is False
        for key in (
            "qcwlanstate_write_executed",
            "iwifi_start_executed",
            "live_esoc_ioctl_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "subsys_esoc0_open_attempted",
        )
    )
    single_scan_after_spawn = all(
        key in contract
        for key in (
            "fd_match.mdm_helper_esoc0_gate.begin",
            "fd_match.mdm_helper_esoc0_gate.end",
            "runtime_after_spawn.begin",
            "runtime_after_spawn.end",
        )
    )

    checks = {
        "android_service_window_positive": android_service_window_positive,
        "android_mdm_helper_fd": android_mdm_helper_fd,
        "android_gpio_identity": android_gpio_identity,
        "native_prior_mdm_helper_fd": native_prior_mdm_helper_fd,
        "v1004_actor_set_observed": v1004_actor_set_observed,
        "v1004_fd_gate_closed": v1004_fd_gate_closed,
        "v1004_domain_correct": v1004_domain_correct,
        "v1004_no_forbidden_actions": no_forbidden,
        "v1004_single_scan_after_spawn": single_scan_after_spawn,
    }

    if all(checks.values()):
        decision = "v1005-select-service-window-mdm-helper-fd-poll-support"
        passed = True
        route = "source-build-helper-v171-mdm-helper-fd-poll"
        reason = (
            "Android and prior native evidence prove mdm_helper can hold /dev/esoc-0, "
            "while V1004 proves the full service-window actor set did not expose it at the single post-spawn gate"
        )
        next_step = (
            "Add helper v171 support for repeated mdm_helper /dev/esoc-0 fd polling inside the service window, "
            "from immediately after mdm_helper spawn through cnss-daemon spawn, before any /dev/subsys_esoc0 trigger"
        )
    elif android_service_window_positive and v1004_fd_gate_closed:
        decision = "v1005-select-android-dmesg-refresh-before-native-retry"
        passed = True
        route = "android-read-only-dmesg-recapture"
        reason = "Android service-window positive evidence exists, but one or more fd/context comparison inputs are stale or missing"
        next_step = "Run Android read-only dmesg/proc recapture, then rerun this classifier before changing the native trigger"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1005-fd-gap-evidence-incomplete"
        passed = False
        route = "repair-evidence-before-live"
        reason = f"required comparison evidence missing: {missing}"
        next_step = "refresh V1000/V911/V1004 evidence before selecting another native live gate"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "events": events,
        "deltas_ms": {
            "mdm_helper_start_to_cnss_daemon_start": delta_ms(events, "cnss_daemon_start", "mdm_helper_start"),
            "mdm_helper_start_to_esoc0_get": delta_ms(events, "esoc0_get", "mdm_helper_start"),
            "cnss_daemon_start_to_esoc0_get": delta_ms(events, "esoc0_get", "cnss_daemon_start"),
            "esoc0_get_to_wlfw_start": delta_ms(events, "wlfw_start", "esoc0_get"),
            "wlfw_start_to_wlan_pd": delta_ms(events, "wlan_pd", "wlfw_start"),
            "wlan_pd_to_icnss_qmi": delta_ms(events, "icnss_qmi_connected", "wlan_pd"),
        },
        "v1004": {
            "decision": v1004_manifest.get("decision"),
            "pass": v1004_manifest.get("pass"),
            "result": contract.get("result"),
            "reason": contract.get("reason"),
            "mdm_helper_pid": contract.get("fd_match.mdm_helper_esoc0_gate.pid"),
            "mdm_helper_esoc0_fd_count": contract.get("mdm_helper_esoc0_fd_count"),
            "subsys_trigger_start_attempted": contract.get("subsys_trigger_start_attempted"),
            "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted"),
            "child_started": contract.get("child_started"),
        },
    }


def event_rows(events: dict[str, dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for name in EVENT_PATTERNS:
        event = events[name]
        rows.append(
            (
                name,
                "yes" if event["present"] else "no",
                "" if event["time"] is None else f"{event['time']:.6f}",
                str(event["line_number"] or ""),
            )
        )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    checks = classification["checks"]
    deltas = classification["deltas_ms"]
    return "\n".join(
        [
            "# V1005 V1004 fd Gap Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{classification['decision']}`",
            f"- pass: `{classification['pass']}`",
            f"- route: `{classification['route']}`",
            f"- reason: {classification['reason']}",
            f"- next: {classification['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path", "exists", "sha256"],
                [
                    (name, payload["path"], str(payload["exists"]), payload["sha256"])
                    for name, payload in manifest["inputs"].items()
                ],
            ),
            "",
            "## Checks",
            "",
            markdown_table(["check", "pass"], [(name, str(value)) for name, value in checks.items()]),
            "",
            "## Android Timing",
            "",
            markdown_table(["event", "present", "time_s", "line"], event_rows(classification["events"])),
            "",
            "## Deltas",
            "",
            markdown_table(
                ["delta", "ms"],
                [(name, "" if value is None else str(value)) for name, value in deltas.items()],
            ),
            "",
            "## V1004 Native Gate",
            "",
            "```json",
            json.dumps(classification["v1004"], ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    inputs = {
        "v1000_dmesg": args.v1000_dmesg,
        "v1000_process": args.v1000_process,
        "v1000_gpio": args.v1000_gpio,
        "v911_report": args.v911_report,
        "v1004_manifest": args.v1004_manifest,
        "v1004_transcript": args.v1004_transcript,
    }
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "host_only": True,
        "device_commands_executed": False,
        "device_mutations": False,
        "native_live_executed": False,
        "android_live_executed": False,
        "classification": classification,
        "inputs": {
            name: {
                "path": str(repo_path(path)),
                "exists": repo_path(path).exists(),
                "sha256": sha256(path),
                "bytes": repo_path(path).stat().st_size if repo_path(path).exists() else 0,
            }
            for name, path in inputs.items()
        },
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"route: {classification['route']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
