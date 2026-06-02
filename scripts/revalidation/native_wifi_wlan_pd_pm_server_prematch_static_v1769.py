#!/usr/bin/env python3
"""V1769 host-only static classifier for pm-service pre-match register path.

This unit disassembles the retained stock pm-service binary around the V1768
`0x6048..0x60cc` boundary and reconciles it with V1107 mutex-owner evidence.  It
does not contact the device.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1769-wlan-pd-pm-server-prematch-static"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1769_WLAN_PD_PM_SERVER_PREMATCH_STATIC_2026-06-03.md"
)

PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
INPUTS = {
    "pm_service": PM_SERVICE,
    "v1768": REPO_ROOT / "tmp" / "wifi" / "v1768-wlan-pd-pm-server-branch-classifier" / "manifest.json",
    "v1107": REPO_ROOT / "tmp" / "wifi" / "v1107-pm-server-mutex-owner-classifier" / "manifest.json",
    "v1107_report": REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1107_PM_SERVER_MUTEX_OWNER_CLASSIFIER_2026-05-27.md",
}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = display_path(path)
    return payload


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def run_objdump(start: str, stop: str) -> str:
    objdump = shutil.which("aarch64-linux-gnu-objdump") or shutil.which("llvm-objdump") or shutil.which("objdump")
    if not objdump:
        raise RuntimeError("no objdump available")
    result = subprocess.run(
        [objdump, "-d", f"--start-address={start}", f"--stop-address={stop}", str(PM_SERVICE)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.MULTILINE) is not None


def collect(out_dir: Path) -> dict[str, Any]:
    host_dir = out_dir / "host"
    host_dir.mkdir(parents=True, exist_ok=True)

    prematch = run_objdump("0x6048", "0x60cc")
    surrounding = run_objdump("0x6048", "0x614c")
    getter = run_objdump("0x9538", "0x9568")

    write_private_text(host_dir / "pm-service-register-prematch-0x6048-0x60cc.S", prematch)
    write_private_text(host_dir / "pm-service-register-surrounding-0x6048-0x614c.S", surrounding)
    write_private_text(host_dir / "pm-service-record-getter-0x9538-0x9568.S", getter)

    v1768 = load_json(INPUTS["v1768"])
    v1107 = load_json(INPUTS["v1107"])
    v1107_report = read_text(INPUTS["v1107_report"])
    v1107_analysis = v1107.get("analysis") or {}
    v1107_mutex = v1107_analysis.get("mutex_owner") or {}
    owner = v1107_mutex.get("owner") or {}
    owner_state = v1107_analysis.get("owner_thread_state") or {}
    cnss_pending = v1107_analysis.get("target_cnss_pending") or {}
    waiter_state = v1107_analysis.get("waiter_thread_state") or {}

    facts = {
        "pm_service_binary_present": PM_SERVICE.exists(),
        "v1768_prematch_label": v1768.get("label") == "pm-server-register-entry-only-before-match"
        and boolish(v1768.get("pass")),
        "prematch_saves_outputs": contains(prematch, r"str\s+xzr, \[x4\]") and contains(prematch, r"str\s+xzr, \[x5\]"),
        "prematch_iterates_supported_list": contains(prematch, r"ldr\s+x27, \[x0, #40\]")
        and contains(prematch, r"add\s+x28, x0, #0x20"),
        "prematch_calls_record_getter": "bl\t9538" in prematch or "bl\t0000000000009538" in prematch,
        "prematch_uses_strcmp": "strcmp@plt" in prematch,
        "prematch_branches_to_match": "60cc" in prematch and "cbz" in prematch,
        "prematch_falls_to_no_peripheral": "6148" in surrounding,
        "permission_starts_after_match": "getCallingUid" in surrounding and "60d0" in surrounding,
        "getter_locks_record_mutex": "pthread_mutex_lock@plt" in getter and "pthread_mutex_unlock@plt" in getter,
        "v1107_mutex_owner_blocked": v1107.get("decision") == "v1107-modem-mutex-owner-blocked-in-subsystem-get"
        and boolish(v1107.get("pass")),
        "v1107_owner_return_offset": owner.get("return_offset"),
        "v1107_owner_wchans": owner_state.get("wchans") or [],
        "v1107_cnss_waiter_wchans": cnss_pending.get("wchans") or waiter_state.get("wchans") or [],
        "v1107_report_mentions_same_mutex": "CNSS waits in futex on the same mutex" in v1107_report
        or "CNSS TID" in v1107_report
        and "waited in futex on the same mutex" in v1107_report,
    }
    return {
        "facts": facts,
        "artifacts": {
            "prematch_disasm": display_path(host_dir / "pm-service-register-prematch-0x6048-0x60cc.S"),
            "surrounding_disasm": display_path(host_dir / "pm-service-register-surrounding-0x6048-0x614c.S"),
            "getter_disasm": display_path(host_dir / "pm-service-record-getter-0x9538-0x9568.S"),
        },
    }


def classify(facts: dict[str, Any]) -> tuple[str, bool, str, str]:
    required = (
        "pm_service_binary_present",
        "v1768_prematch_label",
        "prematch_iterates_supported_list",
        "prematch_calls_record_getter",
        "prematch_uses_strcmp",
        "prematch_branches_to_match",
        "permission_starts_after_match",
        "getter_locks_record_mutex",
        "v1107_mutex_owner_blocked",
    )
    missing = [key for key in required if not facts.get(key)]
    if missing:
        return (
            "v1769-pm-server-prematch-input-incomplete",
            False,
            "missing retained/static evidence: " + ",".join(missing),
            "pm-server-prematch-input-incomplete",
        )
    return (
        "v1769-pm-server-prematch-list-mutex-boundary-host-pass",
        True,
        "pm-service pre-match path is supported-peripheral list traversal through a per-record mutex getter; V1107 shows CNSS can wait behind a modem record mutex held by a pre-CNSS PM path",
        "pm-server-prematch-list-mutex-boundary",
    )


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    return "\n".join(
        [
            "# Native Init V1769 WLAN-PD PM Server Pre-match Static Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1769`",
            "- Type: host-only static disassembly classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Inputs",
            "",
            f"- pm-service binary: `{result['inputs']['pm_service']}`",
            f"- V1768 branch classifier: `{result['inputs']['v1768']}`",
            f"- V1107 mutex owner classifier: `{result['inputs']['v1107']}`",
            f"- V1107 report: `{result['inputs']['v1107_report']}`",
            "",
            "## Disassembly Artifacts",
            "",
            f"- pre-match range: `{result['artifacts']['prematch_disasm']}`",
            f"- surrounding range: `{result['artifacts']['surrounding_disasm']}`",
            f"- record getter: `{result['artifacts']['getter_disasm']}`",
            "",
            "## Facts",
            "",
            f"- V1768 pre-match label retained: `{facts['v1768_prematch_label']}`",
            f"- Pre-match iterates supported list: `{facts['prematch_iterates_supported_list']}`",
            f"- Pre-match calls record getter `0x9538`: `{facts['prematch_calls_record_getter']}`",
            f"- Pre-match uses `strcmp`: `{facts['prematch_uses_strcmp']}`",
            f"- Match branch target is `0x60cc`: `{facts['prematch_branches_to_match']}`",
            f"- Permission/caller UID starts after match: `{facts['permission_starts_after_match']}`",
            f"- Getter locks/unlocks record mutex: `{facts['getter_locks_record_mutex']}`",
            f"- V1107 mutex owner blocked: `{facts['v1107_mutex_owner_blocked']}`",
            f"- V1107 owner return offset: `{facts['v1107_owner_return_offset']}`",
            f"- V1107 owner wchans: `{facts['v1107_owner_wchans']}`",
            f"- V1107 CNSS waiter wchans: `{facts['v1107_cnss_waiter_wchans']}`",
            "",
            "## Interpretation",
            "",
            "- The `0x6048..0x60cc` path is not a service-manager or permission branch; it is supported-peripheral list traversal.",
            "- The only call before the first match checkpoint is the per-record getter at `0x9538`, followed by dereferencing the requested peripheral string and `strcmp`.",
            "- Caller UID permission checks start after `0x60cc`, so UID/SELinux permission is not the retained V1768 pre-match boundary.",
            "- V1107 independently shows the same modem record mutex can be held by a pre-CNSS PM path while CNSS waits in `futex_wait_queue_me`.",
            "- Combined label: the retained blocker is best modeled as a pre-match list/mutex boundary, not as missing provider registration.",
            "",
            "## Consequence",
            "",
            "- A live PM gate, if explicitly reopened, should avoid pre-CNSS `per_proxy`/positive-control connect paths that hold the modem record mutex.",
            "- While the current stop remains active, the only aligned follow-up is host/source-only reconstruction of the minimal CNSS-first PM register ordering and its expected labels.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
            "## Next",
            "",
            "- Draft a host-only CNSS-first PM register ordering contract that removes pre-CNSS `per_proxy` connect as a positive-control side effect.",
            "- Do not live-run that route unless a new directive explicitly reopens the narrow PM register gate.",
            "- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    EvidenceStore(args.out_dir)
    collected = collect(args.out_dir)
    decision, passed, reason, label = classify(collected["facts"])
    manifest = {
        "cycle": "V1769",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "artifacts": collected["artifacts"],
        "facts": collected["facts"],
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pm_actor_start_executed": False,
        "qcacld_load_executed": False,
        "esoc_rc1_executed": False,
        "restart_pd_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
        "bpf_attach_executed": False,
        "tracefs_write_executed": False,
    }
    write_private_text(args.out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(manifest))
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
