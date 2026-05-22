#!/usr/bin/env python3
"""V636 CDSP-online plus V598-class modem-holder readback composite proof.

This runner prepares a bounded live gate that first uses the V635 firmware
mount + CDSP-only proof, then replays the V598/V625 modem-holder companion and
WLFW QRTR readback path in the same boot. It does not start service-manager,
Wi-Fi HAL, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, route
changes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_firmware_cdsp_only_proof_v635 as v635
import native_wifi_modem_holder_wlfw_readback_v598 as v598
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


base = v598.base

DEFAULT_OUT_DIR = Path("tmp/wifi/v636-cdsp-v598-composite")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v636-v490-current-run/manifest.json")
APPROVAL_PHRASE = (
    "approve v636 cdsp plus v598 composite proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"wlfw_start|wlfw_send", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put: esoc0 count:0|pm_qos_add_request", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=base.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=base.DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--v525-manifest", type=Path, default=base.DEFAULT_V525_MANIFEST)
    parser.add_argument("--holder-sec", type=int, default=90)
    parser.add_argument("--companion-runtime-sec", type=int, default=30)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=35.0)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=2.0)
    parser.add_argument("--cdsp-timeout-sec", type=int, default=v635.DEFAULT_CDSP_TIMEOUT_SEC)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="preflight")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def count_markers(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in MARKERS}


def capture_cdsp_state(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       name: str) -> dict[str, Any]:
    command = [
        "run",
        args.busybox,
        "sh",
        "-c",
        (
            f"BB={args.busybox}; "
            "for d in /sys/bus/msm_subsys/devices/*; do "
            "[ -e \"$d/name\" ] && $BB grep -q '^cdsp$' \"$d/name\" && "
            "{ echo $d; $BB cat \"$d/name\"; $BB cat \"$d/state\"; $BB cat \"$d/firmware_name\"; }; "
            "done; true"
        ),
    ]
    return base.run_step(args, store, steps, name, command, 15.0)


def cdsp_online(text: str) -> bool:
    return bool(re.search(r"(^|\n)ONLINE(\n|$)", text))


def add_cdsp_initial_check(checks: list[base.Check], cdsp_state_text: str) -> None:
    already_online = cdsp_online(cdsp_state_text)
    base.add_check(
        checks,
        "cdsp-initial-not-online",
        "pass" if not already_online else "blocked",
        "blocker",
        f"initial_cdsp_online={already_online}",
        [line for line in cdsp_state_text.splitlines()[:8]],
        "reboot to fresh native baseline before V636 run",
    )


def build_preflight(args: argparse.Namespace,
                    store: EvidenceStore,
                    steps: list[dict[str, Any]]) -> tuple[dict[str, Any], list[base.Check]]:
    v490 = load_manifest(args.v490_manifest)
    v525 = load_manifest(args.v525_manifest)
    mount_preflight = base.capture_preflight(args, store, steps)
    cdsp = capture_cdsp_state(args, store, steps, "initial-cdsp-state")
    checks = base.build_checks(args, steps, mount_preflight, v490, v525)
    add_cdsp_initial_check(checks, str(cdsp.get("payload") or ""))
    return mount_preflight, checks


def blockers(checks: list[base.Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    cdsp_proof = v635.run_cdsp_proof(args, store, steps, mount_preflight)
    cdsp_counts = cdsp_proof.get("marker_delta") or {}
    if not cdsp_proof.get("cdsp_returned") or int(cdsp_counts.get("kernel_warning", 0) or 0) > 0:
        return {
            "cdsp_proof": cdsp_proof,
            "v598_live": {},
            "v598_executed": False,
            "post_cdsp_markers": {},
        }
    capture_cdsp_state(args, store, steps, "post-cdsp-state-before-v598")
    v598_live = base.run_live(args, store, steps, mount_preflight)
    post_cdsp_counts = count_markers(str(v598_live.get("dmesg_delta") or ""))
    return {
        "cdsp_proof": cdsp_proof,
        "v598_live": v598_live,
        "v598_executed": True,
        "post_cdsp_markers": post_cdsp_counts,
    }


def decide(args: argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v636-cdsp-v598-composite-plan-ready", True, "plan-only; no device command executed", "run fresh V490 then V636 preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v636-cdsp-v598-blocked", False, "blocked by " + ", ".join(blocked), "clear blockers before live proof", False
    if args.command == "preflight":
        return "v636-cdsp-v598-preflight-ready", True, "fresh CDSP/V598 prerequisites are present", "run V636 composite proof", False
    if not approved(args):
        return "v636-cdsp-v598-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V636 approval", False
    if not live:
        return "v636-cdsp-v598-missing-live", False, "missing live result", "inspect runner failure", True
    cdsp_proof = live.get("cdsp_proof") or {}
    if not cdsp_proof.get("cdsp_returned"):
        return "v636-cdsp-v598-cdsp-proof-regressed", False, "CDSP proof did not return before V598 replay", "stop and inspect CDSP evidence", True
    if not live.get("v598_executed"):
        return "v636-cdsp-v598-v598-skipped", False, "V598 replay skipped after CDSP proof", "inspect CDSP proof and guardrails", True
    counts = live.get("post_cdsp_markers") or {}
    if int(counts.get("kernel_warning", 0) or 0) > 0:
        return "v636-cdsp-v598-kernel-warning", False, f"kernel_warning={counts.get('kernel_warning')}", "do not repeat until warning is explained", True
    if int(counts.get("wlan0", 0) or 0) > 0 or int(counts.get("wlan_fw_ready", 0) or 0) > 0:
        return "v636-cdsp-v598-wlan-advanced", True, f"post_cdsp_markers={counts}", "plan bounded link/scan gate; still protect credentials", True
    if int(counts.get("service_notifier_74", 0) or 0) > 0 or int(counts.get("wlan_pd", 0) or 0) > 0:
        return "v636-cdsp-v598-service74-advanced", True, f"post_cdsp_markers={counts}", "plan bounded WLFW/CNSS readiness gate", True
    if int(counts.get("service_notifier_180", 0) or 0) > 0:
        return "v636-cdsp-v598-service180-only", True, f"post_cdsp_markers={counts}", "classify why CDSP-online still does not publish service 74", True
    return "v636-cdsp-v598-no-lower-publication", True, f"post_cdsp_markers={counts}", "compare V636 against V625/V627 for regression", True


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live") or {}
    cdsp_proof = live.get("cdsp_proof") or {}
    return "\n".join([
        "# Native Init V636 CDSP + V598 Composite Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- cdsp_write_executed: `{manifest['cdsp_write_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Live",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["cdsp_marker_delta", cdsp_proof.get("marker_delta", {})],
                ["cdsp_returned", cdsp_proof.get("cdsp_returned", "")],
                ["v598_executed", live.get("v598_executed", "")],
                ["post_cdsp_markers", live.get("post_cdsp_markers", {})],
            ],
        ) if live else "- none",
        "",
        "## Guardrails",
        "",
        "- no ADSP/SLPI/boot_wlan/qcwlanstate/shutdown_wlan write",
        "- no service-manager or Wi-Fi HAL start",
        "- no scan/connect/link-up, credentials, DHCP, routes, or external ping",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    base.APPROVAL_PHRASE = APPROVAL_PHRASE
    steps: list[dict[str, Any]] = []
    mount_preflight: dict[str, Any] = {}
    checks: list[base.Check] = []
    live: dict[str, Any] | None = None
    if args.command != "plan":
        mount_preflight, checks = build_preflight(args, store, steps)
    else:
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V636 preflight")
    if args.command == "run" and approved(args) and not blockers(checks):
        live = run_live(args, store, steps, mount_preflight)
    decision, pass_ok, reason, next_step, live_executed = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "mount_preflight": mount_preflight,
        "live": live or {},
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": live_executed,
        "mount_unmount_executed": live_executed,
        "sysfs_writes_executed": live_executed,
        "cdsp_write_executed": live_executed,
        "daemon_start_executed": bool(live and live.get("v598_executed")),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"cdsp_write_executed: {manifest['cdsp_write_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
