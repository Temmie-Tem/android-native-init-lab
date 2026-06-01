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
DEFAULT_WIFI_TEST_PID = "/cache/native-init-wifi-test-boot-v1393.pid"
DEFAULT_WIFI_TEST_WATCHER_PID = "/cache/native-init-wifi-test-boot-v1393-watcher.pid"
DEFAULT_WIFI_TEST_WATCH_SEC = 35
DEFAULT_WIFI_TEST_SUPERVISOR_TIMEOUT_SEC = 40
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v286"
EXPECTED_HELPER_SHA256 = "e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f"
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
    rc1_case_aligned_micro_endpoint_flags = (
        ["-DA90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER=1"]
        if args.wifi_test_rc1_case_aligned_micro_endpoint_sampler
        else []
    )
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
        *rc1_case_aligned_micro_endpoint_flags,
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
    ]
    if args.wifi_test_mount_debugfs:
        expected.extend([
            "debugfs_mount_requested",
            "debugfs prepare rc=",
            "/sys/kernel/debug/pci-msm/case",
        ])
    if args.wifi_test_pid1_rc1_watcher:
        expected.extend([
            "pid1_rc1_watcher_requested",
            "pid1 rc1 watcher",
            args.wifi_test_rc1_watcher_result,
            "delay_ms=%d",
            "/dev/kmsg",
            "/proc/kmsg",
            "/sys/kernel/debug/pci-msm/rc_sel",
        ])
    if args.wifi_test_rc1_window_sampler:
        sampler_marker = (
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
            "micro_writer rc=%d",
            "rc1_micro_writer_summary",
        ])
        if not args.wifi_test_rc1_case_aligned_micro_endpoint_sampler:
            expected.extend([
                "read-only-v1441-micro-endpoint",
                "micro_after_case_%dms",
                "post_micro_200ms",
            ])
    if args.wifi_test_rc1_case_aligned_micro_endpoint_sampler:
        expected.extend([
            "rc1_case_aligned_micro_endpoint_sampler_requested",
            "read-only-v1445-case-aligned-micro-endpoint",
            "case_aligned_micro_after_case_%dms",
            "post_case_aligned_micro_200ms",
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
            "pid": args.wifi_test_pid,
            "watcher_pid": args.wifi_test_watcher_pid,
            "watch_sec": args.wifi_test_watch_sec,
            "fresh_log": True,
            "summary_watcher": True,
            "supervise_helper": args.wifi_test_supervise_helper,
            "supervisor_timeout_sec": args.wifi_test_supervisor_timeout_sec,
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
            "rc1_case_aligned_micro_endpoint_sampler": args.wifi_test_rc1_case_aligned_micro_endpoint_sampler,
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
    parser.add_argument("--wifi-test-pid", default=DEFAULT_WIFI_TEST_PID)
    parser.add_argument("--wifi-test-watcher-pid", default=DEFAULT_WIFI_TEST_WATCHER_PID)
    parser.add_argument("--wifi-test-watch-sec", type=int, default=DEFAULT_WIFI_TEST_WATCH_SEC)
    parser.add_argument("--wifi-test-supervise-helper", action="store_true")
    parser.add_argument("--wifi-test-supervisor-timeout-sec", type=int, default=DEFAULT_WIFI_TEST_SUPERVISOR_TIMEOUT_SEC)
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
    parser.add_argument("--wifi-test-rc1-case-aligned-micro-endpoint-sampler", action="store_true")
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
    args.helper_binary = args.helper_binary or args.out_dir / "a90_android_execns_probe_v286"
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
