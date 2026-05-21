#!/usr/bin/env python3
"""V488 native SELinux policy assembly inventory.

This runner uses `a90_android_execns_probe v46` in `sepolicy-inventory` mode to
inspect Android split-policy inputs inside the helper's private namespace. The
helper mounts system/vendor read-only and emits file presence, size/hash, and
precompiled policy hash compatibility facts.

No service-manager, hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, DHCP,
routing, credential read, or external ping is executed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from a90_kernel_tools import collect_host_metadata, markdown_table  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v488-native-selinux-policy-inventory")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_SHA256 = "81a205579fada4d286eb4cac751a378c09a46757eb39aed593176cbead12ef24"
APPROVAL_PHRASE = (
    "approve v488 native SELinux policy inventory only; "
    "no daemon start and no Wi-Fi bring-up"
)


@dataclass
class Step:
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str = ""


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def run_capture(args: argparse.Namespace, store: EvidenceStore, name: str,
                command: list[str], timeout: float | None = None) -> Step:
    started = time.monotonic()
    text = ""
    error = ""
    rc: int | None = None
    status = "missing"
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            timeout if timeout is not None else args.timeout,
            command,
            retry_unsafe=False,
        )
        text = result.text
        rc = result.rc
        status = result.status
        ok = result.rc == 0 and result.status == "ok"
    except Exception as exc:  # noqa: BLE001 - preserve transport evidence
        ok = False
        error = str(exc)
        text = error + "\n"
    duration = time.monotonic() - started
    path = store.write_text(f"commands/{name}.txt", text)
    return Step(name, command, ok, rc, status, duration, str(path), error)


def read_step(step: Step | None) -> str:
    if step is None:
        return ""
    return Path(step.file).read_text(encoding="utf-8", errors="replace")


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip().replace("\x00", "")
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            keys[key] = value
    return keys


def helper_sha_matches(expected_sha256: str, helper_sha_text: str, helper: str) -> bool:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        return False
    for line in helper_sha_text.splitlines():
        if helper not in line:
            continue
        fields = line.strip().split()
        if fields and fields[0].lower() == expected_sha256.lower():
            return True
    return False


def add_check(checks: list[Check], name: str, status: str, severity: str,
              detail: str, evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "sepolicy-inventory",
        "--target-profile",
        "system-toybox",
        "--timeout-sec",
        "5",
    ]


def preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Step]:
    return {
        "version": run_capture(args, store, "version", ["version"], args.timeout),
        "status": run_capture(args, store, "status", ["status"], args.timeout),
        "ps": run_capture(args, store, "ps", ["run", args.toybox, "ps", "-A"], args.timeout),
        "netdev": run_capture(args, store, "proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], args.timeout),
        "mounts": run_capture(args, store, "proc-mounts", ["run", args.toybox, "cat", "/proc/mounts"], args.timeout),
        "selinux-current": run_capture(args, store, "selinux-current", ["run", args.toybox, "cat", "/proc/self/attr/current"], args.timeout),
        "selinux-enforce": run_capture(args, store, "selinux-enforce", ["run", args.toybox, "cat", "/sys/fs/selinux/enforce"], args.timeout),
        "system-root": run_capture(args, store, "system-root", ["run", args.toybox, "ls", "-ld", "/mnt/system/system", "/mnt/system/system/bin"], args.timeout),
        "helper-sha": run_capture(args, store, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], args.timeout),
        "helper-usage": run_capture(args, store, "helper-usage", ["run", args.helper], args.timeout),
    }


def summarize_inventory(step: Step | None) -> dict[str, Any]:
    text = read_step(step)
    keys = parse_keys(text)
    return {
        "file": step.file if step else "",
        "ok": bool(step and step.ok),
        "keys": keys,
        "result": keys.get("sepolicy_inventory.result", ""),
        "split_policy_device": keys.get("sepolicy_inventory.split_policy_device", ""),
        "vendor_precompiled_present": keys.get("sepolicy_inventory.vendor_precompiled_present", ""),
        "precompiled_usable": keys.get("sepolicy_inventory.precompiled_usable", ""),
        "precompiled_hash_required_count": keys.get("sepolicy_inventory.precompiled_hash_required_count", ""),
        "precompiled_hash_match_count": keys.get("sepolicy_inventory.precompiled_hash_match_count", ""),
        "secilc_present": keys.get("sepolicy_inventory.secilc_present", ""),
        "vendor_policy_cil_present": keys.get("sepolicy_inventory.vendor_policy_cil_present", ""),
        "vendor_plat_pub_versioned_present": keys.get("sepolicy_inventory.vendor_plat_pub_versioned_present", ""),
        "compile_inputs_present": keys.get("sepolicy_inventory.compile_inputs_present", ""),
        "plat_hash_match": keys.get("sepolicy.hash.plat.match", ""),
        "system_ext_hash_match": keys.get("sepolicy.hash.system_ext.match", ""),
        "product_hash_match": keys.get("sepolicy.hash.product.match", ""),
    }


def build_checks(args: argparse.Namespace,
                 steps: dict[str, Step],
                 inventory: dict[str, Any] | None = None) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed")
        return checks

    version = read_step(steps.get("version"))
    status = read_step(steps.get("status"))
    ps = read_step(steps.get("ps"))
    netdev = read_step(steps.get("netdev"))
    mounts = read_step(steps.get("mounts"))
    system_root = read_step(steps.get("system-root"))
    helper_sha = read_step(steps.get("helper-sha"))
    helper_usage = read_step(steps.get("helper-usage"))
    process_hits = [
        line.strip()
        for line in ps.splitlines()
        if any(token in line for token in (
            "servicemanager",
            "hwservicemanager",
            "vendor.samsung.hardware.wifi",
            "android.hardware.wifi",
            "cnss-daemon",
            "wpa_supplicant",
            "wificond",
        ))
    ]
    wifi_links = [line.strip() for line in netdev.splitlines() if re.search(r"\b(wlan|wifi|p2p)", line)]

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3])
    add_check(checks, "native-clean", "pass" if "fail=0" in status else "blocked", "blocker",
              "status/selftest fail=0 expected", [line for line in status.splitlines() if "selftest:" in line][:2],
              "fix native runtime before SELinux inventory")
    sha_match = helper_sha_matches(args.helper_sha256, helper_sha, args.helper)
    helper_ready = (
        sha_match
        and "a90_android_execns_probe v46" in helper_usage
        and "sepolicy-inventory" in helper_usage
    )
    add_check(checks, "helper-v46", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={sha_match} marker={'a90_android_execns_probe v46' in helper_usage} mode={'sepolicy-inventory' in helper_usage}",
              [line for line in helper_sha.splitlines() if args.helper in line][:2],
              "deploy helper v46 before V488 run")
    system_root_ready = "/mnt/system/system" in system_root and "/mnt/system/system/bin" in system_root
    add_check(checks, "system-root-mounted", "pass" if system_root_ready else "blocked", "blocker",
              "Android system root must be mounted before private namespace policy probing",
              [line for line in system_root.splitlines() if "/mnt/system/system" in line][:4],
              "mount system read-only before SELinux policy probing")
    add_check(checks, "selinuxfs-mounted", "pass" if "/sys/fs/selinux" in mounts and " selinuxfs " in mounts else "blocked", "blocker",
              "global SELinuxfs must be mounted for inventory context", [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3],
              "mount SELinuxfs before policy inventory")
    add_check(checks, "process-surface-clean", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "do not run inventory over existing manager/HAL/CNSS process")
    add_check(checks, "wifi-link-clean", "pass" if not wifi_links else "blocked", "blocker",
              f"wifi_link_count={len(wifi_links)}", wifi_links[:8],
              "do not run inventory while Wi-Fi link is active")
    add_check(checks, "approval-gate", "pass" if approved(args) else "needs-operator", "approval",
              f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
              [APPROVAL_PHRASE], "exact approval required before namespace inventory run")

    if inventory is not None:
        keys = inventory["keys"]
        add_check(checks, "inventory-result", "pass" if inventory["result"] == "split-policy-inventory-pass" else "gap", "finding",
                  f"result={inventory['result']}", [inventory["file"]],
                  "inspect policy input presence")
        add_check(checks, "precompiled-policy", "pass" if inventory["precompiled_usable"] == "1" else "gap", "finding",
                  f"present={inventory['vendor_precompiled_present']} usable={inventory['precompiled_usable']} hashes={inventory['precompiled_hash_match_count']}/{inventory['precompiled_hash_required_count']}",
                  [f"plat={inventory['plat_hash_match']}", f"system_ext={inventory['system_ext_hash_match']}", f"product={inventory['product_hash_match']}"],
                  "if unusable, native policy setup needs compile path rather than precompiled load")
        add_check(checks, "compile-inputs", "pass" if inventory["compile_inputs_present"] == "1" else "gap", "finding",
                  f"secilc={inventory['secilc_present']} vendor_policy={inventory['vendor_policy_cil_present']} plat_pub={inventory['vendor_plat_pub_versioned_present']}",
                  [
                      keys.get("sepolicy.path.system_secilc.path", "/system/bin/secilc"),
                      keys.get("sepolicy.path.vendor_policy_cil.path", "/vendor/etc/selinux/vendor_sepolicy.cil"),
                      keys.get("sepolicy.path.vendor_plat_pub_versioned.path", "/vendor/etc/selinux/plat_pub_versioned.cil"),
                  ],
                  "missing compile inputs block native mini LoadSelinuxPolicyAndroid")
    return checks


def blockers(checks: list[Check], ignore_approval: bool = False) -> list[str]:
    blocked: list[str] = []
    for check in checks:
        if check.severity == "blocker" and check.status != "pass":
            blocked.append(check.name)
        if check.severity == "approval" and check.status != "pass" and not ignore_approval:
            blocked.append(check.name)
    return blocked


def decide(args: argparse.Namespace,
           checks: list[Check],
           inventory: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v488-selinux-policy-inventory-plan-ready", True, "plan-only; no device command executed", "deploy v46 and run preflight"
    pre_run_blockers = blockers(checks, ignore_approval=args.command == "preflight" or (args.command == "run" and approved(args)))
    if args.command == "preflight":
        if pre_run_blockers:
            return "v488-selinux-policy-inventory-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before V488 run"
        return "v488-selinux-policy-inventory-preflight-ready", True, "preflight passed; run still needs exact approval", "run approved read-only namespace inventory"
    if not approved(args):
        return "v488-selinux-policy-inventory-approval-required", False, "missing exact approval phrase or apply flags", "rerun with exact V488 approval"
    if pre_run_blockers:
        return "v488-selinux-policy-inventory-blocked", False, "blocked before run by " + ", ".join(pre_run_blockers), "resolve blockers before retry"
    if inventory is None or not inventory.get("ok"):
        return "v488-selinux-policy-inventory-run-failed", False, "inventory helper did not complete", "inspect helper transcript"
    if inventory["precompiled_usable"] == "1":
        return "v488-selinux-policy-precompiled-load-candidate", True, "precompiled vendor policy hashes match mounted system policy inputs", "plan a bounded policy-load proof before HAL registration"
    if inventory["compile_inputs_present"] == "1":
        return "v488-selinux-policy-compile-candidate", True, "precompiled policy is not directly usable but split-policy compile inputs are present", "plan bounded secilc/policy-load proof before HAL registration"
    return "v488-selinux-policy-input-gap", True, "policy inventory completed but key load/compile inputs are missing", "resolve policy input gaps before retrying SELinux handoff"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[check["name"], check["status"], check["severity"], check["detail"]] for check in manifest["checks"]]
    inventory = manifest.get("inventory") or {}
    rows = [
        ["split_policy_device", inventory.get("split_policy_device", "")],
        ["vendor_precompiled_present", inventory.get("vendor_precompiled_present", "")],
        ["precompiled_usable", inventory.get("precompiled_usable", "")],
        ["precompiled_hashes", f"{inventory.get('precompiled_hash_match_count', '')}/{inventory.get('precompiled_hash_required_count', '')}"],
        ["secilc_present", inventory.get("secilc_present", "")],
        ["vendor_policy_cil_present", inventory.get("vendor_policy_cil_present", "")],
        ["vendor_plat_pub_versioned_present", inventory.get("vendor_plat_pub_versioned_present", "")],
        ["compile_inputs_present", inventory.get("compile_inputs_present", "")],
    ]
    return "\n".join([
        "# V488 Native SELinux Policy Inventory",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Inventory",
        "",
        markdown_table(["item", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], checks),
        "",
        "## Safety",
        "",
        "- Uses helper private namespace with read-only system/vendor mounts.",
        "- No daemon/HAL/CNSS process is started.",
        "- No Wi-Fi scan/connect/link-up or external ping is attempted.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: dict[str, Step] = {}
    inventory: dict[str, Any] | None = None
    if args.command != "plan":
        steps = preflight(args, store)
    checks = build_checks(args, steps)
    if args.command == "run" and approved(args) and not blockers(checks, ignore_approval=True):
        inventory_step = run_capture(args, store, "sepolicy-inventory", helper_command(args), timeout=args.timeout + 20.0)
        inventory = summarize_inventory(inventory_step)
        checks = build_checks(args, steps, inventory)
    decision, pass_ok, reason, next_step = decide(args, checks, inventory)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "plan": {
            "helper": args.helper,
            "helper_version": "a90_android_execns_probe v46",
            "helper_sha256": args.helper_sha256,
            "helper_mode": "sepolicy-inventory",
            "system_root": "/mnt/system/system",
            "vendor_block": "/dev/block/sda29",
            "vendor_fstype": "ext4",
        },
        "steps": {name: asdict(step) for name, step in steps.items()},
        "inventory": inventory,
        "checks": [asdict(check) for check in checks],
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "run" and approved(args),
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_text("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {args.out_dir.resolve()}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
