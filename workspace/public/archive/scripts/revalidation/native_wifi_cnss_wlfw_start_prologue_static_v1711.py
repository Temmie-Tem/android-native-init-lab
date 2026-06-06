#!/usr/bin/env python3
"""Host-only V1711 classifier for cnss-daemon wlfw_start prologue flow."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_cnss_wlfw_downstream_static_v1703 as v1703


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1711"
DATE = "2026-06-02"
DEFAULT_CNSS_DAEMON = v1703.DEFAULT_CNSS_DAEMON
DEFAULT_OBJDUMP = v1703.DEFAULT_OBJDUMP
DEFAULT_V1706_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1706-cnss-wlfw-start-branch-static" / "manifest.json"
DEFAULT_V1710_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1710-cnss-wlfw-pre-dms-microtrace-handoff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1711-cnss-wlfw-start-prologue-static"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / f"NATIVE_INIT_{CYCLE}_CNSS_WLFW_START_PROLOGUE_STATIC_{DATE}.md"
)

PROLOGUE_TARGETS = [
    {
        "name": "wlfw_start_entry",
        "offset": "0xec00",
        "instruction": "stp x29, x30, [sp, #-32]!",
        "meaning": "function entry; V1705/V1708/V1710 prove this target is reachable",
    },
    {
        "name": "wlfw_start_log_arg_severity",
        "offset": "0xec20",
        "instruction": "mov w0, #0x2",
        "meaning": "sets severity for the unconditional Starting log call",
    },
    {
        "name": "wlfw_start_log_call",
        "offset": "0xec24",
        "instruction": "bl 0xa21c",
        "meaning": "unconditional log wrapper call before any pthread init",
    },
    {
        "name": "wlfw_start_post_log_branch",
        "offset": "0xec28",
        "instruction": "cbnz w19, 0xec48",
        "meaning": "first proof that the unconditional log call returned",
    },
    {
        "name": "wlfw_start_optional_pm_init1_call",
        "offset": "0xec34",
        "instruction": "bl 0xc39c",
        "meaning": "optional setup call when wlfw_start argument is zero",
    },
    {
        "name": "wlfw_start_optional_pm_init1_return",
        "offset": "0xec38",
        "instruction": "adrp x1, 0x6000",
        "meaning": "optional setup call 1 returned",
    },
    {
        "name": "wlfw_start_optional_pm_init2_call",
        "offset": "0xec44",
        "instruction": "bl 0xc39c",
        "meaning": "optional setup call 2 when wlfw_start argument is zero",
    },
    {
        "name": "wlfw_start_common_state_base",
        "offset": "0xec48",
        "instruction": "adrp x20, 0x21000",
        "meaning": "common path after log/optional setup; first target before mutex state setup",
    },
    {
        "name": "wlfw_start_cal_mutex_arg",
        "offset": "0xec50",
        "instruction": "add x0, x20, #0x148",
        "meaning": "builds cal_mutex pointer immediately before pthread_mutex_init",
    },
    {
        "name": "wlfw_start_cal_mutex_call",
        "offset": "0xec58",
        "instruction": "bl pthread_mutex_init@plt",
        "meaning": "first pre-DMS pthread init call; V1710 proves this did not hit",
    },
]

EXPECTED_PROLOGUE_PATTERNS = {
    "entry": "ec00:\ta9be7bfd \tstp\tx29, x30, [sp, #-32]!",
    "save_regs": "ec04:\ta9014ff4 \tstp\tx20, x19, [sp, #16]",
    "arg_save": "ec14:\t2a0003f3 \tmov\tw19, w0",
    "log_severity": "ec20:\t52800040 \tmov\tw0, #0x2",
    "log_call": "ec24:\t97ffed7e \tbl\ta21c",
    "post_log_branch": "ec28:\t35000113 \tcbnz\tw19, ec48",
    "optional_pm_init1_call": "ec34:\t97fff5da \tbl\tc39c",
    "optional_pm_init1_return": "ec38:\t90ffffc1 \tadrp\tx1, 6000",
    "optional_pm_init2_call": "ec44:\t97fff5d6 \tbl\tc39c",
    "common_state_base": "ec48:\tf0000094 \tadrp\tx20, 21000",
    "cal_mutex_arg": "ec50:\t91052280 \tadd\tx0, x20, #0x148",
    "cal_mutex_call": "ec58:\t940015ea \tbl\t14400 <pthread_mutex_init@plt>",
}

NEXT_LIVE_TARGETS = [
    {
        "target": "cnss-daemon+0xec20",
        "name": "wlfw_start_log_arg_severity",
        "purpose": "prove execution reaches the instruction immediately before the unconditional log call",
    },
    {
        "target": "cnss-daemon+0xec24",
        "name": "wlfw_start_log_call",
        "purpose": "prove the unconditional log call itself is attempted",
    },
    {
        "target": "cnss-daemon+0xec28",
        "name": "wlfw_start_post_log_branch",
        "purpose": "prove the log call returns to wlfw_start",
    },
    {
        "target": "cnss-daemon+0xec34",
        "name": "wlfw_start_optional_pm_init1_call",
        "purpose": "detect the zero-argument optional setup path if taken",
    },
    {
        "target": "cnss-daemon+0xec44",
        "name": "wlfw_start_optional_pm_init2_call",
        "purpose": "detect the second optional setup call if the zero-argument path is taken",
    },
    {
        "target": "cnss-daemon+0xec48",
        "name": "wlfw_start_common_state_base",
        "purpose": "prove execution reaches the common path after log/optional setup",
    },
    {
        "target": "cnss-daemon+0xec50",
        "name": "wlfw_start_cal_mutex_arg",
        "purpose": "prove execution reaches the instruction immediately before first pthread_mutex_init",
    },
    {
        "target": "cnss-daemon+0xec58",
        "name": "wlfw_start_cal_mutex_call",
        "purpose": "retain the V1710 first pthread init call target as downstream continuity check",
    },
]


def display_path(path: Path) -> str:
    return v1703.display_path(path)


def read_json(path: Path) -> dict[str, Any]:
    return v1703.read_json(path)


def intish(value: Any, default: int = 0) -> int:
    return v1703.intish(value, default)


def extract_block(disassembly: str, start: str = "ec00", end: str = "ec5c") -> str:
    lines: list[str] = []
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


def check_patterns(block: str) -> dict[str, bool]:
    return {name: pattern in block for name, pattern in EXPECTED_PROLOGUE_PATTERNS.items()}


def v1710_basis_ok(v1710: dict[str, Any]) -> bool:
    gate = v1710.get("gate", {})
    return (
        v1710.get("decision") == "v1710-wlfw-start-pthread-create-not-reached-rollback-pass"
        and v1710.get("pass") is True
        and v1710.get("rollback", {}).get("ok") is True
        and gate.get("nonlog_label") == "wlfw-start-pthread-create-not-reached"
        and intish(gate.get("nonlog_wlfw_start_hit_count")) >= 1
        and intish(gate.get("nonlog_wlfw_cal_mutex_call_hit_count")) == 0
        and intish(gate.get("nonlog_wlfw_cal_mutex_retcheck_hit_count")) == 0
        and intish(gate.get("nonlog_wlfw_dms_initialize_call_hit_count")) == 0
        and gate.get("old_firmware_serve_label") == "firmware-not-requested"
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1706 = read_json(args.v1706_manifest)
    v1710 = read_json(args.v1710_manifest)
    v1703.ensure_objdump(args.cnss_daemon, args.objdump)
    disassembly = args.objdump.read_text(encoding="utf-8", errors="replace")
    block = extract_block(disassembly)
    patterns = check_patterns(block)
    binary_sha = v1703.sha256_file(args.cnss_daemon)
    v1706_ready = (
        v1706.get("decision") == "v1706-wlfw-start-branch-static-map-pass"
        and v1706.get("pass") is True
    )
    basis_ok = v1706_ready and v1710_basis_ok(v1710)
    static_ok = binary_sha == v1703.EXPECTED_CNSS_SHA and bool(block) and all(patterns.values())
    pass_ok = basis_ok and static_ok
    decision = (
        "v1711-wlfw-start-prologue-static-map-pass"
        if pass_ok
        else "v1711-wlfw-start-prologue-static-map-incomplete"
    )
    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1710 proves wlfw_start entry but no first pthread init call; static prologue map identifies adjacent targets before 0xec58"
            if pass_ok else
            "V1710 basis or wlfw_start prologue static map is incomplete"
        ),
        "inputs": {
            "v1706_manifest": display_path(args.v1706_manifest),
            "v1710_manifest": display_path(args.v1710_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "objdump": display_path(args.objdump),
        },
        "binary": {
            "sha256": binary_sha,
            "sha256_ok": binary_sha == v1703.EXPECTED_CNSS_SHA,
            "size": args.cnss_daemon.stat().st_size,
        },
        "v1706_basis": {
            "decision": v1706.get("decision"),
            "pass": v1706.get("pass"),
        },
        "v1710_basis": {
            "decision": v1710.get("decision"),
            "pass": v1710.get("pass"),
            "rollback_ok": v1710.get("rollback", {}).get("ok"),
            "nonlog_label": v1710.get("gate", {}).get("nonlog_label"),
            "wlfw_start_hit_count": v1710.get("gate", {}).get("nonlog_wlfw_start_hit_count"),
            "cal_mutex_call_hit_count": v1710.get("gate", {}).get("nonlog_wlfw_cal_mutex_call_hit_count"),
            "legacy_firmware_serve_label": v1710.get("gate", {}).get("old_firmware_serve_label"),
        },
        "prologue_block_present": bool(block),
        "prologue_block": block,
        "prologue_patterns": patterns,
        "prologue_targets": PROLOGUE_TARGETS,
        "interpretation": {
            "entry_only_meaning": "V1710 entry hit plus 0xec58 miss means the gap is between entry and first pthread_mutex_init, or the live target interpretation needs adjacent-instruction validation",
            "first_live_discriminator": "0xec24 hit without 0xec28 hit means the unconditional log wrapper did not return in the bounded window",
            "common_path_discriminator": "0xec48/0xec50 hits without 0xec58 hit would narrow the block to the first pthread_mutex_init call edge",
            "safe_scope": "read-only tracefs uprobes under the same internal-modem firmware-serve route; no new actors or Wi-Fi HAL/connect expansion",
        },
        "next_gate": {
            "cycle": "V1712 candidate",
            "type": "source/build-only helper expansion then one-run rollbackable adjacent prologue uprobe classifier",
            "route": "reuse V1710 internal-modem firmware-serve route only",
            "primary_targets": NEXT_LIVE_TARGETS,
            "labels": [
                "wlfw-start-log-call-no-return",
                "wlfw-start-common-path-not-reached",
                "wlfw-start-common-path-no-cal-mutex-arg",
                "wlfw-start-cal-mutex-edge-no-call",
                "wlfw-start-cal-mutex-call-reached",
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
        "# Native Init V1711 CNSS WLFW Start Prologue Static Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{result['cycle']}`",
        "- Type: host-only `cnss-daemon` `wlfw_start@0xec00..0xec58` prologue classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{status}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{display_path(DEFAULT_OUT_DIR)}`",
        "",
        "## Basis",
        "",
        f"- V1706 decision: `{result['v1706_basis']['decision']}` pass `{result['v1706_basis']['pass']}`",
        f"- V1710 decision: `{result['v1710_basis']['decision']}` pass `{result['v1710_basis']['pass']}` rollback `{result['v1710_basis']['rollback_ok']}`",
        f"- V1710 label: `{result['v1710_basis']['nonlog_label']}`",
        f"- V1710 hits: `wlfw_start={result['v1710_basis']['wlfw_start_hit_count']}`, `cal_mutex_call={result['v1710_basis']['cal_mutex_call_hit_count']}`",
        f"- Legacy firmware-serve label: `{result['v1710_basis']['legacy_firmware_serve_label']}`",
        "",
        "## Prologue Map",
        "",
        "| Target | Offset | Instruction | Meaning |",
        "| --- | --- | --- | --- |",
    ]
    for target in result["prologue_targets"]:
        lines.append(f"| `{target['name']}` | `{target['offset']}` | `{target['instruction']}` | {target['meaning']} |")
    lines.extend([
        "",
        "## Pattern Checks",
        "",
        "| Pattern | Present |",
        "| --- | --- |",
    ])
    for name, present in result["prologue_patterns"].items():
        lines.append(f"| `{name}` | `{present}` |")
    lines.extend([
        "",
        "## Disassembly",
        "",
        "```",
        result["prologue_block"],
        "```",
        "",
        "## Interpretation",
        "",
        "- V1710 proves `wlfw_start@0xec00` is reached but `pthread_mutex_init@0xec58` is not reached.",
        "- The only static instructions between those points are the unconditional log call at `0xec24`, an optional two-call setup path when the argument is zero, and the common state-base setup at `0xec48..0xec54`.",
        "- Therefore the next live discriminator should trace adjacent prologue targets, especially `0xec24`, `0xec28`, `0xec48`, `0xec50`, and `0xec58`.",
        "- Do not expand to WLFW QMI, BDF, MSA, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until this prologue gap is resolved.",
        "",
        "## Next Gate",
        "",
        "- Type: source/build-only helper expansion followed by one rollbackable adjacent-prologue uprobe live run.",
        "- Route: reuse V1710 internal-modem firmware-serve route only.",
        "- Labels: `wlfw-start-log-call-no-return`, `wlfw-start-common-path-not-reached`, `wlfw-start-common-path-no-cal-mutex-arg`, `wlfw-start-cal-mutex-edge-no-call`, `wlfw-start-cal-mutex-call-reached`, `cnss-target-unavailable`.",
        "- Forbidden: PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--v1706-manifest", type=Path, default=DEFAULT_V1706_MANIFEST)
    parser.add_argument("--v1710-manifest", type=Path, default=DEFAULT_V1710_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    for path in (args.cnss_daemon, args.v1706_manifest, args.v1710_manifest):
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
