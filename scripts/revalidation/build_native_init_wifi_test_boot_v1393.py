#!/usr/bin/env python3
"""Build the V1393 rollbackable Wi-Fi test native-init boot artifact.

This is source/build-only tooling. It compiles the stock-kernel native PID1
with the V1393 test-boot hook enabled, rebuilds the execns helper from source,
bundles that helper into the ramdisk as /bin/a90_android_execns_probe, and
reuses the verified v724 boot image header/kernel metadata while replacing only
the ramdisk.

The generated artifact is for a later explicit flash/handoff gate. This script
does not contact the device and does not flash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from collections.abc import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
LINUX_INIT = REPO_ROOT / "stage3" / "linux_init"
HELPER_BUILD_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "build_android_execns_probe_helper.sh"
DEFAULT_BASE_BOOT = REPO_ROOT / "stage3" / "boot_linux_v724.img"
DEFAULT_INIT_SOURCE = LINUX_INIT / "init_v724.c"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1393-wifi-test-boot"
DEFAULT_INIT_VERSION = "0.9.69"
DEFAULT_INIT_BUILD = "v1393-wifitest"
DEFAULT_INIT_CREATOR = "made by device owner"
DEFAULT_CYCLE = "V1393"
DEFAULT_DECISION = "v1393-wifi-test-boot-source-build-pass"
DEFAULT_WIFI_TEST_LABEL = "v1393"
DEFAULT_WIFI_TEST_KLOG_PREFIX = "A90v1393"
DEFAULT_WIFI_TEST_LOG = "/cache/native-init-wifi-test-boot-v1393.log"
DEFAULT_WIFI_TEST_SUMMARY = "/cache/native-init-wifi-test-boot-v1393.summary"
DEFAULT_WIFI_TEST_HELPER_RESULT = "/cache/native-init-wifi-test-boot-v1393-helper.result"
DEFAULT_WIFI_TEST_PID = "/cache/native-init-wifi-test-boot-v1393.pid"
DEFAULT_WIFI_TEST_WATCHER_PID = "/cache/native-init-wifi-test-boot-v1393-watcher.pid"
DEFAULT_WIFI_TEST_WATCH_SEC = 35
DEFAULT_WIFI_TEST_SUPERVISOR_TIMEOUT_SEC = 40
DEFAULT_WIFI_TEST_HELPER_MODE = "post-pm-observer"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v288"
EXPECTED_HELPER_SHA256 = "ecc889253d8de7b8afdc09721ca780ea28d839fec00b5cb16380c6b7fd419c5b"
REPRODUCIBLE_MTIME = 0

FORBIDDEN_BYTES = (
    bytes([116, 101, 109, 109, 105, 101, 48, 50, 49, 52]),
    bytes([116, 101, 109, 109, 105, 101, 53, 71]),
)


def run(command: list[object], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + shlex.join(str(item) for item in command), flush=True)
    return subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pid1_sources() -> list[Path]:
    sources = [DEFAULT_INIT_SOURCE]
    for path in sorted(LINUX_INIT.glob("a90_*.c")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "int main(" in text or "int main (" in text:
            continue
        sources.append(path)
    return sources


def shell_define(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def helper_runtime_mode(args: argparse.Namespace) -> str:
    if args.wifi_test_helper_mode == "android-service-window-start-only":
        return "wifi-companion-android-wifi-service-window-start-only"
    if args.wifi_test_helper_mode == "android-service-window-subsys-trigger-capture":
        return "wifi-companion-android-wifi-service-window-subsys-trigger-capture"
    return "wifi-companion-post-pm-mdm-helper-esoc-observer"


def uses_android_service_window(args: argparse.Namespace) -> bool:
    return args.wifi_test_helper_mode in {
        "android-service-window-start-only",
        "android-service-window-subsys-trigger-capture",
    }


def build_helper(args: argparse.Namespace) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    run(["bash", HELPER_BUILD_SCRIPT, args.helper_binary])
    helper_sha = sha256(args.helper_binary)
    if helper_sha != EXPECTED_HELPER_SHA256:
        raise RuntimeError(
            f"helper sha mismatch: got {helper_sha}, expected {EXPECTED_HELPER_SHA256}"
        )
    strings = run(["strings", args.helper_binary], capture=True).stdout
    if EXPECTED_HELPER_MARKER not in strings:
        raise RuntimeError(f"missing helper marker: {EXPECTED_HELPER_MARKER}")


def build_init(args: argparse.Namespace) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    supervisor_flags = ["-DA90_WIFI_TEST_BOOT_SUPERVISE_HELPER=1"] if args.wifi_test_supervise_helper else []
    debugfs_flags = ["-DA90_WIFI_TEST_BOOT_MOUNT_DEBUGFS=1"] if args.wifi_test_mount_debugfs else []
    rc1_watcher_flags = (
        [
            "-DA90_WIFI_TEST_BOOT_PID1_RC1_WATCHER=1",
            f"-DA90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC={args.wifi_test_rc1_watcher_timeout_sec}",
            f"-DA90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS={args.wifi_test_rc1_watcher_delay_ms}",
            shell_define("A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT", args.wifi_test_rc1_watcher_result),
        ]
        if args.wifi_test_pid1_rc1_watcher
        else []
    )
    rc1_window_flags = (
        [
            "-DA90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER=1",
            shell_define("A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT", args.wifi_test_rc1_window_result),
        ]
        if args.wifi_test_rc1_window_sampler
        else []
    )
    rc1_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_endpoint_sampler
        else []
    )
    rc1_focused_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_focused_endpoint_sampler
        else []
    )
    rc1_immediate_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_immediate_endpoint_sampler
        else []
    )
    rc1_micro_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_micro_endpoint_sampler
        else []
    )
    rc1_micro_focused_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_micro_focused_endpoint_sampler
        else []
    )
    rc1_micro_batched_focused_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_micro_batched_focused_endpoint_sampler
        else []
    )
    rc1_micro_source_timestamped_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER=1"]
        if args.wifi_test_rc1_micro_source_timestamped_sampler
        else []
    )
    rc1_micro_critical_fast_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_micro_critical_fast_endpoint_sampler
        else []
    )
    rc1_case_aligned_micro_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_case_aligned_micro_endpoint_sampler
        else []
    )
    rc1_sysfs_client_enumerate_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE=1"]
        if args.wifi_test_rc1_sysfs_client_enumerate
        else []
    )
    provider_trigger_micro_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_provider_trigger_micro_endpoint_sampler
        else []
    )
    provider_trigger_exact_line_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE=1"]
        if args.wifi_test_provider_trigger_exact_line
        else []
    )
    provider_trigger_long_window_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW=1"]
        if args.wifi_test_provider_trigger_long_window
        else []
    )
    provider_trigger_thread_state_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE=1"]
        if args.wifi_test_provider_trigger_thread_state
        else []
    )
    provider_trigger_tracepoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER=1"]
        if args.wifi_test_provider_trigger_tracepoint_sampler
        else []
    )
    provider_trigger_pil_tracepoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER=1"]
        if args.wifi_test_provider_trigger_pil_tracepoint_sampler
        else []
    )
    provider_trigger_effective_level_flags = (
        ["-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER=1"]
        if args.wifi_test_provider_trigger_effective_level_sampler
        else []
    )
    provider_trigger_ap2mdm_hold_flags = (
        [
            "-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD=1",
            f"-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS={args.wifi_test_provider_trigger_ap2mdm_hold_after_ms}",
            f"-DA90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS={args.wifi_test_provider_trigger_ap2mdm_hold_ms}",
        ]
        if args.wifi_test_provider_trigger_ap2mdm_hold
        else []
    )
    auto_readiness_flags = (
        ["-DA90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR=1"]
        if args.wifi_test_auto_readiness_supervisor
        else []
    )
    service_window_flags: list[str] = []
    if uses_android_service_window(args):
        service_window_flags.append("-DA90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW=1")
    if args.wifi_test_helper_mode == "android-service-window-subsys-trigger-capture":
        service_window_flags.append("-DA90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE=1")
    rc1_retry_flags = []
    if args.wifi_test_rc1_retry_count > 0:
        rc1_retry_flags = [
            f"-DA90_WIFI_TEST_BOOT_RC1_RETRY_COUNT={args.wifi_test_rc1_retry_count}",
            f"-DA90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS={args.wifi_test_rc1_retry_delay_ms}",
        ]
    command = [
        args.cross_gcc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-DA90_WIFI_TEST_BOOT=1",
        shell_define("INIT_VERSION", args.init_version),
        shell_define("INIT_BUILD", args.init_build),
        shell_define("INIT_CREATOR", args.init_creator),
        shell_define("A90_WIFI_TEST_BOOT_LABEL", args.cycle_label),
        shell_define("A90_WIFI_TEST_BOOT_KLOG_PREFIX", args.wifi_test_klog_prefix),
        shell_define("A90_WIFI_TEST_BOOT_DISABLE", args.wifi_test_disable),
        shell_define("A90_WIFI_TEST_BOOT_LOG", args.wifi_test_log),
        shell_define("A90_WIFI_TEST_BOOT_SUMMARY", args.wifi_test_summary),
        shell_define("A90_WIFI_TEST_BOOT_HELPER_RESULT", args.wifi_test_helper_result),
        shell_define("A90_WIFI_TEST_BOOT_PID", args.wifi_test_pid),
        shell_define("A90_WIFI_TEST_BOOT_WATCHER_PID", args.wifi_test_watcher_pid),
        f"-DA90_WIFI_TEST_BOOT_WATCH_SEC={args.wifi_test_watch_sec}",
        f"-DA90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC={args.wifi_test_supervisor_timeout_sec}",
        *supervisor_flags,
        *debugfs_flags,
        *rc1_watcher_flags,
        *rc1_window_flags,
        *rc1_endpoint_flags,
        *rc1_focused_endpoint_flags,
        *rc1_immediate_endpoint_flags,
        *rc1_micro_endpoint_flags,
        *rc1_micro_focused_endpoint_flags,
        *rc1_micro_batched_focused_endpoint_flags,
        *rc1_micro_source_timestamped_flags,
        *rc1_micro_critical_fast_endpoint_flags,
        *rc1_case_aligned_micro_endpoint_flags,
        *rc1_sysfs_client_enumerate_flags,
        *provider_trigger_micro_endpoint_flags,
        *provider_trigger_exact_line_flags,
        *provider_trigger_long_window_flags,
        *provider_trigger_thread_state_flags,
        *provider_trigger_tracepoint_flags,
        *provider_trigger_pil_tracepoint_flags,
        *provider_trigger_effective_level_flags,
        *provider_trigger_ap2mdm_hold_flags,
        *auto_readiness_flags,
        *service_window_flags,
        *rc1_retry_flags,
        "-o",
        args.init_binary,
        *pid1_sources(),
    ]
    run(command)
    run([args.strip, args.init_binary])
    run(["file", args.init_binary])


def ramdisk_helpers(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "bin/a90sleep": LINUX_INIT / "a90_sleep",
        "bin/a90_cpustress": LINUX_INIT / "helpers" / "a90_cpustress",
        "bin/a90_longsoak": LINUX_INIT / "helpers" / "a90_longsoak",
        "bin/a90_rshell": LINUX_INIT / "helpers" / "a90_rshell",
        "bin/a90_tcpctl": (
            REPO_ROOT / "external_tools" / "userland" / "bin" / "a90_tcpctl-aarch64-static"
        ),
        "bin/a90_android_execns_probe": args.helper_binary,
    }


def build_ramdisk(args: argparse.Namespace) -> None:
    if args.ramdisk_dir.exists():
        shutil.rmtree(args.ramdisk_dir)
    (args.ramdisk_dir / "bin").mkdir(parents=True, mode=0o755)

    shutil.copy2(args.init_binary, args.ramdisk_dir / "init")
    helpers = ramdisk_helpers(args)
    for relative, source in helpers.items():
        destination = args.ramdisk_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for path in [args.ramdisk_dir / "init", *(args.ramdisk_dir / item for item in helpers)]:
        path.chmod(0o755)

    for path in sorted(args.ramdisk_dir.rglob("*"), key=lambda item: str(item), reverse=True):
        os.utime(path, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)
    os.utime(args.ramdisk_dir, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)

    if args.ramdisk_cpio.exists():
        args.ramdisk_cpio.unlink()
    command = "find . | LC_ALL=C sort | cpio -o -H newc > " + shlex.quote(str(args.ramdisk_cpio))
    run(["bash", "-lc", command], cwd=args.ramdisk_dir)
    args.ramdisk_cpio.chmod(0o600)


def build_boot_image(args: argparse.Namespace) -> None:
    with tempfile.TemporaryDirectory(prefix="a90-v1393-unpack-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_args = run(
            [
                "python3",
                REPO_ROOT / "mkbootimg" / "unpack_bootimg.py",
                "--boot_img",
                args.base_boot,
                "--out",
                temp_dir,
                "--format=mkbootimg",
            ],
            capture=True,
        ).stdout
        mkboot_args = shlex.split(unpack_args)

        for index, item in enumerate(mkboot_args):
            if item == "--ramdisk":
                mkboot_args[index + 1] = str(args.ramdisk_cpio)
                break
        else:
            raise RuntimeError("base boot image mkbootimg args did not include --ramdisk")

        if args.boot_image.exists():
            args.boot_image.unlink()
        run([
            "python3",
            REPO_ROOT / "mkbootimg" / "mkbootimg.py",
            *mkboot_args,
            "--output",
            args.boot_image,
        ])
    args.boot_image.chmod(0o600)


def verify_static(path: Path) -> None:
    dynamic = run(["aarch64-linux-gnu-readelf", "-d", path], capture=True).stdout
    if "There is no dynamic section" not in dynamic:
        raise RuntimeError(f"dynamic section found in {path}")
    program_headers = run(["aarch64-linux-gnu-readelf", "-l", path], capture=True).stdout
    if "INTERP" in program_headers:
        raise RuntimeError(f"INTERP segment found in {path}")


def verify_init_route_contract(args: argparse.Namespace) -> None:
    strings = run(["strings", args.init_binary], capture=True).stdout
    expected = [
        helper_runtime_mode(args),
    ]
    forbidden: list[str] = []
    if uses_android_service_window(args):
        expected.extend([
            "--allow-android-wifi-service-window",
        ])
        if args.wifi_test_helper_mode == "android-service-window-subsys-trigger-capture":
            expected.append("--allow-android-wifi-service-window-subsys-trigger-capture")
        forbidden.extend([
            "--allow-pm-service-trigger-observer",
            "--allow-post-pm-mdm-helper-esoc-observer",
            "--allow-post-pm-mdm-helper-lower-trace",
            "--pm-observer-continue-after-provider",
            "--pm-observer-start-cnss-after-provider",
            "--pm-observer-start-mdm-helper-after-cnss",
            "--pm-observer-start-mdm-helper-before-cnss",
            "--pm-observer-early-powerup-corrected-rc1-enumerate",
            "--pm-observer-private-cnss-daemon-sdx50m",
            "--private-cnss-daemon-path",
        ])
    else:
        expected.extend([
            "--allow-pm-service-trigger-observer",
            "--allow-post-pm-mdm-helper-esoc-observer",
            "--pm-observer-current-route-cnss-wlfw-precondition-summary",
        ])
        forbidden.extend([
            "--allow-android-wifi-service-window",
            "--allow-android-wifi-service-window-subsys-trigger-capture",
        ])
    missing = [marker for marker in expected if marker not in strings]
    if missing:
        raise RuntimeError("missing init route markers: " + ", ".join(missing))
    present_forbidden = [marker for marker in forbidden if marker in strings]
    if present_forbidden:
        raise RuntimeError("forbidden init route markers present: " + ", ".join(present_forbidden))


def verify_ramdisk(args: argparse.Namespace) -> None:
    listing = run(["bash", "-lc", f"cpio -it < {shlex.quote(str(args.ramdisk_cpio))}"], capture=True).stdout
    required = {
        "init",
        "bin/a90_android_execns_probe",
        "bin/a90_tcpctl",
        "bin/a90_rshell",
    }
    missing = sorted(item for item in required if item not in listing.splitlines())
    if missing:
        raise RuntimeError("missing ramdisk entries: " + ", ".join(missing))


def verify_markers(args: argparse.Namespace) -> None:
    strings = run(["strings", args.boot_image], capture=True).stdout
    expected = [
        f"A90 Linux init {args.init_version} ({args.init_build})",
        EXPECTED_HELPER_MARKER,
        args.wifi_test_klog_prefix,
        "wifi test boot armed",
        args.wifi_test_log,
        args.wifi_test_summary,
        args.wifi_test_pid,
        args.wifi_test_watcher_pid,
        "wifi-v1393-test-boot",
        "/bin/a90_android_execns_probe",
        helper_runtime_mode(args),
    ]
    if uses_android_service_window(args):
        expected.append("--allow-android-wifi-service-window")
        if args.wifi_test_helper_mode == "android-service-window-subsys-trigger-capture":
            expected.append("--allow-android-wifi-service-window-subsys-trigger-capture")
    else:
        expected.append("--allow-post-pm-mdm-helper-esoc-observer")
    if args.wifi_test_mount_debugfs:
        expected.extend([
            "debugfs_mount_requested",
            "debugfs prepare rc=",
        ])
        if not args.wifi_test_rc1_sysfs_client_enumerate:
            expected.append("/sys/kernel/debug/pci-msm/case")
    if args.wifi_test_pid1_rc1_watcher:
        expected.extend([
            "pid1_rc1_watcher_requested",
            "pid1 rc1 watcher",
            args.wifi_test_rc1_watcher_result,
            "delay_ms=%d",
            "/dev/kmsg",
            "/proc/kmsg",
        ])
        if not args.wifi_test_rc1_sysfs_client_enumerate:
            expected.append("/sys/kernel/debug/pci-msm/rc_sel")
    if args.wifi_test_rc1_window_sampler:
        sampler_marker = (
            "auto-v1485-wifi-readiness-test"
            if args.wifi_test_auto_readiness_supervisor
            else
            "bounded-v1477-ap2mdm-hold-test"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
                and args.wifi_test_provider_trigger_effective_level_sampler
                and args.wifi_test_provider_trigger_ap2mdm_hold
            )
            else
            "read-only-v1472-exact-provider-effective-level"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
                and args.wifi_test_provider_trigger_effective_level_sampler
            )
            else
            "read-only-v1467-exact-provider-pil-gpio-tracepoint"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
            )
            else
            "read-only-v1462-exact-provider-tracepoint"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
            )
            else
            "read-only-v1458-exact-provider-thread-state"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
            )
            else
            "read-only-v1454-exact-provider-long-endpoint"
            if (
                args.wifi_test_provider_trigger_micro_endpoint_sampler
                and args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
            )
            else
            "read-only-v1450-provider-trigger-micro-endpoint"
            if args.wifi_test_provider_trigger_micro_endpoint_sampler
            else
            "read-only-v1445-case-aligned-micro-endpoint"
            if args.wifi_test_rc1_case_aligned_micro_endpoint_sampler
            else
            "read-only-v1441-micro-endpoint"
            if args.wifi_test_rc1_micro_endpoint_sampler
            else
            "read-only-v1437-immediate-endpoint"
            if args.wifi_test_rc1_immediate_endpoint_sampler
            else
            "read-only-v1433-focused-endpoint-prereq"
            if args.wifi_test_rc1_focused_endpoint_sampler
            else
            "read-only-v1429-endpoint-prereq"
            if args.wifi_test_rc1_endpoint_sampler
            else "read-only-v1420"
        )
        expected.extend([
            "rc1_window_sampler_requested",
            "rc1_window_sample label=%s",
            sampler_marker,
            args.wifi_test_rc1_window_result,
            "/proc/interrupts",
            "/sys/kernel/debug/gpio",
            "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
        ])
    if args.wifi_test_rc1_endpoint_sampler:
        expected.extend([
            "endpoint_sampler=1",
            "pcie_1_gdsc",
            "gpio103",
            "/sys/kernel/debug/regulator/regulator_summary",
            "/sys/kernel/debug/clk/clk_summary",
            "current_link_state",
        ])
    if args.wifi_test_rc1_focused_endpoint_sampler:
        expected.extend([
            "focused_regulator",
            "focused_clk",
            "focused_debug_gpio",
            "focused_pinmux",
            "focused_pinconf",
            "sample=%s source=%s needle=%s match=%s",
            "gcc_pcie_1_pipe_clk",
            "gpio142",
        ])
    if args.wifi_test_rc1_immediate_endpoint_sampler:
        expected.extend([
            "rc1_immediate_endpoint_sampler_requested",
            "read-only-v1437-immediate-endpoint",
            "rc1_immediate_sample label=%s",
            "immediate_endpoint_sampler=1",
            "immediate_regulator",
            "immediate_clk",
            "immediate_debug_gpio",
            "immediate_pinmux",
            "immediate_pinconf",
            "after_case_0ms",
            "after_case_20ms",
        ])
    if args.wifi_test_rc1_micro_endpoint_sampler:
        expected.extend([
            "rc1_micro_endpoint_sampler_requested",
            "rc1_micro_sample label=%s",
            "micro_endpoint_sampler=1",
            "micro_interrupts",
            "micro_debug_gpio",
            "micro_pcie1_current_link_state",
        ])
        if not args.wifi_test_provider_trigger_micro_endpoint_sampler:
            expected.extend([
                "micro_writer rc=%d",
                "rc1_micro_writer_summary",
            ])
        if (
            not args.wifi_test_rc1_case_aligned_micro_endpoint_sampler
            and not args.wifi_test_provider_trigger_micro_endpoint_sampler
        ):
            expected.extend([
                "read-only-v1441-micro-endpoint",
                "micro_after_case_%dms",
                "post_micro_200ms",
            ])
    if args.wifi_test_rc1_micro_focused_endpoint_sampler:
        expected.extend([
            "rc1_micro_focused_endpoint_sampler_requested",
            "micro_focused_endpoint_sampler=1",
            "micro_focused_regulator",
            "micro_focused_clk",
            "micro_focused_debug_gpio",
            "micro_focused_pinmux",
            "micro_focused_pinconf",
            "gcc_pcie_1_pipe_clk",
            "pcie_1_gdsc",
            "gpio135",
        ])
    if args.wifi_test_rc1_micro_batched_focused_endpoint_sampler:
        expected.extend([
            "rc1_micro_batched_focused_endpoint_sampler_requested",
            "micro_batched_focused_endpoint_sampler=1",
            "micro_batched_regulator",
            "micro_batched_clk",
            "micro_batched_debug_gpio",
            "micro_batched_pinmux",
            "micro_batched_pinconf",
            "gcc_pcie_1_pipe_clk",
            "pcie_1_gdsc",
            "gpio135",
        ])
    if args.wifi_test_rc1_micro_source_timestamped_sampler:
        expected.extend([
            "rc1_micro_source_timestamped_sampler_requested",
            "micro_source_timestamped_sampler=1",
            "source_timing=%s",
            "source_duration_ms=%ld",
        ])
    if args.wifi_test_rc1_micro_critical_fast_endpoint_sampler:
        expected.extend([
            "rc1_micro_critical_fast_endpoint_sampler_requested",
            "micro_critical_fast_endpoint_sampler=1",
            "micro_critical_regulator",
            "micro_critical_pinmux",
            "micro_critical_clk_summary_skipped=1",
            "clk_summary-too-slow-for-pre-l0-window",
        ])
    if args.wifi_test_rc1_case_aligned_micro_endpoint_sampler:
        expected.extend([
            "rc1_case_aligned_micro_endpoint_sampler_requested",
            "case_aligned_micro_after_case_%dms",
            "post_case_aligned_micro_200ms",
        ])
        if not args.wifi_test_auto_readiness_supervisor:
            expected.append("read-only-v1445-case-aligned-micro-endpoint")
    if args.wifi_test_rc1_sysfs_client_enumerate:
        expected.extend([
            "sysfs_client_enumerate",
            "sysfs_client_enumerate=%d",
            "trigger_mode=%s",
            "sysfs_path=%s",
            "/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate",
        ])
    if args.wifi_test_provider_trigger_micro_endpoint_sampler:
        expected.extend([
            "provider_trigger_micro_endpoint_sampler_requested",
            "read-only-v1454-exact-provider-long-endpoint"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and not args.wifi_test_provider_trigger_thread_state
            )
            else
            "bounded-v1477-ap2mdm-hold-test"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
                and args.wifi_test_provider_trigger_effective_level_sampler
                and args.wifi_test_provider_trigger_ap2mdm_hold
            )
            else
            "read-only-v1472-exact-provider-effective-level"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
                and args.wifi_test_provider_trigger_effective_level_sampler
            )
            else
            "read-only-v1462-exact-provider-tracepoint"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and not args.wifi_test_provider_trigger_pil_tracepoint_sampler
            )
            else
            "read-only-v1467-exact-provider-pil-gpio-tracepoint"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
                and args.wifi_test_provider_trigger_tracepoint_sampler
                and args.wifi_test_provider_trigger_pil_tracepoint_sampler
            )
            else
            "read-only-v1458-exact-provider-thread-state"
            if (
                args.wifi_test_provider_trigger_exact_line
                and args.wifi_test_provider_trigger_long_window
                and args.wifi_test_provider_trigger_thread_state
            )
            else "read-only-v1450-provider-trigger-micro-endpoint",
            "provider_micro_after_trigger_%dms",
            "exact_provider_line=%d",
            "long_provider_window=%d",
            "post_provider_micro_1200ms"
            if args.wifi_test_provider_trigger_long_window
            else "post_provider_micro_200ms",
        ])
        if args.wifi_test_provider_trigger_thread_state:
            expected.extend([
                "provider_thread_state label=%s",
                "provider_thread_state=1",
                "provider_thread_comm",
                "provider_thread_wchan",
                "provider_thread_status",
                "/proc/%d/wchan",
            ])
        if args.wifi_test_provider_trigger_tracepoint_sampler:
            expected.extend([
                "provider_trigger_tracepoint_sampler_requested",
                "tracepoint_sampler=%d",
                "provider tracepoint arm",
                "provider tracepoint disarm",
                "provider_tracepoint_sample label=%s",
                "/sys/kernel/debug/tracing/events/gpio/gpio_value/enable",
                "/sys/kernel/debug/tracing/events/gpio/gpio_direction/enable",
                "gpio_value: 1270",
                "gpio_direction: 135",
            ])
            if args.wifi_test_provider_trigger_pil_tracepoint_sampler:
                expected.extend([
                    "provider_trigger_pil_tracepoint_sampler_requested",
                    "pil_tracepoint_sampler=%d",
                    "provider_pil_gpio_trace",
                    "/sys/kernel/debug/tracing/events/msm_pil_event/pil_notif/enable",
                    "pil_notif:",
                    "fw=esoc0",
                    "pil_notif_rc=%d",
                ])
            else:
                expected.append("provider_gpio_trace")
        if args.wifi_test_provider_trigger_effective_level_sampler:
            expected.append("provider_trigger_effective_level_sampler_requested")
            if not args.wifi_test_provider_trigger_ap2mdm_hold:
                expected.append("read-only-v1472-exact-provider-effective-level")
    if args.wifi_test_provider_trigger_ap2mdm_hold:
        expected.extend([
            "bounded-v1477-ap2mdm-hold-test",
            "provider_trigger_ap2mdm_hold_requested",
            "provider_trigger_ap2mdm_hold_after_ms",
            "provider_trigger_ap2mdm_hold_ms",
            "ap2mdm_hold gate_sample=%s",
            "ap2mdm_hold attempt export_rc=%d",
            "ap2mdm_hold cleanup release_rc=%d",
            "ap2mdm_hold summary attempted=%d",
            "/sys/class/gpio/export",
            "/sys/class/gpio/gpio135/direction",
            "/sys/class/gpio/gpio135/value",
            "/sys/class/gpio/unexport",
            "ap2mdm_hold_after_high_0ms",
            "ap2mdm_hold_after_release",
        ])
    if args.wifi_test_auto_readiness_supervisor:
        expected.extend([
            "auto-v1485-wifi-readiness-test",
            "auto_readiness_supervisor_requested",
            "auto_readiness_pid1.begin=1",
            "auto_readiness_pid1.primary_checkpoint=%s",
            "--pm-observer-auto-readiness-summary",
            "auto_readiness.begin=1",
            "auto_readiness.primary_checkpoint=%s",
            "auto_readiness.safety_credentials=0",
        ])
    if args.wifi_test_rc1_retry_count > 0:
        expected.extend([
            "retry_count=%d",
            "retry_delay_ms=%d",
            "rc1_retry_count",
            "pid1 rc1 watcher retry index=%d",
        ])
    missing = [marker for marker in expected if marker not in strings]
    if missing:
        raise RuntimeError("missing boot image markers: " + ", ".join(missing))


def verify_no_forbidden(paths: list[Path]) -> None:
    hits: list[str] = []
    for path in paths:
        data = path.read_bytes()
        if any(needle in data for needle in FORBIDDEN_BYTES):
            hits.append(str(path))
    if hits:
        raise RuntimeError("forbidden credential-like bytes found in: " + ", ".join(hits))


def write_manifest(args: argparse.Namespace) -> None:
    manifest: dict[str, Any] = {
        "cycle": args.cycle,
        "decision": args.decision,
        "base_boot": str(args.base_boot.relative_to(REPO_ROOT)),
        "init_version": args.init_version,
        "init_build": args.init_build,
        "helper_marker": EXPECTED_HELPER_MARKER,
        "helper_sha256": sha256(args.helper_binary),
        "wifi_test": {
            "label": args.cycle_label,
            "log": args.wifi_test_log,
            "summary": args.wifi_test_summary,
            "helper_result": args.wifi_test_helper_result,
            "pid": args.wifi_test_pid,
            "watcher_pid": args.wifi_test_watcher_pid,
            "watch_sec": args.wifi_test_watch_sec,
            "fresh_log": True,
            "summary_watcher": True,
            "supervise_helper": args.wifi_test_supervise_helper,
            "supervisor_timeout_sec": args.wifi_test_supervisor_timeout_sec,
            "helper_mode": args.wifi_test_helper_mode,
            "helper_runtime_mode": helper_runtime_mode(args),
            "android_service_window": uses_android_service_window(args),
            "scan_connect_credentials": False,
            "mount_debugfs": args.wifi_test_mount_debugfs,
            "pid1_rc1_watcher": args.wifi_test_pid1_rc1_watcher,
            "rc1_watcher_timeout_sec": args.wifi_test_rc1_watcher_timeout_sec,
            "rc1_watcher_delay_ms": args.wifi_test_rc1_watcher_delay_ms,
            "rc1_watcher_result": args.wifi_test_rc1_watcher_result,
            "rc1_window_sampler": args.wifi_test_rc1_window_sampler,
            "rc1_window_result": args.wifi_test_rc1_window_result,
            "rc1_endpoint_sampler": args.wifi_test_rc1_endpoint_sampler,
            "rc1_focused_endpoint_sampler": args.wifi_test_rc1_focused_endpoint_sampler,
            "rc1_immediate_endpoint_sampler": args.wifi_test_rc1_immediate_endpoint_sampler,
            "rc1_micro_endpoint_sampler": args.wifi_test_rc1_micro_endpoint_sampler,
            "rc1_micro_focused_endpoint_sampler": args.wifi_test_rc1_micro_focused_endpoint_sampler,
            "rc1_micro_batched_focused_endpoint_sampler": args.wifi_test_rc1_micro_batched_focused_endpoint_sampler,
            "rc1_micro_source_timestamped_sampler": args.wifi_test_rc1_micro_source_timestamped_sampler,
            "rc1_micro_critical_fast_endpoint_sampler": args.wifi_test_rc1_micro_critical_fast_endpoint_sampler,
            "rc1_case_aligned_micro_endpoint_sampler": args.wifi_test_rc1_case_aligned_micro_endpoint_sampler,
            "rc1_sysfs_client_enumerate": args.wifi_test_rc1_sysfs_client_enumerate,
            "provider_trigger_micro_endpoint_sampler": args.wifi_test_provider_trigger_micro_endpoint_sampler,
            "provider_trigger_exact_line": args.wifi_test_provider_trigger_exact_line,
            "provider_trigger_long_window": args.wifi_test_provider_trigger_long_window,
            "provider_trigger_thread_state": args.wifi_test_provider_trigger_thread_state,
            "provider_trigger_tracepoint_sampler": args.wifi_test_provider_trigger_tracepoint_sampler,
            "provider_trigger_pil_tracepoint_sampler": args.wifi_test_provider_trigger_pil_tracepoint_sampler,
            "provider_trigger_effective_level_sampler": args.wifi_test_provider_trigger_effective_level_sampler,
            "provider_trigger_ap2mdm_hold": args.wifi_test_provider_trigger_ap2mdm_hold,
            "provider_trigger_ap2mdm_hold_after_ms": args.wifi_test_provider_trigger_ap2mdm_hold_after_ms,
            "provider_trigger_ap2mdm_hold_ms": args.wifi_test_provider_trigger_ap2mdm_hold_ms,
            "auto_readiness_supervisor": args.wifi_test_auto_readiness_supervisor,
            "rc1_retry_count": args.wifi_test_rc1_retry_count,
            "rc1_retry_delay_ms": args.wifi_test_rc1_retry_delay_ms,
        },
        "init_binary": str(args.init_binary.relative_to(REPO_ROOT)),
        "init_sha256": sha256(args.init_binary),
        "ramdisk_cpio": str(args.ramdisk_cpio.relative_to(REPO_ROOT)),
        "ramdisk_sha256": sha256(args.ramdisk_cpio),
        "boot_image": str(args.boot_image.relative_to(REPO_ROOT)),
        "boot_sha256": sha256(args.boot_image),
        "safety": {
            "device_command": False,
            "flash": False,
            "partition_write": False,
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_external_ping": False,
        },
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.manifest.chmod(0o600)


def resolve_args(args: argparse.Namespace) -> argparse.Namespace:
    args.out_dir = args.out_dir.resolve()
    args.base_boot = args.base_boot.resolve()
    args.init_binary = args.init_binary.resolve()
    args.helper_binary = args.helper_binary.resolve()
    args.ramdisk_dir = args.ramdisk_dir.resolve()
    args.ramdisk_cpio = args.ramdisk_cpio.resolve()
    args.boot_image = args.boot_image.resolve()
    args.manifest = args.manifest.resolve()
    if uses_android_service_window(args):
        incompatible = {
            "wifi_test_mount_debugfs": args.wifi_test_mount_debugfs,
            "wifi_test_pid1_rc1_watcher": args.wifi_test_pid1_rc1_watcher,
            "wifi_test_rc1_window_sampler": args.wifi_test_rc1_window_sampler,
            "wifi_test_rc1_endpoint_sampler": args.wifi_test_rc1_endpoint_sampler,
            "wifi_test_rc1_focused_endpoint_sampler": args.wifi_test_rc1_focused_endpoint_sampler,
            "wifi_test_rc1_immediate_endpoint_sampler": args.wifi_test_rc1_immediate_endpoint_sampler,
            "wifi_test_rc1_micro_endpoint_sampler": args.wifi_test_rc1_micro_endpoint_sampler,
            "wifi_test_rc1_micro_focused_endpoint_sampler": args.wifi_test_rc1_micro_focused_endpoint_sampler,
            "wifi_test_rc1_micro_batched_focused_endpoint_sampler": args.wifi_test_rc1_micro_batched_focused_endpoint_sampler,
            "wifi_test_rc1_micro_source_timestamped_sampler": args.wifi_test_rc1_micro_source_timestamped_sampler,
            "wifi_test_rc1_micro_critical_fast_endpoint_sampler": args.wifi_test_rc1_micro_critical_fast_endpoint_sampler,
            "wifi_test_rc1_case_aligned_micro_endpoint_sampler": args.wifi_test_rc1_case_aligned_micro_endpoint_sampler,
            "wifi_test_rc1_sysfs_client_enumerate": args.wifi_test_rc1_sysfs_client_enumerate,
            "wifi_test_provider_trigger_micro_endpoint_sampler": args.wifi_test_provider_trigger_micro_endpoint_sampler,
            "wifi_test_provider_trigger_exact_line": args.wifi_test_provider_trigger_exact_line,
            "wifi_test_provider_trigger_long_window": args.wifi_test_provider_trigger_long_window,
            "wifi_test_provider_trigger_thread_state": args.wifi_test_provider_trigger_thread_state,
            "wifi_test_provider_trigger_tracepoint_sampler": args.wifi_test_provider_trigger_tracepoint_sampler,
            "wifi_test_provider_trigger_pil_tracepoint_sampler": args.wifi_test_provider_trigger_pil_tracepoint_sampler,
            "wifi_test_provider_trigger_effective_level_sampler": args.wifi_test_provider_trigger_effective_level_sampler,
            "wifi_test_provider_trigger_ap2mdm_hold": args.wifi_test_provider_trigger_ap2mdm_hold,
            "wifi_test_auto_readiness_supervisor": args.wifi_test_auto_readiness_supervisor,
            "wifi_test_rc1_retry_count": args.wifi_test_rc1_retry_count > 0,
        }
        enabled = [key for key, value in incompatible.items() if value]
        if enabled:
            raise RuntimeError(
                "Android service-window route must not combine RC1/provider/auto-readiness options: "
                + ", ".join(enabled)
            )
    return args


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-gcc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cycle", default=DEFAULT_CYCLE)
    parser.add_argument("--decision", default=DEFAULT_DECISION)
    parser.add_argument("--cycle-label", default=DEFAULT_WIFI_TEST_LABEL)
    parser.add_argument("--init-version", default=DEFAULT_INIT_VERSION)
    parser.add_argument("--init-build", default=DEFAULT_INIT_BUILD)
    parser.add_argument("--init-creator", default=DEFAULT_INIT_CREATOR)
    parser.add_argument("--wifi-test-klog-prefix", default=DEFAULT_WIFI_TEST_KLOG_PREFIX)
    parser.add_argument("--wifi-test-disable", default="/cache/native-init-wifi-test-boot-v1393.disable")
    parser.add_argument("--wifi-test-log", default=DEFAULT_WIFI_TEST_LOG)
    parser.add_argument("--wifi-test-summary", default=DEFAULT_WIFI_TEST_SUMMARY)
    parser.add_argument("--wifi-test-helper-result", default=DEFAULT_WIFI_TEST_HELPER_RESULT)
    parser.add_argument("--wifi-test-pid", default=DEFAULT_WIFI_TEST_PID)
    parser.add_argument("--wifi-test-watcher-pid", default=DEFAULT_WIFI_TEST_WATCHER_PID)
    parser.add_argument("--wifi-test-watch-sec", type=int, default=DEFAULT_WIFI_TEST_WATCH_SEC)
    parser.add_argument("--wifi-test-supervise-helper", action="store_true")
    parser.add_argument("--wifi-test-supervisor-timeout-sec", type=int, default=DEFAULT_WIFI_TEST_SUPERVISOR_TIMEOUT_SEC)
    parser.add_argument(
        "--wifi-test-helper-mode",
        choices=[
            "post-pm-observer",
            "android-service-window-start-only",
            "android-service-window-subsys-trigger-capture",
        ],
        default=DEFAULT_WIFI_TEST_HELPER_MODE,
    )
    parser.add_argument("--wifi-test-mount-debugfs", action="store_true")
    parser.add_argument("--wifi-test-pid1-rc1-watcher", action="store_true")
    parser.add_argument("--wifi-test-rc1-watcher-timeout-sec", type=int, default=45)
    parser.add_argument("--wifi-test-rc1-watcher-delay-ms", type=int, default=0)
    parser.add_argument(
        "--wifi-test-rc1-watcher-result",
        default="/cache/native-init-wifi-test-boot-v1393-rc1-watcher.result",
    )
    parser.add_argument("--wifi-test-rc1-window-sampler", action="store_true")
    parser.add_argument(
        "--wifi-test-rc1-window-result",
        default="/cache/native-init-wifi-test-boot-v1393-rc1-window.result",
    )
    parser.add_argument("--wifi-test-rc1-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-focused-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-immediate-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-micro-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-micro-focused-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-micro-batched-focused-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-micro-source-timestamped-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-micro-critical-fast-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-case-aligned-micro-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-rc1-sysfs-client-enumerate", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-micro-endpoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-exact-line", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-long-window", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-thread-state", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-tracepoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-pil-tracepoint-sampler", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-effective-level-sampler", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-ap2mdm-hold", action="store_true")
    parser.add_argument("--wifi-test-provider-trigger-ap2mdm-hold-after-ms", type=int, default=320)
    parser.add_argument("--wifi-test-provider-trigger-ap2mdm-hold-ms", type=int, default=500)
    parser.add_argument("--wifi-test-auto-readiness-supervisor", action="store_true")
    parser.add_argument("--wifi-test-rc1-retry-count", type=int, default=0)
    parser.add_argument("--wifi-test-rc1-retry-delay-ms", type=int, default=0)
    parser.add_argument("--init-binary", type=Path)
    parser.add_argument("--helper-binary", type=Path)
    parser.add_argument("--ramdisk-dir", type=Path)
    parser.add_argument("--ramdisk-cpio", type=Path)
    parser.add_argument("--boot-image", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)

    args.init_binary = args.init_binary or args.out_dir / "init_v1393_wifi_test"
    args.helper_binary = args.helper_binary or args.out_dir / "a90_android_execns_probe_v288"
    args.ramdisk_dir = args.ramdisk_dir or args.out_dir / "ramdisk"
    args.ramdisk_cpio = args.ramdisk_cpio or args.out_dir / "ramdisk_v1393_wifi_test.cpio"
    args.boot_image = args.boot_image or args.out_dir / "boot_linux_v1393_wifi_test.img"
    args.manifest = args.manifest or args.out_dir / "manifest.json"
    return resolve_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    build_helper(args)
    build_init(args)
    verify_static(args.init_binary)
    verify_static(args.helper_binary)
    verify_init_route_contract(args)
    build_ramdisk(args)
    verify_ramdisk(args)
    build_boot_image(args)
    verify_markers(args)
    verify_no_forbidden([args.init_binary, args.helper_binary, args.ramdisk_cpio, args.boot_image])
    write_manifest(args)
    print(f"manifest={args.manifest}")
    print(f"init_sha256={sha256(args.init_binary)}")
    print(f"helper_sha256={sha256(args.helper_binary)}")
    print(f"ramdisk_sha256={sha256(args.ramdisk_cpio)}")
    print(f"boot_sha256={sha256(args.boot_image)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
