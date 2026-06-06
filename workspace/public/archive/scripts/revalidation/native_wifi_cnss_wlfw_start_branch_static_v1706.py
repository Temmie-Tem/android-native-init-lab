#!/usr/bin/env python3
"""Host-only V1706 classifier for cnss-daemon wlfw_start branch flow."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_cnss_wlfw_downstream_static_v1703 as v1703


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1706"
DATE = "2026-06-02"
DEFAULT_CNSS_DAEMON = v1703.DEFAULT_CNSS_DAEMON
DEFAULT_OBJDUMP = v1703.DEFAULT_OBJDUMP
DEFAULT_V1703_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1703-cnss-wlfw-downstream-static" / "manifest.json"
DEFAULT_V1705_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1705-cnss-wlfw-downstream-uprobe-handoff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1706-cnss-wlfw-start-branch-static"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / f"NATIVE_INIT_{CYCLE}_CNSS_WLFW_START_BRANCH_STATIC_{DATE}.md"
)

BRANCH_TARGETS = [
    {
        "name": "entry",
        "offset": "0xec00",
        "instruction": "stp x29, x30",
        "meaning": "wlfw_start entry; already proven by V1702/V1705",
    },
    {
        "name": "cal_mutex_init_retcheck",
        "offset": "0xec5c",
        "instruction": "cbz w0, 0xec70",
        "meaning": "first pthread_mutex_init return check; failure logs cal_mutex init and exits before worker setup",
    },
    {
        "name": "mutex_init_retcheck",
        "offset": "0xec7c",
        "instruction": "cbz w0, 0xec90",
        "meaning": "second pthread_mutex_init return check; failure exits before condition variables",
    },
    {
        "name": "cond_init_retcheck",
        "offset": "0xeca0",
        "instruction": "cbz w0, 0xecb4",
        "meaning": "first pthread_cond_init return check; failure exits before DMS/thread creation",
    },
    {
        "name": "cond_rsp_init_retcheck",
        "offset": "0xecc0",
        "instruction": "cbz w0, 0xecd4",
        "meaning": "second pthread_cond_init return check; failure exits before DMS/thread creation",
    },
    {
        "name": "dms_initialize_call",
        "offset": "0xecd4",
        "instruction": "bl 0xeb14",
        "meaning": "calls pthread_initialize_dms before creating wlfw_service_request worker",
    },
    {
        "name": "dms_initialize_retcheck",
        "offset": "0xecd8",
        "instruction": "cbnz w0, 0xed0c",
        "meaning": "DMS initialization failure path skips wlfw_service_request pthread_create",
    },
    {
        "name": "wlfw_worker_pthread_create_call",
        "offset": "0xecf0",
        "instruction": "bl pthread_create",
        "meaning": "attempts to create wlfw_service_request@0xd9fc",
    },
    {
        "name": "wlfw_worker_pthread_create_retcheck",
        "offset": "0xecf4",
        "instruction": "cbz w0, 0xeda0",
        "meaning": "pthread_create return check; success branches to Start done flag/log",
    },
    {
        "name": "wlfw_worker_pthread_create_failure",
        "offset": "0xecf8",
        "instruction": "log Failed to create thread",
        "meaning": "pthread_create returned nonzero; cleanup follows and worker never starts",
    },
    {
        "name": "cleanup_after_preworker_failure",
        "offset": "0xed0c",
        "instruction": "pthread_cond_destroy cond_rsp",
        "meaning": "shared cleanup after DMS init failure or worker pthread_create failure",
    },
    {
        "name": "wlfw_worker_pthread_create_success",
        "offset": "0xeda0",
        "instruction": "Start done success path",
        "meaning": "pthread_create returned zero; if worker entry is still absent, scheduling/target mismatch must be checked",
    },
    {
        "name": "wlfw_start_success_flag",
        "offset": "0xedc0",
        "instruction": "strb w9, [x8, #328]",
        "meaning": "sets wlfw start done flag on success path",
    },
]

EXPECTED_BRANCH_PATTERNS = {
    "entry": "ec00:\ta9be7bfd \tstp\tx29, x30, [sp, #-32]!",
    "log_starting": "ec24:\t97ffed7e \tbl\ta21c",
    "cal_mutex_init_retcheck": "ec5c:\t340000a0 \tcbz\tw0, ec70",
    "cal_mutex_init_fail_branch": "ec68:\t9112e421 \tadd\tx1, x1, #0x4b9",
    "mutex_init_retcheck": "ec7c:\t340000a0 \tcbz\tw0, ec90",
    "mutex_init_fail_branch": "ec88:\t91223421 \tadd\tx1, x1, #0x88d",
    "cond_init_retcheck": "eca0:\t340000a0 \tcbz\tw0, ecb4",
    "cond_init_fail_branch": "ecac:\t913c8c21 \tadd\tx1, x1, #0xf23",
    "cond_rsp_init_retcheck": "ecc0:\t340000a0 \tcbz\tw0, ecd4",
    "cond_rsp_init_fail_branch": "eccc:\t91147c21 \tadd\tx1, x1, #0x51f",
    "dms_initialize_call": "ecd4:\t97ffff90 \tbl\teb14",
    "dms_initialize_retcheck": "ecd8:\t350001a0 \tcbnz\tw0, ed0c",
    "wlfw_worker_thread_target": "ece4:\t9127f042 \tadd\tx2, x2, #0x9fc",
    "wlfw_worker_pthread_create_call": "ecf0:\t94001528 \tbl\t14190 <pthread_create@plt>",
    "wlfw_worker_pthread_create_retcheck": "ecf4:\t34000560 \tcbz\tw0, eda0",
    "wlfw_worker_pthread_create_failure": "ed00:\t91219421 \tadd\tx1, x1, #0x865",
    "cleanup_after_preworker_failure": "ed0c:\t91041280 \tadd\tx0, x20, #0x104",
    "success_path": "eda0:\tb0ffffa1 \tadrp\tx1, 3000",
    "success_flag": "edc0:\t39052109 \tstrb\tw9, [x8, #328]",
}

EXPECTED_STRING_OFFSETS = {
    "wlfw_start": "0x5ab9",
    "wlfw_start_starting_format": "0x5f96",
    "start_done_format": "0x3ee1",
    "failed_create_thread": "0x6865",
    "failed_init_cal_mutex": "0x64b9",
    "failed_init_mutex": "0x588d",
    "failed_init_cond": "0x4f23",
    "failed_init_cond_rsp": "0x451f",
    "failed_destroy_cond_rsp": "0x4f3f",
    "failed_destroy_cond": "0x6333",
    "failed_destroy_mutex": "0x6885",
    "failed_destroy_cal_mutex": "0x4a17",
}

STRING_VALUES = {
    "wlfw_start": "wlfw_start",
    "wlfw_start_starting_format": "%s: Starting",
    "start_done_format": "%s: Start done: %d",
    "failed_create_thread": "Failed to create thread, ret %d",
    "failed_init_cal_mutex": "Failed to init cal_mutex, ret %d",
    "failed_init_mutex": "Failed to init mutex, ret %d",
    "failed_init_cond": "Failed to init cond, ret %d",
    "failed_init_cond_rsp": "Failed to init cond_rsp, ret %d",
    "failed_destroy_cond_rsp": "Failed to destroy cond_rsp, ret %d",
    "failed_destroy_cond": "Failed to destroy cond, ret %d",
    "failed_destroy_mutex": "Failed to destroy mutex, ret %d",
    "failed_destroy_cal_mutex": "Failed to destroy cal_mutex, ret %d",
}

NEXT_LIVE_TARGETS = [
    {
        "target": "cnss-daemon+0xecd4",
        "name": "dms_initialize_call",
        "purpose": "prove wlfw_start reaches the DMS initialization call",
    },
    {
        "target": "cnss-daemon+0xecd8",
        "name": "dms_initialize_retcheck",
        "purpose": "prove wlfw_start returns from DMS initialization and reaches its return-code branch",
    },
    {
        "target": "cnss-daemon+0xecf0",
        "name": "wlfw_worker_pthread_create_call",
        "purpose": "prove wlfw_start attempts pthread_create for wlfw_service_request",
    },
    {
        "target": "cnss-daemon+0xecf8",
        "name": "wlfw_worker_pthread_create_failure",
        "purpose": "detect pthread_create nonzero return path before cleanup",
    },
    {
        "target": "cnss-daemon+0xeda0",
        "name": "wlfw_worker_pthread_create_success",
        "purpose": "detect pthread_create zero return path and start-done logging path",
    },
]


def display_path(path: Path) -> str:
    return v1703.display_path(path)


def read_json(path: Path) -> dict[str, Any]:
    return v1703.read_json(path)


def intish(value: Any, default: int = 0) -> int:
    return v1703.intish(value, default)


def extract_function_block(disassembly: str, start: str = "ec00", end: str = "edd0") -> str:
    lines = []
    in_block = False
    start_re = re.compile(rf"^\s*{start}:")
    end_re = re.compile(rf"^\s*{end}:")
    for line in disassembly.splitlines():
        if start_re.match(line):
            in_block = True
        if in_block:
            lines.append(line)
            if end_re.match(line):
                break
    return "\n".join(lines)


def parse_strings(binary: Path) -> dict[str, dict[str, Any]]:
    output = v1703.run_text(["strings", "-a", "-t", "x", str(binary)])
    found_by_value: dict[str, str] = {}
    wanted = set(STRING_VALUES.values())
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
        found_by_value[value] = f"0x{offset:x}"
    checks: dict[str, dict[str, Any]] = {}
    for key, expected_offset in EXPECTED_STRING_OFFSETS.items():
        value = STRING_VALUES[key]
        actual = found_by_value.get(value)
        checks[key] = {
            "value": value,
            "expected_offset": expected_offset,
            "actual_offset": actual,
            "match": actual == expected_offset,
        }
    return checks


def check_patterns(function_block: str) -> dict[str, bool]:
    return {name: pattern in function_block for name, pattern in EXPECTED_BRANCH_PATTERNS.items()}


def v1705_basis_ok(v1705: dict[str, Any]) -> bool:
    gate = v1705.get("gate", {})
    return (
        v1705.get("decision") == "v1705-wlfw-worker-thread-missing-after-wlfw-start-rollback-pass"
        and v1705.get("pass") is True
        and v1705.get("rollback", {}).get("ok") is True
        and gate.get("nonlog_label") == "wlfw-worker-thread-missing-after-wlfw-start"
        and intish(gate.get("nonlog_wlfw_start_hit_count")) >= 1
        and intish(gate.get("nonlog_wlfw_service_request_hit_count")) == 0
        and intish(gate.get("nonlog_wlfw_ind_register_qmi_hit_count")) == 0
        and intish(gate.get("nonlog_wlfw_cap_qmi_hit_count")) == 0
        and gate.get("old_firmware_serve_label") == "firmware-not-requested"
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1703_manifest = read_json(args.v1703_manifest)
    v1705_manifest = read_json(args.v1705_manifest)
    v1703.ensure_objdump(args.cnss_daemon, args.objdump)
    disassembly = args.objdump.read_text(encoding="utf-8", errors="replace")
    function_block = extract_function_block(disassembly)
    strings = parse_strings(args.cnss_daemon)
    patterns = check_patterns(function_block)
    binary_sha = v1703.sha256_file(args.cnss_daemon)

    v1703_ready = (
        v1703_manifest.get("decision") == "v1703-cnss-wlfw-downstream-static-map-pass"
        and v1703_manifest.get("pass") is True
        and v1703_manifest.get("binary", {}).get("sha256_ok") is True
    )
    basis_ok = v1703_ready and v1705_basis_ok(v1705_manifest)
    static_ok = (
        binary_sha == v1703.EXPECTED_CNSS_SHA
        and bool(function_block)
        and all(patterns.values())
        and all(item["match"] for item in strings.values())
    )
    pass_ok = basis_ok and static_ok
    decision = "v1706-wlfw-start-branch-static-map-pass" if pass_ok else "v1706-wlfw-start-branch-static-map-incomplete"
    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1705 proves wlfw_start entry but no worker entry; static branch map identifies the pre-worker pthread_create gate"
            if pass_ok else
            "V1705 basis or wlfw_start static branch map is incomplete"
        ),
        "inputs": {
            "v1703_manifest": display_path(args.v1703_manifest),
            "v1705_manifest": display_path(args.v1705_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "objdump": display_path(args.objdump),
        },
        "binary": {
            "sha256": binary_sha,
            "sha256_ok": binary_sha == v1703.EXPECTED_CNSS_SHA,
            "size": args.cnss_daemon.stat().st_size,
        },
        "v1703_basis": {
            "decision": v1703_manifest.get("decision"),
            "pass": v1703_manifest.get("pass"),
            "sha256_ok": v1703_manifest.get("binary", {}).get("sha256_ok"),
        },
        "v1705_basis": {
            "decision": v1705_manifest.get("decision"),
            "pass": v1705_manifest.get("pass"),
            "rollback_ok": v1705_manifest.get("rollback", {}).get("ok"),
            "nonlog_label": v1705_manifest.get("gate", {}).get("nonlog_label"),
            "wlfw_start_hit_count": v1705_manifest.get("gate", {}).get("nonlog_wlfw_start_hit_count"),
            "wlfw_service_request_hit_count": v1705_manifest.get("gate", {}).get("nonlog_wlfw_service_request_hit_count"),
            "ind_register_hit_count": v1705_manifest.get("gate", {}).get("nonlog_wlfw_ind_register_qmi_hit_count"),
            "cap_hit_count": v1705_manifest.get("gate", {}).get("nonlog_wlfw_cap_qmi_hit_count"),
            "legacy_firmware_serve_label": v1705_manifest.get("gate", {}).get("old_firmware_serve_label"),
        },
        "function_block_present": bool(function_block),
        "function_block": function_block,
        "branch_patterns": patterns,
        "strings": strings,
        "branch_targets": BRANCH_TARGETS,
        "preworker_model": {
            "entry": "wlfw_start@0xec00 logs Starting unconditionally",
            "init_sequence": [
                "pthread_mutex_init cal_mutex -> fail before worker if nonzero",
                "pthread_mutex_init mutex -> fail before worker if nonzero",
                "pthread_cond_init cond -> fail before worker if nonzero",
                "pthread_cond_init cond_rsp -> fail before worker if nonzero",
                "pthread_initialize_dms@0xeb14 -> fail before worker if nonzero",
            ],
            "worker_create": "pthread_create@0xecf0 targets wlfw_service_request@0xd9fc; success branches to 0xeda0 and sets flag at 0xedc0",
            "v1705_gap": "wlfw_start hit plus wlfw_service_request hit 0 means execution likely exits before/at pthread_create, or pthread_create success path does not schedule the expected target within the window",
        },
        "next_gate": {
            "cycle": "V1707/V1708 candidate",
            "type": "source/build-only then one-run rollbackable branch uprobe classifier",
            "route": "reuse V1705 internal-modem firmware-serve route only",
            "primary_targets": NEXT_LIVE_TARGETS,
            "labels": [
                "wlfw-start-dms-init-failed-before-worker",
                "wlfw-start-pthread-create-not-reached",
                "wlfw-start-pthread-create-failed",
                "wlfw-start-pthread-create-success-worker-missing",
                "wlfw-start-worker-entry-reached",
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
        "# Native Init V1706 CNSS WLFW Start Branch Static Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{result['cycle']}`",
        "- Type: host-only cnss-daemon `wlfw_start` branch classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{status}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{display_path(DEFAULT_OUT_DIR)}`",
        "",
        "## Basis",
        "",
        f"- V1703 decision: `{result['v1703_basis']['decision']}` pass `{result['v1703_basis']['pass']}` sha ok `{result['v1703_basis']['sha256_ok']}`",
        f"- V1705 decision: `{result['v1705_basis']['decision']}` pass `{result['v1705_basis']['pass']}` rollback `{result['v1705_basis']['rollback_ok']}`",
        f"- V1705 label: `{result['v1705_basis']['nonlog_label']}`",
        f"- V1705 hits: `wlfw_start={result['v1705_basis']['wlfw_start_hit_count']}`, `wlfw_service_request={result['v1705_basis']['wlfw_service_request_hit_count']}`, `ind_register={result['v1705_basis']['ind_register_hit_count']}`, `cap={result['v1705_basis']['cap_hit_count']}`",
        f"- Legacy firmware-serve label: `{result['v1705_basis']['legacy_firmware_serve_label']}`",
        "",
        "## Branch Map",
        "",
        "| Target | Offset | Meaning |",
        "| --- | --- | --- |",
    ]
    for target in result["branch_targets"]:
        lines.append(f"| `{target['name']}` | `{target['offset']}` | {target['meaning']} |")
    lines.extend([
        "",
        "## Pattern Checks",
        "",
        "| Pattern | Present |",
        "| --- | --- |",
    ])
    for name, present in result["branch_patterns"].items():
        lines.append(f"| `{name}` | `{present}` |")
    lines.extend([
        "",
        "## Failure / Status Strings",
        "",
        "| Key | Offset | Text | Match |",
        "| --- | --- | --- | --- |",
    ])
    for key, item in result["strings"].items():
        lines.append(f"| `{key}` | `{item['actual_offset']}` | `{item['value']}` | `{item['match']}` |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `wlfw_start` logs `Starting` before any meaningful initialization, so a `wlfw_start` hit alone is not enough to prove worker creation.",
        "- The primary gap is now narrowed to the pre-worker sequence inside `wlfw_start`: mutex/cond init, `pthread_initialize_dms`, or `pthread_create@0xecf0`.",
        "- V1705 saw no `wlfw_service_request@0xd9fc` hit, so WLFW QMI/BDF remains downstream and should not be chased yet.",
        "- The next bounded live unit should trace `0xecd4`, `0xecd8`, `0xecf0`, `0xecf8`, and `0xeda0` under the same internal-modem firmware-serve route.",
        "",
        "## Next Gate",
        "",
        "- Type: source/build-only helper expansion followed by one rollbackable branch uprobe live run.",
        "- Route: reuse V1705 internal-modem firmware-serve route only.",
        "- Labels: `wlfw-start-dms-init-failed-before-worker`, `wlfw-start-pthread-create-not-reached`, `wlfw-start-pthread-create-failed`, `wlfw-start-pthread-create-success-worker-missing`, `wlfw-start-worker-entry-reached`, `cnss-target-unavailable`.",
        "- Forbidden: PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--v1703-manifest", type=Path, default=DEFAULT_V1703_MANIFEST)
    parser.add_argument("--v1705-manifest", type=Path, default=DEFAULT_V1705_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    for path in (args.cnss_daemon, args.v1703_manifest, args.v1705_manifest):
        if not path.exists():
            raise SystemExit(f"missing required input: {display_path(path)}")

    v1703.ensure_private_dir(args.out_dir)
    result = build_manifest(args)
    manifest_path = args.out_dir / "manifest.json"
    v1703.write_private_text(manifest_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    v1703.write_private_text(args.report, render_report(result))
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
