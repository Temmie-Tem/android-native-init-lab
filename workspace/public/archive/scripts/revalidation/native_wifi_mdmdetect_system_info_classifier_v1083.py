#!/usr/bin/env python3
"""V1083 host-only libmdmdetect get_system_info classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1083-mdmdetect-system-info-classifier")
DEFAULT_LIBMDMDETECT = Path("tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so")
DEFAULT_V1082_MANIFEST = Path("tmp/wifi/v1082-pm-service-instruction-trace-live/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1083-mdmdetect-system-info-classifier.txt")

REQUIRED_SYMBOLS = (
    "get_system_info",
    "get_subsystem_info",
    "esoc_supported",
    "get_esoc_details",
    "get_soc_name",
    "get_soc_link",
    "get_soc_port",
    "get_soc_ramdump_path",
)

KEY_STRINGS = {
    "esoc_root": "/sys/bus/esoc/devices",
    "msm_subsys_root": "/sys/bus/msm_subsys/devices",
    "dev_subsys_template": "/dev/subsys_%s",
    "esoc_name_attr": "esoc_name",
    "esoc_link_attr": "esoc_link",
    "esoc_link_info_attr": "esoc_link_info",
    "soc_name_modem": "modem",
    "soc_name_slpi": "slpi",
    "soc_name_spss": "spss",
    "sdx50m": "SDX50M",
    "failed_open": "Failed to open %s: %s",
    "failed_esoc_dir": "Failed to open ESOC dir",
    "failed_ssr_bus": "Failed to open ssr bus directory",
    "failed_ssr_root": "Failed to open SSR root dir: %s",
    "failed_information": "Failed to get information on : %s",
    "failed_find_ssr": "Failed to find a ssr entry for %s",
}

DEFAULT_SYMBOLS = {
    "get_system_info": {"value": "0x2c94", "size": 868},
    "get_subsystem_info": {"value": "0x2aa4", "size": 496},
    "esoc_supported": {"value": "0x276c", "size": 300},
    "get_esoc_details": {"value": "0x2904", "size": 416},
}

V1084_CANDIDATE_OFFSETS = {
    "mdm_get_system_info_entry": "0x2c94",
    "mdm_stat_esoc_call": "0x2d18",
    "mdm_esoc_stat_fail_branch": "0x2d1c",
    "mdm_esoc_opendir_call": "0x2d28",
    "mdm_esoc_opendir_fail_branch": "0x2d2c",
    "mdm_esoc_readdir_first": "0x2d34",
    "mdm_esoc_supported_call": "0x2d74",
    "mdm_get_esoc_details_call": "0x2d94",
    "mdm_msm_opendir_call": "0x2de8",
    "mdm_msm_opendir_fail_log": "0x2e50",
    "mdm_msm_readdir_first": "0x2df4",
    "mdm_msm_entry_process": "0x2e78",
    "mdm_get_soc_name_read_call": "0x2e94",
    "mdm_get_subsystem_info_nonmodem_call": "0x2ee8",
    "mdm_get_subsystem_info_modem_call": "0x2f1c",
    "mdm_success_return": "0x2f3c",
    "mdm_failure_after_msm_open": "0x2e54",
    "mdm_failure_get_info_log_nonmodem": "0x2fc4",
    "mdm_failure_get_info_log_modem": "0x2fe0",
    "mdm_failure_return_after_info": "0x2fec",
    "subsys_info_entry": "0x2aa4",
    "subsys_compare_slpi": "0x2b0c",
    "subsys_compare_modem": "0x2b24",
    "subsys_compare_spss": "0x2b3c",
    "subsys_device_path_format": "0x2c78",
    "subsys_success_return": "0x2c80",
}


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
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def run_capture(store: EvidenceStore, name: str, command: list[str], timeout: float = 30.0) -> dict[str, Any]:
    started = now_iso()
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
        output = result.stdout
        rc = result.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n[TIMEOUT]\n"
        rc = -1
    rel = f"analysis/{name}.txt"
    store.write_text(rel, output.rstrip() + "\n")
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "file": rel,
        "started_at": started,
    }


def command_output(command: list[str], timeout: float = 30.0) -> str:
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
    except subprocess.TimeoutExpired as exc:
        return (exc.stdout or "") + "\n[TIMEOUT]\n"
    return result.stdout


def parse_symbols(readelf_text: str) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+\S+\s+\S+\s+\S+\s+([A-Za-z0-9_]+)(?:@@?\S+)?\s*$"
    )
    for line in readelf_text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value_hex, size_text, symbol_type, name = match.groups()
        if name in REQUIRED_SYMBOLS or name == "supported_modems":
            symbols[name] = {
                "value": f"0x{int(value_hex, 16):x}",
                "size": int(size_text),
                "type": symbol_type,
            }
    return symbols


def focused_strings(strings_text: str) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for line in strings_text.splitlines():
        stripped = line.strip()
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            continue
        offset, text = parts
        for key, needle in KEY_STRINGS.items():
            if text == needle:
                found[key] = {"offset": f"0x{offset}", "text": text}
    return found


def range_for(symbols: dict[str, dict[str, Any]], symbol: str) -> tuple[str, str]:
    data = symbols.get(symbol) or DEFAULT_SYMBOLS[symbol]
    start = int(str(data["value"]), 16)
    size = int(data["size"])
    return f"0x{start:x}", f"0x{start + size:x}"


def objdump_binary() -> str:
    return shutil.which("aarch64-linux-gnu-objdump") or shutil.which("objdump") or "objdump"


def disasm_command(binary: Path, symbols: dict[str, dict[str, Any]], symbol: str) -> list[str]:
    start, stop = range_for(symbols, symbol)
    return [
        objdump_binary(),
        "-d",
        str(binary),
        f"--start-address={start}",
        f"--stop-address={stop}",
    ]


def all_offsets_aligned(offsets: dict[str, str]) -> bool:
    return all(int(value, 16) % 4 == 0 for value in offsets.values())


def classify(
    binary_exists: bool,
    v1082: dict[str, Any],
    symbols: dict[str, dict[str, Any]],
    found_strings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required_symbol_presence = {name: name in symbols for name in REQUIRED_SYMBOLS}
    string_presence = {name: name in found_strings for name in KEY_STRINGS}
    required_surface_keys = (
        "esoc_root",
        "msm_subsys_root",
        "dev_subsys_template",
        "esoc_name_attr",
        "esoc_link_attr",
        "esoc_link_info_attr",
        "soc_name_modem",
        "soc_name_slpi",
        "soc_name_spss",
    )
    required_surfaces_present = all(string_presence[key] for key in required_surface_keys)
    required_symbols_present = all(required_symbol_presence.values())
    v1082_confirms_get_system_info = (
        v1082.get("decision") == "v1082-pm-service-get-system-info-failure-branch-confirmed"
        and bool(v1082.get("pass"))
    )
    trace_counts = (((v1082.get("analysis") or {}).get("tracefs_uprobe") or {}).get("counts") or {})
    v1082_negative_controls = (
        int(trace_counts.get("helper_get_system_info_success_path", 0)) == 0
        and int(trace_counts.get("main_binder_driver_call", 0)) == 0
    )
    return {
        "binary_exists": binary_exists,
        "v1082_decision": v1082.get("decision", ""),
        "v1082_pass": bool(v1082.get("pass")),
        "v1082_confirms_get_system_info_failure": v1082_confirms_get_system_info,
        "v1082_negative_controls_present": v1082_negative_controls,
        "required_symbol_presence": required_symbol_presence,
        "required_symbols_present": required_symbols_present,
        "symbols": symbols,
        "string_presence": string_presence,
        "focused_strings": found_strings,
        "required_surfaces_present": required_surfaces_present,
        "get_system_info_model": [
            "validate caller output pointer",
            "stat /sys/bus/esoc/devices",
            "if ESOC root exists, opendir it and enumerate entries",
            "for supported ESOC entries, read esoc_name/esoc_link/esoc_link_info via get_esoc_details",
            "fall back to opendir /sys/bus/msm_subsys/devices",
            "enumerate subsystem entries and read name/state-style sysfs attributes",
            "classify slpi/modem/spss in get_subsystem_info",
            "format /dev/subsys_%s device paths for recognized subsystem entries",
            "return success only after enumeration completes without fatal classification failures",
        ],
        "android_state_requirements": [
            "/sys/bus/esoc/devices must be readable if the eSoC framework is present",
            "ESOC entries need esoc_name, esoc_link, and esoc_link_info attributes",
            "/sys/bus/msm_subsys/devices must be readable as the SSR fallback root",
            "MSM subsystem entries need readable name/state-style attributes",
            "recognized modem/slpi/spss entries must map to /dev/subsys_%s paths",
        ],
        "failure_classes_for_v1084": [
            "ESOC root stat or opendir failure",
            "ESOC entry accepted but get_esoc_details failure",
            "MSM subsystem root opendir failure",
            "MSM entry name read or get_subsystem_info failure",
            "recognized modem entry missing compatible /dev/subsys_%s device path state",
        ],
        "v1084_candidate_offsets": V1084_CANDIDATE_OFFSETS,
        "v1084_offsets_4byte_aligned": all_offsets_aligned(V1084_CANDIDATE_OFFSETS),
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not analysis["binary_exists"]:
        return (
            "v1083-libmdmdetect-missing",
            False,
            "local libmdmdetect.so is missing",
            "rerun V1073 vendor extraction before PM-service analysis",
        )
    if not analysis["v1082_confirms_get_system_info_failure"]:
        return (
            "v1083-v1082-proof-missing",
            False,
            "V1082 did not confirm the PM-service get_system_info failure branch",
            "rerun V1082 instruction trace before classifying libmdmdetect requirements",
        )
    if not analysis["v1082_negative_controls_present"]:
        return (
            "v1083-v1082-negative-controls-missing",
            False,
            "V1082 negative controls are missing or inconsistent",
            "inspect V1082 tracefs counts before selecting library offsets",
        )
    if not analysis["required_symbols_present"]:
        return (
            "v1083-libmdmdetect-symbols-incomplete",
            False,
            "required libmdmdetect symbols are not all visible",
            "use disassembly-only fallback around observed PLT target offsets",
        )
    if not analysis["required_surfaces_present"]:
        return (
            "v1083-libmdmdetect-surface-strings-incomplete",
            False,
            "required libmdmdetect sysfs/device strings are not all present",
            "refresh vendor extraction and reclassify the library surface",
        )
    if not analysis["v1084_offsets_4byte_aligned"]:
        return (
            "v1083-v1084-offset-alignment-failed",
            False,
            "one or more proposed ARM64 uprobe offsets are not 4-byte aligned",
            "fix V1084 candidate offsets before live tracing",
        )
    return (
        "v1083-mdmdetect-system-info-requirements-classified",
        True,
        "libmdmdetect get_system_info requires ESOC/MSM SSR sysfs enumeration and /dev/subsys_%s path synthesis; V1084 should trace the library branch actually failing",
        "run V1084 tracefs-only libmdmdetect instruction trace under the same PM observer, with no Wi-Fi HAL or bring-up",
    )


def markdown_table(rows: list[tuple[str, str]]) -> str:
    return "\n".join(["| item | value |", "| --- | --- |"] + [f"| `{key}` | `{value}` |" for key, value in rows])


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    symbols = analysis["symbols"]
    symbol_rows = [(name, f"{data['value']} size={data['size']}") for name, data in symbols.items()]
    string_rows = [
        (key, f"{value['offset']} {value['text']}")
        for key, value in analysis["focused_strings"].items()
    ]
    offset_rows = list(analysis["v1084_candidate_offsets"].items())
    return "\n".join([
        "# V1083 libmdmdetect System Info Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- libmdmdetect: `{manifest['libmdmdetect']}`",
        f"- v1082_manifest: `{manifest['v1082_manifest']}`",
        "",
        "## Model",
        "",
        *[f"- {item}" for item in analysis["get_system_info_model"]],
        "",
        "## Android State Requirements",
        "",
        *[f"- {item}" for item in analysis["android_state_requirements"]],
        "",
        "## Failure Classes for V1084",
        "",
        *[f"- {item}" for item in analysis["failure_classes_for_v1084"]],
        "",
        "## Symbols",
        "",
        markdown_table(symbol_rows),
        "",
        "## Focused Strings",
        "",
        markdown_table(string_rows),
        "",
        "## V1084 Candidate Offsets",
        "",
        markdown_table(offset_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--libmdmdetect", type=Path, default=DEFAULT_LIBMDMDETECT)
    parser.add_argument("--v1082-manifest", type=Path, default=DEFAULT_V1082_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    binary = repo_path(args.libmdmdetect)
    v1082 = load_json(args.v1082_manifest)
    commands: list[dict[str, Any]] = []

    readelf_text = ""
    strings_text = ""
    symbols: dict[str, dict[str, Any]] = {}
    found_strings: dict[str, dict[str, Any]] = {}
    if binary.exists():
        commands.append(run_capture(store, "libmdmdetect-file", ["file", str(binary)]))
        readelf_command = ["readelf", "-Ws", str(binary)]
        readelf_text = command_output(readelf_command)
        store.write_text("analysis/libmdmdetect-readelf-symbols.txt", readelf_text.rstrip() + "\n")
        commands.append({
            "name": "libmdmdetect-readelf-symbols",
            "command": readelf_command,
            "rc": 0 if readelf_text else 1,
            "ok": bool(readelf_text),
            "file": "analysis/libmdmdetect-readelf-symbols.txt",
            "started_at": now_iso(),
        })
        strings_command = ["strings", "-tx", str(binary)]
        strings_text = command_output(strings_command)
        found_strings = focused_strings(strings_text)
        focused_text = "\n".join(
            f"{value['offset']} {value['text']}"
            for value in found_strings.values()
        )
        store.write_text("analysis/libmdmdetect-strings-focused.txt", focused_text + ("\n" if focused_text else ""))
        commands.append({
            "name": "libmdmdetect-strings-focused",
            "command": strings_command,
            "rc": 0 if strings_text else 1,
            "ok": bool(strings_text),
            "file": "analysis/libmdmdetect-strings-focused.txt",
            "started_at": now_iso(),
        })
        commands.append(run_capture(store, "libmdmdetect-dynamic", ["readelf", "-d", str(binary)]))
        symbols = parse_symbols(readelf_text)
        for symbol in ("get_system_info", "get_subsystem_info", "esoc_supported", "get_esoc_details"):
            commands.append(run_capture(store, f"libmdmdetect-{symbol}-disasm", disasm_command(binary, symbols, symbol)))

    analysis = classify(binary.exists(), v1082, symbols, found_strings)
    decision, passed, reason, next_step = decide(analysis)
    manifest = {
        "cycle": "v1083",
        "generated_at": now_iso(),
        "libmdmdetect": str(binary),
        "v1082_manifest": str(repo_path(args.v1082_manifest)),
        "commands": commands,
        "analysis": analysis,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "bpf_attach_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
