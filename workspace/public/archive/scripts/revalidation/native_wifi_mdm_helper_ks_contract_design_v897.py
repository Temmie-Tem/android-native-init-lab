#!/usr/bin/env python3
"""V897 host-only native mdm_helper/ks image-contract design classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v897-mdm-helper-ks-contract-design")
LATEST_POINTER = Path("tmp/wifi/latest-v897-mdm-helper-ks-contract-design.txt")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")
DEFAULT_V764_MANIFEST = Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json")
DEFAULT_V855_MANIFEST = Path("tmp/wifi/v855-esoc-node-parity-preflight/manifest.json")
DEFAULT_V867_MANIFEST = Path("tmp/wifi/v867-pm-init-contract-live-r3/manifest.json")
DEFAULT_V895_MANIFEST = Path("tmp/wifi/v895-mdm2ap-irq-snapshot-live/manifest.json")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    parser.add_argument("--v764-manifest", type=Path, default=DEFAULT_V764_MANIFEST)
    parser.add_argument("--v855-manifest", type=Path, default=DEFAULT_V855_MANIFEST)
    parser.add_argument("--v867-manifest", type=Path, default=DEFAULT_V867_MANIFEST)
    parser.add_argument("--v895-manifest", type=Path, default=DEFAULT_V895_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=HELPER_SOURCE)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def line_hit(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            stripped = line.strip()
            if len(stripped) > 180:
                stripped = stripped[:177] + "..."
            return {"present": True, "line": index, "text": stripped}
    return {"present": False, "line": 0, "text": ""}


def extract_version(text: str) -> str:
    match = re.search(r'#define\s+EXECNS_VERSION\s+"([^"]+)"', text)
    return match.group(1) if match else "unknown"


def extract_v896(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "next_step": manifest.get("next_step", ""),
        "classification": manifest.get("classification") or {},
        "actor_flags": manifest.get("v853_actor_flags") or {},
        "android_irq": ((manifest.get("v852") or {}).get("irq_mdm_status") or {}),
    }


def extract_v764(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
    }


def extract_v855(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    materialize = analysis.get("materialize") or {}
    cleanup = analysis.get("cleanup") or {}
    preflight = analysis.get("preflight") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "created_count": materialize.get("created_count"),
        "created": materialize.get("created") or [],
        "removed_all_created": bool(cleanup.get("removed_all_created")),
        "esoc_major_visible": bool(preflight.get("esoc_major_visible")),
        "subsys_major_visible": bool(preflight.get("subsys_major_visible")),
    }


def extract_v867(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "per_mgr_holds_subsys_esoc0": bool(helper.get("per_mgr_holds_subsys_esoc0")),
        "per_mgr_holds_subsys_modem": bool(helper.get("per_mgr_holds_subsys_modem")),
        "per_proxy_helper_holds_subsys": bool(helper.get("per_proxy_helper_holds_subsys")),
        "result": (helper.get("keys") or {}).get("result", ""),
        "reason": (helper.get("keys") or {}).get("reason", manifest.get("reason", "")),
    }


def extract_v895(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    conditional = helper.get("conditional") or {}
    irq = manifest.get("v895_irq_snapshot") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "request_observed": conditional.get("request_observed", ""),
        "img_xfer_sent": conditional.get("img_xfer_sent", ""),
        "status_last_value": conditional.get("status_last_value", ""),
        "boot_done_sent": conditional.get("boot_done_sent", ""),
        "irq_fired": bool(irq.get("irq_fired")),
        "irq_delta_total": irq.get("delta_total"),
    }


def inspect_helper_source(text: str) -> dict[str, Any]:
    checks = {
        "version": extract_version(text),
        "mdm_helper_identity_contract": line_hit(text, r"apply_mdm_helper_identity_contract"),
        "old_service74_gated_mdm_helper_mode": line_hit(text, r"wifi-companion-service74-gated-mdm-helper-start-only"),
        "old_service180_gated_mdm_helper_mode": line_hit(text, r"wifi-companion-service180-gated-mdm-helper-start-only"),
        "old_sysmon_gated_mdm_helper_mode": line_hit(text, r"wifi-companion-sysmon-gated-mdm-helper-start-only"),
        "new_image_contract_mode": line_hit(text, r"wifi-companion-mdm-helper-(?:ks-)?image-contract"),
        "vendor_ks_exec_model": line_hit(text, r'"/vendor/bin/ks"'),
        "android_mhi_pipe_10_literal": line_hit(text, r"/dev/mhi_0305_01\.01\.00_pipe_10"),
        "mdm_helper_before_subsys_order": line_hit(text, r"mdm_helper.*subsys_esoc0|subsys_esoc0.*mdm_helper"),
        "manual_reg_req_engine": line_hit(text, r"REG_REQ_ENG"),
        "conditional_img_xfer_mode": line_hit(text, r"wifi-companion-esoc-conditional-response-preflight"),
        "mdm_status_irq_snapshot": line_hit(text, r"mdm_status_count_total"),
    }
    return checks


def design_steps() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "name": "node parity",
            "contract": "materialize Android-equivalent /dev/esoc-0, /dev/subsys_esoc0, and /dev/subsys_modem",
            "guard": "no node open yet",
        },
        {
            "step": 2,
            "name": "mdm_helper first",
            "contract": "start /vendor/bin/mdm_helper before opening /dev/subsys_esoc0",
            "guard": "no CNSS, Wi-Fi HAL, scan/connect, DHCP, or external ping",
        },
        {
            "step": 3,
            "name": "request ownership",
            "contract": "do not register REQ engine in the controller; mdm_helper must own /dev/esoc-0 request handling",
            "guard": "no manual ESOC_NOTIFY from the controller",
        },
        {
            "step": 4,
            "name": "subsys trigger",
            "contract": "open /dev/subsys_esoc0 in a bounded child only after mdm_helper is observable",
            "guard": "timeout and reboot-required cleanup path",
        },
        {
            "step": 5,
            "name": "ks/MHI observation",
            "contract": "observe mdm_helper spawning ks and ks using /dev/mhi_0305_01.01.00_pipe_10",
            "guard": "if MHI node appears outside the private root, mirror/bind strategy must be explicit",
        },
        {
            "step": 6,
            "name": "readiness observation",
            "contract": "sample GPIO142 mdm status IRQ, mdm3 state, MHI/PCIe dmesg, and WLFW/BDF markers",
            "guard": "BOOT_DONE, HAL, scan/connect remain blocked unless readiness is proven",
        },
    ]


def decide(
    v896: dict[str, Any],
    v764: dict[str, Any],
    v855: dict[str, Any],
    v867: dict[str, Any],
    v895: dict[str, Any],
    helper: dict[str, Any],
) -> tuple[str, bool, str, str, dict[str, Any]]:
    v896_ok = v896.get("decision") == "v896-android-mdm-helper-image-contract-classified" and v896.get("pass")
    old_mode_insufficient = v764.get("decision") == "v764-mdm-helper-started-no-lower-progress"
    node_parity_ready = (
        v855.get("decision") == "v855-esoc-node-parity-clean"
        and v855.get("pass")
        and v855.get("removed_all_created")
    )
    v895_negative = (
        v895.get("decision") == "v895-mdm-status-irq-not-fired-reboot-cleaned"
        and v895.get("pass")
        and v895.get("img_xfer_sent") == "1"
        and v895.get("boot_done_sent") == "0"
        and v895.get("irq_delta_total") == 0
    )
    helper_has_old_mdm = all(
        bool((helper.get(key) or {}).get("present"))
        for key in (
            "old_service74_gated_mdm_helper_mode",
            "old_service180_gated_mdm_helper_mode",
            "old_sysmon_gated_mdm_helper_mode",
        )
    )
    helper_has_new_contract = all(
        bool((helper.get(key) or {}).get("present"))
        for key in (
            "new_image_contract_mode",
            "vendor_ks_exec_model",
            "android_mhi_pipe_10_literal",
            "mdm_helper_before_subsys_order",
        )
    )
    pm_alone_not_enough = (
        v867.get("decision") == "v867-residual-actor-cleanup-required"
        and not v867.get("per_mgr_holds_subsys_esoc0")
        and not v867.get("per_mgr_holds_subsys_modem")
    )
    classification = {
        "v896_ok": v896_ok,
        "old_mdm_helper_modes_exist": helper_has_old_mdm,
        "old_service_gated_mdm_helper_insufficient": old_mode_insufficient,
        "node_parity_ready": node_parity_ready,
        "pm_alone_not_enough": pm_alone_not_enough,
        "v895_immediate_image_done_negative": v895_negative,
        "helper_new_contract_present": helper_has_new_contract,
        "required_helper_delta": [
            "add a distinct mdm_helper image-contract mode",
            "start mdm_helper before /dev/subsys_esoc0 open",
            "do not REG_REQ_ENG or ESOC_NOTIFY from the controller in that mode",
            "observe ks and /dev/mhi_0305_01.01.00_pipe_10",
            "define private /dev MHI pipe visibility or mirroring strategy",
            "sample GPIO142 mdm status IRQ and block Wi-Fi HAL/scan/connect",
        ],
    }
    if v896_ok and old_mode_insufficient and node_parity_ready and v895_negative and not helper_has_new_contract:
        return (
            "v897-mdm-helper-ks-contract-build-needed",
            True,
            "current helper has only old service-gated mdm_helper modes; the required pre-subsys mdm_helper/ks image contract is not implemented",
            "implement V898 source/build-only helper support for a fail-closed mdm_helper image-contract mode",
            classification,
        )
    if v896_ok and helper_has_new_contract:
        return (
            "v897-mdm-helper-ks-contract-support-present",
            True,
            "helper source already exposes the required mdm_helper/ks image-contract markers",
            "plan deploy-only proof before live actor start",
            classification,
        )
    return (
        "v897-mdm-helper-ks-contract-incomplete",
        False,
        (
            f"v896_ok={v896_ok} old_mode_insufficient={old_mode_insufficient} "
            f"node_parity_ready={node_parity_ready} v895_negative={v895_negative} "
            f"helper_new_contract_present={helper_has_new_contract}"
        ),
        "repair prerequisite evidence before V898 helper work",
        classification,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    helper_rows: list[list[Any]] = []
    for key, value in (manifest.get("helper_source") or {}).items():
        if key == "version":
            helper_rows.append([key, True, "", value])
        else:
            helper_rows.append([key, value.get("present"), value.get("line"), value.get("text")])
    prereq_rows = [
        ["v896", manifest["v896"].get("decision"), manifest["v896"].get("pass")],
        ["v764", manifest["v764"].get("decision"), manifest["v764"].get("pass")],
        ["v855", manifest["v855"].get("decision"), manifest["v855"].get("pass")],
        ["v867", manifest["v867"].get("decision"), manifest["v867"].get("pass")],
        ["v895", manifest["v895"].get("decision"), manifest["v895"].get("pass")],
    ]
    return "\n".join([
        "# V897 mdm_helper/ks Contract Design Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- actor_start_executed: `{manifest['actor_start_executed']}`",
        "",
        "## Prerequisites",
        "",
        markdown_table(["source", "decision", "pass"], prereq_rows),
        "",
        "## Helper Source Markers",
        "",
        markdown_table(["marker", "present", "line", "text"], helper_rows),
        "",
        "## Required Contract Sequence",
        "",
        markdown_table(
            ["step", "name", "contract", "guard"],
            [[item["step"], item["name"], item["contract"], item["guard"]] for item in manifest.get("design_steps", [])],
        ),
        "",
        "## Classification",
        "",
        markdown_table(["field", "value"], [[key, json.dumps(value, sort_keys=True)] for key, value in manifest.get("classification", {}).items()]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v896 = extract_v896(load_json(args.v896_manifest))
    v764 = extract_v764(load_json(args.v764_manifest))
    v855 = extract_v855(load_json(args.v855_manifest))
    v867 = extract_v867(load_json(args.v867_manifest))
    v895 = extract_v895(load_json(args.v895_manifest))
    helper_source = inspect_helper_source(read_text(args.helper_source))
    decision, pass_ok, reason, next_step, classification = decide(v896, v764, v855, v867, v895, helper_source)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v896_manifest": str(args.v896_manifest),
            "v764_manifest": str(args.v764_manifest),
            "v855_manifest": str(args.v855_manifest),
            "v867_manifest": str(args.v867_manifest),
            "v895_manifest": str(args.v895_manifest),
            "helper_source": str(args.helper_source),
        },
        "v896": v896,
        "v764": v764,
        "v855": v855,
        "v867": v867,
        "v895": v895,
        "helper_source": helper_source,
        "design_steps": design_steps(),
        "classification": classification,
        "device_contact": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "live_esoc_ioctl_executed": False,
        "actor_start_executed": False,
        "mdm_helper_start_executed": False,
        "ks_start_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
