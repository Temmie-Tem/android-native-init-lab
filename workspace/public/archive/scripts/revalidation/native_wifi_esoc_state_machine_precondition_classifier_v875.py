#!/usr/bin/env python3
"""V875 host-only eSoC state-machine precondition classifier.

This classifier reads only local source/docs/evidence. It must not contact the
device, deploy helpers, execute eSoC ioctls, start Android actors, bring up
Wi-Fi, or use credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v875-esoc-state-machine-precondition-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v875-esoc-state-machine-precondition-classifier.txt")
KERNEL_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
ESOC_CTRL = KERNEL_ROOT / "include/uapi/linux/esoc_ctrl.h"
ESOC_CLIENT = KERNEL_ROOT / "include/linux/esoc_client.h"
SSR_C = KERNEL_ROOT / "drivers/soc/qcom/subsystem_restart.c"
SSR_H = KERNEL_ROOT / "include/soc/qcom/subsystem_restart.h"
ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
V849_MANIFEST = Path("tmp/wifi/v849-subsys-esoc0-wait-state-sampler/manifest.json")
V874_MANIFEST = Path("tmp/wifi/v874-esoc-control-preflight-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def load_manifest(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"path": str(path), "exists": False}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    return {"path": str(path), "exists": True, **data}


def source_presence() -> dict[str, Any]:
    paths = {
        "esoc_ctrl": repo_path(ESOC_CTRL),
        "esoc_client": repo_path(ESOC_CLIENT),
        "subsystem_restart_c": repo_path(SSR_C),
        "subsystem_restart_h": repo_path(SSR_H),
        "esoc_research": repo_path(ESOC_RESEARCH),
    }
    return {name: {"path": str(path), "exists": path.exists()} for name, path in paths.items()}


def extract_uapi(text: str) -> dict[str, Any]:
    define_re = re.compile(r"#define\s+(ESOC_[A-Z0-9_]+)\s+(.+)")
    enum_re = re.compile(r"\b(ESOC_[A-Z0-9_]+)\s*(?:=\s*([0-9]+))?\s*,")
    defines: dict[str, str] = {}
    enums: dict[str, int | None] = {}
    for line in text.splitlines():
        define_match = define_re.match(line.strip())
        if define_match:
            defines[define_match.group(1)] = define_match.group(2).strip()
        enum_match = enum_re.search(line)
        if enum_match:
            enums[enum_match.group(1)] = int(enum_match.group(2)) if enum_match.group(2) else None
    return {"defines": defines, "enums": enums}


def extract_source_contract(ssr_text: str, ssr_header: str, client_text: str) -> dict[str, Any]:
    patterns = {
        "subsys_open_calls_get_with_fwname": "subsystem_get_with_fwname(subsys_dev->desc->name" in ssr_text,
        "subsys_release_calls_put": "subsystem_put(subsys_dev);" in ssr_text,
        "subsystem_get_count_gate": "if (!subsys->count)" in ssr_text and "ret = subsys_start(subsys);" in ssr_text,
        "subsys_start_calls_powerup": "ret = subsys->desc->powerup(subsys->desc);" in ssr_text,
        "subsys_start_waits_err_ready": "wait_for_err_ready(subsys)" in ssr_text,
        "err_ready_timeout_10000ms": "msecs_to_jiffies(10000)" in ssr_text,
        "state_attr_read_only": "static DEVICE_ATTR_RO(state);" in ssr_text,
        "pm_proxy_helper_put_exception": "pm_proxy_helper" in ssr_text and "poff_depends_on" in ssr_text,
        "esoc_client_hooks_available": "esoc_register_client_hook" in client_text and "ESOC_MHI_HOOK" in client_text,
        "ssr_descriptor_has_powerup": "int (*powerup)(const struct subsys_desc *desc);" in ssr_header,
    }
    provider_source_present = any(
        repo_path(candidate).exists()
        for candidate in (
            KERNEL_ROOT / "drivers/esoc/esoc-mdm-drv.c",
            KERNEL_ROOT / "drivers/esoc/esoc-mdm-4x.c",
            KERNEL_ROOT / "drivers/soc/qcom/esoc-mdm-drv.c",
            KERNEL_ROOT / "drivers/soc/qcom/esoc-mdm-4x.c",
        )
    )
    patterns["provider_source_present_in_osrc"] = provider_source_present
    return patterns


def classify_operations(uapi: dict[str, Any]) -> list[dict[str, Any]]:
    defines = uapi["defines"]
    enums = uapi["enums"]
    return [
        {
            "operation": "ESOC_REG_CMD_ENG",
            "request": defines.get("ESOC_REG_CMD_ENG", ""),
            "kind": "mutating-registration",
            "power_effect": "no direct PWR_ON argument",
            "next_gate": "source/build helper support only before live",
            "allowed_in_v875": False,
        },
        {
            "operation": "ESOC_REG_REQ_ENG",
            "request": defines.get("ESOC_REG_REQ_ENG", ""),
            "kind": "mutating-registration",
            "power_effect": "may unblock provider req_eng_wait but does not pass ESOC_PWR_ON",
            "next_gate": "source/build helper support only before live",
            "allowed_in_v875": False,
        },
        {
            "operation": "ESOC_CMD_EXE(ESOC_PWR_ON)",
            "request": defines.get("ESOC_CMD_EXE", ""),
            "kind": "power-command",
            "power_effect": f"explicit power-on enum value {enums.get('ESOC_PWR_ON')}",
            "next_gate": "blocked until CMD/REQ registration and firmware request loop are proven",
            "allowed_in_v875": False,
        },
        {
            "operation": "ESOC_WAIT_FOR_REQ",
            "request": defines.get("ESOC_WAIT_FOR_REQ", ""),
            "kind": "blocking-request-loop",
            "power_effect": "no direct power command but can block waiting for modem firmware requests",
            "next_gate": "blocked until firmware-server/tftp/rmt_storage contract is ready",
            "allowed_in_v875": False,
        },
        {
            "operation": "ESOC_NOTIFY",
            "request": defines.get("ESOC_NOTIFY", ""),
            "kind": "mutating-response",
            "power_effect": "reports image/boot state to eSoC state machine",
            "next_gate": "blocked until WAIT_FOR_REQ and firmware delivery are proven",
            "allowed_in_v875": False,
        },
        {
            "operation": "/dev/subsys_esoc0 open",
            "request": "subsystem_get_with_fwname(esoc0)",
            "kind": "subsystem-refcount-powerup-path",
            "power_effect": "enters desc->powerup and wait_for_err_ready",
            "next_gate": "only after CMD/REQ/PWR_ON sequencing is defined",
            "allowed_in_v875": False,
        },
    ]


def build_next_gate(contract: dict[str, Any], v849: dict[str, Any], v874: dict[str, Any]) -> dict[str, Any]:
    v849_ok = bool(v849.get("exists") and v849.get("pass"))
    v874_ok = bool(v874.get("exists") and v874.get("pass") and v874.get("decision") == "v874-esoc-readonly-ioctl-probe-pass")
    source_ok = all(
        contract.get(key)
        for key in (
            "subsys_open_calls_get_with_fwname",
            "subsystem_get_count_gate",
            "subsys_start_calls_powerup",
            "subsys_start_waits_err_ready",
            "state_attr_read_only",
        )
    )
    selected = v849_ok and v874_ok and source_ok
    return {
        "selected": selected,
        "label": "v875-esoc-cmd-req-registration-helper-selected" if selected else "v875-esoc-precondition-review",
        "next_cycle": "V876 helper v137 source/build-only CMD/REQ registration support" if selected else "repair missing source/evidence before helper work",
        "live_allowed_next": False,
        "recommended_sequence": [
            "V876 source/build helper v137 with fail-closed CMD/REQ registration mode",
            "V877 deploy-only helper v137 checksum/version/mode proof",
            "V878 bounded live CMD/REQ registration preflight, still no CMD_EXE/PWR_ON/subsys open",
            "later gate: firmware request loop and only then explicit PWR_ON consideration",
        ],
    }


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    next_gate = manifest["analysis"]["next_gate"]
    if next_gate["selected"]:
        return (
            "v875-esoc-state-machine-precondition-pass",
            True,
            "local source and evidence select helper-only CMD/REQ registration support as next step",
            next_gate["next_cycle"],
        )
    return (
        "v875-esoc-state-machine-precondition-review",
        False,
        "required source/evidence inputs are incomplete",
        next_gate["next_cycle"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    op_rows = [
        [
            op["operation"],
            op["kind"],
            op["power_effect"],
            op["allowed_in_v875"],
            op["next_gate"],
        ]
        for op in analysis["operations"]
    ]
    source_rows = [[key, value] for key, value in sorted(analysis["source_contract"].items())]
    evidence_rows = [
        ["V849", analysis["evidence"]["v849"].get("exists"), analysis["evidence"]["v849"].get("decision"), analysis["evidence"]["v849"].get("pass")],
        ["V874", analysis["evidence"]["v874"].get("exists"), analysis["evidence"]["v874"].get("decision"), analysis["evidence"]["v874"].get("pass")],
    ]
    next_gate = analysis["next_gate"]
    return "\n".join([
        "# V875 eSoC State-machine Precondition Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_device_contact: `{manifest['live_device_contact']}`",
        f"- mutating_esoc_ioctl_executed: `{manifest['mutating_esoc_ioctl_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Evidence",
        "",
        markdown_table(["unit", "exists", "decision", "pass"], evidence_rows),
        "",
        "## Source Contract",
        "",
        markdown_table(["condition", "value"], source_rows),
        "",
        "## Operation Classification",
        "",
        markdown_table(["operation", "kind", "power_effect", "allowed_in_v875", "next_gate"], op_rows),
        "",
        "## Selected Next Gate",
        "",
        f"- selected: `{next_gate['selected']}`",
        f"- label: `{next_gate['label']}`",
        f"- live_allowed_next: `{next_gate['live_allowed_next']}`",
        "",
        "## Recommended Sequence",
        "",
        *[f"- {item}" for item in next_gate["recommended_sequence"]],
        "",
        "## Guardrails",
        "",
        "- Host-only classifier: no bridge/device command.",
        "- No `REG_CMD_ENG`, `REG_REQ_ENG`, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, or `NOTIFY`.",
        "- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager trio, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])


def build_manifest() -> dict[str, Any]:
    presence = source_presence()
    esoc_text = read_text(ESOC_CTRL)
    ssr_text = read_text(SSR_C)
    ssr_header = read_text(SSR_H)
    client_text = read_text(ESOC_CLIENT)
    uapi = extract_uapi(esoc_text)
    contract = extract_source_contract(ssr_text, ssr_header, client_text)
    v849 = load_manifest(V849_MANIFEST)
    v874 = load_manifest(V874_MANIFEST)
    operations = classify_operations(uapi)
    next_gate = build_next_gate(contract, v849, v874)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "source_presence": presence,
        "analysis": {
            "uapi": uapi,
            "source_contract": contract,
            "operations": operations,
            "evidence": {
                "v849": {key: v849.get(key) for key in ("path", "exists", "decision", "pass", "reason")},
                "v874": {key: v874.get(key) for key in ("path", "exists", "decision", "pass", "reason")},
            },
            "next_gate": next_gate,
        },
        "live_device_contact": False,
        "device_mutations": False,
        "mutating_esoc_ioctl_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    decision, pass_ok, reason, next_step = decide(manifest)
    manifest.update({"decision": decision, "pass": pass_ok, "reason": reason, "next_step": next_step})
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest()
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"live_device_contact: {manifest['live_device_contact']}")
    print(f"mutating_esoc_ioctl_executed: {manifest['mutating_esoc_ioctl_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
