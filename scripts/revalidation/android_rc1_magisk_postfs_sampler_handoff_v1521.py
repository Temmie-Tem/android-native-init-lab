#!/usr/bin/env python3
"""V1521 bounded Android handoff with temporary Magisk post-fs-data sampler.

The runner installs a temporary read-only Magisk module while the device is in
recovery, boots Android, lets the module sample early RC1-critical sources from
post-fs-data, pulls the evidence, removes the module from recovery, and restores
the native v724 boot image.

The module writes only under `/data/local/tmp/a90-v1521-rc1-postfs-sampler` and
the recovery cleanup removes only `/data/adb/modules/a90_v1521_rc1_sampler` plus
that bounded evidence directory after it has been pulled. It does not enable
Wi-Fi, scan/connect, handle credentials, run DHCP/routes, ping externally,
write PMIC/GPIO/GDSC/eSoC state, issue eSoC notify/BOOT_DONE, rescan PCI, or
bind/unbind platforms.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text
from android_hwservice_handoff_v424 import (
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_REMOTE_ANDROID_IMAGE,
    StepResult,
    adb_base,
    execute_bridge_step,
    execute_step,
    image_context,
    reason_for as v424_reason_for,
    require_approval,
    step_text,
    wait_for_adb_state,
    write_step,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v1521-android-rc1-magisk-postfs-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1521_ANDROID_RC1_MAGISK_POSTFS_HANDOFF_2026-06-01.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1521-android-rc1-magisk-postfs-handoff.txt")
MODULE_NAME = "a90_v1521_rc1_sampler"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1521-rc1-postfs-sampler"
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")
DMESG_FILTER_RE = re.compile(
    r"subsys-restart|__subsystem_get|subsys_esoc0|subsys_modem|mdm_subsys_powerup|"
    r"esoc0|SDX50M|ap2mdm|mdm2ap|GPIO 135|GPIO135|GPIO 142|GPIO142|mdm status|"
    r"msm_pcie|PCIe|RC1|LTSSM|MHI|mhi|mhi_0305_01\.01\.00_pipe_10|\bks\b|"
    r"icnss|wlfw|BDF file|regdb\.bin|bdwlan\.bin|FW ready|WLAN FW is ready|wlan0",
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
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=360)
    parser.add_argument("--sampler-samples", type=int, default=90)
    parser.add_argument("--sampler-delay-us", type=int, default=50000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=90)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def remote_quote(path: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"remote path must be absolute: {path}")
    return shlex.quote(path)


def module_stage_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "magisk-module"


def pulled_evidence_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "android-postfs-evidence"


def post_fs_data_script(samples: int, delay_us: int) -> str:
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
SAMPLES={samples}
DELAY_US={delay_us}
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
LOG="$OUT/samples.log"
STATUS="$OUT/status.txt"
DMSG="$OUT/dmesg-filtered.txt"
PROPS="$OUT/props.txt"
dump_filtered_dmesg() {{
  dmesg 2>&1 | grep -Ei 'subsys-restart|__subsystem_get|subsys_esoc0|subsys_modem|mdm_subsys_powerup|esoc0|SDX50M|ap2mdm|mdm2ap|GPIO 135|GPIO135|GPIO 142|GPIO142|mdm status|msm_pcie|PCIe|RC1|LTSSM|MHI|mhi|mhi_0305_01\\.01\\.00_pipe_10|\\bks\\b|icnss|wlfw|BDF file|regdb\\.bin|bdwlan\\.bin|FW ready|WLAN FW is ready|wlan0' > "$DMSG.tmp"
  mv "$DMSG.tmp" "$DMSG" 2>/dev/null || true
}}
dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.per_proxy init.svc.vendor.mdm_helper init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.per_proxy ro.boottime.vendor.mdm_helper ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}
(
  echo "A90_V1521_STATUS start $(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')" > "$STATUS"
  : > "$DMSG"
  : > "$PROPS"
  echo A90_V1521_POSTFS_SAMPLER_BEGIN > "$LOG"
  i=0
  while [ "$i" -lt "$SAMPLES" ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    echo "A90_V1521_STATUS sample $i $uptime" > "$STATUS"
    echo "A90_V1521_SAMPLE_BEGIN index=$i uptime=$uptime" >> "$LOG"
    echo "SRC interrupts" >> "$LOG"
    cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +142|msmgpio-dc +104|mdm status|msm_pcie_wake|mhi|pcie' >> "$LOG" 2>/dev/null || true
    echo "SRC debug_gpio" >> "$LOG"
    if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio >> "$LOG" 2>/dev/null || true; else echo unreadable >> "$LOG"; fi
    echo "SRC pcie_state" >> "$LOG"
    for f in \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/link_state \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/power/runtime_status \\
      /sys/devices/platform/soc/1c08000.qcom,pcie/power/control; do
      [ -e "$f" ] && {{ printf 'FILE %s=' "$f" >> "$LOG"; cat "$f" >> "$LOG" 2>&1; printf '\\n' >> "$LOG"; }}
    done
    if [ "$((i % 5))" = "0" ]; then
      echo "SRC regulator" >> "$LOG"
      if [ -r /sys/kernel/debug/regulator/regulator_summary ]; then grep -Ei 'pcie_1_gdsc|pcie_0_gdsc|pm8150_l5|pm8150l_l3' /sys/kernel/debug/regulator/regulator_summary >> "$LOG" 2>/dev/null || true; else echo unreadable >> "$LOG"; fi
    fi
    if [ "$((i % 10))" = "0" ]; then
      echo "SRC pinmux" >> "$LOG"
      for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
        [ -r "$f" ] || continue
        grep -Ei 'pin 102 |pin 103 |pin 104 |pin 135 |pin 142 ' "$f" >> "$LOG" 2>/dev/null || true
      done
    fi
    if [ "$((i % 5))" = "0" ]; then
      dump_filtered_dmesg
      dump_props
      chmod 755 "$OUT" 2>/dev/null
      chmod 644 "$OUT"/* 2>/dev/null
    fi
    echo "A90_V1521_SAMPLE_END index=$i uptime=$uptime" >> "$LOG"
    i=$((i + 1))
    if command -v usleep >/dev/null 2>&1; then usleep "$DELAY_US"; else sleep 1; fi
  done
  echo A90_V1521_POSTFS_SAMPLER_END >> "$LOG"
  dump_filtered_dmesg
  dump_props
  echo "A90_V1521_STATUS done $(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')" >> "$STATUS"
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def module_prop() -> str:
    return "\n".join(
        [
            "id=a90_v1521_rc1_sampler",
            "name=A90 V1521 RC1 Readonly Sampler",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only post-fs-data sampler for Android-good RC1 timing. Remove after capture.",
            "",
        ]
    )


def prepare_module(store: EvidenceStore, args: argparse.Namespace, execute: bool) -> StepResult:
    started = time.monotonic()
    path = module_stage_dir(store)
    if execute:
        ensure_private_dir(path)
        write_private_text(path / "module.prop", module_prop())
        write_private_text(path / "post-fs-data.sh", post_fs_data_script(args.sampler_samples, args.sampler_delay_us))
        (path / "post-fs-data.sh").chmod(0o700)
        text = "\n".join(
            [
                f"module_dir={path}",
                f"samples={args.sampler_samples}",
                f"delay_us={args.sampler_delay_us}",
                "files=module.prop post-fs-data.sh",
                "",
            ]
        )
        return write_step(store, "prepare-magisk-module", "host:prepare temporary Magisk module", text, "", 0, time.monotonic() - started)
    return write_step(store, "prepare-magisk-module", "host:prepare temporary Magisk module", "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence runner preserves failures
        return None, "", str(exc), time.monotonic() - started


def execute_host_step(store: EvidenceStore, name: str, command: list[str], timeout: int, execute: bool) -> StepResult:
    if not execute:
        return write_step(store, name, command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    rc, text, error, duration = run_process(command, timeout)
    return write_step(store, name, command, text, error, rc, duration)


def execute_host_retry_step(store: EvidenceStore,
                            name: str,
                            command: list[str],
                            timeout: int,
                            execute: bool,
                            attempts: int = 8,
                            sleep_sec: float = 2.0) -> StepResult:
    if not execute:
        return write_step(store, name, command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    started = time.monotonic()
    chunks: list[str] = []
    last_rc: int | None = None
    last_error = ""
    for attempt in range(1, attempts + 1):
        rc, text, error, duration = run_process(command, timeout)
        last_rc = rc
        last_error = error
        chunks.append(f"A90_V1521_ATTEMPT {attempt} rc={rc} duration_sec={duration:.3f}")
        chunks.append(text if text else error)
        if rc == 0:
            break
        lower = f"{text}\n{error}".lower()
        if "no devices" not in lower and "closed" not in lower and "offline" not in lower and "device" not in lower:
            break
        time.sleep(sleep_sec)
    return write_step(store, name, command, "\n".join(chunks), last_error, last_rc, time.monotonic() - started)


def wait_sampler_done_step(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> StepResult:
    command = f"host:poll {REMOTE_EVIDENCE_DIR}/done"
    if not execute:
        return write_step(store, "wait-v1521-sampler-done", command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)

    started = time.monotonic()
    chunks: list[str] = []
    last_status = ""
    stable_count = 0
    deadline = started + args.sampler_wait_timeout
    status_command = [*adb_base(args), "shell", "cat", f"{REMOTE_EVIDENCE_DIR}/status.txt"]
    done_command = [*adb_base(args), "shell", "ls", f"{REMOTE_EVIDENCE_DIR}/done"]
    list_command = [*adb_base(args), "shell", "ls", "-la", REMOTE_EVIDENCE_DIR]

    while time.monotonic() < deadline:
        status_rc, status_text, status_error, _ = run_process(status_command, args.timeout)
        status = (status_text or status_error).strip()
        if status and status == last_status:
            stable_count += 1
        elif status:
            stable_count = 0
            last_status = status
        done_rc, done_text, done_error, _ = run_process(done_command, args.timeout)
        chunks.append(f"A90_V1521_WAIT status_rc={status_rc} done_rc={done_rc} status={status!r}")
        if done_rc == 0:
            list_rc, list_text, list_error, _ = run_process(list_command, args.timeout)
            chunks.append("A90_V1521_DONE_SEEN")
            chunks.append(done_text or done_error)
            chunks.append(list_text or list_error)
            return write_step(store, "wait-v1521-sampler-done", command, "\n".join(chunks), "", list_rc, time.monotonic() - started, ok_override=True)
        if stable_count >= 5 and "A90_V1521_STATUS sample" in last_status:
            chunks.append("A90_V1521_PARTIAL_STABLE")
            return write_step(store, "wait-v1521-sampler-done", command, "\n".join(chunks), "", 0, time.monotonic() - started, ok_override=True)
        time.sleep(2.0)

    chunks.append("A90_V1521_WAIT_TIMEOUT")
    return write_step(store, "wait-v1521-sampler-done", command, "\n".join(chunks), "sampler done not observed before timeout", 1, time.monotonic() - started)


def capture_android_dmesg_step(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> StepResult:
    command = [*adb_base(args), "shell", "su", "-c", "dmesg"]
    if not execute:
        return write_step(store, "capture-android-dmesg-filtered", command, "[dry-run] not executed\n", "", 0, 0.0, skipped=True, ok_override=True)
    started = time.monotonic()
    rc, text, error, _ = run_process(command, args.timeout)
    if rc != 0 or not text:
        fallback = [*adb_base(args), "shell", "dmesg"]
        fallback_rc, fallback_text, fallback_error, _ = run_process(fallback, args.timeout)
        if fallback_text:
            command = fallback
            rc = fallback_rc
            text = fallback_text
            error = fallback_error
    filtered = "\n".join(line for line in text.splitlines() if DMESG_FILTER_RE.search(line))
    ensure_private_dir(pulled_evidence_dir(store))
    write_private_text(pulled_evidence_dir(store) / "host-dmesg-filtered.txt", filtered + ("\n" if filtered else ""))
    output = "\n".join(
        [
            f"A90_V1521_HOST_DMESG rc={rc}",
            f"A90_V1521_HOST_DMESG_FILTERED_LINES={len(filtered.splitlines()) if filtered else 0}",
            filtered,
        ]
    )
    return write_step(store, "capture-android-dmesg-filtered", command, output, error, rc, time.monotonic() - started)


def pull_sampler_evidence_step(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> StepResult:
    dest = pulled_evidence_dir(store)
    ensure_private_dir(dest.parent)
    command = [*adb_base(args), "pull", REMOTE_EVIDENCE_DIR, str(dest)]
    return execute_host_retry_step(store, "pull-v1521-sampler-evidence", command, args.timeout * 4, execute, attempts=10, sleep_sec=2.0)


def cleanup_module_android_command(args: argparse.Namespace) -> list[str]:
    shell = f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; sync"
    return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell)]


def install_module_android_steps(args: argparse.Namespace, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    stage = module_stage_dir(store)
    remote_prop = "/data/local/tmp/a90_v1521_module.prop"
    remote_postfs = "/data/local/tmp/a90_v1521_post-fs-data.sh"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)}; "
        "sync"
    )
    return [
        (
            "push-v1521-module-prop-android",
            [*adb_base(args), "push", str(stage / "module.prop"), remote_prop],
            args.timeout,
        ),
        (
            "push-v1521-post-fs-data-android",
            [*adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs],
            args.timeout,
        ),
        (
            "install-v1521-module-android-su",
            [*adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)],
            args.timeout,
        ),
    ]


def wait_boot_complete_command(args: argparse.Namespace) -> list[str]:
    shell = (
        "i=0; while [ $i -lt 180 ]; do "
        "[ \"$(getprop sys.boot_completed 2>/dev/null)\" = \"1\" ] && exit 0; "
        "sleep 2; i=$((i+1)); done; exit 1"
    )
    return [*adb_base(args), "shell", shell]


def cleanup_module_recovery_best_effort_command(args: argparse.Namespace) -> list[str]:
    return [
        *adb_base(args),
        "shell",
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} 2>/dev/null || true; sync",
    ]


def build_plan(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    remote_android = remote_quote(args.remote_android_image)
    boot_block = remote_quote(args.boot_block)
    android_count = android_image.size // 4096
    restore_command = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        native_image.path,
        "--adb",
        args.adb,
        "--expect-version",
        args.native_expect_version,
        "--verify-protocol",
        "auto",
    ]
    if args.serial:
        restore_command.extend(["--serial", args.serial])
    return [
        ("native-version", ["python3", "scripts/revalidation/a90ctl.py", "--json", "version"], args.timeout),
        ("native-status", ["python3", "scripts/revalidation/a90ctl.py", "status"], args.timeout),
        ("hide-menu", f"bridge:{args.bridge_host}:{args.bridge_port} hide", args.timeout),
        ("native-recovery", f"bridge:{args.bridge_host}:{args.bridge_port} recovery", args.recovery_timeout),
        ("wait-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ("push-android-boot", [*adb_base(args), "push", android_image.path, args.remote_android_image], args.timeout * 4),
        ("remote-android-sha", [*adb_base(args), "shell", f"sha256sum {remote_android} 2>/dev/null || toybox sha256sum {remote_android}"], args.timeout),
        ("flash-android-boot", [*adb_base(args), "shell", f"dd if={remote_android} of={boot_block} bs=4M conv=fsync && sync"], args.timeout * 4),
        (
            "readback-android-boot",
            [
                *adb_base(args),
                "shell",
                f"dd if={boot_block} bs=4096 count={android_count} 2>/dev/null | sha256sum 2>/dev/null || "
                f"dd if={boot_block} bs=4096 count={android_count} 2>/dev/null | toybox sha256sum",
            ],
            args.timeout * 2,
        ),
        ("reboot-android", [*adb_base(args), "shell", "twrp reboot"], args.timeout),
        ("wait-android", [*adb_base(args), "devices"], args.android_timeout),
        ("wait-android-boot-complete-for-install", wait_boot_complete_command(args), args.android_timeout),
        ("wait-android-ready-for-module-push", [*adb_base(args), "devices"], args.android_timeout),
        *install_module_android_steps(args, store),
        ("reboot-android-with-v1521-module", [*adb_base(args), "reboot"], args.timeout),
        ("wait-android-second", [*adb_base(args), "devices"], args.android_timeout),
        ("wait-v1521-sampler-done", ["host:wait-sampler-done"], args.sampler_wait_timeout + args.timeout),
        ("capture-android-dmesg-filtered", ["host:capture-android-dmesg-filtered"], args.timeout),
        ("pull-v1521-sampler-evidence", ["host:pull-sampler-evidence"], args.timeout * 4),
        ("cleanup-v1521-module-android", cleanup_module_android_command(args), args.timeout),
        ("reboot-recovery-for-rollback", [*adb_base(args), "reboot", "recovery"], args.timeout),
        ("wait-rollback-recovery", [*adb_base(args), "devices"], args.recovery_timeout),
        ("cleanup-v1521-module-recovery-best-effort", cleanup_module_recovery_best_effort_command(args), args.timeout),
        ("restore-native", restore_command, args.recovery_timeout + args.android_timeout),
    ]


SAMPLE_BEGIN_RE = re.compile(r"A90_V1521_SAMPLE_BEGIN index=(?P<index>\d+) uptime=(?P<uptime>[0-9.]+)")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")


def first_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def parse_samples(text: str) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body: list[str] = []
    for line in text.splitlines():
        match = SAMPLE_BEGIN_RE.search(line)
        if match:
            if current is not None:
                current["text"] = "\n".join(body)
                samples.append(current)
            current = {"index": int(match.group("index")), "uptime": float(match.group("uptime"))}
            body = []
            continue
        if line.startswith("A90_V1521_SAMPLE_END"):
            if current is not None:
                current["text"] = "\n".join(body)
                samples.append(current)
                current = None
                body = []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        current["text"] = "\n".join(body)
        samples.append(current)
    for sample in samples:
        text = sample.get("text", "")
        sample["gpio135_line"] = first_line(text, r"gpio135\s*:")
        sample["gpio142_line"] = first_line(text, r"gpio142\s*:")
        sample["gpio142_irq_line"] = first_line(text, r"msmgpio-dc\s+142|mdm status")
        sample["pcie1_gdsc_line"] = first_line(text, r"pcie_1_gdsc")
        sample["pcie_link_state_line"] = first_line(text, r"current_link_state|link_state")
        sample["pcie_pinmux_line"] = first_line(text, r"pin 10[234] .*qcom,pcie")
    return samples


def first_time(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw_line in text.splitlines():
        if not regex.search(raw_line):
            continue
        match = TS_RE.match(raw_line.strip())
        if match:
            return float(match.group("ts"))
    return None


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def slim_sample(sample: dict[str, Any] | None) -> dict[str, Any] | None:
    if not sample:
        return None
    return {
        "index": sample["index"],
        "uptime": sample["uptime"],
        "gpio135_line": sample.get("gpio135_line", ""),
        "gpio142_line": sample.get("gpio142_line", ""),
        "gpio142_irq_line": sample.get("gpio142_irq_line", ""),
        "pcie1_gdsc_line": sample.get("pcie1_gdsc_line", ""),
        "pcie_link_state_line": sample.get("pcie_link_state_line", ""),
        "pcie_pinmux_line": sample.get("pcie_pinmux_line", ""),
    }


def sample_before(samples: list[dict[str, Any]], timestamp: float | None) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    candidates = [sample for sample in samples if sample["uptime"] <= timestamp]
    return max(candidates, key=lambda item: item["uptime"]) if candidates else None


def sample_after(samples: list[dict[str, Any]], timestamp: float | None) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    candidates = [sample for sample in samples if sample["uptime"] >= timestamp]
    return min(candidates, key=lambda item: item["uptime"]) if candidates else None


def read_pulled(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = pulled_evidence_dir(store)
    base = root
    if (base / "a90-v1521-rc1-postfs-sampler").is_dir():
        base = base / "a90-v1521-rc1-postfs-sampler"
    samples_text = read_pulled(base / "samples.log")
    module_dmesg_text = read_pulled(base / "dmesg-filtered.txt")
    host_dmesg_text = read_pulled(root / "host-dmesg-filtered.txt")
    dmesg_text = "\n".join(part for part in (module_dmesg_text, host_dmesg_text) if part)
    props_text = read_pulled(base / "props.txt")
    status_text = read_pulled(base / "status.txt")
    samples = parse_samples(samples_text)
    wlfw_time = first_time(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_time(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    wlan0_time = first_time(dmesg_text, r"\bwlan0\b")
    pcie_l0_time = first_time(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes")
    first_lower_time = min([value for value in (wlfw_time, bdf_time, wlan0_time) if value is not None], default=None)
    return {
        "base": str(base),
        "files_present": {
            "samples": bool(samples_text),
            "dmesg": bool(dmesg_text),
            "module_dmesg": bool(module_dmesg_text),
            "host_dmesg": bool(host_dmesg_text),
            "props": bool(props_text),
            "status": bool(status_text),
            "done": (base / "done").exists(),
        },
        "status_text": status_text.strip(),
        "sample_count": len(samples),
        "sample_first_uptime": samples[0]["uptime"] if samples else None,
        "sample_last_uptime": samples[-1]["uptime"] if samples else None,
        "dmesg": {
            "pcie_l0_time": pcie_l0_time,
            "wlfw_time": wlfw_time,
            "bdf_time": bdf_time,
            "wlan0_time": wlan0_time,
            "pcie_l0_lines": count_lines(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes"),
            "wlfw_lines": count_lines(dmesg_text, r"\bwlfw\b|WLFW"),
            "bdf_lines": count_lines(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "wlan0_lines": count_lines(dmesg_text, r"\bwlan0\b"),
        },
        "matched_window": {
            "first_lower_time": first_lower_time,
            "has_pre_lower_sample": sample_before(samples, first_lower_time) is not None,
            "has_post_lower_sample": sample_after(samples, first_lower_time) is not None,
            "sample_before_lower": slim_sample(sample_before(samples, first_lower_time)),
            "sample_after_lower": slim_sample(sample_after(samples, first_lower_time)),
            "has_pre_l0_sample": sample_before(samples, pcie_l0_time) is not None,
            "has_post_l0_sample": sample_after(samples, pcie_l0_time) is not None,
            "sample_before_l0": slim_sample(sample_before(samples, pcie_l0_time)),
            "sample_after_l0": slim_sample(sample_after(samples, pcie_l0_time)),
            "first_sample": slim_sample(samples[0]) if samples else None,
            "last_sample": slim_sample(samples[-1]) if samples else None,
        },
        "props_text": props_text.strip(),
    }


def execute_plan(args: argparse.Namespace, store: EvidenceStore, execute: bool) -> tuple[list[StepResult], dict[str, Any], str, bool]:
    native_image, android_images, android_image = image_context(args)
    approval_ok, missing_flags = require_approval(args)
    context: dict[str, Any] = {
        "native_image": asdict(native_image),
        "android_images": [asdict(image) for image in android_images],
        "android_image": asdict(android_image) if android_image else None,
        "approval_ok": approval_ok,
        "missing_approval_flags": missing_flags,
        "remote_module_dir": REMOTE_MODULE_DIR,
        "remote_evidence_dir": REMOTE_EVIDENCE_DIR,
        "pulled_evidence_dir": str(pulled_evidence_dir(store)),
        "sampler_samples": args.sampler_samples,
        "sampler_delay_us": args.sampler_delay_us,
    }
    if not native_image.present or not native_image.aligned_4k or not native_image.android_magic or not native_image.native_marker:
        return [], context, "v1521-handoff-missing-native-rollback", False
    if android_image is None:
        return [], context, "v1521-handoff-missing-android-boot", False
    if android_image.sha256 == native_image.sha256:
        return [], context, "v1521-handoff-image-collision", False
    if args.command == "run" and not approval_ok:
        return [], context, "v1521-handoff-approval-required", False

    plan = build_plan(args, store, android_image, native_image)
    steps: list[StepResult] = []
    if args.command == "plan":
        steps.append(prepare_module(store, args, execute=False))
        for name, command, _ in plan:
            steps.append(write_step(store, name, command, "[plan] not executed\n", "", 0, 0.0, skipped=True, ok_override=True))
        return steps, context, "v1521-handoff-plan-ready", True

    steps.append(prepare_module(store, args, execute=execute))
    restore_entry = next(item for item in plan if item[0] == "restore-native")
    cleanup_step_seen = False
    cleanup_android_ok = False
    restore_step_seen = False
    sampler_done_ok = False
    pull_ok = False

    for name, command, timeout in plan:
        if isinstance(command, str) and command.startswith("bridge:"):
            step = execute_bridge_step(store, args, name, command.split(" ", 1)[1], timeout, execute)
        elif name in {"wait-recovery", "wait-rollback-recovery"}:
            step = wait_for_adb_state(args, {"recovery"}, timeout, execute, store, name)
        elif name in {"wait-android", "wait-android-second", "wait-android-ready-for-module-push"}:
            step = wait_for_adb_state(args, {"device"}, timeout, execute, store, name)
        elif name == "wait-android-boot-complete-for-install":
            step = execute_host_retry_step(
                store,
                name,
                command if isinstance(command, list) else [command],
                timeout,
                execute,
                attempts=6,
                sleep_sec=3.0,
            )
        elif name == "wait-v1521-sampler-done":
            step = wait_sampler_done_step(args, store, execute)
            sampler_done_ok = step.ok
        elif name == "capture-android-dmesg-filtered":
            step = capture_android_dmesg_step(args, store, execute)
        elif name == "pull-v1521-sampler-evidence":
            step = pull_sampler_evidence_step(args, store, execute)
            pull_ok = step.ok
        elif name in {
            "push-v1521-module-prop-android",
            "push-v1521-post-fs-data-android",
            "install-v1521-module-android-su",
            "cleanup-v1521-module-android",
        }:
            step = execute_host_retry_step(store, name, command if isinstance(command, list) else [command], timeout, execute)
        else:
            step = execute_step(store, name, command, timeout, execute)
        steps.append(step)

        if name == "remote-android-sha" and execute and step.ok and android_image.sha256 not in step_text(store, step):
            return steps, context, "v1521-handoff-remote-sha-mismatch", False
        if name == "flash-android-boot" and execute and not step.ok:
            context["emergency_rollback_attempted"] = True
            context["emergency_rollback_reason"] = "flash-android-boot failed after boot write was requested"
            restore_name, restore_command, restore_timeout = restore_entry
            rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
            steps.append(rollback_step)
            context["emergency_rollback_ok"] = rollback_step.ok
            return steps, context, "v1521-handoff-flash-failed-rollback-attempted", False
        if name == "readback-android-boot" and execute:
            readback_text = step_text(store, step) if step.file else ""
            if not step.ok or android_image.sha256 not in readback_text:
                context["emergency_rollback_attempted"] = True
                context["emergency_rollback_reason"] = "Android boot readback failed or SHA did not match"
                restore_name, restore_command, restore_timeout = restore_entry
                rollback_step = execute_step(store, restore_name, restore_command, restore_timeout, execute=True)
                steps.append(rollback_step)
                context["emergency_rollback_ok"] = rollback_step.ok
                return steps, context, "v1521-handoff-readback-failed-rollback-attempted", False
        if name == "cleanup-v1521-module-android":
            cleanup_step_seen = True
            cleanup_android_ok = step.ok
        if name == "cleanup-v1521-module-recovery-best-effort":
            cleanup_step_seen = True
        if name == "restore-native":
            restore_step_seen = True
        if execute and not step.ok and name not in {
            "wait-v1521-sampler-done",
            "capture-android-dmesg-filtered",
            "pull-v1521-sampler-evidence",
            "cleanup-v1521-module-android",
            "cleanup-v1521-module-recovery-best-effort",
        }:
            return steps, context, f"v1521-handoff-failed-{name}", False

    if execute:
        analysis = analyze_pulled_evidence(store) if pull_ok else {}
        context["analysis"] = analysis
        if not cleanup_step_seen:
            return steps, context, "v1521-handoff-cleanup-not-run", False
        if not restore_step_seen:
            return steps, context, "v1521-handoff-rollback-not-run", False
        if not cleanup_android_ok:
            return steps, context, "v1521-handoff-android-cleanup-failed-rollback-pass", False
        if not pull_ok:
            return steps, context, "v1521-handoff-sampler-missing-rollback-pass", False
        files_present = analysis.get("files_present") or {}
        if not all(files_present.get(name) for name in ("samples", "dmesg", "props", "status")):
            return steps, context, "v1521-handoff-sampler-files-missing-rollback-pass", False
        matched = analysis.get("matched_window") or {}
        dmesg = analysis.get("dmesg") or {}
        android_lower_ok = dmesg.get("wlfw_lines", 0) > 0 and dmesg.get("bdf_lines", 0) > 0 and dmesg.get("wlan0_lines", 0) > 0
        if android_lower_ok and matched.get("has_pre_lower_sample") and matched.get("has_post_lower_sample"):
            if not files_present.get("done") or not sampler_done_ok:
                return steps, context, "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass", True
            return steps, context, "v1521-magisk-postfs-pre-lower-window-rollback-pass", True
        if android_lower_ok:
            if not files_present.get("done") or not sampler_done_ok:
                return steps, context, "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass", True
            return steps, context, "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass", True
        if not files_present.get("done") or not sampler_done_ok:
            return steps, context, "v1521-magisk-postfs-partial-evidence-captured-rollback-review", True
        return steps, context, "v1521-magisk-postfs-evidence-captured-rollback-review", True
    return steps, context, "v1521-handoff-dryrun-ready", True


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    matched = analysis.get("matched_window") or {}
    return "\n".join(
        [
            "# V1521 Android RC1 Magisk Post-fs-data Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Analysis",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["sample_count", analysis.get("sample_count")],
                    ["sample_first_uptime", analysis.get("sample_first_uptime")],
                    ["sample_last_uptime", analysis.get("sample_last_uptime")],
                    ["wlfw/bdf/wlan0", f"{dmesg.get('wlfw_time')}/{dmesg.get('bdf_time')}/{dmesg.get('wlan0_time')}"],
                    ["pre/post first lower", f"{matched.get('has_pre_lower_sample')}/{matched.get('has_post_lower_sample')}"],
                    ["pre/post L0", f"{matched.get('has_pre_l0_sample')}/{matched.get('has_post_l0_sample')}"],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
            "",
            "## Matched Samples",
            "",
            markdown_table(
                ["sample", "value"],
                [
                    ["first", json.dumps(matched.get("first_sample"), sort_keys=True)],
                    ["before_lower", json.dumps(matched.get("sample_before_lower"), sort_keys=True)],
                    ["after_lower", json.dumps(matched.get("sample_after_lower"), sort_keys=True)],
                    ["before_l0", json.dumps(matched.get("sample_before_l0"), sort_keys=True)],
                    ["after_l0", json.dumps(matched.get("sample_after_l0"), sort_keys=True)],
                    ["last", json.dumps(matched.get("last_sample"), sort_keys=True)],
                ],
            ),
            "",
            "## Steps",
            "",
            markdown_table(
                ["step", "status", "rc", "duration", "file"],
                [
                    [
                        item["name"],
                        "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
                        item["rc"],
                        f"{item['duration_sec']:.3f}s",
                        item["file"],
                    ]
                    for item in manifest["steps"]
                ],
            ),
            "",
            "## Safety",
            "",
            "Bounded Android handoff with a temporary Magisk module and native rollback. The module writes only to `/data/local/tmp/a90-v1521-rc1-postfs-sampler`; recovery cleanup removes that path and `/data/adb/modules/a90_v1521_rc1_sampler` before restoring native v724. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify, global PCI rescan, platform bind/unbind, or partition write beyond the declared boot image handoff/rollback is performed.",
            "",
            "## Next",
            "",
            "- If V1521 captured a pre-lower window, compare those source lines against V1518 native no-L0 evidence.",
            "- If V1521 still missed, use a still-earlier init hook or kernel log-only classifier before native mutation.",
            "",
        ]
    )


def reason_for(decision: str) -> str:
    reasons = {
        "v1521-handoff-plan-ready": "plan-only handoff; no device command executed",
        "v1521-handoff-dryrun-ready": "dry-run handoff completed without device mutation",
        "v1521-magisk-postfs-pre-lower-window-rollback-pass": "temporary Magisk post-fs-data sampler captured pre/post lower Wi-Fi source window and native rollback completed",
        "v1521-magisk-postfs-partial-pre-lower-window-rollback-pass": "temporary Magisk post-fs-data sampler captured pre/post lower Wi-Fi source window before full sampler completion; native rollback completed",
        "v1521-magisk-postfs-android-lower-no-pre-window-rollback-pass": "Android reached lower Wi-Fi markers, but post-fs-data sampler did not bracket the first lower marker; native rollback completed",
        "v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass": "Android reached lower Wi-Fi markers with partial post-fs-data evidence, but the sampler did not bracket the first lower marker; native rollback completed",
        "v1521-magisk-postfs-evidence-captured-rollback-review": "post-fs-data evidence captured and native rollback completed; review child analysis",
        "v1521-magisk-postfs-partial-evidence-captured-rollback-review": "partial post-fs-data evidence captured before full sampler completion; review child analysis",
        "v1521-handoff-sampler-missing-rollback-pass": "sampler evidence missing or incomplete, but cleanup and native rollback completed",
        "v1521-handoff-sampler-files-missing-rollback-pass": "sampler completed but pulled evidence files are missing; cleanup and native rollback completed",
        "v1521-handoff-android-cleanup-failed-rollback-pass": "Android cleanup of the temporary module failed, but native rollback completed",
    }
    return reasons.get(decision) or v424_reason_for(decision)


def check_forbidden_output(manifest: dict[str, Any], summary: str) -> list[str]:
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n" + summary
    leaks: list[str] = []
    for key in FORBIDDEN_OUTPUT_ENV_KEYS:
        value = __import__("os").environ.get(key, "")
        if value and value in text:
            leaks.append(key)
    return leaks


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, decision, pass_ok = execute_plan(args, store, execute=execute)
    manifest = {
        "cycle": "V1521",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision),
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    leaks = check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1521-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
