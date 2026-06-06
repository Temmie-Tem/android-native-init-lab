#!/usr/bin/env python3
"""V812 bounded below-HAL mdm3/WLAN-PD/service69 live observer.

The runner refreshes current-boot SELinux prep, reuses the established V735
CNSS-only lower observer with the current helper, and reclassifies the result
against V811.  It remains below Wi-Fi HAL, scan/connect, credentials, DHCP,
routes, external ping, esoc0, bind/unbind, and module load/unload.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v812-mdm3-wlanpd-service69-observer")
LATEST_POINTER = Path("tmp/wifi/latest-v812-mdm3-wlanpd-service69-observer.txt")
DEFAULT_V811_MANIFEST = Path("tmp/wifi/v811-wlfw-publication-precondition-classifier/manifest.json")
DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
V401_APPROVAL = "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"
V490_APPROVAL = "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up"

FORBIDDEN_ACTIONS = (
    "Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "esoc0 open or subsystem state write",
    "bind/unbind, driver_override, or module load/unload",
    "boot image write, partition write, or custom kernel flash",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--companion-runtime-sec", type=int, default=30)
    parser.add_argument("--v811-manifest", type=Path, default=DEFAULT_V811_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def run_host_step(store: EvidenceStore,
                  name: str,
                  command: list[str],
                  timeout: float) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        timed_out = False
        rc = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
    ended = dt.datetime.now(dt.timezone.utc)
    transcript = "\n".join([
        "$ " + " ".join(command),
        f"[rc] {rc}",
        f"[timed_out] {timed_out}",
        "[stdout]",
        stdout.rstrip(),
        "[stderr]",
        stderr.rstrip(),
        "",
    ])
    rel = f"host/{name}.txt"
    store.write_text(rel, transcript)
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "timed_out": timed_out,
        "ok": rc == 0 and not timed_out,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_sec": (ended - started).total_seconds(),
        "file": rel,
        "stdout_tail": stdout.splitlines()[-12:],
        "stderr_tail": stderr.splitlines()[-12:],
    }


def prep_commands(args: argparse.Namespace, root: Path) -> tuple[list[str], list[str]]:
    v401_dir = root / "prep" / "v401"
    v490_dir = root / "prep" / "v490"
    v401 = [
        "python3",
        "scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py",
        "--out-dir",
        str(v401_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--approval-phrase",
        V401_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    v490 = [
        "python3",
        "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
        "--out-dir",
        str(v490_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        "A90 Linux init 0.9.68 (v724)",
        "--helper-sha256",
        args.helper_sha256,
        "--approval-phrase",
        V490_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    return v401, v490


def mountsystem_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--hide-on-busy",
        "mountsystem",
        "ro",
    ]


def hide_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--hide-on-busy",
        "hide",
    ]


def v735_command(args: argparse.Namespace, root: Path) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/native_wifi_current_cnss_only_observer_v735.py",
        "--out-dir",
        str(root / "arm-v812-v735"),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        args.helper_marker,
        "--companion-runtime-sec",
        str(args.companion_runtime_sec),
        "--v490-manifest",
        str(root / "prep" / "v490" / "manifest.json"),
        "--proof-id",
        "v812",
        "run",
    ]


def summarize_v735(v735: dict[str, Any]) -> dict[str, Any]:
    live = v735.get("live") if isinstance(v735.get("live"), dict) else {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    readback = live.get("qrtr_readback") if isinstance(live.get("qrtr_readback"), dict) else {}
    helper = live.get("helper_result") if isinstance(live.get("helper_result"), dict) else {}
    return {
        "decision": v735.get("decision", ""),
        "pass": bool(v735.get("pass")),
        "reason": v735.get("reason", ""),
        "mss_after_holder": live.get("mss_after_holder", ""),
        "mss_after_companion": live.get("mss_after_companion", ""),
        "mdm3_after_holder": live.get("mdm3_after_holder", ""),
        "mdm3_after_companion": live.get("mdm3_after_companion", ""),
        "holder_opened": bool(live.get("holder_opened")),
        "companion_executed": bool(live.get("companion_executed")),
        "reboot_cleanup": live.get("reboot_cleanup") or {},
        "helper": {
            "mode": helper.get("mode"),
            "order": helper.get("order"),
            "child_started": helper.get("child_started"),
            "all_observable": helper.get("all_observable"),
            "all_postflight_safe": helper.get("all_postflight_safe"),
            "cnss_diag": helper.get("cnss_diag"),
            "cnss_daemon": helper.get("cnss_daemon"),
            "service_manager": helper.get("service_manager"),
            "wifi_hal": helper.get("wifi_hal"),
            "wificond": helper.get("wificond"),
            "scan_connect_linkup": helper.get("scan_connect_linkup"),
            "external_ping": helper.get("external_ping"),
        },
        "markers": {
            name: int_value(markers.get(name))
            for name in (
                "qrtr_rx",
                "qrtr_tx",
                "sysmon_qmi",
                "service_notifier",
                "wlan_pd",
                "mhi",
                "qca6390",
                "wlfw",
                "bdf",
                "wlan0",
                "kernel_warning",
            )
        },
        "qrtr_readback": {
            "service_events": int_value(readback.get("service_events")),
            "timeouts": int_value(readback.get("timeouts")),
            "end_of_list": int_value(readback.get("end_of_list")),
            "qmi_attempted": int_value(readback.get("qmi_attempted")),
            "result": readback.get("result"),
        },
    }


def build_checks(command: str,
                 v811: dict[str, Any],
                 prep: dict[str, Any],
                 v735_summary: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "bounded live observer plan; no device command executed",
            "next_step": "run V812 after bridge/native health check",
        }]
    helper = v735_summary.get("helper") if isinstance(v735_summary.get("helper"), dict) else {}
    markers = v735_summary.get("markers") if isinstance(v735_summary.get("markers"), dict) else {}
    readback = v735_summary.get("qrtr_readback") if isinstance(v735_summary.get("qrtr_readback"), dict) else {}
    forbidden_clean = all(
        int_value(helper.get(name)) == 0
        for name in ("service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")
    )
    return [
        {
            "name": "v811-route-ready",
            "status": "pass"
            if v811.get("pass") is True
            and v811.get("decision") == "v811-wlfw-publication-precondition-mdm3-wlanpd-gap-selected"
            else "blocked",
            "detail": {"decision": v811.get("decision"), "pass": v811.get("pass")},
            "next_step": "complete V811 before live observer",
        },
        {
            "name": "current-boot-prep",
            "status": "pass"
            if prep.get("v401", {}).get("pass")
            and prep.get("v490", {}).get("pass")
            else "blocked",
            "detail": prep,
            "next_step": "refresh V401/V490 before starting lower observer",
        },
        {
            "name": "v735-live-completed",
            "status": "pass" if v735_summary.get("pass") else "blocked",
            "detail": {
                "decision": v735_summary.get("decision"),
                "pass": v735_summary.get("pass"),
                "reason": v735_summary.get("reason"),
            },
            "next_step": "inspect V735 arm evidence if it failed",
        },
        {
            "name": "below-hal-contract",
            "status": "pass" if forbidden_clean and int_value(readback.get("qmi_attempted")) == 0 else "blocked",
            "detail": {"helper": helper, "qrtr_readback": readback},
            "next_step": "discard result if helper crossed HAL/connect or sent QMI payloads",
        },
        {
            "name": "mdm3-wlanpd-service69-surface",
            "status": "finding",
            "detail": {
                "mss": [v735_summary.get("mss_after_holder"), v735_summary.get("mss_after_companion")],
                "mdm3": [v735_summary.get("mdm3_after_holder"), v735_summary.get("mdm3_after_companion")],
                "markers": markers,
                "service69_events": readback.get("service_events"),
                "timeouts": readback.get("timeouts"),
            },
            "next_step": "if service69/WLFW advances, route to FW_READY/BDF; otherwise continue mdm3/WLAN-PD precondition isolation",
        },
        {
            "name": "postflight-cleanup",
            "status": "pass"
            if (v735_summary.get("reboot_cleanup") or {}).get("status_healthy")
            else "blocked",
            "detail": v735_summary.get("reboot_cleanup") or {},
            "next_step": "verify native health manually if cleanup did not pass",
        },
    ]


def decide(command: str,
           checks: list[dict[str, Any]],
           v735_summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v812-mdm3-wlanpd-service69-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "run bounded V812 live observer",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v812-mdm3-wlanpd-service69-observer-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear live observer blocker before retry",
        )
    markers = v735_summary.get("markers") if isinstance(v735_summary.get("markers"), dict) else {}
    readback = v735_summary.get("qrtr_readback") if isinstance(v735_summary.get("qrtr_readback"), dict) else {}
    advanced = any(int_value(markers.get(name)) for name in ("wlan_pd", "wlfw", "bdf", "wlan0")) or int_value(readback.get("service_events")) > 0
    if advanced:
        return (
            "v812-wlfw-publication-advanced",
            True,
            "below-HAL observer saw WLAN-PD/WLFW/service69/BDF/wlan0 progress",
            "capture FW_READY/BDF/netdev readiness before any Wi-Fi HAL or connect",
        )
    if int_value(markers.get("service_notifier")) > 0:
        return (
            "v812-service-publication-without-wlfw",
            True,
            "below-HAL observer reproduced service-notifier publication but service69/WLFW/BDF/wlan0 remain absent",
            "isolate mdm3/WLAN-PD publication preconditions before repeating boot_wlan or HAL work",
        )
    if int_value(markers.get("sysmon_qmi")) > 0 or int_value(markers.get("qrtr_tx")) > 0:
        return (
            "v812-sysmon-without-service69",
            True,
            "below-HAL observer reached QRTR/sysmon but service-notifier/WLFW/service69 remain absent",
            "target post-sysmon mdm3/WLAN-PD/service publication preconditions",
        )
    return (
        "v812-no-post-rx-advance",
        True,
        "below-HAL observer did not progress beyond modem QRTR RX",
        "refresh firmware holder and lower companion preconditions",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    root = store.run_dir
    v811 = load_json(args.v811_manifest)
    host_steps: list[dict[str, Any]] = []
    prep: dict[str, Any] = {}
    v735_data: dict[str, Any] = {}
    v735_summary: dict[str, Any] = {}
    if args.command == "run":
        v401_cmd, v490_cmd = prep_commands(args, root)
        host_steps.append(run_host_step(store, "v812-hide-before-prep", hide_command(args), 60.0))
        host_steps.append(run_host_step(store, "v812-v401", v401_cmd, 180.0))
        v401_manifest = load_json(root / "prep" / "v401" / "manifest.json")
        host_steps.append(run_host_step(store, "v812-mountsystem-ro", mountsystem_command(args), 120.0))
        host_steps.append(run_host_step(store, "v812-v490", v490_cmd, 300.0))
        v490_manifest = load_json(root / "prep" / "v490" / "manifest.json")
        prep = {
            "v401": {
                "ok": host_steps[-3]["ok"],
                "decision": v401_manifest.get("decision"),
                "pass": v401_manifest.get("pass"),
                "manifest": str(root / "prep" / "v401" / "manifest.json"),
            },
            "mountsystem": {
                "ok": host_steps[-2]["ok"],
                "rc": host_steps[-2]["rc"],
                "file": host_steps[-2]["file"],
            },
            "v490": {
                "ok": host_steps[-1]["ok"],
                "decision": v490_manifest.get("decision"),
                "pass": v490_manifest.get("pass"),
                "manifest": str(root / "prep" / "v490" / "manifest.json"),
            },
        }
        if prep["v401"]["pass"] and prep["v490"]["pass"]:
            host_steps.append(run_host_step(store, "v812-v735-arm", v735_command(args, root), 900.0))
            v735_data = load_json(root / "arm-v812-v735" / "manifest.json")
            v735_summary = summarize_v735(v735_data)
        else:
            v735_summary = {"pass": False, "decision": "not-run", "reason": "prep failed"}
    checks = build_checks(args.command, v811, prep, v735_summary)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v735_summary)
    helper = v735_summary.get("helper") if isinstance(v735_summary.get("helper"), dict) else {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v812",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v811_manifest": str(repo_path(args.v811_manifest)),
            "helper_sha256": args.helper_sha256,
            "helper_marker": args.helper_marker,
            "companion_runtime_sec": args.companion_runtime_sec,
        },
        "host_steps": host_steps,
        "prep": prep,
        "v811": {"decision": v811.get("decision"), "pass": v811.get("pass"), "path": v811.get("path")},
        "v735_arm": {
            "manifest": str(root / "arm-v812-v735" / "manifest.json"),
            "summary": v735_summary,
        },
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "firmware_mounts_executed": bool(v735_summary),
        "subsys_modem_open_attempted": bool(v735_summary),
        "subsys_modem_opened": bool(v735_summary.get("holder_opened")),
        "lower_companion_start_executed": bool(v735_summary.get("companion_executed")),
        "cnss_diag_start_executed": bool(int_value(helper.get("cnss_diag"))),
        "cnss_daemon_start_executed": bool(int_value(helper.get("cnss_daemon"))),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "esoc0_access_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "reboot_cleanup_executed": args.command == "run" and bool(v735_summary),
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    signal = manifest.get("v735_arm", {}).get("summary", {})
    signal_rows = [
        ["decision", str(signal.get("decision", ""))],
        ["mss", json.dumps([signal.get("mss_after_holder"), signal.get("mss_after_companion")])],
        ["mdm3", json.dumps([signal.get("mdm3_after_holder"), signal.get("mdm3_after_companion")])],
        ["markers", json.dumps(signal.get("markers", {}), sort_keys=True)],
        ["qrtr_readback", json.dumps(signal.get("qrtr_readback", {}), sort_keys=True)],
        ["helper", json.dumps(signal.get("helper", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(signal.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V812 MDM3/WLAN-PD/Service69 Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- subsys_modem_opened: `{manifest['subsys_modem_opened']}`",
        f"- lower_companion_start_executed: `{manifest['lower_companion_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("host")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"lower_companion_start_executed: {manifest['lower_companion_start_executed']}")
    print(f"cnss_diag_start_executed: {manifest['cnss_diag_start_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
