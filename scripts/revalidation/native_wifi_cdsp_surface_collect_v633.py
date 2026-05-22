#!/usr/bin/env python3
"""V633 native CDSP read-only surface collector.

This collector contacts the current native device only for read-only commands.
It does not write sysfs, boot DSP nodes, start daemons, start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP, change routes, or ping
externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v633-cdsp-surface-readonly")
DEFAULT_BUSYBOX = "/cache/bin/busybox"

FORBIDDEN_ACTIONS = [
    "sysfs write",
    "ADSP/CDSP/SLPI boot-node write",
    "boot_wlan/qcwlanstate write",
    "boot image build/flash",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]

COMMANDS: tuple[tuple[str, str], ...] = (
    (
        "boot-cdsp-surface",
        r"""echo A90_V633_BOOT_CDSP_BEGIN;
$BB ls -la /sys/kernel/boot_cdsp 2>&1;
for f in /sys/kernel/boot_cdsp/*; do
  echo "--- $f";
  if [ -r "$f" ]; then $BB cat "$f" 2>&1; else echo not-readable; fi;
done;
echo A90_V633_BOOT_CDSP_END""",
    ),
    (
        "subsys-state",
        r"""echo A90_V633_SUBSYS_BEGIN;
for d in /sys/bus/msm_subsys/devices/*; do
  [ -d "$d" ] || continue;
  echo "--- $d";
  for f in name state restart_level firmware_name fw_name; do
    [ -e "$d/$f" ] && printf "%s=" "$f" && $BB cat "$d/$f" 2>&1;
  done;
done;
echo A90_V633_SUBSYS_END""",
    ),
    (
        "firmware-surface",
        r"""echo A90_V633_FIRMWARE_BEGIN;
printf "firmware_class.path=";
$BB cat /sys/module/firmware_class/parameters/path 2>&1;
$BB cat /proc/mounts | $BB grep -Ei 'firmware|vendor|persist|modem' || true;
for d in /vendor/firmware_mnt/image /vendor/firmware-modem/image /vendor/firmware/image /firmware/image /mnt/vendor/persist; do
  echo "--- $d";
  if [ -d "$d" ]; then
    $BB ls -la "$d" 2>&1 | $BB head -n 40;
    $BB find "$d" -maxdepth 2 \( -iname '*cdsp*' -o -iname 'cdsp*' -o -iname '*turing*' \) 2>/dev/null | $BB head -n 80;
  else
    echo missing;
  fi;
done;
echo A90_V633_FIRMWARE_END""",
    ),
    (
        "threads-cdsp",
        r"""echo A90_V633_THREADS_BEGIN;
$BB ps -A -o pid,stat,comm 2>&1 | $BB grep -Ei 'cdsp|fastrpc|q6|sysmon|pil|turing' || true;
echo A90_V633_THREADS_END""",
    ),
    (
        "dmesg-cdsp",
        r"""echo A90_V633_DMESG_BEGIN;
$BB dmesg | $BB grep -Ei 'cdsp|turing|fastrpc|subsys|sysmon|service-notifier|firmware|pil|q6|boot_cdsp' | $BB tail -n 300 || true;
echo A90_V633_DMESG_END""",
    ),
)

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("boot_cdsp_dir", re.compile(r"/sys/kernel/boot_cdsp", re.I)),
    ("boot_cdsp_not_readable", re.compile(r"not-readable", re.I)),
    ("subsys_cdsp", re.compile(r"name=cdsp|cdsp", re.I)),
    ("subsys_offline", re.compile(r"state=OFFLINE|state=OFFLINING", re.I)),
    ("subsys_online", re.compile(r"state=ONLINE", re.I)),
    ("firmware_path_vendor", re.compile(r"firmware_class\.path=/vendor/firmware", re.I)),
    ("firmware_mount", re.compile(r"^(?!---)\S+\s+/(?:vendor/firmware_mnt|vendor/firmware-modem|vendor/firmware|firmware|mnt/vendor/persist)\b", re.I)),
    ("firmware_dir_missing", re.compile(r"^missing$", re.I)),
    ("cdsp_firmware_name", re.compile(r"cdsp|turing", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("service_notifier", re.compile(r"service-notifier", re.I)),
    ("fastrpc", re.compile(r"fastrpc", re.I)),
    ("direct_firmware_fail", re.compile(r"Direct firmware load.*failed|Falling back to sysfs fallback", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    return parser.parse_args()


def strip_protocol(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("a90:/#"):
            continue
        if line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line.startswith("[done] ") or line.startswith("[exit "):
            continue
        if line.startswith("run: pid="):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip() + "\n"


def count_markers(text: str) -> dict[str, int]:
    counts = {name: 0 for name, _ in MARKERS}
    for line in text.splitlines():
        for name, pattern in MARKERS:
            if pattern.search(line):
                counts[name] += 1
    return counts


def first_line(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for line in text.splitlines():
        if line.startswith("A90_V633_"):
            continue
        if compiled.search(line):
            return line.strip()
    return "missing"


def classify(counts: dict[str, int], captures_ok: bool) -> tuple[str, bool, str, str]:
    if not captures_ok:
        return (
            "v633-cdsp-readonly-capture-incomplete",
            False,
            "one or more read-only captures failed",
            "rerun V633 after bridge/device status is stable",
        )
    if counts.get("sysmon_cdsp", 0) > 0:
        return (
            "v633-cdsp-already-online",
            True,
            "native read-only evidence already contains CDSP sysmon",
            "compare service 74/WLAN-PD gap before any CDSP write proof",
        )
    if counts.get("firmware_path_vendor", 0) > 0 and counts.get("firmware_mount", 0) == 0:
        return (
            "v633-cdsp-firmware-surface-missing",
            True,
            "native read-only evidence has firmware_class.path set to a vendor firmware path but no matching firmware mount is visible",
            "mount/verify firmware surfaces read-only before any CDSP write proof",
        )
    if counts.get("subsys_offline", 0) > 0 and counts.get("subsys_online", 0) == 0:
        return (
            "v633-cdsp-subsys-unready",
            True,
            "CDSP-related subsystem state is not online in native read-only evidence",
            "classify exact CDSP subsystem/prerequisite before another write",
        )
    return (
        "v633-cdsp-readonly-surface-captured",
        True,
        "CDSP read-only surfaces were captured but no single missing prerequisite was proven",
        "build a narrower CDSP-only proof only after reviewing captured surfaces",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V633 CDSP Read-Only Surface Report",
        "",
        "- date: `2026-05-23 KST`",
        "- status: `captured/live-readonly`; Wi-Fi external ping is **not** complete",
        "- runner: `scripts/revalidation/native_wifi_cdsp_surface_collect_v633.py`",
        f"- evidence: `{manifest['out_dir']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Scope",
        "",
        "V633 contacts the current native device only through read-only shell",
        "commands. It collects CDSP boot-node metadata, subsystem state, firmware",
        "surface visibility, CDSP-related kernel threads, and CDSP-related dmesg",
        "markers.",
        "",
        "It does not write sysfs, boot ADSP/CDSP/SLPI, start daemons, start",
        "service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials,",
        "run DHCP, change routes, or ping externally.",
        "",
        "## Command Results",
        "",
        markdown_table(
            ["name", "ok", "rc", "status", "raw"],
            [
                [item["name"], str(item["ok"]), str(item["rc"]), item["status"], item["raw_file"]]
                for item in manifest["captures"]
            ],
        ),
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], [[key, str(value)] for key, value in manifest["counts"].items()]),
        "",
        "## Key Lines",
        "",
        markdown_table(["key", "line"], [[key, value] for key, value in manifest["key_lines"].items()]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def record_capture(store: EvidenceStore, out_dir: Path, captures: list[dict[str, Any]], name: str, capture: Any) -> str:
    raw_text = capture.text or capture.error
    stripped = strip_protocol(raw_text)
    store.write_text(f"{name}.txt", stripped)
    item = capture_to_manifest(capture)
    item["name"] = name
    item["raw_file"] = str(out_dir / f"{name}.txt")
    captures.append(item)
    return stripped


def is_busy_capture(capture: Any) -> bool:
    return capture.status == "busy" or capture.rc == -16


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    captures: list[dict[str, Any]] = []
    combined_text = ""

    bootstatus = run_capture(args, "bootstatus", ["bootstatus"], timeout=args.timeout)
    combined_text += "\n" + record_capture(store, out_dir, captures, "bootstatus", bootstatus)

    initial_hide = run_capture(args, "initial-hide", ["hide"], timeout=min(args.timeout, 10.0))
    combined_text += "\n" + record_capture(store, out_dir, captures, "initial-hide", initial_hide)

    for name, shell_script in COMMANDS:
        command = ["run", args.busybox, "sh", "-c", f"BB={args.busybox}; {shell_script}"]
        capture = run_capture(args, name, command, timeout=args.timeout)
        if is_busy_capture(capture):
            retry_hide = run_capture(args, f"{name}-hide-retry", ["hide"], timeout=min(args.timeout, 10.0))
            combined_text += "\n" + record_capture(store, out_dir, captures, f"{name}-hide-retry", retry_hide)
            capture = run_capture(args, name, command, timeout=args.timeout)
        combined_text += "\n" + record_capture(store, out_dir, captures, name, capture)

    counts = count_markers(combined_text)
    captures_ok = all(item["ok"] for item in captures if "hide" not in item["name"])
    decision, pass_ok, reason, next_step = classify(counts, captures_ok)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "out_dir": str(out_dir),
        "host": collect_host_metadata(),
        "captures": captures,
        "counts": counts,
        "key_lines": {
            "firmware_class_path": first_line(combined_text, r"firmware_class\.path="),
            "boot_cdsp_line": first_line(combined_text, r"/sys/kernel/boot_cdsp"),
            "cdsp_subsys_line": first_line(combined_text, r"^name=cdsp$"),
            "cdsp_state_line": first_line(combined_text, r"state=.*"),
            "cdsp_firmware_line": first_line(combined_text, r"firmware_name=cdsp|/cdsp|turing"),
            "sysmon_cdsp_line": first_line(combined_text, r"sysmon-qmi:.*cdsp"),
            "direct_firmware_fail_line": first_line(combined_text, r"Direct firmware load.*failed|Falling back to sysfs fallback"),
        },
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": True,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "boot_image_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"evidence: {out_dir}")
    print("sysfs_writes_executed: False")
    print("wifi_bringup_executed: False")
    print("external_ping_executed: False")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
