#!/usr/bin/env python3
"""V1078 bounded active PM-service uprobe/BPF proof."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1078-pm-service-uprobe-active-live")
DEFAULT_V1077_MANIFEST = Path("tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/manifest.json")
DEFAULT_UPROBE_HELPER = "/cache/bin/a90_pm_service_uprobe_counter"
DEFAULT_UPROBE_HELPER_SHA256 = "05a8b9786fdfe95de94ada2883e0ee9326df69cf8548018b05d65aef3b384d9d"
DEFAULT_UPROBE_MARKER = "a90_pm_service_uprobe_counter v1076"
DEFAULT_EXECNS_HELPER_SHA256 = "61b8ac54460f05e1d3a6fc6b68d8873c04537c171054921b4266be1ef6a0fb59"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v196"
DEFAULT_VENDOR_BLOCK = "/dev/block/sda29"
DEFAULT_VENDOR_MOUNT = "/mnt/vendor"
DEFAULT_PM_BINARY = "/mnt/vendor/bin/pm-service"
DEFAULT_TRACEFS_ROOT = "/sys/kernel/tracing"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1078"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1078/pm-observer.sh"
TRACEFS_TARGET = "/sys/kernel/tracing"
LATEST_POINTER = Path("tmp/wifi/latest-v1078-pm-service-uprobe-active-live.txt")

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
EVENT_COUNT_RE = re.compile(r"^event\.([A-Za-z0-9_]+)\.count=(\d+)$", re.MULTILINE)
UPROBE_RESULT_RE = re.compile(r"^result=(uprobe-count-[A-Za-z0-9_-]+)$", re.MULTILINE)

EVENT_SPECS = (
    "elf_entry:0x6000",
    "libc_init_main_candidate:0x7650",
    "android_log:0x9e60",
    "binder_driver:0xa0a0",
    "mdmdetect_system_info:0x9f40",
    "qmi_csi_register:0x9fb0",
    "property_set:0x9ec0",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracefs_mounted(text: str) -> bool:
    return re.search(r"\s/sys/kernel/tracing\s+tracefs\s", text) is not None


def mount_present(text: str, target: str) -> bool:
    return re.search(rf"\s{re.escape(target)}\s+", text) is not None


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return [
        "run",
        args.busybox,
        "sh",
        "-c",
        script.replace("$BB", args.busybox).replace("$TB", args.toybox),
    ]


def step_payload(store: EvidenceStore, step: dict[str, Any]) -> str:
    file_name = step.get("file")
    if not file_name:
        return ""
    path = store.run_dir / str(file_name)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def pm_observer_child_command(args: argparse.Namespace) -> list[str]:
    child = base.helper_command(args)
    if len(child) >= 3 and child[0] == args.toybox and child[1] == "timeout":
        return child[3:]
    return child


def helper_command(args: argparse.Namespace) -> list[str]:
    command = [
        args.uprobe_helper,
        "--allow-tracefs-write",
        "--allow-attach",
        "--allow-child-command",
        "--stop-on-child-exit",
        "--binary",
        args.pm_binary,
        "--tracefs-root",
        args.tracefs_root,
        "--duration-sec",
        str(args.uprobe_duration_sec),
        "--verbose",
    ]
    for event in EVENT_SPECS:
        command.extend(["--event", event])
    command.append("--")
    command.extend([args.busybox, "sh", args.child_script])
    return command


def parse_uprobe_output(text: str) -> dict[str, Any]:
    result_match = UPROBE_RESULT_RE.search(text)
    counts = {label: int(value) for label, value in EVENT_COUNT_RE.findall(text)}
    keys = parse_keys(text)
    pm_contract = {
        key[len("pm_service_trigger_observer."):]: value
        for key, value in keys.items()
        if key.startswith("pm_service_trigger_observer.")
    }
    register_failures = [line.strip() for line in text.splitlines() if ".register=failed" in line]
    attach_failures = [line.strip() for line in text.splitlines() if ".attach=failed" in line]
    cleanup_failures = [line.strip() for line in text.splitlines() if ".cleanup=remove-failed" in line]
    return {
        "result": result_match.group(1) if result_match else keys.get("result", ""),
        "counts": counts,
        "hit_count": sum(1 for value in counts.values() if value > 0),
        "entry_hit": counts.get("elf_entry", 0) > 0,
        "main_hit": counts.get("libc_init_main_candidate", 0) > 0,
        "register_failures": register_failures,
        "attach_failures": attach_failures,
        "cleanup_failures": cleanup_failures,
        "pm_contract": pm_contract,
        "forbidden_true": {
            key: value
            for key, value in pm_contract.items()
            if key in {
                "mdm_helper_start_executed",
                "cnss_daemon_start_executed",
                "wifi_hal_start_executed",
                "scan_connect_linkup",
                "external_ping",
                "subsys_esoc0_open_attempted",
            } and value not in ("0", "False", "false", "")
        },
    }


def remote_sha_check(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], name: str, path: str, expected: str) -> dict[str, Any]:
    step = base.run_tcpctl(args, store, steps, name, [args.toybox, "sha256sum", path], timeout=30.0)
    text = step_payload(store, step)
    return {"file": step["file"], "ok": expected in text, "expected": expected}


def append_device_file(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       path: str,
                       text: str,
                       label: str) -> None:
    base.run_a90ctl(args, store, steps, f"{label}-rm", ["run", args.busybox, "rm", "-f", path], timeout=12.0, allow_error=True)
    for index in range(0, len(text), 1200):
        chunk = text[index:index + 1200]
        base.run_a90ctl(args, store, steps, f"{label}-append-{index // 1200:03d}", ["appendfile", path, chunk], timeout=15.0)
    base.run_a90ctl(args, store, steps, f"{label}-chmod", ["run", args.busybox, "chmod", "755", path], timeout=12.0)


def write_child_script(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    child = pm_observer_child_command(args)
    script = "#!" + args.busybox + " sh\nexec " + " ".join(shlex.quote(part) for part in child) + "\n"
    store.write_text("host/pm-observer-child-script.txt", script)
    base.run_a90ctl(args, store, steps, "child-script-mkdir", ["run", args.busybox, "mkdir", "-p", args.work_dir], timeout=12.0)
    append_device_file(args, store, steps, args.child_script, script, "child-script")


def run_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {"mounted_tracefs_before": False, "mounted_vendor_before": False}
    base.run_a90ctl(args, store, steps, "pre-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "pre-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], timeout=15.0)
    mounts_before = step_payload(store, steps[-1])
    analysis["mounted_tracefs_before"] = tracefs_mounted(mounts_before)
    analysis["mounted_vendor_before"] = mount_present(mounts_before, args.vendor_mount)

    base.run_a90ctl(args, store, steps, "selinuxfs-probe", base.selinuxfs_probe_command(args), timeout=12.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "mount-selinuxfs", base.selinuxfs_mount_command(args), timeout=12.0, allow_error=True)
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "tracefs-mount",
            shell_cmd(args, "$BB mkdir -p /sys/kernel/tracing; $BB mount -t tracefs tracefs /sys/kernel/tracing"),
            timeout=20.0,
        )
    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(
            args,
            store,
            steps,
            "vendor-ro-mount",
            shell_cmd(
                args,
                (
                    f"$BB mkdir -p {args.work_dir} {args.vendor_mount}; "
                    "dev=$($BB cat /sys/class/block/sda29/dev); "
                    "maj=${dev%:*}; min=${dev#*:}; "
                    f"$BB rm -f {args.work_dir}/sda29; "
                    f"$BB mknod {args.work_dir}/sda29 b $maj $min; "
                    f"$BB mount -t ext4 -o ro,noload {args.work_dir}/sda29 {args.vendor_mount}"
                ),
            ),
            timeout=25.0,
        )
    pm_binary_step = base.run_a90ctl(args, store, steps, "pm-binary-stat", ["run", args.busybox, "stat", args.pm_binary], timeout=15.0, allow_error=True)
    analysis["pm_binary_visible"] = bool(pm_binary_step.get("ok"))
    analysis["execns_helper"] = remote_sha_check(args, store, steps, "execns-helper-sha", args.helper, args.helper_sha256)
    analysis["uprobe_helper"] = remote_sha_check(args, store, steps, "uprobe-helper-sha", args.uprobe_helper, args.uprobe_helper_sha256)
    write_child_script(args, store, steps)

    helper_step = base.run_tcpctl(args, store, steps, "pm-service-uprobe-observer", helper_command(args), timeout=args.uprobe_duration_sec + 90.0)
    helper_text = step_payload(store, helper_step)
    analysis["uprobe"] = parse_uprobe_output(helper_text)

    analysis["post_surface"] = base.post_surface(args, store, steps)
    base.run_a90ctl(args, store, steps, "post-selftest", ["selftest"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "proc-mounts-before-cleanup", ["cat", "/proc/mounts"], timeout=15.0)

    if not analysis["mounted_vendor_before"]:
        base.run_a90ctl(args, store, steps, "vendor-umount", shell_cmd(args, f"$BB umount {args.vendor_mount}; $BB rm -f {args.work_dir}/sda29 {args.child_script}"), timeout=20.0, allow_error=True)
    if not analysis["mounted_tracefs_before"]:
        base.run_a90ctl(args, store, steps, "tracefs-umount", shell_cmd(args, "$BB umount /sys/kernel/tracing"), timeout=20.0, allow_error=True)
    if args.allow_selinuxfs_mount:
        base.run_a90ctl(args, store, steps, "umount-selinuxfs", base.selinuxfs_umount_command(args), timeout=12.0, allow_error=True)
    base.run_a90ctl(args, store, steps, "proc-mounts-after-cleanup", ["cat", "/proc/mounts"], timeout=15.0)
    base.run_a90ctl(args, store, steps, "post-netservice-status", ["netservice", "status"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-bootstatus", ["bootstatus"], timeout=12.0)
    base.run_a90ctl(args, store, steps, "post-selftest-final", ["selftest"], timeout=12.0)
    mounts_after = step_payload(store, steps[-4]) if len(steps) >= 4 else ""
    analysis["mounted_tracefs_after"] = tracefs_mounted(mounts_after)
    analysis["mounted_vendor_after"] = mount_present(mounts_after, args.vendor_mount)
    return steps, analysis


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    for flag, enabled in (
        ("--allow-tracefs-mount", args.allow_tracefs_mount),
        ("--allow-tracefs-write", args.allow_tracefs_write),
        ("--allow-bpf-attach", args.allow_bpf_attach),
        ("--allow-vendor-mount", args.allow_vendor_mount),
        ("--allow-selinuxfs-mount", args.allow_selinuxfs_mount),
        ("--allow-pm-service-trigger-observer", args.allow_pm_service_trigger_observer),
        ("--assume-yes", args.assume_yes),
    ):
        if not enabled:
            missing.append(flag)
    return missing


def decide(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1078-pm-service-uprobe-active-plan-ready",
            True,
            "plan-only; no tracefs write, BPF attach, PM actor, or Wi-Fi action executed",
            "run V1078 with explicit allow flags",
        )
    missing = required_flags(args)
    if missing:
        return (
            "v1078-pm-service-uprobe-active-approval-required",
            False,
            "missing explicit flags: " + ", ".join(missing),
            "rerun with all V1078 allow flags",
        )
    analysis = manifest.get("analysis") or {}
    uprobe = analysis.get("uprobe") or {}
    post = analysis.get("post_surface") or {}
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1078-execns-helper-sha-mismatch", False, "remote execns helper is not v196", "redeploy V1074 helper v196")
    if not analysis.get("uprobe_helper", {}).get("ok"):
        return ("v1078-uprobe-helper-sha-mismatch", False, "remote uprobe helper is not V1076 artifact", "rerun V1077 deploy/check-only")
    if not analysis.get("pm_binary_visible"):
        return ("v1078-pm-binary-not-visible", False, "global read-only vendor mount did not expose pm-service", "repair synthetic sda29 mount before active uprobe retry")
    if uprobe.get("result") != "uprobe-count-pass":
        return ("v1078-uprobe-active-failed", False, f"uprobe result={uprobe.get('result')}", "inspect active helper transcript")
    if uprobe.get("register_failures") or uprobe.get("attach_failures") or uprobe.get("cleanup_failures"):
        return ("v1078-uprobe-active-cleanup-review", False, "register/attach/cleanup failures present", "inspect tracefs cleanup before retry")
    if not (uprobe.get("entry_hit") or uprobe.get("main_hit")):
        return ("v1078-pm-service-uprobe-no-hit", False, "pm-service entry/main uprobes did not fire", "verify vendor inode path and offset mapping")
    if uprobe.get("forbidden_true"):
        return ("v1078-forbidden-action-observed", False, f"forbidden={uprobe.get('forbidden_true')}", "stop and audit helper contract")
    if post.get("forbidden_actor_hits") or post.get("wifi_link_hits"):
        return ("v1078-postflight-safety-review", False, "forbidden actors or Wi-Fi link appeared", "cleanup device before continuing")
    return (
        "v1078-pm-service-uprobe-boundary-captured",
        True,
        f"entry_hit={uprobe.get('entry_hit')} main_hit={uprobe.get('main_hit')} hit_count={uprobe.get('hit_count')}",
        "classify callsite counts and choose the next PM-service exit-255 root-cause probe",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1077 = load_json(args.v1077_manifest)
    manifest: dict[str, Any] = {
        "cycle": "v1078",
        "generated_at": now_iso(),
        "command": args.command,
        "v1077": {
            "manifest": str(repo_path(args.v1077_manifest)),
            "decision": v1077.get("decision", ""),
            "pass": bool(v1077.get("pass")),
        },
        "event_specs": list(EVENT_SPECS),
        "steps": [],
        "analysis": {},
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    if args.command == "run" and not required_flags(args) and v1077.get("decision") == "v1077-pm-service-uprobe-helper-deploy-checkonly-pass":
        steps, analysis = run_live(args, store)
        manifest["steps"] = steps
        manifest["analysis"] = analysis
        manifest["tracefs_write_executed"] = True
        manifest["bpf_attach_executed"] = True
        manifest["pm_actor_executed"] = True
        uprobe = analysis.get("uprobe") or {}
        contract = uprobe.get("pm_contract") or {}
        manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
        manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
        manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    decision, passed, reason, next_step = decide(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    uprobe = (manifest.get("analysis") or {}).get("uprobe") or {}
    counts = uprobe.get("counts") or {}
    step_rows = [[step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")] for step in manifest.get("steps", [])]
    return "\n".join([
        "# V1078 PM Service Uprobe Active Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Uprobe",
        "",
        f"- result: `{uprobe.get('result', '')}`",
        f"- entry_hit: `{uprobe.get('entry_hit', '')}`",
        f"- main_hit: `{uprobe.get('main_hit', '')}`",
        f"- hit_count: `{uprobe.get('hit_count', '')}`",
        "",
        "```json",
        json.dumps(counts, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        base.markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.DEFAULT_PORT)
    parser.add_argument("--device-ip", default=base.DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=base.DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=90.0)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_EXECNS_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_EXECNS_HELPER_MARKER)
    parser.add_argument("--uprobe-helper", default=DEFAULT_UPROBE_HELPER)
    parser.add_argument("--uprobe-helper-sha256", default=DEFAULT_UPROBE_HELPER_SHA256)
    parser.add_argument("--v1077-manifest", type=Path, default=DEFAULT_V1077_MANIFEST)
    parser.add_argument("--property-root", default=base.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=4)
    parser.add_argument("--toybox-timeout-sec", type=int, default=18)
    parser.add_argument("--uprobe-duration-sec", type=int, default=18)
    parser.add_argument("--vendor-block", default=DEFAULT_VENDOR_BLOCK)
    parser.add_argument("--vendor-mount", default=DEFAULT_VENDOR_MOUNT)
    parser.add_argument("--pm-binary", default=DEFAULT_PM_BINARY)
    parser.add_argument("--tracefs-root", default=DEFAULT_TRACEFS_ROOT)
    parser.add_argument("--work-dir", default=DEFAULT_WORK_DIR)
    parser.add_argument("--child-script", default=DEFAULT_CHILD_SCRIPT)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--allow-tracefs-write", action="store_true")
    parser.add_argument("--allow-bpf-attach", action="store_true")
    parser.add_argument("--allow-vendor-mount", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-pm-service-trigger-observer", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
