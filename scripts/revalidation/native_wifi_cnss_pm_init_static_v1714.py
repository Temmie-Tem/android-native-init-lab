#!/usr/bin/env python3
"""Host-only V1714 classifier for cnss-daemon pm_init flow."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_cnss_wlfw_downstream_static_v1703 as v1703


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1714"
DATE = "2026-06-02"
DEFAULT_CNSS_DAEMON = v1703.DEFAULT_CNSS_DAEMON
DEFAULT_OBJDUMP = v1703.DEFAULT_OBJDUMP
DEFAULT_V1711_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1711-cnss-wlfw-start-prologue-static" / "manifest.json"
DEFAULT_V1713_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1713-cnss-wlfw-prologue-adjacent-uprobe-handoff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1714-cnss-pm-init-static"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / f"NATIVE_INIT_{CYCLE}_CNSS_PM_INIT_STATIC_{DATE}.md"
)

PM_INIT_TARGETS = [
    {
        "name": "pm_init_entry",
        "offset": "0xc39c",
        "instruction": "stp x29, x30, [sp, #-96]!",
        "meaning": "function entry; V1713 proves wlfw_start blocks after calling this function",
    },
    {
        "name": "pm_init_entry_log_call",
        "offset": "0xc400",
        "instruction": "bl 0xa21c",
        "meaning": "logs pm_init start with requested type",
    },
    {
        "name": "pm_init_type_check",
        "offset": "0xc404",
        "instruction": "cmp w19, #0x2",
        "meaning": "rejects unsupported mdm type >= 2",
    },
    {
        "name": "pm_init_get_system_info_call",
        "offset": "0xc444",
        "instruction": "bl get_system_info@plt",
        "meaning": "reads modem/eSoC system info from libmdmdetect",
    },
    {
        "name": "pm_init_system_info_ok",
        "offset": "0xc470",
        "instruction": "ldr w3, [sp, #8]",
        "meaning": "get_system_info succeeded and count is about to be logged/read",
    },
    {
        "name": "pm_init_null_peripheral_branch",
        "offset": "0xc49c",
        "instruction": "cbz x21, 0xc58c",
        "meaning": "V1713 call uses x1=NULL, so this branch should enter the null-peripheral all-entry loop",
    },
    {
        "name": "pm_init_null_peripheral_loop_entry",
        "offset": "0xc58c",
        "instruction": "add x8, sp, #0x8",
        "meaning": "null-peripheral path entry",
    },
    {
        "name": "pm_init_null_loop_type_check",
        "offset": "0xc5e0",
        "instruction": "ldur w8, [x26, #-4]",
        "meaning": "iterates system-info entries looking for requested type",
    },
    {
        "name": "pm_init_pm_client_register_call",
        "offset": "0xc624",
        "instruction": "bl pm_client_register@plt",
        "meaning": "registers peripheral manager client for matching entry",
    },
    {
        "name": "pm_init_pm_client_register_retcheck",
        "offset": "0xc628",
        "instruction": "cbnz w0, 0xc5b8",
        "meaning": "detects pm_client_register return; failure loops to next entry",
    },
    {
        "name": "pm_init_handle_load",
        "offset": "0xc62c",
        "instruction": "ldr x19, [x20]",
        "meaning": "loads pm client handle after registration success",
    },
    {
        "name": "pm_init_pm_client_connect_call",
        "offset": "0xc650",
        "instruction": "bl pm_client_connect@plt",
        "meaning": "connects/votes to peripheral manager; likely live blocking candidate if register succeeds",
    },
    {
        "name": "pm_init_pm_client_connect_retcheck",
        "offset": "0xc654",
        "instruction": "mov w25, w0",
        "meaning": "first proof that pm_client_connect returned",
    },
    {
        "name": "pm_init_return_path",
        "offset": "0xc554",
        "instruction": "ldr x8, [x28, #40]",
        "meaning": "common return path",
    },
]

EXPECTED_PATTERNS = {
    "entry": "c39c:\ta9ba7bfd \tstp\tx29, x30, [sp, #-96]!",
    "start_log": "c400:\t97fff787 \tbl\ta21c",
    "type_check": "c404:\t71000a7f \tcmp\tw19, #0x2",
    "get_system_info_call": "c444:\t94001f93 \tbl\t14290 <get_system_info@plt>",
    "system_info_ok_branch": "c448:\t34000140 \tcbz\tw0, c470",
    "null_peripheral_branch": "c49c:\tb4000795 \tcbz\tx21, c58c",
    "null_path_entry": "c58c:\t910023e8 \tadd\tx8, sp, #0x8",
    "null_loop_type_check": "c5e0:\tb85fc348 \tldur\tw8, [x26, #-4]",
    "pm_client_register_call": "c624:\t94001f23 \tbl\t142b0 <pm_client_register@plt>",
    "pm_client_register_retcheck": "c628:\t35fffc80 \tcbnz\tw0, c5b8",
    "handle_load": "c62c:\tf9400293 \tldr\tx19, [x20]",
    "pm_client_connect_call": "c650:\t94001f1c \tbl\t142c0 <pm_client_connect@plt>",
    "pm_client_connect_retcheck": "c654:\t2a0003f9 \tmov\tw25, w0",
    "return_path": "c554:\tf9401788 \tldr\tx8, [x28, #40]",
}

NEXT_LIVE_TARGETS = [
    {
        "target": "cnss-daemon+0xc400",
        "name": "pm_init_entry_log_call",
        "purpose": "prove pm_init reaches and returns from its entry logging path",
    },
    {
        "target": "cnss-daemon+0xc444",
        "name": "pm_init_get_system_info_call",
        "purpose": "prove pm_init reaches libmdmdetect system-info read",
    },
    {
        "target": "cnss-daemon+0xc470",
        "name": "pm_init_system_info_ok",
        "purpose": "prove get_system_info returned success",
    },
    {
        "target": "cnss-daemon+0xc58c",
        "name": "pm_init_null_peripheral_loop_entry",
        "purpose": "prove x1=NULL path enters all-entry PM registration loop",
    },
    {
        "target": "cnss-daemon+0xc624",
        "name": "pm_init_pm_client_register_call",
        "purpose": "prove pm_client_register is attempted",
    },
    {
        "target": "cnss-daemon+0xc628",
        "name": "pm_init_pm_client_register_retcheck",
        "purpose": "prove pm_client_register returns",
    },
    {
        "target": "cnss-daemon+0xc650",
        "name": "pm_init_pm_client_connect_call",
        "purpose": "prove pm_client_connect is attempted after registration success",
    },
    {
        "target": "cnss-daemon+0xc654",
        "name": "pm_init_pm_client_connect_retcheck",
        "purpose": "prove pm_client_connect returned",
    },
]


def display_path(path: Path) -> str:
    return v1703.display_path(path)


def read_json(path: Path) -> dict[str, Any]:
    return v1703.read_json(path)


def intish(value: Any, default: int = 0) -> int:
    return v1703.intish(value, default)


def extract_block(disassembly: str, start: str = "c39c", end: str = "c690") -> str:
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
    return {name: pattern in block for name, pattern in EXPECTED_PATTERNS.items()}


def v1713_basis_ok(v1713: dict[str, Any]) -> bool:
    gate = v1713.get("gate", {})
    return (
        v1713.get("decision") == "v1713-wlfw-start-optional-pm-init1-call-no-return-rollback-pass"
        and v1713.get("pass") is True
        and v1713.get("rollback", {}).get("ok") is True
        and gate.get("nonlog_label") == "wlfw-start-optional-pm-init1-call-no-return"
        and intish(gate.get("nonlog_wlfw_optional_pm_init1_call_hit_count")) >= 1
        and intish(gate.get("nonlog_wlfw_optional_pm_init1_return_hit_count")) == 0
        and gate.get("old_firmware_serve_label") == "firmware-not-requested"
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1711 = read_json(args.v1711_manifest)
    v1713 = read_json(args.v1713_manifest)
    v1703.ensure_objdump(args.cnss_daemon, args.objdump)
    disassembly = args.objdump.read_text(encoding="utf-8", errors="replace")
    block = extract_block(disassembly)
    patterns = check_patterns(block)
    binary_sha = v1703.sha256_file(args.cnss_daemon)
    v1711_ready = (
        v1711.get("decision") == "v1711-wlfw-start-prologue-static-map-pass"
        and v1711.get("pass") is True
    )
    basis_ok = v1711_ready and v1713_basis_ok(v1713)
    static_ok = binary_sha == v1703.EXPECTED_CNSS_SHA and bool(block) and all(patterns.values())
    pass_ok = basis_ok and static_ok
    decision = "v1714-cnss-pm-init-static-map-pass" if pass_ok else "v1714-cnss-pm-init-static-map-incomplete"
    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1713 proves wlfw_start blocks inside pm_init; static map identifies get_system_info, pm_client_register, and pm_client_connect discriminators"
            if pass_ok else
            "V1713 basis or pm_init static map is incomplete"
        ),
        "inputs": {
            "v1711_manifest": display_path(args.v1711_manifest),
            "v1713_manifest": display_path(args.v1713_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "objdump": display_path(args.objdump),
        },
        "binary": {
            "sha256": binary_sha,
            "sha256_ok": binary_sha == v1703.EXPECTED_CNSS_SHA,
            "size": args.cnss_daemon.stat().st_size,
        },
        "v1711_basis": {
            "decision": v1711.get("decision"),
            "pass": v1711.get("pass"),
        },
        "v1713_basis": {
            "decision": v1713.get("decision"),
            "pass": v1713.get("pass"),
            "rollback_ok": v1713.get("rollback", {}).get("ok"),
            "nonlog_label": v1713.get("gate", {}).get("nonlog_label"),
            "optional_pm_init1_call_hit_count": v1713.get("gate", {}).get("nonlog_wlfw_optional_pm_init1_call_hit_count"),
            "optional_pm_init1_return_hit_count": v1713.get("gate", {}).get("nonlog_wlfw_optional_pm_init1_return_hit_count"),
            "legacy_firmware_serve_label": v1713.get("gate", {}).get("old_firmware_serve_label"),
        },
        "pm_init_block_present": bool(block),
        "pm_init_block": block,
        "pm_init_patterns": patterns,
        "pm_init_targets": PM_INIT_TARGETS,
        "interpretation": {
            "v1713_gap": "pm_init is called from wlfw_start with x1=NULL and does not return in the bounded window",
            "null_path": "x1=NULL selects the all-entry loop at 0xc58c after get_system_info succeeds",
            "likely_live_discriminators": "pm_client_register@0xc624 and pm_client_connect@0xc650 are the first concrete external PM-client calls on the null path",
            "safe_scope": "read-only tracefs uprobes under the same internal-modem firmware-serve route; no PM/service actor addition before this path is classified",
        },
        "next_gate": {
            "cycle": "V1715 candidate",
            "type": "source/build-only helper expansion then one-run rollbackable pm_init uprobe classifier",
            "route": "reuse V1713 internal-modem firmware-serve route only",
            "primary_targets": NEXT_LIVE_TARGETS,
            "labels": [
                "pm-init-get-system-info-blocked",
                "pm-init-null-loop-not-reached",
                "pm-init-register-call-no-return",
                "pm-init-register-returned-no-connect",
                "pm-init-connect-call-no-return",
                "pm-init-connect-returned",
                "cnss-target-unavailable",
            ],
            "forbidden": [
                "adding PM/service-window actors",
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
        "# Native Init V1714 CNSS pm_init Static Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{result['cycle']}`",
        "- Type: host-only `cnss-daemon` `pm_init@0xc39c` classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{status}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{display_path(DEFAULT_OUT_DIR)}`",
        "",
        "## Basis",
        "",
        f"- V1711 decision: `{result['v1711_basis']['decision']}` pass `{result['v1711_basis']['pass']}`",
        f"- V1713 decision: `{result['v1713_basis']['decision']}` pass `{result['v1713_basis']['pass']}` rollback `{result['v1713_basis']['rollback_ok']}`",
        f"- V1713 label: `{result['v1713_basis']['nonlog_label']}`",
        f"- V1713 hits: `optional_pm_init1_call={result['v1713_basis']['optional_pm_init1_call_hit_count']}`, `optional_pm_init1_return={result['v1713_basis']['optional_pm_init1_return_hit_count']}`",
        f"- Legacy firmware-serve label: `{result['v1713_basis']['legacy_firmware_serve_label']}`",
        "",
        "## pm_init Map",
        "",
        "| Target | Offset | Instruction | Meaning |",
        "| --- | --- | --- | --- |",
    ]
    for target in result["pm_init_targets"]:
        lines.append(f"| `{target['name']}` | `{target['offset']}` | `{target['instruction']}` | {target['meaning']} |")
    lines.extend([
        "",
        "## Pattern Checks",
        "",
        "| Pattern | Present |",
        "| --- | --- |",
    ])
    for name, present in result["pm_init_patterns"].items():
        lines.append(f"| `{name}` | `{present}` |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- V1713 proves `wlfw_start` reaches `pm_init@0xc39c` and does not return from the first call.",
        "- The call site uses the zero-argument path, so `pm_init` should eventually branch to the null-peripheral loop at `0xc58c` after `get_system_info` succeeds.",
        "- The first concrete PM-client operations on that path are `pm_client_register@0xc624` and `pm_client_connect@0xc650`.",
        "- Do not add PM/service-window actors until a bounded live probe proves whether this route blocks in `get_system_info`, `pm_client_register`, or `pm_client_connect`.",
        "",
        "## Next Gate",
        "",
        "- Type: source/build-only helper expansion followed by one rollbackable `pm_init` uprobe live run.",
        "- Route: reuse V1713 internal-modem firmware-serve route only.",
        "- Labels: `pm-init-get-system-info-blocked`, `pm-init-null-loop-not-reached`, `pm-init-register-call-no-return`, `pm-init-register-returned-no-connect`, `pm-init-connect-call-no-return`, `pm-init-connect-returned`, `cnss-target-unavailable`.",
        "- Forbidden: adding PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--v1711-manifest", type=Path, default=DEFAULT_V1711_MANIFEST)
    parser.add_argument("--v1713-manifest", type=Path, default=DEFAULT_V1713_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    for path in (args.cnss_daemon, args.v1711_manifest, args.v1713_manifest):
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
