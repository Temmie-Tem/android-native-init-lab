#!/usr/bin/env python3
"""V1520 Android read-only early RC1 critical-source sampler.

This collector is intended to run immediately after Android ADB first reports a
device. It samples kernel uptime-aligned GPIO, interrupt, regulator, pinmux, and
pcie1 state while Android performs its normal SDX50M/RC1 bring-up. It performs
no Wi-Fi HAL action, scan/connect, credential handling, DHCP/routes, external
ping, sysfs/debugfs write, eSoC notify, boot image write, or partition write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1520-android-rc1-early-critical-source-sample")
DEFAULT_TIMEOUT = 90.0
DEFAULT_SAMPLES = 180
DEFAULT_DELAY = 0.03
LATEST_POINTER = Path("tmp/wifi/latest-v1520-android-rc1-early-critical-source-sample.txt")

DMESG_PATTERN = (
    "subsys-restart|__subsystem_get|subsys_esoc0|subsys_modem|"
    "mdm_subsys_powerup|esoc0|SDX50M|ap2mdm|mdm2ap|GPIO 135|GPIO135|"
    "GPIO 142|GPIO142|mdm status|msm_pcie|PCIe|RC1|LTSSM|"
    "MHI|mhi|mhi_0305_01\\.01\\.00_pipe_10|\\bks\\b|icnss|wlfw|"
    "BDF file|regdb\\.bin|bdwlan\\.bin|FW ready|WLAN FW is ready|wlan0"
)
SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(r"(?i)(ssid|bssid|p" + "sk|pass" + "word|pass" + "phrase)=([^\\s]+)"), r"\1=<redacted>"),
    (re.compile(r"(?i)(androidboot\\.serialno|androidboot\\.ap_serial|ro\\.serialno|ro\\.boot\\.serialno|serialno)=([^\\s]+)"), r"\1=<redacted>"),
)
FORBIDDEN_OUTPUT_ENV_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")


@dataclass(frozen=True)
class Capture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--no-su", action="store_true")
    parser.add_argument("--include-regulator-loop", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.no_su:
        return [*adb_base(args), "shell", shell_command]
    return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]


def run_command(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
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


def redact(text: str) -> str:
    redacted = text
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> Capture:
    body = f"$ {shlex.join(command)}\n{redact(text if text else error).rstrip()}\nrc={rc}\n"
    path = store.write_text(f"android/commands/{safe_name(name)}.txt", body)
    visible = redact(text if text else error)
    if len(visible) > 20000:
        visible = visible[:20000] + "\n[truncated in manifest]\n"
    return Capture(
        name=name,
        command=shlex.join(command),
        ok=rc == 0,
        rc=rc,
        status="ok" if rc == 0 else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        text=visible,
        error=error,
    )


def adb_devices(args: argparse.Namespace) -> dict[str, Any]:
    command = [*adb_base(args), "devices", "-l"]
    rc, text, error, duration = run_command(command, timeout=10.0)
    devices: list[str] = []
    for raw_line in text.splitlines()[1:]:
        parts = raw_line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return {
        "rc": rc,
        "text": redact(text),
        "error": error,
        "duration_sec": duration,
        "devices": devices,
        "device_count": len(devices),
    }


def selected_device_available(args: argparse.Namespace, devices: dict[str, Any]) -> bool:
    if args.serial:
        return args.serial in devices["devices"]
    return devices["device_count"] == 1


def capture_shell(args: argparse.Namespace, store: EvidenceStore, name: str, shell_command: str, timeout: float) -> Capture:
    command = adb_shell(args, shell_command)
    rc, text, error, duration = run_command(command, timeout=max(args.timeout, timeout))
    return write_capture(store, name, command, rc, text, error, duration)


def capture_shell_retry(args: argparse.Namespace,
                        store: EvidenceStore,
                        name: str,
                        shell_command: str,
                        timeout: float,
                        attempts: int = 8,
                        sleep_sec: float = 1.0) -> Capture:
    command = adb_shell(args, shell_command)
    combined = []
    started = time.monotonic()
    last_rc: int | None = None
    last_error = ""
    for attempt in range(1, attempts + 1):
        rc, text, error, duration = run_command(command, timeout=max(args.timeout, timeout))
        last_rc = rc
        last_error = error
        combined.append(f"A90_V1520_ATTEMPT {attempt} rc={rc} duration_sec={duration:.3f}")
        combined.append(text if text else error)
        if rc == 0:
            break
        if "no devices" not in text.lower() and "no devices" not in error.lower():
            break
        time.sleep(sleep_sec)
    return write_capture(store, name, command, last_rc, "\n".join(combined), last_error, time.monotonic() - started)


def early_loop_script(samples: int, delay: float, include_regulator: bool) -> str:
    regulator_block = (
        "if [ -r /sys/kernel/debug/regulator/regulator_summary ]; then "
        "grep -Ei 'pcie_1_gdsc|pcie_0_gdsc|pm8150_l5|pm8150l_l3' /sys/kernel/debug/regulator/regulator_summary 2>/dev/null || true; "
        "else echo unreadable; fi"
        if include_regulator
        else "echo skipped reason=adb-stability"
    )
    return rf"""
SAMPLES={samples}
DELAY={delay}
echo A90_V1520_EARLY_LOOP_BEGIN
i=0
while [ "$i" -lt "$SAMPLES" ]; do
  uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
  echo "A90_V1520_SAMPLE_BEGIN index=$i uptime=$uptime"
  echo "SRC interrupts"
  cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +142|msmgpio-dc +104|mdm status|msm_pcie_wake|mhi|pcie' || true
  echo "SRC debug_gpio"
  if [ -r /sys/kernel/debug/gpio ]; then grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio 2>/dev/null || true; else echo unreadable; fi
  echo "SRC pcie_state"
  for f in \
    /sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state \
    /sys/devices/platform/soc/1c08000.qcom,pcie/link_state \
    /sys/devices/platform/soc/1c08000.qcom,pcie/power/runtime_status \
    /sys/devices/platform/soc/1c08000.qcom,pcie/power/control; do
    [ -e "$f" ] && {{ printf 'FILE %s=' "$f"; cat "$f" 2>&1 | head -c 200; printf '\n'; }}
  done
  echo "SRC regulator"
  {regulator_block}
  echo "SRC pinmux"
  for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
    [ -r "$f" ] || continue
    grep -Ei 'pin 102 |pin 103 |pin 104 |pin 135 |pin 142 ' "$f" 2>/dev/null || true
  done
  echo "A90_V1520_SAMPLE_END index=$i uptime=$uptime"
  i=$((i + 1))
  sleep "$DELAY" 2>/dev/null || sleep 1
done
echo A90_V1520_EARLY_LOOP_END
"""


def dmesg_script() -> str:
    return f"dmesg 2>&1 | grep -Ei {DMESG_PATTERN!r} | tail -n 2200 || true"


def props_script() -> str:
    return (
        "for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr "
        "init.svc.vendor.per_proxy init.svc.vendor.mdm_helper init.svc.cnss-daemon "
        "ro.boottime.vendor.per_mgr ro.boottime.vendor.per_proxy "
        "ro.boottime.vendor.mdm_helper ro.boottime.cnss-daemon; do "
        "echo \"$p=$(getprop $p 2>/dev/null)\"; done"
    )


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    return [
        capture_shell(args, store, "v1520-early-critical-loop", early_loop_script(args.samples, args.delay, args.include_regulator_loop), args.timeout),
        capture_shell_retry(args, store, "v1520-dmesg-filtered", dmesg_script(), 35.0),
        capture_shell_retry(args, store, "v1520-props-final", props_script(), 15.0),
    ]


SAMPLE_BEGIN_RE = re.compile(r"A90_V1520_SAMPLE_BEGIN index=(?P<index>\d+) uptime=(?P<uptime>[0-9.]+)")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]\s*(?P<line>.*)$")


def capture_text(captures: list[Capture], *names: str) -> str:
    wanted = set(names)
    return "\n".join(capture.text for capture in captures if capture.name in wanted)


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
            current = {
                "index": int(match.group("index")),
                "uptime": float(match.group("uptime")),
            }
            body = []
            continue
        if line.startswith("A90_V1520_SAMPLE_END"):
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
        text_value = sample.get("text", "")
        sample["gpio135_line"] = first_line(text_value, r"gpio135\s*:")
        sample["gpio142_line"] = first_line(text_value, r"gpio142\s*:")
        sample["gpio142_irq_line"] = first_line(text_value, r"msmgpio-dc\s+142|mdm status")
        sample["pcie1_gdsc_line"] = first_line(text_value, r"pcie_1_gdsc")
        sample["pcie_link_state_line"] = first_line(text_value, r"current_link_state|link_state")
        sample["pcie_pinmux_line"] = first_line(text_value, r"pin 10[234] .*qcom,pcie")
    return samples


def first_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


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


def sample_before(samples: list[dict[str, Any]], timestamp: float | None) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    candidates = [sample for sample in samples if sample["uptime"] <= timestamp]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["uptime"])


def sample_after(samples: list[dict[str, Any]], timestamp: float | None) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    candidates = [sample for sample in samples if sample["uptime"] >= timestamp]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item["uptime"])


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


def summarize(captures: list[Capture], store: EvidenceStore) -> dict[str, Any]:
    loop_text = capture_text(captures, "v1520-early-critical-loop")
    dmesg_text = capture_text(captures, "v1520-dmesg-filtered")
    samples = parse_samples(loop_text)
    pcie_reset_time = first_time(dmesg_text, r"Assert the reset of endpoint of RC1|PCIe.*RC1.*reset")
    pcie_l0_time = first_time(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes")
    link_failed_time = first_time(dmesg_text, r"link.*fail|failed.*link|LTSSM.*POLL_COMPLIANCE")
    wlfw_time = first_time(dmesg_text, r"\bwlfw\b|WLFW")
    bdf_time = first_time(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin")
    wlan0_time = first_time(dmesg_text, r"\bwlan0\b")
    before_l0 = sample_before(samples, pcie_l0_time)
    after_l0 = sample_after(samples, pcie_l0_time)
    first_sample = slim_sample(samples[0]) if samples else None
    last_sample = slim_sample(samples[-1]) if samples else None
    sample_rows = [
        {
            "index": sample["index"],
            "uptime": sample["uptime"],
            "gpio135": sample.get("gpio135_line", ""),
            "gpio142": sample.get("gpio142_line", ""),
            "pcie1_gdsc": sample.get("pcie1_gdsc_line", ""),
        }
        for sample in samples[:12]
    ]
    store.write_text("sample-preview.json", json.dumps(sample_rows, indent=2, sort_keys=True) + "\n")
    return {
        "all_commands_ok": all(capture.ok for capture in captures),
        "sample_count": len(samples),
        "sample_first_uptime": samples[0]["uptime"] if samples else None,
        "sample_last_uptime": samples[-1]["uptime"] if samples else None,
        "dmesg": {
            "pcie_reset_time": pcie_reset_time,
            "pcie_l0_time": pcie_l0_time,
            "link_failed_or_poll_compliance_time": link_failed_time,
            "wlfw_time": wlfw_time,
            "bdf_time": bdf_time,
            "wlan0_time": wlan0_time,
            "pcie_rc1_lines": count_lines(dmesg_text, r"PCIe.*RC1|RC1.*PCIe|msm_pcie"),
            "ltssm_l0_lines": count_lines(dmesg_text, r"LTSSM_STATE:.*L0|PCIe RC1 Current|Current GEN[0-9].*lanes"),
            "wlfw_lines": count_lines(dmesg_text, r"\bwlfw\b|WLFW"),
            "bdf_lines": count_lines(dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "wlan0_lines": count_lines(dmesg_text, r"\bwlan0\b"),
        },
        "matched_window": {
            "has_pre_l0_sample": before_l0 is not None,
            "has_post_l0_sample": after_l0 is not None,
            "pre_l0_delta_ms": round((pcie_l0_time - before_l0["uptime"]) * 1000, 3) if before_l0 and pcie_l0_time is not None else None,
            "post_l0_delta_ms": round((after_l0["uptime"] - pcie_l0_time) * 1000, 3) if after_l0 and pcie_l0_time is not None else None,
            "first_sample": first_sample,
            "last_sample": last_sample,
            "sample_before_l0": slim_sample(before_l0),
            "sample_after_l0": slim_sample(after_l0),
        },
    }


def decide(args: argparse.Namespace, devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1520-android-rc1-early-critical-source-sample-plan-ready",
            True,
            "plan-only; no ADB command executed",
            "run preflight with Android ADB available or invoke through V1520 handoff",
        )
    if not selected_device_available(args, devices):
        return (
            "v1520-android-adb-device-unavailable",
            False,
            "selected Android ADB device is unavailable",
            "boot Android or run the bounded V1520 handoff",
        )
    if args.command == "preflight":
        return (
            "v1520-android-rc1-early-critical-source-preflight-pass",
            True,
            "Android ADB target is available",
            "run the early critical-source sampler immediately after Android ADB appears",
        )
    if not summary.get("all_commands_ok"):
        return (
            "v1520-android-rc1-early-critical-source-command-failed",
            False,
            "one or more read-only Android captures failed",
            "inspect command evidence before retry",
        )
    dmesg = summary["dmesg"]
    matched = summary["matched_window"]
    android_lower_positive = dmesg["wlfw_lines"] > 0 and dmesg["bdf_lines"] > 0 and dmesg["wlan0_lines"] > 0
    android_l0_positive = dmesg["ltssm_l0_lines"] > 0
    first_sample_uptime = summary.get("sample_first_uptime")
    earliest_lower_time = min(
        [value for value in (dmesg.get("wlfw_time"), dmesg.get("bdf_time"), dmesg.get("wlan0_time")) if value is not None],
        default=None,
    )
    if android_l0_positive and android_lower_positive and matched["has_pre_l0_sample"] and matched["has_post_l0_sample"]:
        return (
            "v1520-android-good-matched-rc1-critical-source-window-captured",
            True,
            "Android-good RC1 L0 has uptime-aligned pre/post critical-source samples plus lower Wi-Fi markers",
            "compare this matched Android-good window against V1517/V1518 native no-L0 evidence",
        )
    if android_lower_positive:
        timing_note = ""
        if isinstance(first_sample_uptime, float) and earliest_lower_time is not None and first_sample_uptime > earliest_lower_time:
            timing_note = f"; first sample uptime {first_sample_uptime}s is after first lower marker {earliest_lower_time}s"
        return (
            "v1520-android-good-positive-but-adb-sampler-missed-pre-l0",
            True,
            "Android reached WLFW/BDF/wlan0, but early ADB sampler did not bracket RC1 L0" + timing_note,
            "switch V1521 to an earlier Android boot hook such as a temporary Magisk post-fs-data sampler",
        )
    return (
        "v1520-android-good-lower-chain-not-observed",
        False,
        "Android-good lower chain was not observed in this read-only capture",
        "inspect dmesg/boot state and retry only if rollback is healthy",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    dmesg = summary.get("dmesg", {})
    matched = summary.get("matched_window", {})
    return "\n".join(
        [
            "# V1520 Android RC1 Early Critical Source Sampler",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Capture Summary",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["sample_count", summary.get("sample_count")],
                    ["sample_first_uptime", summary.get("sample_first_uptime")],
                    ["sample_last_uptime", summary.get("sample_last_uptime")],
                    ["pcie_reset_time", dmesg.get("pcie_reset_time")],
                    ["pcie_l0_time", dmesg.get("pcie_l0_time")],
                    ["wlfw/bdf/wlan0 times", f"{dmesg.get('wlfw_time')}/{dmesg.get('bdf_time')}/{dmesg.get('wlan0_time')}"],
                    ["pre/post L0 samples", f"{matched.get('has_pre_l0_sample')}/{matched.get('has_post_l0_sample')}"],
                    ["pre/post L0 delta ms", f"{matched.get('pre_l0_delta_ms')}/{matched.get('post_l0_delta_ms')}"],
                ],
            ),
            "",
            "## Matched Samples",
            "",
            markdown_table(
                ["sample", "value"],
                [
                    ["first", json.dumps(matched.get("first_sample"), sort_keys=True)],
                    ["before_l0", json.dumps(matched.get("sample_before_l0"), sort_keys=True)],
                    ["after_l0", json.dumps(matched.get("sample_after_l0"), sort_keys=True)],
                    ["last", json.dumps(matched.get("last_sample"), sort_keys=True)],
                ],
            ),
            "",
            "## Safety",
            "",
            "Read-only Android collector. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, sysfs/debugfs write, eSoC notify, boot image write, or partition write is performed by this collector.",
            "",
        ]
    )


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
    devices = adb_devices(args) if args.command != "plan" else {"devices": [], "device_count": 0, "rc": 0}
    captures: list[Capture] = []
    summary: dict[str, Any] = {
        "all_commands_ok": True,
        "sample_count": 0,
        "dmesg": {},
        "matched_window": {},
    }
    if args.command == "run" and selected_device_available(args, devices):
        captures = collect(args, store)
        summary = summarize(captures, store)
    decision, pass_ok, reason, next_step = decide(args, devices, captures, summary)
    manifest = {
        "cycle": "V1520",
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "adb_devices": devices,
        "captures": [asdict(capture) for capture in captures],
        "summary": summary,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
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
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    summary_text = render_summary(manifest)
    leaks = check_forbidden_output(manifest, summary_text)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1520-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        manifest["next_step"] = "remove sensitive output before continuing"
        summary_text = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary_text)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
