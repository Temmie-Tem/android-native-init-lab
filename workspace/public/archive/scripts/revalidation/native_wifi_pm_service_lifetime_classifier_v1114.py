#!/usr/bin/env python3
"""V1114 host-only classifier for V1113 PM-service lifetime/readiness.

V1113 proved the global firmware + global `/dev/subsys_modem` holder
precondition, but CNSS PM client register/connect returns were not reproduced
inside the combined window.  This classifier parses the V1113 manifest and
observer transcript to decide whether the next gate should repair timing rather
than widening toward Wi-Fi HAL.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1114-pm-service-lifetime-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1114-pm-service-lifetime-classifier.txt")
DEFAULT_V1113_MANIFEST = Path("tmp/wifi/v1113-global-firmware-pm-connect-live/manifest.json")
DEFAULT_V1113_OBSERVER = Path(
    "tmp/wifi/v1113-global-firmware-pm-connect-live/host/pm-server-wchan-tracefs-observer.txt"
)
EXPECTED_V1113_DECISION = "v1113-global-holder-cnss-pm-connect-not-reproduced"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def nested_get(value: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def cnss_returns(tracefs: dict[str, Any], label: str) -> list[str]:
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in str(comm):
            values.extend([str(item) for item in (labels or {}).get(label, [])])
    return values


def observer_line_matches(text: str, pattern: str, limit: int = 16) -> list[str]:
    regex = re.compile(pattern)
    matches: list[str] = []
    for index, raw_line in enumerate(text.splitlines(), 1):
        if regex.search(raw_line):
            matches.append(f"{index}:{raw_line.strip()}")
            if len(matches) >= limit:
                break
    return matches


def classify(manifest: dict[str, Any], observer_text: str) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    counts = tracefs.get("counts") or {}
    keys = parse_key_values(observer_text)

    per_mgr = {
        "start_executed": contract.get("per_mgr_start_executed"),
        "post_start_observable": contract.get("child.per_mgr.post_start_observable"),
        "post_start_ready": contract.get("child.per_mgr.post_start_ready"),
        "post_start_fd_summary_captured": contract.get("child.per_mgr.post_start_fd_summary_captured"),
        "observable": contract.get("child.per_mgr.observable"),
        "exited": contract.get("child.per_mgr.exited"),
        "exit_code": contract.get("child.per_mgr.exit_code"),
        "signal": contract.get("child.per_mgr.signal"),
        "reaped": contract.get("child.per_mgr.reaped"),
        "postflight_safe": contract.get("child.per_mgr.postflight_safe"),
        "subsys_modem_seen": contract.get("per_mgr_subsys_modem_seen"),
    }
    cnss = {
        "start_executed": contract.get("cnss_daemon_start_executed"),
        "hit_count": tracefs.get("cnss_daemon_hit_count"),
        "pm_client_register_entry_count": counts.get("pm_client_register_entry"),
        "pm_client_register_ret": cnss_returns(tracefs, "pm_client_register_ret"),
        "pm_client_connect_entry_count": counts.get("pm_client_connect_entry"),
        "pm_client_connect_ret": cnss_returns(tracefs, "pm_client_connect_ret"),
    }
    pm_proxy_helper = {
        "start_executed": contract.get("pm_proxy_helper_start_executed"),
        "subsys_modem_seen": contract.get("pm_proxy_helper_subsys_modem_seen"),
        "poll_00_subsys_modem_count": contract.get("poll_00.pm_proxy_helper_subsys_modem_count"),
    }
    readiness = {
        "vndservice_provider_after_per_mgr": keys.get(
            "wifi_vndservice_query.pm_observer_after_per_mgr_probe.vendor_qcom_peripheral_manager_seen"
        ),
        "vndservice_query_after_per_mgr_result": keys.get(
            "wifi_vndservice_query.pm_observer_after_per_mgr_probe.result"
        ),
        "thread_samples_by_tid": tracefs.get("thread_samples_by_tid") or {},
        "pm_service_pids_by_sample": tracefs.get("pm_service_pids_by_sample") or {},
        "pm_service_by_comm": (tracefs.get("by_comm") or {}).get("pm-service", {}),
    }

    global_ok = (
        all((global_fw.get("mounted_hits") or {}).values())
        and bool(global_fw.get("holder_opened"))
        and "ONLINE" in {global_fw.get("mss_after_holder"), global_fw.get("mss_after_observer")}
        and bool((global_fw.get("qrtr_rx_wait") or {}).get("seen"))
    )
    per_mgr_short_lived = (
        per_mgr["start_executed"] == "1"
        and per_mgr["post_start_observable"] == "0"
        and per_mgr["post_start_ready"] == "0"
        and per_mgr["exited"] == "1"
        and per_mgr["exit_code"] == "0"
        and per_mgr["signal"] == "0"
    )
    cnss_not_reached = (
        cnss["start_executed"] == "1"
        and int_value(cnss["hit_count"]) == 0
        and int_value(cnss["pm_client_register_entry_count"]) == 0
        and int_value(cnss["pm_client_connect_entry_count"]) == 0
    )
    helper_holds_modem = (
        pm_proxy_helper["start_executed"] == "1"
        and pm_proxy_helper["subsys_modem_seen"] == "1"
        and int_value(pm_proxy_helper["poll_00_subsys_modem_count"], -1) > 0
    )
    provider_absent_after_per_mgr = readiness["vndservice_provider_after_per_mgr"] == "0"

    return {
        "v1113_decision": manifest.get("decision", ""),
        "v1113_pass": bool(manifest.get("pass")),
        "observer_exists": bool(observer_text),
        "global_ok": global_ok,
        "per_mgr": per_mgr,
        "cnss": cnss,
        "pm_proxy_helper": pm_proxy_helper,
        "readiness": readiness,
        "per_mgr_short_lived_before_cnss": per_mgr_short_lived,
        "cnss_client_path_not_reached": cnss_not_reached,
        "pm_proxy_helper_holds_modem": helper_holds_modem,
        "provider_absent_after_per_mgr": provider_absent_after_per_mgr,
        "key_lines": {
            "per_mgr_lifetime": observer_line_matches(
                observer_text,
                r"child\.per_mgr\.(post_start|observable|exited|exit_code|signal|reaped)",
            ),
            "cnss_client_counts": observer_line_matches(observer_text, r"event\.pm_client_.*\.count="),
            "syscall_probe": observer_line_matches(observer_text, r"syscall_probe\.poll_..\.alive="),
            "provider_query": observer_line_matches(observer_text, r"pm_observer_after_per_mgr_probe\.(vendor_qcom|result)"),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if analysis["v1113_decision"] != EXPECTED_V1113_DECISION:
        return (
            "v1114-v1113-input-not-current",
            False,
            f"unexpected V1113 decision={analysis['v1113_decision']!r}",
            "refresh V1113 before classifying PM-service lifetime",
        )
    if not analysis["observer_exists"]:
        return (
            "v1114-observer-transcript-missing",
            False,
            "V1113 observer transcript is missing",
            "restore V1113 evidence or rerun V1113",
        )
    if not analysis["global_ok"]:
        return (
            "v1114-global-holder-precondition-not-proven",
            False,
            "V1113 global firmware/holder prerequisite is not proven",
            "repair V1113 lower prerequisite before PM-service timing work",
        )
    if (
        analysis["per_mgr_short_lived_before_cnss"]
        and analysis["cnss_client_path_not_reached"]
        and analysis["pm_proxy_helper_holds_modem"]
        and analysis["provider_absent_after_per_mgr"]
    ):
        return (
            "v1114-select-immediate-cnss-after-per-mgr-start-gate",
            True,
            "pm-service exits cleanly before the current 1000ms post-start probe and CNSS PM client path never fires",
            "V1115 should add an immediate-CNSS-after-per_mgr-start observer that samples pm-service before the 1000ms wait/vndservice query",
        )
    if analysis["cnss_client_path_not_reached"]:
        return (
            "v1114-cnss-client-path-not-reached-classified",
            True,
            "CNSS PM client path did not fire, but PM-service lifetime evidence is incomplete",
            "add earlier PM-service lifetime samples before widening to Wi-Fi HAL",
        )
    return (
        "v1114-pm-service-lifetime-inconclusive",
        True,
        "V1113 did not match the expected short-lived PM-service pattern",
        "inspect V1113 transcript manually before choosing V1115",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    per_mgr = analysis["per_mgr"]
    cnss = analysis["cnss"]
    helper = analysis["pm_proxy_helper"]
    flags = [
        ["global_ok", analysis["global_ok"]],
        ["per_mgr_short_lived_before_cnss", analysis["per_mgr_short_lived_before_cnss"]],
        ["cnss_client_path_not_reached", analysis["cnss_client_path_not_reached"]],
        ["pm_proxy_helper_holds_modem", analysis["pm_proxy_helper_holds_modem"]],
        ["provider_absent_after_per_mgr", analysis["provider_absent_after_per_mgr"]],
    ]
    rows = [
        ["per_mgr", json.dumps(per_mgr, sort_keys=True)],
        ["cnss", json.dumps(cnss, sort_keys=True)],
        ["pm_proxy_helper", json.dumps(helper, sort_keys=True)],
    ]
    return "\n".join([
        "# V1114 PM-Service Lifetime Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Classification Flags",
        "",
        markdown_table(["flag", "value"], flags),
        "",
        "## Evidence Summary",
        "",
        markdown_table(["area", "value"], rows),
        "",
        "## Key Lines",
        "",
        "```json",
        json.dumps(analysis["key_lines"], indent=2, sort_keys=True),
        "```",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1113-manifest", type=Path, default=DEFAULT_V1113_MANIFEST)
    parser.add_argument("--v1113-observer", type=Path, default=DEFAULT_V1113_OBSERVER)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "v1113_decision": "",
            "v1113_pass": False,
            "observer_exists": False,
            "global_ok": False,
            "per_mgr": {},
            "cnss": {},
            "pm_proxy_helper": {},
            "readiness": {},
            "per_mgr_short_lived_before_cnss": False,
            "cnss_client_path_not_reached": False,
            "pm_proxy_helper_holds_modem": False,
            "provider_absent_after_per_mgr": False,
            "key_lines": {},
        }
        decision, passed, reason, next_step = (
            "v1114-pm-service-lifetime-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1114 host-only classifier against V1113 evidence",
        )
    else:
        v1113 = load_json(args.v1113_manifest)
        observer_text = read_text(args.v1113_observer)
        analysis = classify(v1113, observer_text)
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1114",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1113_manifest": str(repo_path(args.v1113_manifest)),
            "v1113_observer": str(repo_path(args.v1113_observer)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "firmware_mounts_executed": False,
        "global_modem_holder_opened": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
