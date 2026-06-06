#!/usr/bin/env python3
"""V1217: fake eSoC name readback-only proof.

This gate proves whether helper v252's private namespace bind of
``esoc_name=SDXPRAIRIE`` is visible through the paths used by
``libmdmdetect.so``.  It intentionally exits before daemon start: no
service-manager, CNSS, HAL, scan/connect, DHCP, route, credential, or external
ping activity is permitted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1217-fake-esoc-name-readback")
LATEST_POINTER = Path("tmp/wifi/latest-v1217-fake-esoc-name-readback.txt")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER_SHA256 = "4511f11399d4f86f5265d79eb57b2db04ae5ad869ab543565f2c657b97af8587"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v252"
APPROVAL_PHRASE = (
    "approve v1217 fake esoc name readback only; "
    "no daemon start and no Wi-Fi bring-up"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def capture_native(args: argparse.Namespace,
                   store: EvidenceStore,
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if capture.text else text
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, stripped)
    data = capture_to_manifest(capture)
    data["file"] = rel
    return data


def parse_prefixed_lines(text: str, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(prefix) or "=" not in line:
            continue
        key, value = line[len(prefix):].split("=", 1)
        result[key] = value
    return result


def read_step_text(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = step.get("file")
    if not rel:
        return ""
    try:
        return store.path(str(rel)).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def readback_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.remote_helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "wifi-companion-pm-service-trigger-observer",
        "--target-profile",
        "cnss-daemon",
        "--capture-mode",
        "none",
        "--timeout-sec",
        "3",
        "--allow-pm-service-trigger-observer",
        "--pm-observer-fake-esoc-name-sdxprairie",
        "--pm-observer-fake-esoc-name-readback-only",
    ]


def preflight_commands(args: argparse.Namespace) -> list[tuple[str, list[str], float]]:
    return [
        ("selftest", ["selftest"], 10.0),
        ("netservice-status", ["netservice", "status"], 10.0),
        ("sha-helper", ["run", args.toybox, "sha256sum", args.remote_helper], 15.0),
        ("helper-usage", ["run", args.remote_helper], 15.0),
    ]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for name, command, timeout in preflight_commands(args):
        steps.append(capture_native(args, store, name, command, timeout=timeout))
    if args.command == "run":
        steps.append(capture_native(args, store, "fake-esoc-name-readback", readback_command(args), timeout=args.timeout))

    readback_text = ""
    if args.command == "run":
        readback_text = read_step_text(store, steps[-1])

    fake_bind = parse_prefixed_lines(readback_text, "fake_esoc_name.")
    readback = parse_prefixed_lines(readback_text, "fake_esoc_readback.")
    control = parse_prefixed_lines(readback_text, "fake_esoc_name_readback_only.")
    manifest: dict[str, Any] = {
        "cycle": "v1217",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "plan": {
            "goal": "prove fake SDXPRAIRIE esoc_name read path inside private namespace",
            "helper": DEFAULT_HELPER_MARKER,
            "remote_helper": args.remote_helper,
            "daemon_start_allowed": False,
            "wifi_bringup_allowed": False,
        },
        "steps": steps,
        "fake_esoc_name": fake_bind,
        "fake_esoc_readback": readback,
        "fake_esoc_name_readback_only": control,
    }
    decision, passed, reason, next_step = decide(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def helper_sha_ok(manifest: dict[str, Any]) -> bool:
    for step in manifest.get("steps", []):
        if step.get("name") == "sha-helper" and DEFAULT_HELPER_SHA256 in str(step.get("text", "")):
            return True
    return False


def helper_marker_ok(manifest: dict[str, Any]) -> bool:
    for step in manifest.get("steps", []):
        if step.get("name") == "helper-usage" and DEFAULT_HELPER_MARKER in str(step.get("text", "")):
            return True
    return False


def safety_control_ok(control: dict[str, str]) -> bool:
    required_zero = [
        "daemon_start_executed",
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_linkup",
        "credentials",
        "dhcp_routing",
        "external_ping",
    ]
    return bool(control) and all(control.get(key) == "0" for key in required_zero)


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not helper_sha_ok(manifest) or not helper_marker_ok(manifest):
        return (
            "v1217-helper-version-blocked",
            False,
            "remote helper is not the expected v252 binary",
            "deploy V1217 helper v252 before running readback proof",
        )
    if manifest.get("command") == "preflight":
        return (
            "v1217-preflight-pass",
            True,
            "remote helper v252 preflight checks passed; live readback not executed",
            "run V1217 readback-only proof with the exact approval phrase",
        )
    if not manifest.get("fake_esoc_readback"):
        return (
            "v1217-readback-missing",
            False,
            "readback command did not emit fake_esoc_readback markers",
            "inspect native/fake-esoc-name-readback.txt and helper argument validation",
        )
    control = manifest.get("fake_esoc_name_readback_only") or {}
    if not safety_control_ok(control):
        return (
            "v1217-safety-control-missing",
            False,
            f"readback-only safety controls missing or nonzero: {control}",
            "fix helper readback-only branch before any live PM/CNSS retry",
        )
    readback = manifest["fake_esoc_readback"]
    platform = readback.get("platform_mdm3_esoc0_esoc_name.value")
    bus = readback.get("bus_esoc_devices_esoc0_esoc_name.value")
    class_rc = readback.get("sys_class_esoc_dev.opendir_rc")
    class_count_text = readback.get("sys_class_esoc_dev.count", "-1")
    try:
        class_count = int(class_count_text)
    except ValueError:
        class_count = -1

    if platform == "SDXPRAIRIE" and bus == "SDXPRAIRIE" and class_rc == "0" and class_count > 0:
        return (
            "v1217-readback-path-positive",
            True,
            "platform path, bus alias, and esoc-dev class are visible before daemon start",
            "V1218: rerun bounded PM/CNSS observer with helper v252 and require SDXPRAIRIE registration",
        )
    if platform == "SDXPRAIRIE" and bus != "SDXPRAIRIE":
        return (
            "v1217-bus-alias-readback-miss",
            False,
            f"platform path reads SDXPRAIRIE but bus alias reads {bus!r}",
            "bind the path actually followed by /sys/bus/esoc/devices/esoc0 before CNSS",
        )
    if platform != "SDXPRAIRIE":
        return (
            "v1217-platform-bind-readback-miss",
            False,
            f"platform path reads {platform!r}, expected SDXPRAIRIE",
            "repair fake esoc_name bind source/target before another PM/CNSS live gate",
        )
    return (
        "v1217-class-surface-incomplete",
        False,
        f"platform/bus readback ok but esoc-dev class rc={class_rc!r} count={class_count}",
        "repair /sys/class/esoc-dev bind before rerunning PM/CNSS observer",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    readback = manifest.get("fake_esoc_readback") or {}
    control = manifest.get("fake_esoc_name_readback_only") or {}
    return "\n".join(
        [
            "# V1217 Fake eSoC Name Readback",
            "",
            f"- decision: `{manifest.get('decision')}`",
            f"- pass: `{manifest.get('pass')}`",
            f"- reason: {manifest.get('reason')}",
            f"- next: {manifest.get('next_step')}",
            "",
            "## Key Readbacks",
            "",
            f"- platform esoc_name: `{readback.get('platform_mdm3_esoc0_esoc_name.value')}`",
            f"- bus alias esoc_name: `{readback.get('bus_esoc_devices_esoc0_esoc_name.value')}`",
            f"- esoc-dev opendir rc: `{readback.get('sys_class_esoc_dev.opendir_rc')}`",
            f"- esoc-dev count: `{readback.get('sys_class_esoc_dev.count')}`",
            "",
            "## Safety Controls",
            "",
            f"- daemon start: `{control.get('daemon_start_executed')}`",
            f"- service manager start: `{control.get('service_manager_start_executed')}`",
            f"- Wi-Fi HAL start: `{control.get('wifi_hal_start_executed')}`",
            f"- scan/connect/link-up: `{control.get('scan_connect_linkup')}`",
            f"- credentials: `{control.get('credentials')}`",
            f"- DHCP/routes: `{control.get('dhcp_routing')}`",
            f"- external ping: `{control.get('external_ping')}`",
            "",
        ]
    )


def print_plan() -> None:
    print("V1217 fake esoc_name readback-only proof")
    print(f"approval phrase: {APPROVAL_PHRASE}")
    print("run starts no daemon and performs no Wi-Fi bring-up.")


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        print_plan()
        return 0
    if args.command == "run" and not approved(args):
        print("refusing live readback without exact approval phrase", flush=True)
        print(f"required: {APPROVAL_PHRASE}", flush=True)
        return 2

    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    try:
        write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    except OSError:
        pass

    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(json.dumps({
        "platform": (manifest.get("fake_esoc_readback") or {}).get("platform_mdm3_esoc0_esoc_name.value"),
        "bus": (manifest.get("fake_esoc_readback") or {}).get("bus_esoc_devices_esoc0_esoc_name.value"),
        "class_count": (manifest.get("fake_esoc_readback") or {}).get("sys_class_esoc_dev.count"),
    }, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
