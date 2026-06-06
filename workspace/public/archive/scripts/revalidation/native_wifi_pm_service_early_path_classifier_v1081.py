#!/usr/bin/env python3
"""V1081 host-only PM-service early exit path classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1081-pm-service-early-path-classifier")
DEFAULT_BINARY = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
DEFAULT_V1080_MANIFEST = Path("tmp/wifi/v1080-pm-service-tracefs-expanded-live/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1081-pm-service-early-path-classifier.txt")

PROBE_OFFSETS = {
    "main_entry": "0x7650",
    "main_pipe_call": "0x7748",
    "main_helper_call": "0x77c8",
    "main_helper_return_branch": "0x77cc",
    "main_error_close0": "0x77d4",
    "main_error_close1": "0x77dc",
    "main_binder_driver_call": "0x78e0",
    "helper_entry": "0x6b6c",
    "helper_get_system_info_call": "0x6bc0",
    "helper_get_system_info_branch": "0x6bc4",
    "helper_get_system_info_failure_log": "0x6bdc",
    "helper_get_system_info_failure_return": "0x6be0",
    "helper_get_system_info_success_path": "0x6be8",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def run_capture(store: EvidenceStore, name: str, command: list[str], timeout: float = 30.0) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
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
        "started_at": started.isoformat(),
    }


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def disasm_command(binary: Path, start: str, stop: str) -> list[str]:
    return [
        "aarch64-linux-gnu-objdump",
        "-d",
        str(binary),
        f"--start-address={start}",
        f"--stop-address={stop}",
    ]


def classify(v1080: dict[str, Any], binary_exists: bool) -> dict[str, Any]:
    tracefs = ((v1080.get("analysis") or {}).get("tracefs_uprobe") or {})
    counts = tracefs.get("counts") or {}
    contract = tracefs.get("pm_contract") or {}
    expected_hits = {
        "elf_entry": 1,
        "libc_init_main_candidate": 1,
        "pipe": 1,
        "mdmdetect_system_info": 1,
        "android_log": 1,
        "close": 2,
    }
    zero_before_server = [
        "binder_driver",
        "binder_service_manager",
        "qmi_csi_register",
        "qmi_csi_event_loop",
        "property_set",
        "open",
        "access",
        "select",
        "write",
    ]
    hit_match = all(int(counts.get(key, 0)) >= value for key, value in expected_hits.items())
    zero_match = all(int(counts.get(key, 0)) == 0 for key in zero_before_server)
    runtime_gap = (
        contract.get("result") == "observer-runtime-gap"
        and contract.get("child.per_mgr.exit_code") == "255"
        and contract.get("per_mgr_subsys_modem_seen") == "0"
    )
    return {
        "binary_exists": binary_exists,
        "v1080_decision": v1080.get("decision", ""),
        "counts": counts,
        "pm_contract_subset": {
            key: contract.get(key, "")
            for key in (
                "result",
                "reason",
                "child.per_mgr.exit_code",
                "child.per_proxy.exit_code",
                "per_mgr_subsys_modem_seen",
                "pm_proxy_helper_subsys_modem_seen",
                "all_postflight_safe",
            )
        },
        "expected_hits_present": hit_match,
        "server_setup_not_reached": zero_match,
        "runtime_gap_reconfirmed": runtime_gap,
        "inferred_path": [
            "main@0x7650 entered",
            "pipe@0x7748 succeeded",
            "helper@0x6b6c called from main@0x77c8",
            "helper get_system_info@0x6bc0 called",
            "helper failure log@0x6bdc executed",
            "helper returned nonzero to main@0x77cc",
            "main closed pipe fds at 0x77d4 and 0x77dc",
            "Binder/QMI/open path starting at 0x78d4/0x78e0 was not reached",
        ],
        "next_instruction_uprobes": PROBE_OFFSETS,
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not analysis["binary_exists"]:
        return "v1081-pm-service-binary-missing", False, "local pm-service binary missing", "rerun V1073 vendor extract"
    if analysis["v1080_decision"] != "v1080-pm-service-tracefs-uprobe-boundary-captured":
        return "v1081-v1080-evidence-missing", False, "V1080 PASS evidence missing", "rerun V1080 expanded live"
    if not analysis["expected_hits_present"]:
        return "v1081-observed-hit-pattern-mismatch", False, "V1080 expected early hits not present", "inspect V1080 tracefs evidence"
    if not analysis["server_setup_not_reached"]:
        return "v1081-server-setup-was-reached", False, "Binder/QMI/open path was reached unexpectedly", "reclassify branch inference"
    if not analysis["runtime_gap_reconfirmed"]:
        return "v1081-runtime-gap-not-confirmed", False, "PM observer runtime gap not confirmed", "inspect PM observer contract"
    return (
        "v1081-pm-service-early-exit-path-classified",
        True,
        "per_mgr exits after get_system_info failure path and before Binder/QMI/open server setup",
        "use instruction-level tracefs uprobes at helper branch/return offsets in V1082",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [[key, value] for key, value in analysis["next_instruction_uprobes"].items()]
    table = "\n".join(["| label | offset |", "| --- | --- |"] + [f"| `{key}` | `{value}` |" for key, value in rows])
    return "\n".join([
        "# V1081 PM Service Early Path Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- binary: `{manifest['binary']}`",
        "",
        "## Inferred Path",
        "",
        *[f"- {item}" for item in analysis["inferred_path"]],
        "",
        "## V1082 Candidate Offsets",
        "",
        table,
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(analysis["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## PM Contract",
        "",
        "```json",
        json.dumps(analysis["pm_contract_subset"], indent=2, sort_keys=True),
        "```",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--v1080-manifest", type=Path, default=DEFAULT_V1080_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    binary = repo_path(args.binary)
    v1080 = load_json(args.v1080_manifest)
    commands = []
    if binary.exists():
        commands.append(run_capture(store, "pm-service-file", ["file", str(binary)]))
        commands.append(run_capture(store, "pm-service-main-early-disasm", disasm_command(binary, "0x7650", "0x78f0")))
        commands.append(run_capture(store, "pm-service-helper-get-system-info-disasm", disasm_command(binary, "0x6b6c", "0x6bf0")))
        commands.append(run_capture(store, "pm-service-strings-filter", ["sh", "-c", f"strings -tx {shlex_quote(str(binary))} | grep -Ei 'system information|QMI service|Peripheral|pipe|binder|permission|Failed|failed' || true"]))
    analysis = classify(v1080, binary.exists())
    decision, passed, reason, next_step = decide(analysis)
    manifest = {
        "cycle": "v1081",
        "generated_at": now_iso(),
        "binary": str(binary),
        "v1080_manifest": str(repo_path(args.v1080_manifest)),
        "commands": commands,
        "analysis": analysis,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "wifi_hal_start_executed": False,
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


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


if __name__ == "__main__":
    raise SystemExit(main())
