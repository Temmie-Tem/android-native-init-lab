#!/usr/bin/env python3
"""Host-only V1703 classifier for cnss-daemon WLFW downstream control flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1703"
DATE = "2026-06-02"
EXPECTED_CNSS_SHA = "bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc"
DEFAULT_CNSS_DAEMON = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v226-vendor-root-live-export"
    / "vendor-source"
    / "bin"
    / "cnss-daemon"
)
DEFAULT_OBJDUMP = REPO_ROOT / "tmp" / "wifi" / "cnss-daemon.objdump.txt"
DEFAULT_V1702_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1702-wlan-pd-cnss-tracefs-target-path-handoff"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1703-cnss-wlfw-downstream-static"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / f"NATIVE_INIT_{CYCLE}_CNSS_WLFW_DOWNSTREAM_STATIC_{DATE}.md"
)
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


EXPECTED_SYMBOLS = {
    "wlfw_start": {"address": "0xec00", "size": 464, "binding": "GLOBAL"},
    "wlfw_stop": {"address": "0xedd0", "size": 1176, "binding": "GLOBAL"},
    "pthread_initialize_dms": {"address": "0xeb14", "size": 236, "binding": "GLOBAL"},
    "dms_service_request": {"address": "0xe808", "size": 780, "binding": "GLOBAL"},
    "dms_get_wlan_address": {"address": "0xe544", "size": 324, "binding": "GLOBAL"},
    "wlfw_service_request": {"address": "0xd9fc", "size": 1796, "binding": "GLOBAL"},
    "wlfw_send_ind_register_req": {"address": "0xf268", "size": 364, "binding": "LOCAL"},
    "wlfw_send_cap_req": {"address": "0xf3d4", "size": 460, "binding": "LOCAL"},
    "wlfw_send_bdf_download_req": {"address": "0xf76c", "size": 1576, "binding": "LOCAL"},
    "wlfw_send_cal_report_req": {"address": "0xf5a0", "size": 460, "binding": "LOCAL"},
    "wlfw_qmi_ind_cb": {"address": "0xe100", "size": 952, "binding": "LOCAL"},
    "wlfw_qmi_err_cb": {"address": "0xe4b8", "size": 140, "binding": "LOCAL"},
    "wlfw_handle_ind_data": {"address": "0xce24", "size": 2724, "binding": "GLOBAL"},
    "pm_init": {"address": "0xc39c", "size": 760, "binding": "GLOBAL"},
}

EXPECTED_STRINGS = {
    "wlfw_start": "0x5ab9",
    "wlfw_service_request": "0x64a4",
    "dms_service_request": "0x42ce",
    "WLFW service connected": "0x5723",
    "wlfw_send_ind_register_req": "0x5c7b",
    "wlfw_send_cap_req": "0x71ef",
    "wlfw_send_bdf_download_req": "0x5407",
    "wlfw_send_cal_download_req": "0x64da",
    "Wait for FW memory ready indication": "0x6cdf",
    "FW memory is ready": "0x53f4",
    "Wait for MSA ready Indication from FW": "0x4d43",
    "MSA is ready": "0x4a77",
    "Wait for CNSS_BDF_DOWNLOAD_DONE": "0x6c90",
    "bdwlan.bin": "0x5c96",
    "regdb.bin": "0x6f41",
    "Failed to Download the BDF File": "0x40c7",
    "Failed to Download the REGDB File": "0x6f09",
    "Failed to send capability request": "0x5fcc",
}

EXPECTED_PATTERNS = {
    "main_calls_wlfw_start": "9220:\t94001678 \tbl\tec00",
    "wlfw_start_entry": "ec00:\ta9be7bfd \tstp\tx29, x30, [sp, #-32]!",
    "wlfw_start_logs_starting": "ec24:\t97ffed7e \tbl\ta21c",
    "wlfw_start_calls_pthread_initialize_dms": "ecd4:\t97ffff90 \tbl\teb14",
    "pthread_initialize_dms_thread_target": "eba8:\t91202042 \tadd\tx2, x2, #0x808",
    "pthread_initialize_dms_pthread_create": "ebb4:\t94001577 \tbl\t14190 <pthread_create@plt>",
    "wlfw_start_service_thread_target": "ece4:\t9127f042 \tadd\tx2, x2, #0x9fc",
    "wlfw_start_service_pthread_create": "ecf0:\t94001528 \tbl\t14190 <pthread_create@plt>",
    "wlfw_start_success_flag": "edc0:\t39052109 \tstrb\tw9, [x8, #328]",
    "dms_service_request_entry": "e808:\ta9ba7bfd \tstp\tx29, x30, [sp, #-96]!",
    "dms_get_system_info": "e884:\t94001683 \tbl\t14290 <get_system_info@plt>",
    "dms_client_init_instance": "e928:\t9400168e \tbl\t14360 <qmi_client_init_instance@plt>",
    "dms_get_wlan_address_call": "e994:\t97fffeec \tbl\te544",
    "dms_send_mac_qmi": "ea90:\t940015a0 \tbl\t14110 <qmi_client_send_msg_sync@plt>",
    "wlfw_service_request_entry": "d9fc:\td103c3ff \tsub\tsp, sp, #0xf0",
    "wlfw_client_init_instance": "daa8:\t94001a2e \tbl\t14360 <qmi_client_init_instance@plt>",
    "wlfw_service_instance_query": "db18:\t94001a16 \tbl\t14370 <qmi_client_get_service_instance@plt>",
    "wlfw_service_ind_register_call": "dbbc:\t940005ab \tbl\tf268",
    "wlfw_service_cap_call": "dc24:\t940005ec \tbl\tf3d4",
    "wlfw_wait_condition": "dc18:\t940019de \tbl\t14390 <pthread_cond_wait@plt>",
    "wlfw_send_ind_register_msg20": "f318:\t52800401 \tmov\tw1, #0x20",
    "wlfw_send_ind_register_qmi": "f32c:\t94001379 \tbl\t14110 <qmi_client_send_msg_sync@plt>",
    "wlfw_send_cap_msg24": "f42c:\t52800481 \tmov\tw1, #0x24",
    "wlfw_send_cap_qmi": "f460:\t9400132c \tbl\t14110 <qmi_client_send_msg_sync@plt>",
    "wlfw_send_bdf_msg25": "fc34:\t528004a1 \tmov\tw1, #0x25",
    "wlfw_send_bdf_qmi": "fc44:\t94001133 \tbl\t14110 <qmi_client_send_msg_sync@plt>",
}

QMI_CALLS = [
    {
        "function": "dms_get_wlan_address",
        "call_site": "0xe59c",
        "message_id": "0x5c",
        "request_len": "0x4",
        "response_len": "0x18",
        "timeout_ms": 10000,
        "meaning": "DMS WLAN MAC/address query before DMS thread sends MAC to FW",
    },
    {
        "function": "dms_service_request",
        "call_site": "0xea90",
        "message_id": "0x33",
        "request_len": "0x7",
        "response_len": "0x8",
        "timeout_ms": 10000,
        "meaning": "DMS path sends MAC/address data once WLFW state allows it",
    },
    {
        "function": "wlfw_send_ind_register_req",
        "call_site": "0xf32c",
        "message_id": "0x20",
        "request_len": "0x30",
        "response_len": "0x18",
        "timeout_ms": 10000,
        "meaning": "WLFW indication registration; first concrete QMI sync after WLFW service client exists",
    },
    {
        "function": "wlfw_send_cap_req",
        "call_site": "0xf460",
        "message_id": "0x24",
        "request_len": "0x1",
        "response_len": "0x108",
        "timeout_ms": 10000,
        "meaning": "WLFW capability query; follows indication registration and gates BDF/CAL flow",
    },
    {
        "function": "wlfw_send_bdf_download_req",
        "call_site": "0xfc44",
        "message_id": "0x25",
        "request_len": "0x1824",
        "response_len": "0x18",
        "timeout_ms": 10000,
        "meaning": "BDF/REGDB transfer chunks; downstream and not expected before WLFW service is published",
    },
]

NEXT_TRACE_TARGETS = [
    {
        "target": "cnss-daemon+0xd9fc",
        "function": "wlfw_service_request",
        "purpose": "prove the main WLFW worker thread starts after wlfw_start",
    },
    {
        "target": "cnss-daemon+0xe808",
        "function": "dms_service_request",
        "purpose": "prove the DMS worker thread starts; lower priority than wlfw_service_request",
    },
    {
        "target": "cnss-daemon+0xf32c",
        "function": "wlfw_send_ind_register_req/qmi_client_send_msg_sync",
        "purpose": "prove WLFW indication-register QMI send is attempted after service client setup",
    },
    {
        "target": "cnss-daemon+0xf460",
        "function": "wlfw_send_cap_req/qmi_client_send_msg_sync",
        "purpose": "prove capability QMI send is attempted or absent",
    },
]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def cloexec_flag() -> int:
    return getattr(os, "O_CLOEXEC", 0)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory path: {path}")
    path.chmod(PRIVATE_DIR_MODE)


def write_private_bytes(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_text(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)


def ensure_objdump(binary: Path, objdump: Path) -> None:
    if objdump.exists():
        return
    try:
        text = run_text(["aarch64-linux-gnu-objdump", "-d", str(binary)])
    except (FileNotFoundError, subprocess.CalledProcessError):
        text = run_text(["objdump", "-d", str(binary)])
    write_private_text(objdump, text)


def extract_debug_symbols(binary: Path, out_dir: Path) -> dict[str, Any]:
    compressed = out_dir / "cnss-daemon.gnu_debugdata.xz"
    elf = out_dir / "cnss-daemon.gnu_debugdata.elf"
    input_copy = out_dir / "cnss-daemon.input-copy"
    objcopy = shutil.which("aarch64-linux-gnu-objcopy") or shutil.which("llvm-objcopy")
    if not objcopy:
        return {"available": False, "error": "objcopy unavailable", "symbols": {}}
    try:
        write_private_bytes(input_copy, binary.read_bytes())
        run_text([objcopy, "--dump-section", f".gnu_debugdata={compressed}", str(input_copy)])
        debug_elf = subprocess.check_output(["xz", "-dc", str(compressed)])
        write_private_bytes(elf, debug_elf)
        symbols_text = run_text(["readelf", "-Ws", str(elf)])
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"available": False, "error": str(exc), "symbols": {}}
    return {
        "available": True,
        "error": "",
        "input_copy": display_path(input_copy),
        "compressed": display_path(compressed),
        "elf": display_path(elf),
        "symbols": parse_symbols(symbols_text),
    }


def parse_symbols(text: str) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 8 or not parts[0].rstrip(":").isdigit():
            continue
        value, size, sym_type, binding, section, name = (
            parts[1],
            parts[2],
            parts[3],
            parts[4],
            parts[6],
            parts[7],
        )
        if name in EXPECTED_SYMBOLS:
            symbols[name] = {
                "address": f"0x{int(value, 16):x}",
                "size": int(size),
                "type": sym_type,
                "binding": binding,
                "section": section,
            }
    return symbols


def parse_strings(binary: Path) -> dict[str, str]:
    output = run_text(["strings", "-a", "-t", "x", str(binary)])
    result: dict[str, str] = {}
    wanted = set(EXPECTED_STRINGS)
    for line in output.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        offset_text, value = parts
        if value not in wanted:
            continue
        try:
            offset = int(offset_text, 16)
        except ValueError:
            continue
        result[value] = f"0x{offset:x}"
    return result


def intish(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def check_symbols(found: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for name, expected in EXPECTED_SYMBOLS.items():
        actual = found.get(name, {})
        checks[name] = {
            "expected": expected,
            "actual": actual or None,
            "match": (
                actual.get("address") == expected["address"]
                and actual.get("size") == expected["size"]
                and actual.get("binding") == expected["binding"]
            ),
        }
    return checks


def check_strings(found: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {
        text: {
            "expected_offset": expected,
            "actual_offset": found.get(text),
            "match": found.get(text) == expected,
        }
        for text, expected in EXPECTED_STRINGS.items()
    }


def check_patterns(disassembly: str) -> dict[str, bool]:
    return {name: pattern in disassembly for name, pattern in EXPECTED_PATTERNS.items()}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1702 = read_json(args.v1702_manifest)
    gate = v1702.get("gate", {})
    rollback = v1702.get("rollback", {})
    ensure_objdump(args.cnss_daemon, args.objdump)
    disassembly = args.objdump.read_text(encoding="utf-8", errors="replace")
    debugdata = extract_debug_symbols(args.cnss_daemon, args.out_dir)
    strings_found = parse_strings(args.cnss_daemon)
    symbols = check_symbols(debugdata.get("symbols", {}))
    strings = check_strings(strings_found)
    patterns = check_patterns(disassembly)
    binary_sha = sha256_file(args.cnss_daemon)

    v1702_ready = (
        v1702.get("decision") == "v1702-cnss-wlfw-entry-hit-downstream-wait-rollback-pass"
        and v1702.get("pass") is True
        and rollback.get("ok") is True
        and gate.get("nonlog_label") == "cnss-wlfw-entry-hit-downstream-wait"
        and intish(gate.get("nonlog_uprobe_hit_count")) >= 1
        and gate.get("old_firmware_serve_label") == "firmware-not-requested"
        and gate.get("cnss_daemon_running") == "1"
        and gate.get("tftp_running") == "1"
    )
    static_ready = (
        binary_sha == EXPECTED_CNSS_SHA
        and bool(debugdata.get("available"))
        and all(item["match"] for item in symbols.values())
        and all(item["match"] for item in strings.values())
        and all(patterns.values())
    )
    pass_ok = v1702_ready and static_ready
    decision = (
        "v1703-cnss-wlfw-downstream-static-map-pass"
        if pass_ok
        else "v1703-cnss-wlfw-downstream-static-map-incomplete"
    )
    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1702 proved cnss-daemon reaches wlfw_start; debug symbols and disassembly map the downstream WLFW worker/QMI wait path"
            if pass_ok
            else "V1702 basis or cnss-daemon downstream static mapping is incomplete"
        ),
        "inputs": {
            "v1702_manifest": display_path(args.v1702_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "objdump": display_path(args.objdump),
        },
        "binary": {
            "sha256": binary_sha,
            "sha256_ok": binary_sha == EXPECTED_CNSS_SHA,
            "size": args.cnss_daemon.stat().st_size,
        },
        "v1702": {
            "decision": v1702.get("decision"),
            "pass": v1702.get("pass"),
            "rollback_ok": rollback.get("ok"),
            "nonlog_label": gate.get("nonlog_label"),
            "uprobe_hit_count": gate.get("nonlog_uprobe_hit_count"),
            "first_hit_line": gate.get("nonlog_uprobe_first_hit_line"),
            "legacy_firmware_serve_label": gate.get("old_firmware_serve_label"),
            "cnss_daemon_running": gate.get("cnss_daemon_running"),
            "tftp_running": gate.get("tftp_running"),
            "mhi_pipe_fd_count": gate.get("nonlog_mhi_pipe_fd_count"),
            "ks_process_count": gate.get("nonlog_ks_process_count"),
        },
        "debugdata": debugdata,
        "symbols": symbols,
        "strings": strings,
        "patterns": patterns,
        "qmi_calls": QMI_CALLS,
        "control_flow": {
            "entry": "wlfw_start@0xec00",
            "workers": [
                "pthread_initialize_dms creates dms_service_request@0xe808 at pthread_create@0xebb4",
                "wlfw_start creates wlfw_service_request@0xd9fc at pthread_create@0xecf0",
            ],
            "wlfw_worker_core": [
                "wlfw_service_request initializes WLFW QMI client with qmi_client_init_instance@0xdaa8",
                "wlfw_service_request resolves service instance at qmi_client_get_service_instance@0xdb18",
                "wlfw_service_request sends indication registration through wlfw_send_ind_register_req@0xf268",
                "wlfw_service_request waits on pthread_cond_wait@0xdc18 when FW memory/BDF state is not ready",
                "wlfw_service_request sends capability request through wlfw_send_cap_req@0xf3d4 after the wait condition is satisfied",
            ],
            "dms_worker_core": [
                "dms_service_request queries get_system_info@0xe884 and initializes DMS QMI at 0xe928",
                "dms_service_request waits on pthread_cond_wait@0xea10 until WLFW state permits MAC send",
                "dms_service_request sends DMS/MAC QMI at qmi_client_send_msg_sync@0xea90",
            ],
        },
        "next_gate": {
            "cycle": "V1704",
            "type": "one-run rollbackable read-only tracefs uprobe classifier",
            "route": "reuse V1702 internal-modem firmware-serve route only",
            "primary_targets": NEXT_TRACE_TARGETS,
            "labels": [
                "wlfw-worker-thread-started-waiting-for-qmi-service",
                "wlfw-worker-thread-started-qmi-ind-register-sent",
                "wlfw-worker-thread-started-qmi-cap-sent",
                "wlfw-worker-thread-missing-after-wlfw-start",
                "cnss-target-unavailable",
            ],
            "forbidden": [
                "PM/service-window actors",
                "boot_wlan as a WLFW trigger",
                "/dev/subsys_esoc0",
                "forced RC1",
                "fake-ONLINE",
                "PMIC/GPIO/GDSC writes",
                "eSoC notify/BOOT_DONE",
                "PCI rescan",
                "platform bind/unbind",
                "Wi-Fi HAL",
                "scan/connect",
                "credentials",
                "DHCP/routes",
                "external ping",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    status = "PASS" if result["pass"] else "FAIL"
    lines = [
        "# Native Init V1703 CNSS WLFW Downstream Static Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{result['cycle']}`",
        "- Type: host-only cnss-daemon WLFW downstream static classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{status}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{display_path(DEFAULT_OUT_DIR)}`",
        "",
        "## V1702 Basis",
        "",
        f"- V1702 decision: `{result['v1702']['decision']}`",
        f"- V1702 non-log label: `{result['v1702']['nonlog_label']}`",
        f"- Rollback OK: `{result['v1702']['rollback_ok']}`",
        f"- `wlfw_start` uprobe hit count: `{result['v1702']['uprobe_hit_count']}`",
        f"- First hit: `{result['v1702']['first_hit_line']}`",
        f"- Legacy firmware-serve label: `{result['v1702']['legacy_firmware_serve_label']}`",
        f"- `cnss-daemon` / `tftp_server` running: `{result['v1702']['cnss_daemon_running']}` / `{result['v1702']['tftp_running']}`",
        f"- MHI pipe fd / `ks` process count: `{result['v1702']['mhi_pipe_fd_count']}` / `{result['v1702']['ks_process_count']}`",
        "",
        "## Static Inputs",
        "",
        f"- Binary: `{result['inputs']['cnss_daemon']}`",
        f"- SHA256: `{result['binary']['sha256']}`",
        f"- SHA256 expected: `{result['binary']['sha256_ok']}`",
        f"- `.gnu_debugdata` available: `{result['debugdata']['available']}`",
        "",
        "## WLFW Control Flow",
        "",
        "- `wlfw_start@0xec00` is the confirmed entry hit by V1702.",
        "- `pthread_initialize_dms@0xeb14` creates `dms_service_request@0xe808` at `pthread_create@0xebb4`.",
        "- `wlfw_start@0xec00` creates `wlfw_service_request@0xd9fc` at `pthread_create@0xecf0`.",
        "- `wlfw_service_request@0xd9fc` is the primary downstream worker: WLFW QMI client init, service instance resolution, indication registration, condition waits, then capability/BDF flow.",
        "- `dms_service_request@0xe808` is secondary: DMS/system-info/MAC path that waits until WLFW state permits sending MAC data.",
        "",
        "## Key Symbols",
        "",
        "| Symbol | Expected | Actual | Match |",
        "| --- | --- | --- | --- |",
    ]
    for name, item in result["symbols"].items():
        expected = item["expected"]
        actual = item["actual"] or {}
        lines.append(
            f"| `{name}` | `{expected['address']}` size `{expected['size']}` `{expected['binding']}` | "
            f"`{actual.get('address')}` size `{actual.get('size')}` `{actual.get('binding')}` | `{item['match']}` |"
        )
    lines.extend([
        "",
        "## QMI Sync Calls",
        "",
        "| Function | Call Site | Message | Req | Resp | Timeout | Meaning |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for call in result["qmi_calls"]:
        lines.append(
            f"| `{call['function']}` | `{call['call_site']}` | `{call['message_id']}` | "
            f"`{call['request_len']}` | `{call['response_len']}` | `{call['timeout_ms']} ms` | {call['meaning']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- The corrected premise stands: `cnss-daemon` reaches `wlfw_start`; previous missing dmesg/log evidence was a logging artifact.",
        "- The next unknown is not whether `wlfw_start` is entered, but whether `wlfw_service_request` starts and reaches WLFW QMI sends.",
        "- If `wlfw_service_request@0xd9fc` is hit but `wlfw_send_ind_register_req@0xf32c` is not, the block is before WLFW QMI client/service readiness.",
        "- If `0xf32c` is hit and later WLFW 69 remains absent, the block is the modem/WLAN-PD side not publishing or responding to WLFW QMI.",
        "- `wlfw_send_bdf_download_req@0xfc44` is downstream; do not chase BDF/REGDB until WLFW service and capability flow exist.",
        "",
        "## V1704 Proposed Gate",
        "",
        "- Type: one-run rollbackable read-only tracefs uprobe classifier.",
        "- Route: reuse V1702 internal-modem firmware-serve route only.",
        "- Primary trace targets: `cnss-daemon+0xd9fc`, `cnss-daemon+0xf32c`, `cnss-daemon+0xf460`; optional secondary target `cnss-daemon+0xe808`.",
        "- Fixed labels: `wlfw-worker-thread-started-waiting-for-qmi-service`, `wlfw-worker-thread-started-qmi-ind-register-sent`, `wlfw-worker-thread-started-qmi-cap-sent`, `wlfw-worker-thread-missing-after-wlfw-start`, `cnss-target-unavailable`.",
        "- Forbidden: PM/service-window actors, `boot_wlan` as a WLFW trigger, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--v1702-manifest", type=Path, default=DEFAULT_V1702_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    for path in (args.cnss_daemon, args.v1702_manifest):
        if not path.exists():
            raise SystemExit(f"missing required input: {display_path(path)}")

    ensure_private_dir(args.out_dir)
    result = build_manifest(args)
    manifest_path = args.out_dir / "manifest.json"
    write_private_text(manifest_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(result))
    print(json.dumps({
        "cycle": result["cycle"],
        "decision": result["decision"],
        "pass": result["pass"],
        "manifest": display_path(manifest_path),
        "report": display_path(args.report),
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
