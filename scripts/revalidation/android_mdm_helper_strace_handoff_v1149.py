#!/usr/bin/env python3
"""V1149 Android handoff for Magisk mdm_helper strace capture.

This runner temporarily boots Android, installs the V1147 Magisk module, reboots
Android once so the wrapper can capture early mdm_helper execution, pulls
`/data/local/tmp/a90-wifi/`, removes the module, and restores native v724. It
does not enable Wi-Fi, scan/connect, use credentials, run DHCP/routes, external
ping, retry native `/dev/subsys_esoc0`, or run native eSoC ioctls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import tarfile
import time
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from android_hwservice_handoff_v424 import (
    BOOT_READBACK_BLOCK_SIZE,
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_REMOTE_ANDROID_IMAGE,
    StepResult,
    adb_base,
    execute_bridge_step,
    execute_step,
    image_context,
    remote_quote,
    require_approval,
    run_process,
    step_text,
    wait_for_adb_state,
    write_step,
)
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    parse_prop_text,
    prop_poll_command,
)
from native_wifi_android_mdm_helper_strace_module_v1147 import MODULE_ID, TRACE_DIR


DEFAULT_OUT_DIR = Path("tmp/wifi/v1149-android-mdm-helper-strace-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REMOTE_NATIVE_IMAGE = "/tmp/native_init_boot.img"
DEFAULT_MODULE_ROOT = Path("tmp/wifi/v1147-android-mdm-helper-strace-module/module")
DEFAULT_REMOTE_MODULE_ZIP = "/data/local/tmp/a90_mdm_trace_v1149.zip"
DEFAULT_REMOTE_TRACE_TAR = "/data/local/tmp/a90-wifi-v1149.tar.gz"

FORBIDDEN_ACTIVE_WIFI_RE = re.compile(
    r"\b(?:svc\s+wifi|cmd\s+wifi|iw\s+(?:scan|connect)|wpa_cli|"
    r"rfkill\s+(?:un)?block|ip\s+link\s+set\b.*\bup|dhcpcd|udhcpc|ping\s+google|ping\s+8\.8\.8\.8)\b",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--module-root", type=Path, default=DEFAULT_MODULE_ROOT)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--remote-native-image", default=DEFAULT_REMOTE_NATIVE_IMAGE)
    parser.add_argument("--remote-module-zip", default=DEFAULT_REMOTE_MODULE_ZIP)
    parser.add_argument("--remote-trace-tar", default=DEFAULT_REMOTE_TRACE_TAR)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=420)
    parser.add_argument("--boot-complete-timeout", type=int, default=DEFAULT_BOOT_COMPLETE_TIMEOUT)
    parser.add_argument("--capture-settle-sleep", type=int, default=30)
    parser.add_argument("--capture-wifi-ready-timeout", type=int, default=180)
    parser.add_argument("--capture-wifi-ready-poll", type=int, default=2)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def shell_quote(command: str) -> str:
    return shlex.quote(command)


def adb_shell(args: argparse.Namespace, shell_command: str) -> list[str]:
    return [*adb_base(args), "shell", shell_command]


def adb_su(args: argparse.Namespace, shell_command: str) -> list[str]:
    return [*adb_base(args), "shell", "su", "-c", shell_quote(shell_command)]


def package_path(store: EvidenceStore) -> Path:
    return store.path("a90_mdm_trace_v1149.zip")


def pulled_trace_tar_path(store: EvidenceStore) -> Path:
    return store.path("android-trace/a90-wifi-v1149.tar.gz")


def extracted_trace_dir(store: EvidenceStore) -> Path:
    return store.path("android-trace/extracted")


def verify_module_root(module_root: Path) -> tuple[bool, list[str]]:
    root = repo_path(module_root)
    required = [
        root / "module.prop",
        root / "system/vendor/bin/a90_strace",
        root / "vendor/bin/a90_strace",
        root / "system/vendor/bin/mdm_helper",
        root / "vendor/bin/mdm_helper",
        root / "post-fs-data.sh",
        root / "service.sh",
        root / "sepolicy.rule",
        root / "customize.sh",
    ]
    problems: list[str] = []
    for path in required:
        if not path.exists():
            problems.append(f"missing {path}")
    for strace_path in (root / "system/vendor/bin/a90_strace", root / "vendor/bin/a90_strace"):
        if strace_path.exists():
            mode = strace_path.stat().st_mode & 0o777
            if mode & 0o111 == 0:
                problems.append(f"{strace_path.relative_to(root)} is not executable")
    wrapper = root / "system/vendor/bin/mdm_helper"
    if wrapper.exists():
        wrapper_mode = wrapper.stat().st_mode & 0o777
        if wrapper_mode & 0o111 == 0:
            problems.append("system/vendor/bin/mdm_helper wrapper is not executable")
        wrapper_bytes = wrapper.read_bytes()
        if wrapper_bytes.startswith(b"\x7fELF"):
            required_markers = [
                b"a90_mdm_helper_strace_wrapper v1157",
                b"/vendor/bin/a90_strace",
                b"/vendor/bin/mdm_helper.real",
                b"trace=openat,ioctl,read,write,execve",
                b"/sbin/.magisk/mirror/vendor/bin/mdm_helper",
                b"refusing recursive original path",
            ]
            for marker in required_markers:
                if marker not in wrapper_bytes:
                    problems.append(f"ELF wrapper lacks marker {marker.decode('utf-8', errors='replace')}")
        else:
            text = wrapper_bytes.decode("utf-8", errors="replace")
            if "refusing recursive original path" not in text:
                problems.append("wrapper lacks recursive original-path guard")
            for syscall in ("openat", "ioctl", "read", "write", "execve"):
                if syscall not in text:
                    problems.append(f"wrapper lacks syscall filter {syscall}")
    vendor_wrapper = root / "vendor/bin/mdm_helper"
    if vendor_wrapper.exists():
        vendor_mode = vendor_wrapper.stat().st_mode & 0o777
        if vendor_mode & 0o111 == 0:
            problems.append("vendor/bin/mdm_helper wrapper is not executable")
    if vendor_wrapper.exists() and wrapper.exists() and vendor_wrapper.read_bytes() != wrapper.read_bytes():
        problems.append("vendor/bin/mdm_helper wrapper differs from system/vendor/bin/mdm_helper")
    sepolicy = root / "sepolicy.rule"
    if sepolicy.exists():
        sepolicy_text = sepolicy.read_text(encoding="utf-8", errors="replace")
        required_policy_markers = [
            "allow vendor_mdm_helper magisk_file file",
            "allow vendor_mdm_helper adb_data_file file",
            "allow vendor_mdm_helper system_file file",
            "allow vendor_mdm_helper system_data_file file",
            "allow vendor_mdm_helper vendor_file file",
            "execute_no_trans",
            "allow vendor_mdm_helper shell_data_file file",
            "allow vendor_mdm_helper vendor_mdm_helper process ptrace",
        ]
        for marker in required_policy_markers:
            if marker not in sepolicy_text:
                problems.append(f"sepolicy.rule lacks marker {marker}")
        if "setenforce" in sepolicy_text or "permissive" in sepolicy_text.lower():
            problems.append("sepolicy.rule contains forbidden permissive marker")
    customize = root / "customize.sh"
    if customize.exists():
        customize_text = customize.read_text(encoding="utf-8", errors="replace")
        for marker in ("vendor/bin/a90_strace", "system/vendor/bin/a90_strace", "vendor/bin/mdm_helper.real", "system/vendor/bin/mdm_helper.real", "vendor/bin/mdm_helper", "system/vendor/bin/mdm_helper"):
            if marker not in customize_text:
                problems.append(f"customize.sh lacks marker {marker}")
        if "setenforce" in customize_text or "permissive" in customize_text.lower():
            problems.append("customize.sh contains forbidden permissive marker")
    return not problems, problems


def zip_module(module_root: Path, store: EvidenceStore) -> Path:
    root = repo_path(module_root)
    out_zip = package_path(store)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel)
            mode = path.stat().st_mode & 0o777
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())
    out_zip.chmod(0o600)
    return out_zip


def push_flash_readback_steps(
    args: argparse.Namespace,
    *,
    role: str,
    image_path: str,
    image_size: int,
    remote_path: str,
) -> list[tuple[str, list[str], int]]:
    remote = remote_quote(remote_path)
    boot_block = remote_quote(args.boot_block)
    count = image_size // BOOT_READBACK_BLOCK_SIZE
    return [
        (f"push-{role}-boot", [*adb_base(args), "push", image_path, remote_path], args.timeout * 4),
        (
            f"remote-{role}-sha",
            [*adb_base(args), "shell", f"sha256sum {remote} 2>/dev/null || toybox sha256sum {remote}"],
            args.timeout,
        ),
        (
            f"flash-{role}-boot",
            [*adb_base(args), "shell", f"dd if={remote} of={boot_block} bs=4M conv=fsync && sync"],
            args.timeout * 4,
        ),
        (
            f"readback-{role}-boot",
            [
                *adb_base(args),
                "shell",
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} 2>/dev/null | sha256sum 2>/dev/null || "
                f"dd if={boot_block} bs={BOOT_READBACK_BLOCK_SIZE} count={count} 2>/dev/null | toybox sha256sum",
            ],
            args.timeout * 2,
        ),
    ]


def wait_for_boot_complete_named(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    execute: bool,
) -> tuple[StepResult, dict[str, Any]]:
    command = prop_poll_command(args)
    if not execute:
        step = write_step(store, name, command, "[dry-run] wait for sys.boot_completed=1\n", "", 0, 0.0, skipped=True, ok_override=True)
        return step, {"props": {}, "samples": [], "boot_completed": False}

    started = time.monotonic()
    deadline = started + args.boot_complete_timeout
    samples: list[dict[str, Any]] = []
    last_text = ""
    last_error = ""
    while time.monotonic() < deadline:
        rc, text, error, _ = run_process(command, min(args.timeout, 30))
        props = parse_prop_text(text)
        samples.append(
            {
                "elapsed_sec": round(time.monotonic() - started, 3),
                "rc": rc,
                "props": props,
                "error": error,
            }
        )
        last_text = text
        last_error = error
        if rc == 0 and props.get("sys.boot_completed") == "1":
            body = json.dumps({"samples": samples, "final_props": props}, indent=2, sort_keys=True) + "\n"
            step = write_step(store, name, command, body, "", 0, time.monotonic() - started, ok_override=True)
            return step, {"props": props, "samples": samples, "boot_completed": True}
        time.sleep(3.0)

    body = json.dumps({"samples": samples, "last_text": last_text, "last_error": last_error}, indent=2, sort_keys=True) + "\n"
    step = write_step(
        store,
        name,
        command,
        body,
        f"timeout waiting for sys.boot_completed=1 after {args.boot_complete_timeout}s",
        None,
        time.monotonic() - started,
        ok_override=False,
    )
    return step, {"props": samples[-1]["props"] if samples else {}, "samples": samples, "boot_completed": False}


def build_step_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    module_zip = package_path(store)
    trace_tar = pulled_trace_tar_path(store)
    trace_dir_q = remote_quote(TRACE_DIR)
    remote_trace_tar_q = remote_quote(args.remote_trace_tar)
    module_id_q = shlex.quote(MODULE_ID)
    ready_timeout = max(1, args.capture_wifi_ready_timeout)
    ready_poll = max(1, args.capture_wifi_ready_poll)
    wifi_ready_wait = (
        "set -x; "
        f"end=$(( $(date +%s) + {ready_timeout} )); "
        "reason=timeout; ready=0; "
        "while [ $(date +%s) -lt $end ]; do "
        "if ip link show wlan0 >/dev/null 2>&1; then reason=wlan0-netdev; ready=1; break; fi; "
        "if dmesg | tail -n 400 | grep -E 'WLAN FW is ready|FW ready event received|dev : wlan0 : event : 16|dev : swlan0 : event : 16|dev : p2p0 : event : 16|dev : wifi-aware0 : event : 16' >/dev/null 2>&1; then reason=dmesg-fw-ready; ready=1; break; fi; "
        f"sleep {ready_poll}; "
        "done; "
        "echo wifi_ready=$ready; echo wifi_ready_reason=$reason; "
        "ip link show wlan0 2>/dev/null || true; "
        "dmesg | grep -E 'WLAN FW is ready|FW ready event received|dev : wlan0 : event : 16|dev : swlan0 : event : 16|dev : p2p0 : event : 16|dev : wifi-aware0 : event : 16' | tail -n 40 || true; "
        "exit 0"
    )
    plan: list[tuple[str, list[str] | str, int]] = [
        ("native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], args.timeout),
        ("native-selftest", ["python3", "scripts/revalidation/a90ctl.py", "selftest"], args.timeout),
        ("native-netservice-status", ["python3", "scripts/revalidation/a90ctl.py", "netservice", "status"], args.timeout),
        ("hide-menu", f"bridge:{args.bridge_host}:{args.bridge_port} hide", args.timeout),
        ("native-recovery", f"bridge:{args.bridge_host}:{args.bridge_port} recovery", args.recovery_timeout),
        ("wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
    ]
    plan.extend(
        push_flash_readback_steps(
            args,
            role="android",
            image_path=android_image.path,
            image_size=android_image.size,
            remote_path=args.remote_android_image,
        )
    )
    plan.extend(
        [
            ("reboot-android-for-install", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
            ("wait-android-install-boot", [*adb_base(args), "devices"], args.android_timeout),
            ("wait-install-boot-complete", prop_poll_command(args), args.boot_complete_timeout),
            (
                "android-root-magisk-preflight",
                adb_su(args, "id; magisk -v; ls -ld /data/adb/modules /data/adb/modules_update 2>/dev/null || true"),
                args.timeout,
            ),
            ("push-magisk-module-zip", [*adb_base(args), "push", str(module_zip), args.remote_module_zip], args.timeout * 2),
            (
                "install-magisk-module",
                adb_su(args, f"magisk --install-module {remote_quote(args.remote_module_zip)}"),
                args.timeout * 4,
            ),
            ("reboot-android-for-capture", [*adb_base(args), "reboot"], args.timeout),
            ("wait-android-capture-boot", [*adb_base(args), "devices"], args.android_timeout),
            ("wait-capture-boot-complete", prop_poll_command(args), args.boot_complete_timeout),
            (
                "android-wifi-fw-ready-wait",
                adb_su(args, wifi_ready_wait),
                ready_timeout + args.timeout,
            ),
            ("capture-settle", f"sleep {args.capture_settle_sleep}", args.capture_settle_sleep + args.timeout),
            (
                "android-overlay-proof",
                adb_su(
                    args,
                    "set -x; "
                    "getenforce 2>/dev/null || true; "
                    "for p in "
                    "/vendor/bin/mdm_helper "
                    "/system/vendor/bin/mdm_helper "
                    "/vendor/bin/mdm_helper.real "
                    "/system/vendor/bin/mdm_helper.real "
                    "/vendor/bin/a90_strace "
                    "/system/vendor/bin/a90_strace "
                    "/data/adb/modules/a90_mdm_trace/vendor/bin/a90_strace "
                    "/data/adb/modules/a90_mdm_trace/system/vendor/bin/a90_strace "
                    "/data/adb/modules/a90_mdm_trace/customize.sh "
                    "/data/adb/modules/a90_mdm_trace/sepolicy.rule "
                    "/data/adb/modules/a90_mdm_trace/vendor/bin/mdm_helper "
                    "/data/adb/modules/a90_mdm_trace/vendor/bin/mdm_helper.real "
                    "/data/adb/modules/a90_mdm_trace/system/vendor/bin/mdm_helper "
                    "/data/adb/modules/a90_mdm_trace/system/vendor/bin/mdm_helper.real "
                    "/data/local/tmp/a90-wifi; do "
                    "echo ===$p===; "
                    "ls -ldZ \"$p\" 2>/dev/null || true; "
                    "stat -c '%a %U %G %n' \"$p\" 2>/dev/null || true; "
                    "readlink -f \"$p\" 2>/dev/null || true; "
                    "done; "
                    "echo ===sepolicy.rule.head===; "
                    "head -n 40 /data/adb/modules/a90_mdm_trace/sepolicy.rule 2>/dev/null || true; "
                    "echo ===customize.sh.head===; "
                    "head -n 40 /data/adb/modules/a90_mdm_trace/customize.sh 2>/dev/null || true; "
                    "grep -E 'a90_mdm_trace|mdm_helper|/vendor' /proc/mounts | head -n 80 || true",
                ),
                args.timeout,
            ),
            (
                "android-trace-surface",
                adb_su(
                    args,
                    f"set -x; ls -lR {trace_dir_q} 2>/dev/null || true; "
                    f"for f in {trace_dir_q}/mdm_helper.wrapper.log {trace_dir_q}/mdm_helper.strace.txt "
                    f"{trace_dir_q}/service.log {trace_dir_q}/post-fs-data.log {trace_dir_q}/wifi_ready_wait.txt {trace_dir_q}/pids.txt; do "
                    "echo ===$f===; [ -f \"$f\" ] && (head -n 120 \"$f\"; echo ---TAIL---; tail -n 160 \"$f\") || true; done; "
                    f"for d in {trace_dir_q}/proc_a90_strace_* {trace_dir_q}/proc_mdm_helper_real_* {trace_dir_q}/proc_mdm_helper_*; do "
                    "echo ===$d===; [ -d \"$d\" ] && (ls -l \"$d\"; for f in wchan.txt syscall.txt stack.txt fd.txt cmdline.bin status.txt; do echo ---$f---; [ -f \"$d/$f\" ] && cat \"$d/$f\" || true; done) || true; done",
                ),
                args.timeout * 2,
            ),
            (
                "pack-android-trace",
                adb_su(args, f"rm -f {remote_trace_tar_q}; tar -C /data/local/tmp -czf {remote_trace_tar_q} a90-wifi"),
                args.timeout * 3,
            ),
            ("pull-android-trace", [*adb_base(args), "pull", args.remote_trace_tar, str(trace_tar)], args.timeout * 4),
            (
                "remove-magisk-module",
                adb_su(
                    args,
                    f"rm -rf /data/adb/modules/{module_id_q} /data/adb/modules_update/{module_id_q}; "
                    f"rm -f {remote_quote(args.remote_module_zip)} {remote_trace_tar_q}; sync",
                ),
                args.timeout,
            ),
            ("reboot-recovery-for-rollback", [*adb_base(args), "reboot", "recovery"], args.timeout),
            ("wait-rollback-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ]
    )
    plan.extend(
        push_flash_readback_steps(
            args,
            role="native",
            image_path=native_image.path,
            image_size=native_image.size,
            remote_path=args.remote_native_image,
        )
    )
    plan.extend(
        [
            ("reboot-native", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
            ("wait-native-bootstatus", f"bridge:{args.bridge_host}:{args.bridge_port} bootstatus", args.recovery_timeout + args.android_timeout),
            ("wait-native-version", f"bridge:{args.bridge_host}:{args.bridge_port} version", args.timeout),
        ]
    )
    return plan


def rollback_steps(args: argparse.Namespace, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    module_id_q = shlex.quote(MODULE_ID)
    plan: list[tuple[str, list[str] | str, int]] = [
        (
            "cleanup-remove-magisk-module",
            adb_su(args, f"rm -rf /data/adb/modules/{module_id_q} /data/adb/modules_update/{module_id_q}; sync"),
            args.timeout,
        ),
        ("cleanup-reboot-recovery", [*adb_base(args), "reboot", "recovery"], args.timeout),
        ("cleanup-wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
    ]
    plan.extend(
        push_flash_readback_steps(
            args,
            role="cleanup-native",
            image_path=native_image.path,
            image_size=native_image.size,
            remote_path=args.remote_native_image,
        )
    )
    plan.extend(
        [
            ("cleanup-reboot-native", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
            ("cleanup-wait-native-bootstatus", f"bridge:{args.bridge_host}:{args.bridge_port} bootstatus", args.recovery_timeout + args.android_timeout),
        ]
    )
    return plan


def execute_rollback(args: argparse.Namespace, store: EvidenceStore, steps: list[StepResult], native_image: Any) -> dict[str, Any]:
    cleanup_context: dict[str, Any] = {"attempted": True, "steps": []}
    for name, command, timeout in rollback_steps(args, native_image):
        if isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute=True)
        elif name == "cleanup-wait-recovery":
            step = wait_for_adb_state(args, {"recovery"}, timeout, True, store, name)
        else:
            step = execute_step(store, name, command, timeout, execute=True)
        steps.append(step)
        cleanup_context["steps"].append(asdict(step))
        if not step.ok and name in {"cleanup-wait-recovery", "readback-cleanup-native-boot", "cleanup-wait-native-bootstatus"}:
            cleanup_context["ok"] = False
            cleanup_context["failed_step"] = name
            return cleanup_context
    cleanup_context["ok"] = all(item["ok"] for item in cleanup_context["steps"] if item["name"] != "cleanup-remove-magisk-module")
    return cleanup_context


def contains_forbidden_active_wifi(plan: list[tuple[str, list[str] | str, int]]) -> list[str]:
    offenders: list[str] = []
    for name, command, _ in plan:
        rendered = " ".join(command) if isinstance(command, list) else command
        if FORBIDDEN_ACTIVE_WIFI_RE.search(rendered):
            offenders.append(name)
    return offenders


def extract_trace_tar(store: EvidenceStore) -> dict[str, Any]:
    tar_path = pulled_trace_tar_path(store)
    out_dir = extracted_trace_dir(store)
    if not tar_path.exists():
        return {"present": False, "reason": "trace tar not pulled"}
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as archive:
        def safe_member(member: tarfile.TarInfo) -> tarfile.TarInfo:
            target = (out_dir / member.name).resolve()
            if out_dir.resolve() not in target.parents and target != out_dir.resolve():
                raise RuntimeError(f"unsafe tar path: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"refusing link in trace tar: {member.name}")
            return member

        archive.extractall(out_dir, members=[safe_member(item) for item in archive.getmembers()])

    trace_root = out_dir / "a90-wifi"
    wrapper_log = trace_root / "mdm_helper.wrapper.log"
    strace_log = trace_root / "mdm_helper.strace.txt"
    service_log = trace_root / "service.log"
    pids = trace_root / "pids.txt"
    boot_dmesg = trace_root / "boot_dmesg.txt"
    wifi_ready_wait = trace_root / "wifi_ready_wait.txt"
    strace_text = strace_log.read_text(encoding="utf-8", errors="replace")[:2_000_000] if strace_log.exists() else ""
    wrapper_text = wrapper_log.read_text(encoding="utf-8", errors="replace")[:200_000] if wrapper_log.exists() else ""
    pids_text = pids.read_text(encoding="utf-8", errors="replace")[:200_000] if pids.exists() else ""
    dmesg_text = boot_dmesg.read_text(encoding="utf-8", errors="replace")[:2_000_000] if boot_dmesg.exists() else ""
    wifi_ready_text = wifi_ready_wait.read_text(encoding="utf-8", errors="replace")[:20_000] if wifi_ready_wait.exists() else ""
    mdm_helper_exit_statuses = [
        int(match.group(1))
        for match in re.finditer(r"Service 'vendor\.mdm_helper'.*exited with status (\d+)", dmesg_text)
    ]
    proc_dirs = sorted(item.name for item in trace_root.glob("proc_*") if item.is_dir())
    strace_has_ks_exec = bool(
        re.search(r'execve\("([^"]*/)?ks"', strace_text)
        or re.search(r'openat\([^,]+,\s*"[^"]*/ks"', strace_text)
        or re.search(r"^ks\s+\d+", pids_text, flags=re.MULTILINE)
    )
    return {
        "present": True,
        "trace_root": str(trace_root),
        "wrapper_log_present": wrapper_log.exists(),
        "strace_log_present": strace_log.exists(),
        "service_log_present": service_log.exists(),
        "pids_present": pids.exists(),
        "wifi_ready_wait_present": wifi_ready_wait.exists(),
        "wifi_ready_wait": wifi_ready_text.strip(),
        "wrapper_started": "wrapper_start=" in wrapper_text,
        "strace_executed": "exec_strace=" in wrapper_text,
        "original_selected": "original=" in wrapper_text,
        "strace_has_esoc0": "/dev/esoc-0" in strace_text,
        "strace_has_ioctl": "ioctl(" in strace_text,
        "strace_has_cmd_engine_register": "_IOC(_IOC_NONE, 0xcc, 0x7, 0)" in strace_text,
        "strace_has_wait_for_req": "_IOC(_IOC_READ, 0xcc, 0x2, 0x4)" in strace_text,
        "strace_has_wakelock": "/sys/power/wake_lock" in strace_text and "mdm_helper" in strace_text,
        "strace_has_execve": "execve(" in strace_text,
        "strace_has_ks": strace_has_ks_exec,
        "strace_has_mhi_pipe": "/dev/mhi_0305_01.01.00_pipe_10" in strace_text,
        "strace_size": strace_log.stat().st_size if strace_log.exists() else 0,
        "strace_line_count": strace_text.count("\n"),
        "dmesg_present": boot_dmesg.exists(),
        "dmesg_fw_ready": "WLAN FW is ready" in dmesg_text or "FW ready event received" in dmesg_text,
        "dmesg_wlan0_created": "dev : wlan0 : event : 16" in dmesg_text,
        "mdm_helper_init_started": "starting service 'vendor.mdm_helper'" in dmesg_text,
        "mdm_helper_exit_statuses": mdm_helper_exit_statuses,
        "mdm_helper_exit_127": 127 in mdm_helper_exit_statuses,
        "mdm_helper_load_script_crash": "Comm: mdm_helper" in dmesg_text and "load_script" in dmesg_text,
        "proc_dirs": proc_dirs[:80],
    }


def decide_trace(trace: dict[str, Any]) -> tuple[str, bool, str]:
    if not trace.get("present"):
        return "v1149-android-strace-trace-missing-rollback-complete", False, str(trace.get("reason"))
    if not trace.get("wrapper_started"):
        if trace.get("mdm_helper_exit_127"):
            return (
                "v1149-android-elf-wrapper-exit127-rollback-complete",
                False,
                "vendor.mdm_helper exits 127 under ELF overlay; likely wrapper cannot access strace/log path",
            )
        return "v1149-android-strace-wrapper-not-started-rollback-complete", False, "wrapper log did not show mdm_helper wrapper start"
    if not trace.get("strace_log_present"):
        return "v1149-android-strace-log-missing-rollback-complete", False, "strace output file missing"
    if not trace.get("strace_has_esoc0"):
        return "v1149-android-strace-no-esoc0-rollback-complete", False, "strace did not capture /dev/esoc-0"
    return "v1149-android-mdm-helper-strace-captured-rollback-complete", True, "Android mdm_helper strace captured and native rollback completed"


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    module_ok, module_problems = verify_module_root(args.module_root)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "module_root": str(repo_path(args.module_root)),
        "module_ok": module_ok,
        "module_problems": module_problems,
        "module_zip": str(package_path(store)),
        "trace_tar": str(pulled_trace_tar_path(store)),
    }
    if not module_ok:
        return [], context, "v1149-handoff-module-not-ready", False
    zip_module(args.module_root, store)
    store.mkdir("android-trace")
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v1149-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v1149-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v1149-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v1149-handoff-approval-required", False

    plan = build_step_plan(args, store, android_image, native_image)
    offenders = contains_forbidden_active_wifi(plan)
    if offenders:
        context["forbidden_active_wifi_steps"] = offenders
        return [], context, "v1149-handoff-active-wifi-command-blocked", False

    steps: list[StepResult] = []
    if args.command == "plan":
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v1149-handoff-plan-ready", True

    live = args.command == "run"
    android_boot_written = False
    native_restored = False
    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute=live)
        elif name in {"wait-recovery", "wait-rollback-recovery"}:
            step = wait_for_adb_state(args, {"recovery"}, timeout, live, store, name)
        elif name in {"wait-android-install-boot", "wait-android-capture-boot"}:
            step = wait_for_adb_state(args, {"device"}, timeout, live, store, name)
        elif name in {"wait-install-boot-complete", "wait-capture-boot-complete"}:
            step, boot_state = wait_for_boot_complete_named(args, store, name, live)
            context[name.replace("-", "_")] = boot_state
        elif name == "capture-settle":
            step = execute_step(store, name, ["bash", "-lc", command], timeout, execute=live)
        else:
            step = execute_step(store, name, command, timeout, execute=live)
        steps.append(step)

        if live and name == "flash-android-boot" and step.ok:
            android_boot_written = True
        if live and name == "readback-android-boot" and step.ok and android_image.sha256 in step_text(store, step):
            android_boot_written = True
        if live and name == "flash-native-boot" and step.ok:
            native_restored = True
        if live and name == "readback-native-boot" and step.ok and native_image.sha256 in step_text(store, step):
            native_restored = True

        if name == "remote-android-sha" and live and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v1149-handoff-remote-android-sha-mismatch", False
        if name == "readback-android-boot" and live and (not step.ok or android_image.sha256 not in step_text(store, step)):
            if android_boot_written and not native_restored:
                context["cleanup"] = execute_rollback(args, store, steps, native_image)
            return steps, context, "v1149-handoff-readback-android-sha-mismatch", False
        if name == "remote-native-sha" and live and step.ok and native_image.sha256 not in step_text(store, step):
            return steps, context, "v1149-handoff-remote-native-sha-mismatch", False
        if name == "readback-native-boot" and live and (not step.ok or native_image.sha256 not in step_text(store, step)):
            return steps, context, "v1149-handoff-readback-native-sha-mismatch", False
        if live and not step.ok:
            if android_boot_written and not native_restored:
                context["cleanup"] = execute_rollback(args, store, steps, native_image)
            return steps, context, f"v1149-handoff-failed-{name}", False

    if not live:
        return steps, context, "v1149-handoff-dryrun-ready", True

    trace = extract_trace_tar(store)
    context["trace_classification"] = trace
    decision, pass_ok, reason = decide_trace(trace)
    context["trace_reason"] = reason
    return steps, context, decision, pass_ok


def reason_for(decision: str, context: dict[str, Any]) -> str:
    return {
        "v1149-handoff-plan-ready": "execution plan generated without device mutation",
        "v1149-handoff-dryrun-ready": "dry-run recorded all steps without device mutation",
        "v1149-handoff-module-not-ready": "V1147 module scaffold is missing required install-ready files",
        "v1149-handoff-missing-native-rollback": "native rollback image missing or lacks expected marker",
        "v1149-handoff-missing-android-boot": "no Android boot image candidate passed checks",
        "v1149-handoff-image-collision": "Android and native rollback images unexpectedly match",
        "v1149-handoff-approval-required": "live run refused because approval flags are missing",
        "v1149-handoff-active-wifi-command-blocked": "handoff plan contains forbidden active Wi-Fi command pattern",
        "v1149-android-elf-wrapper-exit127-rollback-complete": context.get(
            "trace_reason",
            "vendor.mdm_helper exits 127 under ELF overlay and native rollback completed",
        ),
        "v1149-android-mdm-helper-strace-captured-rollback-complete": context.get("trace_reason", "Android strace captured and native rollback completed"),
    }.get(decision, context.get("trace_reason", decision))


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [item["name"], "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"), str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in manifest["steps"]
    ]
    trace = manifest["context"].get("trace_classification") or {}
    trace_rows = [[key, str(value)] for key, value in trace.items()] if trace else [["-", "-"]]
    return "\n".join(
        [
            "# V1149 Android mdm_helper strace Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- module_zip: `{manifest['context']['module_zip']}`",
            f"- trace_tar: `{manifest['context']['trace_tar']}`",
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Trace Classification",
            "",
            markdown_table(["item", "value"], trace_rows),
            "",
            "## Guardrails",
            "",
            "- Magisk module only; no direct `/vendor` mutation.",
            "- No native `/dev/subsys_esoc0` retry or native eSoC ioctl.",
            "- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.",
            "- Native v724 rollback is part of the live plan.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_plan(args, store, execute=args.command == "run")
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision, context),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run" and decision not in {
            "v1149-handoff-module-not-ready",
            "v1149-handoff-missing-native-rollback",
            "v1149-handoff-missing-android-boot",
            "v1149-handoff-image-collision",
            "v1149-handoff-approval-required",
            "v1149-handoff-active-wifi-command-blocked",
        },
        "wifi_bringup_executed": False,
        "credential_use_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
