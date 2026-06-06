#!/usr/bin/env python3
"""V1166 host-only PM-service action branch classifier.

This classifier consumes already captured Android V1159, native V1165, and
host-extracted pm-service evidence. It does not contact the device, start PM
actors, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, ping
externally, write partitions, flash, or reboot.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1166-pm-action-branch-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1166-pm-action-branch-classifier.txt")
DEFAULT_V1159_ROOT = Path("tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019")
DEFAULT_V1165_MANIFEST = Path("tmp/wifi/v1165-late-per-proxy-actionability-live-after-v490/manifest.json")
DEFAULT_PM_SERVICE = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
CONNECT_BRANCH_START = "0x95f4"
CONNECT_BRANCH_STOP = "0x9828"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1159-root", type=Path, default=DEFAULT_V1159_ROOT)
    parser.add_argument("--v1165-manifest", type=Path, default=DEFAULT_V1165_MANIFEST)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--objdump", default="aarch64-linux-gnu-objdump")
    return parser.parse_args()


def read_text(path: Path, limit: int = 12_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "running"}


def intish(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def dmesg_time(text: str, pattern: str) -> float | None:
    regex = re.compile(r"\[\s*(?P<time>\d+\.\d+)\].*" + pattern)
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def first_line(text: str, *needles: str) -> str:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            return line.strip()
    return ""


def summarize_android(v1159_root: Path) -> dict[str, Any]:
    root = repo_path(v1159_root)
    manifest = load_json(root / "manifest.json")
    extracted = root / "android-trace" / "extracted" / "a90-wifi"
    dmesg = read_text(extracted / "boot_dmesg.txt")
    interesting = read_text(extracted / "pm_thread_interesting.txt")
    trace = (manifest.get("context") or {}).get("trace_classification") or {}
    if not isinstance(trace, dict):
        trace = {}

    times = {
        "per_proxy_helper_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy_helper'"),
        "per_proxy_helper_modem_get": dmesg_time(dmesg, r"pm_proxy_helper:.*__subsystem_get: modem count:0"),
        "per_proxy_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy'"),
        "pm_service_modem_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: modem count:1"),
        "mdm_helper_start": dmesg_time(dmesg, r"starting service 'vendor\.mdm_helper'"),
        "pm_service_esoc0_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: esoc0 count:0"),
        "icnss_qmi_connected": dmesg_time(dmesg, r"icnss_qmi: QMI Server Connected"),
        "bdf_regdb": dmesg_time(dmesg, r"BDF file : regdb\.bin"),
        "bdf_bdwlan": dmesg_time(dmesg, r"BDF file : bdwlan\.bin"),
        "fw_ready": dmesg_time(dmesg, r"FW ready event received"),
        "wlan0": dmesg_time(dmesg, r"dev : wlan0 : event : 16"),
    }

    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "trace_present": boolish(trace.get("present")),
        "dmesg_fw_ready": boolish(trace.get("dmesg_fw_ready")),
        "dmesg_wlan0_created": boolish(trace.get("dmesg_wlan0_created")),
        "pm_thread_sample_count": intish(trace.get("pm_thread_sample_count")),
        "pm_service_powerup_samples": count_lines(interesting, "label=pm-service", "wchan=mdm_subsys_powerup"),
        "pm_service_binder_openat_samples": count_lines(interesting, "label=pm-service", "comm=Binder:", "syscall=56"),
        "pm_service_powerup_first_line": first_line(interesting, "label=pm-service", "wchan=mdm_subsys_powerup"),
        "times": times,
    }


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def trace_lines(tfs: dict[str, Any], labels: tuple[str, ...]) -> list[str]:
    lines = tfs.get("trace_lines") or []
    return [str(line) for line in lines if any(label in str(line) for label in labels)]


def poll_indices(polls: dict[str, Any]) -> list[str]:
    return sorted({
        match.group(1)
        for key in polls
        for match in [re.search(r"late_per_proxy_poll_(\d+)", str(key))]
        if match
    }, key=lambda value: intish(value))


def poll_values(polls: dict[str, Any], suffix: str) -> list[int]:
    return [
        intish(polls.get(f"late_per_proxy_poll_{index}.{suffix}"))
        for index in poll_indices(polls)
    ]


def return_values(tfs: dict[str, Any], comm: str, label: str) -> list[str]:
    values = tfs.get("return_values_by_comm") or {}
    if not isinstance(values, dict):
        return []
    by_comm = values.get(comm) or {}
    if not isinstance(by_comm, dict):
        return []
    raw = by_comm.get(label) or []
    return [str(item) for item in raw] if isinstance(raw, list) else [str(raw)]


def summarize_native(v1165_manifest: Path) -> dict[str, Any]:
    manifest = load_json(v1165_manifest)
    tfs = tracefs(manifest)
    late = tfs.get("late_per_proxy") or {}
    polls = tfs.get("late_per_proxy_polls") or {}
    hits = tfs.get("connect_impl_hits_by_comm") or {}
    pm_hits = hits.get("Binder:2537_2") if isinstance(hits, dict) else {}
    if not isinstance(pm_hits, dict):
        pm_hits = {}
    polls = polls if isinstance(polls, dict) else {}
    late = late if isinstance(late, dict) else {}

    action_labels = (
        "pm_server_connect_impl_state_check",
        "pm_server_connect_impl_start_vote",
        "pm_server_connect_impl_return",
        "pm_server_connect_impl_ret",
        "pm_server_connect_ret",
    )
    forbidden = {
        "wifi_hal_start_executed": boolish(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(manifest.get("scan_connect_executed")),
        "credential_use_executed": boolish(manifest.get("credential_use_executed")),
        "dhcp_route_executed": boolish(manifest.get("dhcp_route_executed")),
        "external_ping_executed": boolish(manifest.get("external_ping_executed")),
    }

    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "late_per_proxy_started": boolish(manifest.get("late_per_proxy_started")) or boolish(late.get("started")),
        "late_gate_positive": boolish(late.get("gate_positive")),
        "late_gate_mdm_helper_esoc0_fd_count": intish(late.get("gate_mdm_helper_esoc0_fd_count")),
        "poll_count": len(poll_indices(polls)),
        "per_proxy_alive_counts": poll_values(polls, "per_proxy_alive"),
        "per_mgr_subsys_modem_counts": poll_values(polls, "per_mgr_subsys_modem_count"),
        "per_mgr_subsys_esoc0_counts": poll_values(polls, "per_mgr_subsys_esoc0_count"),
        "pm_proxy_register_ret": return_values(tfs, "pm-proxy", "pm_client_register_ret"),
        "pm_proxy_connect_ret": return_values(tfs, "pm-proxy", "pm_client_connect_ret"),
        "cnss_register_ret": return_values(tfs, "cnss-daemon", "pm_client_register_ret"),
        "cnss_connect_ret": return_values(tfs, "cnss-daemon", "pm_client_connect_ret"),
        "pm_server_connect_impl_start_vote": intish(pm_hits.get("pm_server_connect_impl_start_vote")),
        "pm_server_connect_ret": return_values(tfs, "Binder:2537_2", "pm_server_connect_ret"),
        "pm_server_connect_impl_ret": return_values(tfs, "Binder:2537_2", "pm_server_connect_impl_ret"),
        "action_trace_lines": trace_lines(tfs, action_labels)[:32],
        "forbidden": forbidden,
    }


def run_objdump(objdump: str, binary: Path) -> tuple[int, str]:
    resolved = repo_path(binary)
    if not resolved.exists():
        return 127, f"missing binary: {resolved}\n"
    command = [
        objdump,
        "-d",
        f"--start-address={CONNECT_BRANCH_START}",
        f"--stop-address={CONNECT_BRANCH_STOP}",
        str(resolved),
    ]
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    return result.returncode, result.stdout


def has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def summarize_pm_service(binary: Path, objdump_rc: int, disassembly: str) -> dict[str, Any]:
    patterns = {
        "client_connected_check": has_any(disassembly, ("bl\t8684", "bl 8684")),
        "shutdown_byte_entry_plus_0x60": has_any(disassembly, ("ldrb\tw8, [x20, #96]", "ldrb w8, [x20, #96]")),
        "mark_client_connected": has_any(disassembly, ("bl\t8678", "bl 8678")),
        "voter_count_entry_plus_0x5c": has_any(disassembly, ("ldr\tw8, [x20, #92]", "ldr w8, [x20, #92]")),
        "voter_count_increment": has_any(disassembly, ("add\tw9, w8, #0x1", "add w9, w8, #0x1")),
        "old_voter_count_branch": has_any(disassembly, ("cbnz\tw8, 97e0", "cbnz w8, 97e0")),
        "reconnect_flag_entry_plus_0x58": has_any(disassembly, ("ldrb\tw8, [x20, #88]", "ldrb w8, [x20, #88]")),
        "state_transition_call": has_any(disassembly, ("bl\t92dc", "bl 92dc")),
    }
    tracepoint_plan = [
        {
            "name": "pm_server_connect_vote_count_before",
            "offset": "0x9738",
            "fetch": "voters_before=%w8",
            "meaning": "old entry voter count before increment",
        },
        {
            "name": "pm_server_connect_vote_count_after_store",
            "offset": "0x9740",
            "fetch": "voters_before=%w8 voters_after=%w9",
            "meaning": "branch condition that skips state transition when old voters are nonzero",
        },
        {
            "name": "pm_server_connect_reconnect_flag_check",
            "offset": "0x9748",
            "fetch": "reconnect_flag=%w8",
            "meaning": "reconnect/timer path that also skips fresh state transition",
        },
        {
            "name": "pm_server_connect_powerup_state_call",
            "offset": "0x97dc",
            "fetch": "entry=%x0 state=%w1",
            "meaning": "direct call to PM state transition helper with state 2",
        },
        {
            "name": "pm_server_state_transition_entry",
            "offset": "0x92dc",
            "fetch": "entry=%x0 state=%w1",
            "meaning": "state/action helper entry; if absent, connect returned before action",
        },
    ]
    return {
        "binary": str(binary),
        "binary_exists": repo_path(binary).exists(),
        "objdump_rc": objdump_rc,
        "connect_branch_range": f"{CONNECT_BRANCH_START}-{CONNECT_BRANCH_STOP}",
        "required_patterns": patterns,
        "all_required_patterns_present": all(patterns.values()),
        "semantic_model": [
            "client connected byte at client+0x10 rejects duplicate connect with -22",
            "entry+0x60 nonzero rejects connect as shutdown-in-progress with -22",
            "entry+0x5c voter count increments on successful connect",
            "old voter count nonzero skips fresh state transition",
            "entry+0x58 reconnect flag path cancels timer and skips fresh state transition",
            "old voter count zero and reconnect flag zero calls state helper 0x92dc with state 2",
        ],
        "tracepoint_plan": tracepoint_plan,
    }


def decide(android: dict[str, Any], native: dict[str, Any], pm: dict[str, Any]) -> tuple[str, bool, str, str]:
    forbidden = any(native.get("forbidden", {}).values())
    android_good = (
        android["times"]["per_proxy_start"] is not None
        and android["times"]["pm_service_esoc0_get"] is not None
        and android["pm_service_powerup_samples"] > 0
        and android["dmesg_fw_ready"]
        and android["dmesg_wlan0_created"]
    )
    native_gap = (
        native["late_per_proxy_started"]
        and native["late_gate_positive"]
        and native["poll_count"] >= 6
        and "0x0" in native["pm_proxy_connect_ret"]
        and "0x0" in native["pm_server_connect_impl_ret"]
        and native["pm_server_connect_impl_start_vote"] > 0
        and native["per_mgr_subsys_esoc0_counts"]
        and all(value == 0 for value in native["per_mgr_subsys_esoc0_counts"])
    )
    if forbidden:
        return (
            "v1166-forbidden-action-detected",
            False,
            "native V1165 evidence contains a forbidden Wi-Fi/network/credential action",
            "discard this evidence and rerun from a clean bounded gate",
        )
    if not android_good:
        return (
            "v1166-android-reference-insufficient",
            False,
            f"android={android}",
            "refresh Android PM thread sampler evidence before PM action-branch classification",
        )
    if not native_gap:
        return (
            "v1166-native-v1165-reference-insufficient",
            False,
            f"native={native}",
            "rerun V1165 after V401/V490 in the same boot before branch classification",
        )
    if not pm["all_required_patterns_present"]:
        return (
            "v1166-pm-service-branch-pattern-incomplete",
            False,
            f"patterns={pm['required_patterns']}",
            "verify pm-service binary extraction and objdump range before live uprobe offsets are used",
        )
    return (
        "v1166-pm-service-action-branch-probe-required",
        True,
        "Android proves pm-service Binder reaches esoc0/mdm_subsys_powerup, while native V1165 reaches PM connect/start-vote with return 0 but never opens /dev/subsys_esoc0; pm-service disassembly shows successful connect can still skip the state transition when old voter count or reconnect state is set",
        "V1167 should add tracefs probes at pm-service offsets 0x9738, 0x9740, 0x9748, 0x97dc, and 0x92dc during the bounded late pm-proxy gate",
    )


def summary_markdown(manifest: dict[str, Any]) -> str:
    android = manifest["android_v1159"]
    native = manifest["native_v1165"]
    pm = manifest["pm_service"]
    return "\n".join([
        "# V1166 PM-Service Action Branch Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Android V1159 Reference",
        "",
        markdown_table(["key", "value"], [
            ["per_proxy_start", android["times"]["per_proxy_start"]],
            ["pm_service_modem_get", android["times"]["pm_service_modem_get"]],
            ["pm_service_esoc0_get", android["times"]["pm_service_esoc0_get"]],
            ["icnss_qmi_connected", android["times"]["icnss_qmi_connected"]],
            ["fw_ready", android["times"]["fw_ready"]],
            ["wlan0", android["times"]["wlan0"]],
            ["pm_service_powerup_samples", android["pm_service_powerup_samples"]],
            ["pm_service_powerup_first_line", android["pm_service_powerup_first_line"]],
        ]),
        "",
        "## Native V1165 Reference",
        "",
        markdown_table(["key", "value"], [
            ["late_per_proxy_started", native["late_per_proxy_started"]],
            ["late_gate_positive", native["late_gate_positive"]],
            ["late_gate_mdm_helper_esoc0_fd_count", native["late_gate_mdm_helper_esoc0_fd_count"]],
            ["poll_count", native["poll_count"]],
            ["pm_proxy_connect_ret", native["pm_proxy_connect_ret"]],
            ["pm_server_connect_impl_ret", native["pm_server_connect_impl_ret"]],
            ["pm_server_connect_impl_start_vote", native["pm_server_connect_impl_start_vote"]],
            ["per_mgr_subsys_modem_counts", native["per_mgr_subsys_modem_counts"][:12]],
            ["per_mgr_subsys_esoc0_counts", native["per_mgr_subsys_esoc0_counts"][:12]],
        ]),
        "",
        "## PM-Service Branch Model",
        "",
        markdown_table(["field", "value"], [
            ["binary", pm["binary"]],
            ["objdump_rc", pm["objdump_rc"]],
            ["range", pm["connect_branch_range"]],
            ["all_required_patterns_present", pm["all_required_patterns_present"]],
        ]),
        "",
        markdown_table(["pattern", "present"], [
            [key, value] for key, value in pm["required_patterns"].items()
        ]),
        "",
        "## V1167 Tracepoint Plan",
        "",
        markdown_table(["name", "offset", "fetch", "meaning"], [
            [item["name"], item["offset"], item["fetch"], item["meaning"]]
            for item in pm["tracepoint_plan"]
        ]),
        "",
        "## Safety",
        "",
        "- Host-only classifier; no device command was executed.",
        "- Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping, partition write, boot image write, flash, and reboot are out of scope.",
        "",
    ]) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    android = summarize_android(args.v1159_root)
    native = summarize_native(args.v1165_manifest)
    objdump_rc, disassembly = run_objdump(args.objdump, args.pm_service)
    store.write_text("pm-service-connect-branch-0x95f4-0x9828.S", disassembly)
    pm = summarize_pm_service(args.pm_service, objdump_rc, disassembly)
    decision, passed, reason, next_step = decide(android, native, pm)
    manifest = {
        "generated_at": now_iso(),
        "cycle": "v1166",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1159_root": str(args.v1159_root),
            "v1165_manifest": str(args.v1165_manifest),
            "pm_service": str(args.pm_service),
        },
        "android_v1159": android,
        "native_v1165": native,
        "pm_service": pm,
        "device_command_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "boot_image_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary_markdown(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next_step: {next_step}")
    print(f"evidence: {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
