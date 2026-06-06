#!/usr/bin/env python3
"""V720 bounded same-window CNSS2 trigger observer orchestrator.

V720 reproduces the V712 provider-first CNSS2 edge window, immediately captures
the hardened V706 current-boot read-only surface after cleanup, then reconciles
both with V719. It does not start Wi-Fi HAL, scan/connect, use credentials,
run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v720-same-window-cnss2-observer")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
DEFAULT_COMPANION_RUNTIME_SEC = 30
APPROVAL_PHRASE = (
    "approve v720 same-window CNSS2 observer only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)
V706_APPROVAL = (
    "approve v666 cnss2 pd-notifier firing check and modem subsys state read; "
    "no Wi-Fi HAL start, no scan/connect, no DHCP, no external ping"
)
FORBIDDEN_ACTIONS = (
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate/sysfs WLAN driver-state writes",
    "esoc0 open/hold",
    "boot image or partition write",
)
ALLOWED_ACTIONS = (
    "V712 provider-first CNSS2 edge proof with V641/V401/V490 prep",
    "bounded companion/CNSS start-only below Wi-Fi HAL",
    "hardened V706 read-only post-cleanup capture",
    "host-only V719 reconciliation",
    "runner-owned reboot cleanup inherited from V712",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--arm-companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def run_host(command: list[str], timeout: float) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


def write_host_output(store: EvidenceStore, name: str, command: list[str], rc: int, output: str) -> str:
    rel = f"host/{name}.txt"
    body = "$ " + " ".join(command) + "\nrc=" + str(rc) + "\n" + output.rstrip() + "\n"
    store.write_text(rel, body)
    return rel


def run_script(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    rc, output = run_host(command, timeout)
    return {
        "rc": rc,
        "ok": rc == 0,
        "file": write_host_output(store, name, command, rc, output),
        "output_tail": output.splitlines()[-20:],
    }


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def script_exists(path: str) -> bool:
    return repo_path(Path(path)).exists()


def bridge_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def build_v712_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py",
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.helper,
        "--arm-companion-runtime-sec",
        str(max(1, min(30, args.arm_companion_runtime_sec))),
        "--apply",
        "--assume-yes",
        "run",
    ]


def build_v706_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py",
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--approval",
        V706_APPROVAL,
        "run",
    ]


def build_v719_command(service_dir: Path, current_dir: Path, out_dir: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py",
        "--out-dir",
        str(out_dir),
        "--service-source",
        str(service_dir),
        "--current-source",
        str(current_dir),
        "run",
    ]


def build_preflight(args: argparse.Namespace) -> dict[str, Any]:
    scripts = {
        "v712": "scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py",
        "v706": "scripts/revalidation/native_wifi_cnss2_pd_notifier_readonly_v706.py",
        "v719": "scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py",
    }
    return {
        "scripts": {name: script_exists(path) for name, path in scripts.items()},
        "bridge_port_open": bridge_port_open(args.host, args.port),
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": bool(args.apply),
        "assume_yes": bool(args.assume_yes),
        "arm_companion_runtime_sec": args.arm_companion_runtime_sec,
        "runtime_valid": 1 <= args.arm_companion_runtime_sec <= 30,
        "ready_for_run": all(script_exists(path) for path in scripts.values()) and 1 <= args.arm_companion_runtime_sec <= 30,
    }


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    service_dir = store.run_dir / "service-positive-v712"
    current_dir = store.run_dir / "current-readonly-v706"
    reconcile_dir = store.run_dir / "reconcile-v719"
    v712 = run_script(store, "v712-service-positive-live", build_v712_command(args, service_dir), 900.0)
    v712_manifest = load_json(service_dir / "manifest.json")
    if not v712_manifest:
        return {
            "v712": {**v712, "manifest": str(service_dir / "manifest.json")},
            "v706": {},
            "v719": {},
        }
    v706 = run_script(store, "v706-current-readonly-live", build_v706_command(args, current_dir), 180.0)
    v706_manifest = load_json(current_dir / "manifest.json")
    if not v706_manifest:
        return {
            "v712": {**v712, "manifest": str(service_dir / "manifest.json"), "decision": v712_manifest.get("decision"), "pass": v712_manifest.get("pass")},
            "v706": {**v706, "manifest": str(current_dir / "manifest.json")},
            "v719": {},
        }
    v719 = run_script(store, "v719-reconcile", build_v719_command(service_dir, current_dir, reconcile_dir), 120.0)
    v719_manifest = load_json(reconcile_dir / "manifest.json")
    return {
        "v712": {
            **v712,
            "manifest": str(service_dir / "manifest.json"),
            "decision": v712_manifest.get("decision"),
            "pass": v712_manifest.get("pass"),
            "reason": v712_manifest.get("reason"),
        },
        "v706": {
            **v706,
            "manifest": str(current_dir / "manifest.json"),
            "decision": v706_manifest.get("decision"),
            "pass": v706_manifest.get("pass"),
            "reason": v706_manifest.get("reason"),
        },
        "v719": {
            **v719,
            "manifest": str(reconcile_dir / "manifest.json"),
            "decision": v719_manifest.get("decision"),
            "pass": v719_manifest.get("pass"),
            "reason": v719_manifest.get("reason"),
            "next_step": v719_manifest.get("next_step"),
        },
    }


def decide(args: argparse.Namespace, preflight: dict[str, Any], live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v720-same-window-cnss2-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight, then approved V720 live observer when bridge access is available",
            False,
        )
    missing_scripts = [name for name, present in (preflight.get("scripts") or {}).items() if not present]
    if missing_scripts:
        return (
            "v720-same-window-cnss2-observer-preflight-blocked",
            False,
            "missing scripts: " + ",".join(missing_scripts),
            "restore required V712/V706/V719 scripts before live run",
            False,
        )
    if not preflight.get("runtime_valid"):
        return (
            "v720-same-window-cnss2-observer-preflight-blocked",
            False,
            f"arm companion runtime must be 1..30 seconds; got {preflight.get('arm_companion_runtime_sec')}",
            "rerun with --arm-companion-runtime-sec <= 30",
            False,
        )
    if args.command == "preflight":
        return (
            "v720-same-window-cnss2-observer-preflight-ready",
            True,
            f"host preflight ready; bridge_port_open={preflight.get('bridge_port_open')}",
            "start a serial bridge with device access, then run approved V720",
            False,
        )
    if not approved(args):
        return (
            "v720-same-window-cnss2-observer-approval-required",
            True,
            "exact V720 approval phrase plus --apply --assume-yes required; no live command executed",
            "rerun with exact V720 approval",
            False,
        )
    if not live:
        return "v720-same-window-cnss2-observer-live-missing", False, "live result missing", "inspect runner failure", True
    v712 = live.get("v712") or {}
    v706 = live.get("v706") or {}
    v719 = live.get("v719") or {}
    if not v712.get("manifest") or v712.get("decision") is None:
        return "v720-v712-live-missing", False, f"v712={v712}", "inspect V712 transcript and bridge/device access", True
    if v712.get("pass") is not True:
        return "v720-v712-live-blocked", False, f"v712_decision={v712.get('decision')}", "resolve service-positive lower path before V720 reconciliation", True
    if not v706.get("manifest") or v706.get("decision") is None:
        return "v720-v706-readonly-missing", False, f"v706={v706}", "inspect hardened V706 transcript", True
    if v706.get("pass") is not True:
        return "v720-v706-readonly-blocked", False, f"v706_decision={v706.get('decision')}", "repair current read-only capture before V719 reconciliation", True
    if not v719.get("manifest") or v719.get("decision") is None:
        return "v720-v719-reconcile-missing", False, f"v719={v719}", "inspect V719 transcript", True
    if v719.get("decision") == "v719-wlfw-or-wlan0-progressed":
        return (
            "v720-wlfw-or-wlan0-progressed",
            True,
            "same-window run progressed WLFW/BDF/fw_ready/wlan0",
            "move to wlan0 readiness before scan/connect",
            True,
        )
    if v719.get("decision") in {
        "v719-service-positive-cnss2-trigger-gap-classified",
        "v719-qrtr-ns-present-servreg-cnss2-trigger-gap-classified",
    }:
        return (
            "v720-same-window-cnss2-trigger-gap-confirmed",
            True,
            "same-window service-positive run still lacks CNSS2 pd_notifier/QCA power/MHI/WLFW/wlan0 progression",
            "instrument CNSS2 kernel event source or compare Android same-window kernel messages before HAL/connect",
            True,
        )
    return (
        "v720-same-window-cnss2-observer-review",
        True,
        f"v719_decision={v719.get('decision')}",
        "inspect V719 summary and choose next bounded gate",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    preflight = manifest.get("preflight") or {}
    live = manifest.get("live") or {}
    check_rows = [
        ["scripts", json.dumps(preflight.get("scripts", {}), sort_keys=True)],
        ["bridge_port_open", str(preflight.get("bridge_port_open"))],
        ["approval_phrase_matched", str(preflight.get("approval_phrase_matched"))],
        ["apply", str(preflight.get("apply"))],
        ["assume_yes", str(preflight.get("assume_yes"))],
        ["arm_companion_runtime_sec", str(preflight.get("arm_companion_runtime_sec"))],
    ]
    live_rows: list[list[str]] = []
    for key in ("v712", "v706", "v719"):
        item = live.get(key) or {}
        live_rows.append([key, "decision", str(item.get("decision", ""))])
        live_rows.append([key, "pass", str(item.get("pass", ""))])
        live_rows.append([key, "manifest", str(item.get("manifest", ""))])
    return "\n".join([
        "# V720 Same-window CNSS2 Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Preflight",
        "",
        markdown_table(["item", "value"], check_rows),
        "",
        "## Live Arms",
        "",
        markdown_table(["arm", "key", "value"], live_rows) if live_rows else "- not executed",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
        "## Allowed Actions",
        "",
        "\n".join(f"- {item}" for item in manifest["allowed_actions"]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    preflight = build_preflight(args)
    live = run_live(args, store) if args.command == "run" and approved(args) and preflight.get("ready_for_run") else None
    decision, pass_ok, reason, next_step, live_executed = decide(args, preflight, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v720",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "preflight": preflight,
        "live": live or {},
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": bool(args.apply),
        "assume_yes": bool(args.assume_yes),
        "allowed_actions": ALLOWED_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": live_executed,
        "device_mutations": live_executed,
        "daemon_start_executed": live_executed,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("host")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
