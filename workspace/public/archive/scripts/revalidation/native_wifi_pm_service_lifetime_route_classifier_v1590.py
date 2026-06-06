#!/usr/bin/env python3
"""V1590 host-only classifier for the current pm-service lifetime route gap.

V1589 proves the V1588 service-window lower-marker sampler works, but it also
shows that `pm-service`/`per_mgr` is gone before the lower-marker window.  This
classifier compares that current route with older positive late-`per_proxy`
evidence that did reach the PM-service-owned `/dev/subsys_esoc0` powerup path.
It does not contact the device or mutate artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1590-pm-service-lifetime-route-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1590_PM_SERVICE_LIFETIME_ROUTE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1590-pm-service-lifetime-route-classifier.txt")

V1589_MANIFEST = Path("tmp/wifi/v1589-service-window-lower-marker-handoff/manifest.json")
V1589_HELPER = Path(
    "tmp/wifi/v1589-service-window-lower-marker-handoff/test-v1393-helper-result.stdout.txt"
)
V1589_DMESG = Path("tmp/wifi/v1589-service-window-lower-marker-handoff/test-v1393-dmesg.stdout.txt")

V1238_MANIFEST = Path("tmp/wifi/v1238-late-per-proxy-only-live/manifest.json")
V1238_SUMMARY = Path("tmp/wifi/v1238-late-per-proxy-only-live/summary.md")
V1303_MANIFEST = Path("tmp/wifi/v1303-compact-powerup-marker-live/manifest.json")
V1303_SUMMARY = Path("tmp/wifi/v1303-compact-powerup-marker-live/summary.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def helper_value(text: str, key: str) -> str | None:
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def summary_value(text: str, key: str) -> str | None:
    prefix = f"| {key} |"
    for line in text.splitlines():
        if line.startswith(prefix):
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) >= 2:
                return parts[1].strip("` ")
    return None


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def analyze() -> dict[str, Any]:
    v1589 = read_json(V1589_MANIFEST)
    v1589_helper = read_text(V1589_HELPER)
    v1589_dmesg = read_text(V1589_DMESG)
    v1238 = read_json(V1238_MANIFEST)
    v1238_summary = read_text(V1238_SUMMARY)
    v1303 = read_json(V1303_MANIFEST)
    v1303_summary = read_text(V1303_SUMMARY)

    v1589_progress = v1589.get("wifi_progress") if isinstance(v1589.get("wifi_progress"), dict) else {}
    v1589_current = {
        "handoff_pass": truthy(v1589.get("pass")) and truthy(v1589.get("handoff_pass")),
        "rollback_ok": truthy((v1589.get("rollback") or {}).get("ok")),
        "final_decision": v1589_progress.get("final_decision"),
        "provider_trigger": truthy(v1589_progress.get("provider_trigger")),
        "modem_trigger": truthy(v1589_progress.get("modem_trigger")),
        "helper_result_contract_seen": truthy(v1589_progress.get("helper_result_contract_seen")),
        "helper_result_subsys_trigger_started": truthy(
            v1589_progress.get("helper_result_subsys_trigger_started")
        ),
        "helper_result_mdm_helper_esoc0_fd_count": int_value(
            v1589_progress.get("helper_result_mdm_helper_esoc0_fd_count"), -1
        ),
        "pm_proxy_contract": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.pm_proxy_contract"), -1
        ),
        "pm_proxy_helper_subsys_modem_fd_count": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count"),
            -1,
        ),
        "per_mgr_subsys_modem_fd_count": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.per_mgr_subsys_modem_fd_count"), -1
        ),
        "pm_full_contract_seen": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.pm_full_contract_seen"), -1
        ),
        "per_mgr_alive_seen": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.lower_marker.per_mgr_alive_seen"), -1
        ),
        "per_mgr_child_observable": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.child.per_mgr.observable"), -1
        ),
        "per_mgr_child_exited": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.child.per_mgr.exited"), -1
        ),
        "per_mgr_child_exit_code": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.child.per_mgr.exit_code"), -99
        ),
        "pm_proxy_child_exited": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.child.pm_proxy.exited"), -1
        ),
        "pm_proxy_child_exit_code": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.child.pm_proxy.exit_code"), -99
        ),
        "global_subsys_esoc0_fd_max": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.lower_marker.global_subsys_esoc0_fd_max"),
            -1,
        ),
        "pm_service_powerup_seen": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.lower_marker.pm_service_powerup_seen"), -1
        ),
        "max_powerup_thread_count": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.lower_marker.max_powerup_thread_count"), -1
        ),
        "trigger_child_alive_seen": int_value(
            helper_value(v1589_helper, "android_wifi_service_window.lower_marker.trigger_child_alive_seen"), -1
        ),
        "trigger_child_stack_powerup_lines": count_lines(v1589_helper, "mdm_subsys_powerup"),
        "dmesg_pm_proxy_helper_modem_get": count_lines(v1589_dmesg, "pm_proxy_helper", "__subsystem_get: modem"),
        "dmesg_scoped_esoc0_get": count_lines(v1589_dmesg, "a90_android_exe", "__subsystem_get: esoc0"),
        "dmesg_pm_service_esoc0_get": count_lines(v1589_dmesg, "pm-service", "__subsystem_get: esoc0"),
        "wlan0_present": truthy(v1589_progress.get("wlan0_present")),
        "connect_ready": truthy(v1589_progress.get("connect_ready")),
    }

    positive_route = {
        "v1238_pass": truthy(v1238.get("pass")),
        "v1238_decision": v1238.get("decision"),
        "v1238_late_per_proxy_started": summary_value(v1238_summary, "late_started"),
        "v1238_pm_service_actor_esoc0_attempt": summary_value(v1238_summary, "pm_service_actor_esoc0_attempt"),
        "v1238_post_pm_fd_esoc0_count": summary_value(v1238_summary, "post_pm_fd_esoc0_count"),
        "v1238_wlan0_seen": summary_value(v1238_summary, "boundary_wlan0_seen"),
        "v1303_pass": truthy(v1303.get("pass")),
        "v1303_decision": v1303.get("decision"),
        "v1303_powerup_marker_emitted": summary_value(v1303_summary, "powerup_marker_emitted"),
        "v1303_max_powerup_thread_count": summary_value(v1303_summary, "max_powerup_thread_count"),
        "v1303_powerup_subsys_esoc0_inferred_seen": summary_value(
            v1303_summary, "powerup_subsys_esoc0_inferred_seen"
        ),
        "v1303_powerup_first_path_values": summary_value(v1303_summary, "powerup_first_path_values"),
        "v1303_powerup_first_wchans": summary_value(v1303_summary, "powerup_first_wchans"),
        "v1303_powerup_first_syscall_names": summary_value(v1303_summary, "powerup_first_syscall_names"),
        "v1303_wlan0_seen": summary_value(v1303_summary, "wlan0_seen"),
    }

    v1589_pm_route_missing = (
        v1589_current["handoff_pass"]
        and v1589_current["rollback_ok"]
        and v1589_current["per_mgr_alive_seen"] == 0
        and v1589_current["per_mgr_child_exited"] == 1
        and v1589_current["per_mgr_child_exit_code"] == 0
        and v1589_current["pm_proxy_child_exited"] == 1
        and v1589_current["pm_proxy_child_exit_code"] == 1
        and v1589_current["global_subsys_esoc0_fd_max"] == 0
        and v1589_current["pm_service_powerup_seen"] == 0
        and v1589_current["max_powerup_thread_count"] == 0
        and v1589_current["dmesg_pm_service_esoc0_get"] == 0
        and v1589_current["trigger_child_alive_seen"] == 1
        and v1589_current["trigger_child_stack_powerup_lines"] > 0
    )
    positive_pm_route_exists = (
        positive_route["v1238_pass"]
        and str(positive_route["v1238_pm_service_actor_esoc0_attempt"]).lower() == "true"
        and int_value(positive_route["v1238_post_pm_fd_esoc0_count"], 0) > 0
        and positive_route["v1303_pass"]
        and str(positive_route["v1303_powerup_subsys_esoc0_inferred_seen"]).lower() == "true"
        and int_value(positive_route["v1303_max_powerup_thread_count"], 0) > 0
        and positive_route["v1303_powerup_first_path_values"] == "/dev/subsys_esoc0"
        and positive_route["v1303_powerup_first_wchans"] == "mdm_subsys_powerup"
    )
    no_wifi_done = (
        not v1589_current["wlan0_present"]
        and not v1589_current["connect_ready"]
        and str(positive_route["v1238_wlan0_seen"]).lower() == "false"
        and str(positive_route["v1303_wlan0_seen"]).lower() == "false"
    )

    checks = [
        {
            "name": "v1589-current-lower-marker-valid",
            "status": "pass" if v1589_current["handoff_pass"] and v1589_current["rollback_ok"] else "fail",
            "detail": "V1589 handoff passed and rollback verified",
        },
        {
            "name": "v1589-pm-service-route-missing",
            "status": "pass" if v1589_pm_route_missing else "fail",
            "detail": "per_mgr exits 0, pm_proxy exits 1, no PM-service-owned /dev/subsys_esoc0/powerup marker",
        },
        {
            "name": "older-positive-pm-route-exists",
            "status": "pass" if positive_pm_route_exists else "fail",
            "detail": "V1238/V1303 show late-per_proxy path reaching /dev/subsys_esoc0/mdm_subsys_powerup",
        },
        {
            "name": "not-ready-for-connect",
            "status": "pass" if no_wifi_done else "fail",
            "detail": "wlan0/connect remain absent; credentials/connect/DHCP/ping are still downstream",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = (
        "v1590-route-current-service-window-loses-pm-service-owned-powerup"
        if pass_ok
        else "v1590-input-evidence-incomplete-review-required"
    )
    reason = (
        "V1589 lower-marker route starts the scoped trigger but loses the PM-service-owned route; V1238/V1303 prove late-per_proxy can reach the correct PM-service /dev/subsys_esoc0 powerup boundary"
        if pass_ok
        else "one or more V1589/V1238/V1303 evidence predicates are missing or contradictory"
    )
    next_step = (
        "V1591 source/build-only: derive a firmware-mount-preserving late-per_proxy-only service-window test boot with lower-marker sampling, no direct scoped trigger, and explicit PM-service lifetime/exit markers"
        if pass_ok
        else "refresh or inspect the missing evidence before another live gate"
    )
    return {
        "cycle": "V1590",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1589_manifest": rel(V1589_MANIFEST),
            "v1589_helper": rel(V1589_HELPER),
            "v1589_dmesg": rel(V1589_DMESG),
            "v1238_manifest": rel(V1238_MANIFEST),
            "v1238_summary": rel(V1238_SUMMARY),
            "v1303_manifest": rel(V1303_MANIFEST),
            "v1303_summary": rel(V1303_SUMMARY),
        },
        "current_v1589": v1589_current,
        "positive_pm_route": positive_route,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    current = manifest["current_v1589"]
    positive = manifest["positive_pm_route"]
    return "\n".join(
        [
            "# V1590 PM-service Lifetime Route Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[key, value] for key, value in manifest["inputs"].items()]),
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "status", "detail"],
                [[item["name"], item["status"], item["detail"]] for item in manifest["checks"]],
            ),
            "",
            "## Current V1589 Route",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in current.items()]),
            "",
            "## Positive PM-service Route References",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in positive.items()]),
            "",
            "## Interpretation",
            "",
            "V1589 proves the compact lower-marker sampler is useful, but the current",
            "service-window ordering does not keep `pm-service` alive long enough to own",
            "`/dev/subsys_esoc0`.  The live powerup stack in V1589 belongs to the scoped",
            "helper trigger child, not to Android's PM-service Binder route.  V1238 and",
            "V1303 remain the better PM-service-owned route references because late",
            "`pm-proxy` caused PM-service to reach `/dev/subsys_esoc0` and",
            "`mdm_subsys_powerup`.",
            "",
            "## Safety",
            "",
            "Host-only classifier. No device command, Wi-Fi HAL, scan/connect,",
            "credentials, DHCP/routes, external ping, flash, boot image write, or",
            "partition write occurred.",
            "",
        ]
    )


def check_forbidden_output(manifest: dict[str, Any]) -> list[str]:
    text = json.dumps(manifest, sort_keys=True) + "\n" + render_summary(manifest)
    forbidden = [b"temmie" + b"5G", b"temmie" + b"0214"]
    encoded = text.encode("utf-8", errors="replace")
    hits: list[str] = []
    for index, value in enumerate(forbidden, 1):
        if value in encoded:
            hits.append(f"forbidden-pattern-{index}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    manifest = analyze()
    manifest["command"] = args.command
    if args.command == "plan":
        manifest["decision"] = "v1590-pm-service-lifetime-route-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only host classifier; no device command or mutation"
        manifest["next_step"] = "run V1590 host-only classifier"

    leaks = check_forbidden_output(manifest)
    manifest["forbidden_output_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1590-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden output string detected"
        manifest["next_step"] = "remove sensitive output before continuing"

    store = EvidenceStore(repo_path(args.out_dir))
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(args.report), summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(
        json.dumps(
            {
                "decision": manifest["decision"],
                "pass": manifest["pass"],
                "reason": manifest["reason"],
                "next_step": manifest["next_step"],
                "out_dir": str(store.run_dir),
                "report": rel(args.report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
