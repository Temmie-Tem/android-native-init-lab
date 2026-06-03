#!/usr/bin/env python3
"""Host-only V1926 libqmi_cci WLFW service-wait classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1926"
DATE = "2026-06-04"
DEFAULT_LIBQMI_CCI64 = repo_path("tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmi_cci.so")
DEFAULT_OUT_DIR = repo_path("tmp/wifi/v1926-libqmi-cci-service-wait-static")
DEFAULT_REPORT_PATH = repo_path(f"docs/reports/NATIVE_INIT_{CYCLE}_LIBQMI_CCI_SERVICE_WAIT_STATIC_{DATE}.md")

SYMBOL_EXPECTATIONS = {
    "qmi_cci_xport_event_new_server": (0x48E8, 208),
    "qmi_client_notifier_init": (0x53B8, 960),
    "qmi_client_get_service_instance": (0x7400, 328),
    "qmi_client_init_instance": (0x7824, 372),
    "qmi_cci_os_signal_wait": (0x7E74, 392),
}

INSTRUCTION_EXPECTATIONS = {
    "init_entry": (0x7824, "sub\tsp, sp, #0x100"),
    "initial_get_service_instance_call": (0x789C, "qmi_client_get_service_instance@plt"),
    "initial_client_init_call": (0x78BC, "qmi_client_init@plt"),
    "notifier_init_call": (0x78EC, "qmi_client_notifier_init@plt"),
    "wait_call": (0x7904, "qmi_cci_os_signal_wait@plt"),
    "wait_timeout_flag_load": (0x7908, "ldr\tw8, [sp, #20]"),
    "wait_timeout_branch": (0x790C, "cbnz\tw8, 7954"),
    "loop_get_service_instance_call": (0x7920, "qmi_client_get_service_instance@plt"),
    "loop_wait_on_missing_service": (0x7924, "cbnz\tw0, 78fc"),
    "loop_client_init_call": (0x7940, "qmi_client_init@plt"),
    "init_timeout_rc": (0x7954, "mov\tw26, #0xfffffffd"),
    "init_release_notifier": (0x795C, "qmi_client_release@plt"),
    "init_return_rc": (0x7970, "mov\tw0, w26"),
    "signal_wait_entry": (0x7E74, "sub\tsp, sp, #0x60"),
    "signal_wait_timed_branch": (0x7E9C, "cbz\tw1, 7efc"),
    "signal_wait_timedwait_call": (0x7FB8, "pthread_cond_timedwait@plt"),
    "signal_wait_etimedout_check": (0x7FBC, "cmp\tw0, #0x6e"),
    "signal_wait_timeout_flag_store": (0x7FC8, "str\tw8, [x19, #4]"),
    "new_server_entry": (0x48E8, "sub\tsp, sp, #0x40"),
    "new_server_signal": (0x496C, "pthread_cond_signal@plt"),
    "new_server_callback": (0x49A0, "br\tx4"),
}

NEXT_LIVE_EVENTS = [
    ("libqmi_client_init_instance_entry", "libqmi_cci.so+0x7824", "fetch x0-x6; confirm WLFW worker enters libqmi with timeout/user-handle args"),
    ("libqmi_initial_get_service_instance_ret", "libqmi_cci.so+0x78a0", "return from the initial service-list lookup"),
    ("libqmi_notifier_init_call", "libqmi_cci.so+0x78ec", "fallback path creates service notifier after absent service or init -2"),
    ("libqmi_wait_call", "libqmi_cci.so+0x7904", "worker is about to block in qmi_cci_os_signal_wait"),
    ("libqmi_loop_get_service_instance_call", "libqmi_cci.so+0x7920", "repeated service-list retry after notifier wake"),
    ("libqmi_init_timeout_path", "libqmi_cci.so+0x7954", "bounded timeout path returns QMI_TIMEOUT_ERR -3"),
    ("libqmi_init_return", "libqmi_cci.so+0x7970", "function return with rc in w26"),
    ("libqmi_signal_wait_entry", "libqmi_cci.so+0x7e74", "confirm actual wait primitive and timeout argument"),
    ("libqmi_signal_wait_timedwait", "libqmi_cci.so+0x7fb8", "pthread_cond_timedwait loop hit"),
    ("libqmi_signal_wait_timeout_store", "libqmi_cci.so+0x7fc8", "wait timed out and set os_params timedout flag"),
    ("libqmi_xport_new_server_entry", "libqmi_cci.so+0x48e8", "libqmi transport observed any new-server event"),
    ("libqmi_xport_new_server_signal", "libqmi_cci.so+0x496c", "new-server event signaled notifier waiters"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libqmi-cci64", type=Path, default=DEFAULT_LIBQMI_CCI64)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def run_text(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=repo_path("."),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def parse_symbols(readelf_text: str) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    regex = re.compile(
        r"^\s*\d+:\s+([0-9A-Fa-f]+)\s+(\d+)\s+FUNC\s+\S+\s+\S+\s+\S+\s+([^\s@]+)"
    )
    for line in readelf_text.splitlines():
        match = regex.match(line)
        if not match:
            continue
        name = match.group(3)
        if name in SYMBOL_EXPECTATIONS:
            symbols[name] = {
                "addr": int(match.group(1), 16),
                "size": int(match.group(2), 10),
                "line": line.strip(),
            }
    return symbols


def parse_instructions(objdump_text: str) -> dict[int, str]:
    instructions: dict[int, str] = {}
    regex = re.compile(r"^\s*([0-9A-Fa-f]+):\s+(.*)$")
    for line in objdump_text.splitlines():
        match = regex.match(line)
        if match:
            instructions[int(match.group(1), 16)] = line.rstrip()
    return instructions


def extract_range(instructions: dict[int, str], start: int, end: int) -> str:
    lines = [line for addr, line in sorted(instructions.items()) if start <= addr < end]
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if not args.libqmi_cci64.exists():
        raise FileNotFoundError(args.libqmi_cci64)

    readelf_rc, readelf_text = run_text(["readelf", "-Ws", str(args.libqmi_cci64)])
    objdump_rc, objdump_text = run_text(["aarch64-linux-gnu-objdump", "-d", str(args.libqmi_cci64)])
    store.write_text("host/readelf-symbols.txt", readelf_text)
    store.write_text("host/libqmi_cci64.objdump.txt", objdump_text)

    symbols = parse_symbols(readelf_text)
    instructions = parse_instructions(objdump_text)
    symbol_checks: list[dict[str, Any]] = []
    for name, (addr, size) in SYMBOL_EXPECTATIONS.items():
        actual = symbols.get(name, {})
        symbol_checks.append(
            {
                "name": name,
                "expected_addr": f"0x{addr:x}",
                "actual_addr": f"0x{actual.get('addr', -1):x}" if actual else "missing",
                "expected_size": size,
                "actual_size": actual.get("size"),
                "ok": actual.get("addr") == addr and actual.get("size") == size,
                "line": actual.get("line", ""),
            }
        )

    instruction_checks: list[dict[str, Any]] = []
    for name, (addr, needle) in INSTRUCTION_EXPECTATIONS.items():
        line = instructions.get(addr, "")
        instruction_checks.append(
            {
                "name": name,
                "offset": f"0x{addr:x}",
                "needle": needle,
                "line": line,
                "ok": bool(line) and needle in line,
            }
        )

    ranges = {
        "qmi_client_init_instance": extract_range(instructions, 0x7824, 0x7998),
        "qmi_cci_os_signal_wait": extract_range(instructions, 0x7E74, 0x7FFC),
        "qmi_cci_xport_event_new_server": extract_range(instructions, 0x48E8, 0x49B8),
    }
    for name, text in ranges.items():
        store.write_text(f"host/{name}.disasm.txt", text + "\n")

    pass_checks = readelf_rc == 0 and objdump_rc == 0 and all(item["ok"] for item in symbol_checks + instruction_checks)
    label = "qmi-client-init-instance-service-wait-map-pass" if pass_checks else "qmi-client-init-instance-service-wait-map-mismatch"
    reason = (
        "qmi_client_init_instance first tries service lookup/init, then creates a notifier and loops "
        "qmi_client_get_service_instance -> qmi_cci_os_signal_wait until service publication or timeout"
        if pass_checks
        else "libqmi_cci symbols or expected wait-loop instructions did not match the captured vendor binary"
    )
    return {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "label": label,
        "pass": pass_checks,
        "reason": reason,
        "libqmi_cci64": rel(args.libqmi_cci64),
        "out_dir": rel(args.out_dir),
        "readelf_rc": readelf_rc,
        "objdump_rc": objdump_rc,
        "symbol_checks": symbol_checks,
        "instruction_checks": instruction_checks,
        "next_live_events": [
            {"event": event, "target": target, "purpose": purpose}
            for event, target, purpose in NEXT_LIVE_EVENTS
        ],
        "host_metadata": collect_host_metadata(),
    }


def render_report(manifest: dict[str, Any]) -> str:
    symbol_rows = [
        [
            item["name"],
            item["ok"],
            item["actual_addr"],
            item["actual_size"],
        ]
        for item in manifest["symbol_checks"]
    ]
    instruction_rows = [
        [
            item["name"],
            item["ok"],
            item["offset"],
            item["line"],
        ]
        for item in manifest["instruction_checks"]
    ]
    event_rows = [
        [item["event"], item["target"], item["purpose"]]
        for item in manifest["next_live_events"]
    ]
    return "\n".join(
        [
            "# Native Init V1926 Libqmi CCI Service-wait Static",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            f"- Binary: `{manifest['libqmi_cci64']}`",
            "",
            "## Static Interpretation",
            "",
            "- V1925 proved the WLFW worker enters `qmi_client_init_instance` and does not reach the caller return check.",
            "- This binary maps that call to an internal wait loop: initial service lookup/init, notifier setup, repeated service lookup, then `qmi_cci_os_signal_wait`.",
            "- `qmi_cci_os_signal_wait` uses `pthread_cond_timedwait` when the caller passes a nonzero timeout and stores a timeout flag before `qmi_client_init_instance` returns `-3`.",
            "- `qmi_cci_xport_event_new_server` is the transport-side wake edge that signals notifier waiters when libqmi observes service publication.",
            "",
            "## Symbols",
            "",
            markdown_table(["symbol", "ok", "addr", "size"], [[str(cell) for cell in row] for row in symbol_rows]),
            "",
            "## Wait-loop Instructions",
            "",
            markdown_table(["check", "ok", "offset", "instruction"], [[str(cell) for cell in row] for row in instruction_rows]),
            "",
            "## Next Live Observer",
            "",
            markdown_table(["event", "target", "purpose"], event_rows),
            "",
            "## Decision",
            "",
            "- Next live unit should add a separate `libqmi_cci.so` uprobe target group in the cnss-daemon process.",
            "- Classify `qmi-client-init-instance-waiting-no-new-server` if wait events hit but `qmi_cci_xport_event_new_server` stays absent for WLFW69/WLAN-PD.",
            "- Classify `qmi-client-init-instance-new-server-no-wake` if new-server events hit but the wait loop does not return to service lookup/init progress.",
            "- Classify `qmi-client-init-instance-timeout` if the timeout path at `0x7954` hits.",
            "- Do not use Wi-Fi HAL/scan/connect/ping until WLFW69/WLAN-PD/wlan0 exists.",
            "",
            "## Safety Scope",
            "",
            "Host-only static analysis. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(args.out_dir)
    store.mkdir("host")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(f"{'PASS' if manifest['pass'] else 'FAIL'} label={manifest['label']} out_dir={rel(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
