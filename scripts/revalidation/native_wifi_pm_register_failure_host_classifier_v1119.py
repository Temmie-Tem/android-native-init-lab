#!/usr/bin/env python3
"""V1119 host-only classifier for CNSS PM register failure semantics."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1119-pm-register-failure-host-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1119-pm-register-failure-host-classifier.txt")
DEFAULT_V1118_MANIFEST = Path("tmp/wifi/v1118-global-holder-zero-delay-cnss-live/manifest.json")
DEFAULT_PERIPHERAL_CLIENT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so")
EXPECTED_V1118_DECISION = "v1118-zero-delay-cnss-pm-register-path-reached"

SYMBOLS = {
    "pm_register_connect": "_ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event",
    "pm_client_register": "pm_client_register",
    "pm_client_connect": "pm_client_connect",
}

PM_CLIENT_REGISTER_OFFSETS = {
    "entry": "0x6ec8",
    "pm_register_connect_call": "0x7034",
    "pm_register_connect_return_branch": "0x7038",
    "connect_failure_log_call": "0x70fc",
    "connect_failure_return_set": "0x7104",
    "argument_failure_return_set": "0x7124",
    "success_return_set": "0x7180",
}

PM_REGISTER_CONNECT_OFFSETS = {
    "entry": "0x612c",
    "init_vndbinder_call": "0x6168",
    "default_service_manager_call": "0x6190",
    "get_service_call": "0x61c4",
    "service_binder_null_check": "0x620c",
    "as_interface_call": "0x6218",
    "interface_null_check": "0x6254",
    "remote_register_call": "0x6274",
    "remote_register_return_check": "0x6278",
    "remote_register_failure_cleanup": "0x662c",
    "failure_return_set": "0x6690",
    "success_return_set": "0x6594",
    "function_return": "0x66dc",
}

V1120_TRACE_CANDIDATES = [
    {
        "label": "pm_register_connect_entry",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["entry"],
        "fetch": "client_ptr=%x0 event_ptr=%x1",
        "reason": "prove cnss-daemon enters lower PM client helper",
    },
    {
        "label": "pm_register_connect_service_null_check",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["service_binder_null_check"],
        "fetch": "binder=%x8",
        "reason": "distinguish vendor.qcom.PeripheralManager lookup failure from later Binder failures",
    },
    {
        "label": "pm_register_connect_interface_null_check",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["interface_null_check"],
        "fetch": "iface=%x0",
        "reason": "distinguish IPeripheralManager::asInterface failure",
    },
    {
        "label": "pm_register_connect_remote_register_call",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["remote_register_call"],
        "fetch": "iface=%x0 peripheral=+0(%x1):string client=+0(%x2):string out_client=%x4 out_state=%x5",
        "reason": "prove a remote register transaction is attempted",
    },
    {
        "label": "pm_register_connect_remote_register_return_check",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["remote_register_return_check"],
        "fetch": "remote_ret=%x0",
        "reason": "classify server transaction status before cleanup",
    },
    {
        "label": "pm_register_connect_ret",
        "binary": "libperipheral_client.so",
        "offset": PM_REGISTER_CONNECT_OFFSETS["entry"],
        "fetch": "ret=$retval",
        "reason": "record pm_register_connect return seen by pm_client_register",
    },
]

INTERESTING_STRINGS = (
    "/dev/vndbinder",
    "vendor.qcom.PeripheralManager",
    "Get service fail",
    "Failed to get binder object",
    "Failed to get binder interface object",
    "failed to register",
    "successfully registered",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def run_host(command: list[str], timeout: int = 20) -> tuple[int, str]:
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
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return result.returncode, result.stdout


def parse_symbols(readelf_text: str) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    for raw_line in readelf_text.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"^\d+:\s+([0-9A-Fa-f]+)\s+(\d+)\s+FUNC\s+\S+\s+\S+\s+\S+\s+(.+)$",
            line,
        )
        if not match:
            continue
        address, size, name = match.groups()
        name = name.split("@@", 1)[0]
        for short_name, symbol_name in SYMBOLS.items():
            if name == symbol_name:
                symbols[short_name] = {
                    "name": name,
                    "address": f"0x{int(address, 16):x}",
                    "size": int(size),
                }
    return symbols


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def cnss_returns(tracefs: dict[str, Any], label: str) -> list[str]:
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in str(comm):
            values.extend(str(item) for item in (labels or {}).get(label, []))
    return values


def collect_binary_analysis(binary_path: Path, store: EvidenceStore) -> dict[str, Any]:
    resolved = repo_path(binary_path)
    readelf_rc, readelf_text = run_host(["aarch64-linux-gnu-readelf", "-sW", str(resolved)])
    strings_rc, strings_text = run_host(["strings", "-a", "-t", "x", str(resolved)])
    client_rc, client_disasm = run_host(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x6ec8",
            "--stop-address=0x71bc",
            str(resolved),
        ]
    )
    register_rc, register_disasm = run_host(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--start-address=0x612c",
            "--stop-address=0x6700",
            str(resolved),
        ]
    )

    store.write_text("libperipheral_client.readelf.txt", readelf_text)
    store.write_text("libperipheral_client.strings.txt", strings_text)
    store.write_text("libperipheral_client.pm_client_register.objdump.txt", client_disasm)
    store.write_text("libperipheral_client.pm_register_connect.objdump.txt", register_disasm)

    string_hits = []
    for line in strings_text.splitlines():
        if any(item in line for item in INTERESTING_STRINGS):
            string_hits.append(line.strip())

    symbols = parse_symbols(readelf_text)
    disasm_checks = {
        "pm_client_register_calls_pm_register_connect": "bl\t96b0" in client_disasm
        or "pm_register_connect" in client_disasm,
        "pm_client_register_failure_sets_minus_one": "mov\tw0, #0xffffffff" in client_disasm,
        "pm_register_connect_uses_vndbinder": "/dev/vndbinder" in strings_text,
        "pm_register_connect_names_peripheral_manager": "vendor.qcom.PeripheralManager" in strings_text,
        "pm_register_connect_has_get_service_fail": "Get service fail" in strings_text,
        "pm_register_connect_has_binder_object_fail": "Failed to get binder object" in strings_text,
        "pm_register_connect_has_interface_fail": "Failed to get binder interface object" in strings_text,
        "pm_register_connect_has_remote_register_callsite": "6274:" in register_disasm and "blr" in register_disasm,
        "pm_register_connect_failure_sets_minus_one": "6690:" in register_disasm
        and "mov\tw19, #0xffffffff" in register_disasm,
    }
    return {
        "binary": str(resolved),
        "exists": resolved.exists(),
        "readelf_rc": readelf_rc,
        "strings_rc": strings_rc,
        "pm_client_register_objdump_rc": client_rc,
        "pm_register_connect_objdump_rc": register_rc,
        "symbols": symbols,
        "string_hits": string_hits,
        "disasm_checks": disasm_checks,
        "pm_client_register_offsets": PM_CLIENT_REGISTER_OFFSETS,
        "pm_register_connect_offsets": PM_REGISTER_CONNECT_OFFSETS,
        "v1120_trace_candidates": V1120_TRACE_CANDIDATES,
    }


def collect_v1118_analysis(manifest: dict[str, Any]) -> dict[str, Any]:
    tracefs = nested_get(manifest, ("analysis", "tracefs_uprobe"), {})
    counts = tracefs.get("counts") or {}
    contract = tracefs.get("pm_contract") or {}
    client_args = tracefs.get("client_register_args_by_comm") or {}
    cnss_register_args = client_args.get("cnss-daemon") or []
    cnss_register_ret = cnss_returns(tracefs, "pm_client_register_ret")
    cnss_connect_ret = cnss_returns(tracefs, "pm_client_connect_ret")
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "counts": {
            "pm_client_register_entry": int_value(counts.get("pm_client_register_entry")),
            "pm_client_register_ret": int_value(counts.get("pm_client_register_ret")),
            "pm_client_connect_entry": int_value(counts.get("pm_client_connect_entry")),
            "pm_client_connect_ret": int_value(counts.get("pm_client_connect_ret")),
            "pm_server_register_entry": int_value(counts.get("pm_server_register_entry")),
            "pm_server_register_ret": int_value(counts.get("pm_server_register_ret")),
            "pm_server_connect_entry": int_value(counts.get("pm_server_connect_entry")),
            "pm_server_connect_ret": int_value(counts.get("pm_server_connect_ret")),
        },
        "cnss": {
            "hit_count": int_value(tracefs.get("cnss_daemon_hit_count")),
            "register_args": cnss_register_args,
            "register_ret": cnss_register_ret,
            "connect_ret": cnss_connect_ret,
        },
        "pm_contract": {
            "per_mgr_start_executed": contract.get("per_mgr_start_executed"),
            "child.per_mgr.exited": contract.get("child.per_mgr.exited"),
            "child.per_mgr.exit_code": contract.get("child.per_mgr.exit_code"),
            "child.per_mgr.signal": contract.get("child.per_mgr.signal"),
            "child.per_mgr.observable": contract.get("child.per_mgr.observable"),
            "vndservice_provider_seen": contract.get("vndservice_provider_seen"),
            "vndservice_query.skipped": contract.get("vndservice_query.pm_observer_after_per_mgr_probe.skipped"),
            "vndservice_query.skip_reason": contract.get("vndservice_query.pm_observer_after_per_mgr_probe.skip_reason"),
            "pm_proxy_helper_subsys_modem_seen": contract.get("pm_proxy_helper_subsys_modem_seen"),
            "per_mgr_subsys_modem_seen": contract.get("per_mgr_subsys_modem_seen"),
            "start_cnss_zero_delay_after_per_mgr": contract.get("start_cnss_zero_delay_after_per_mgr"),
            "per_proxy_start_executed": contract.get("per_proxy_start_executed"),
        },
        "last_label_by_comm": tracefs.get("last_label_by_comm") or {},
        "pm_server_hits_by_comm": tracefs.get("pm_server_hits_by_comm") or {},
    }


def classify(v1118: dict[str, Any], binary: dict[str, Any]) -> dict[str, Any]:
    args = v1118["cnss"]["register_args"]
    valid_cnss_args = any(
        item.get("peripheral") == "modem" and item.get("client") == "cnss-daemon"
        for item in args
        if isinstance(item, dict)
    )
    register_ret_negative = "0xffffffff" in set(v1118["cnss"]["register_ret"])
    server_register_zero = v1118["counts"]["pm_server_register_entry"] == 0
    connect_zero = v1118["counts"]["pm_client_connect_entry"] == 0
    provider_absent = v1118["pm_contract"]["vndservice_provider_seen"] == "0"
    per_mgr_exited_clean = (
        v1118["pm_contract"]["child.per_mgr.exited"] == "1"
        and v1118["pm_contract"]["child.per_mgr.exit_code"] == "0"
        and v1118["pm_contract"]["child.per_mgr.signal"] == "0"
    )
    binary_model_ok = all(
        binary.get("disasm_checks", {}).get(name)
        for name in (
            "pm_client_register_calls_pm_register_connect",
            "pm_register_connect_uses_vndbinder",
            "pm_register_connect_names_peripheral_manager",
            "pm_register_connect_has_get_service_fail",
            "pm_register_connect_has_remote_register_callsite",
        )
    )
    return {
        "v1118": v1118,
        "binary": binary,
        "flags": {
            "v1118_expected_decision": v1118["decision"] == EXPECTED_V1118_DECISION,
            "valid_cnss_register_args": valid_cnss_args,
            "register_ret_negative_one": register_ret_negative,
            "pm_client_connect_not_reached": connect_zero,
            "pm_server_register_not_reached": server_register_zero,
            "provider_absent_in_contract": provider_absent,
            "per_mgr_exited_cleanly_before_provider_hold": per_mgr_exited_clean,
            "binary_model_supports_pre_server_failure": binary_model_ok,
        },
        "interpretation": {
            "closed": [
                "argument-validation failure is inconsistent with captured cnss-daemon/modem args",
                "PM server register reject is inconsistent with pm_server_register_entry=0",
                "PM connect path is not reached because pm_client_connect_entry=0",
                "20 ms observer delay is already closed by V1118 zero-delay evidence",
            ],
            "current_blocker": (
                "pm_client_register calls pm_register_connect; pm_register_connect returns nonzero before "
                "the PM connect path. V1118 provider evidence and zero server register entries make the "
                "pre-server vendor.qcom.PeripheralManager lookup/interface path the active blocker."
            ),
            "remaining_uncertainty": (
                "V1119 is host-only. V1120 should add live tracefs uprobes at the internal "
                "pm_register_connect null-service, null-interface, and remote-register return checks to "
                "prove the exact branch."
            ),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    flags = analysis["flags"]
    if not flags["v1118_expected_decision"]:
        return (
            "v1119-v1118-input-not-current",
            False,
            f"unexpected V1118 decision={analysis['v1118']['decision']!r}",
            "refresh V1118 evidence before PM register failure classification",
        )
    if not analysis["binary"]["exists"]:
        return (
            "v1119-libperipheral-client-missing",
            False,
            "libperipheral_client.so input is missing",
            "restore vendor extraction before classifying PM register failure",
        )
    if not flags["binary_model_supports_pre_server_failure"]:
        return (
            "v1119-binary-model-incomplete",
            False,
            "host disassembly/string model did not expose the expected PM register-connect path",
            "inspect libperipheral_client.so manually and refresh offsets",
        )
    if (
        flags["valid_cnss_register_args"]
        and flags["register_ret_negative_one"]
        and flags["pm_client_connect_not_reached"]
        and flags["pm_server_register_not_reached"]
        and flags["provider_absent_in_contract"]
        and flags["per_mgr_exited_cleanly_before_provider_hold"]
    ):
        return (
            "v1119-pm-register-pre-server-provider-lookup-gap-classified",
            True,
            "CNSS PM register fails with -1 before PM server register/connect while provider is absent and per_mgr has exited cleanly",
            "V1120 should trace pm_register_connect internal null-service/null-interface/remote-register branches under the same zero-delay gate",
        )
    if (
        flags["valid_cnss_register_args"]
        and flags["register_ret_negative_one"]
        and flags["pm_client_connect_not_reached"]
        and flags["pm_server_register_not_reached"]
    ):
        return (
            "v1119-pm-register-pre-server-client-gap-classified",
            True,
            "CNSS PM register fails with -1 before any PM server register entry; provider evidence is incomplete",
            "V1120 should trace pm_register_connect internal branch offsets before changing service order",
        )
    return (
        "v1119-pm-register-failure-inconclusive",
        True,
        "V1118 did not match the expected pre-server PM register failure pattern",
        "inspect V1118 tracefs manifest manually before choosing V1120",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    flags = [[key, value] for key, value in analysis["flags"].items()]
    counts = [[key, value] for key, value in analysis["v1118"]["counts"].items()]
    offsets = [
        ["pm_client_register", json.dumps(analysis["binary"]["pm_client_register_offsets"], sort_keys=True)],
        ["pm_register_connect", json.dumps(analysis["binary"]["pm_register_connect_offsets"], sort_keys=True)],
    ]
    return "\n".join(
        [
            "# V1119 PM Register Failure Host Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            "",
            "## Flags",
            "",
            markdown_table(["flag", "value"], flags),
            "",
            "## V1118 Counts",
            "",
            markdown_table(["event", "count"], counts),
            "",
            "## Binary Model",
            "",
            markdown_table(["item", "value"], offsets),
            "",
            "## Interpretation",
            "",
            "- closed:",
            *[f"  - {item}" for item in analysis["interpretation"]["closed"]],
            f"- current_blocker: {analysis['interpretation']['current_blocker']}",
            f"- remaining_uncertainty: {analysis['interpretation']['remaining_uncertainty']}",
            "",
            "## V1120 Trace Candidates",
            "",
            "```json",
            json.dumps(analysis["binary"]["v1120_trace_candidates"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1118-manifest", type=Path, default=DEFAULT_V1118_MANIFEST)
    parser.add_argument("--peripheral-client", type=Path, default=DEFAULT_PERIPHERAL_CLIENT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "v1118": {},
            "binary": {
                "binary": str(repo_path(args.peripheral_client)),
                "exists": repo_path(args.peripheral_client).exists(),
                "pm_client_register_offsets": PM_CLIENT_REGISTER_OFFSETS,
                "pm_register_connect_offsets": PM_REGISTER_CONNECT_OFFSETS,
                "v1120_trace_candidates": V1120_TRACE_CANDIDATES,
            },
            "flags": {},
            "interpretation": {
                "closed": [],
                "current_blocker": "plan-only",
                "remaining_uncertainty": "run V1119 host-only classifier",
            },
        }
        decision, passed, reason, next_step = (
            "v1119-pm-register-failure-host-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1119 host-only classifier against V1118 evidence and libperipheral_client.so",
        )
    else:
        v1118_manifest = load_json(args.v1118_manifest)
        v1118 = collect_v1118_analysis(v1118_manifest)
        binary = collect_binary_analysis(args.peripheral_client, store)
        analysis = classify(v1118, binary)
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1119",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1118_manifest": str(repo_path(args.v1118_manifest)),
            "peripheral_client": str(repo_path(args.peripheral_client)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "firmware_mounts_executed": False,
        "global_modem_holder_opened": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
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
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
