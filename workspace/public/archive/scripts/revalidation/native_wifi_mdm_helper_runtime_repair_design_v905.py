#!/usr/bin/env python3
"""V905 host-only mdm_helper runtime-repair design classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v905-mdm-helper-runtime-repair-design")
LATEST_POINTER = Path("tmp/wifi/latest-v905-mdm-helper-runtime-repair-design.txt")
DEFAULT_V904_MANIFEST = Path("tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
REPORT_PATHS = {
    "v478_v482_selinux": Path("docs/reports/NATIVE_INIT_V478_V482_SELINUX_CONTEXT_HANDOFF_2026-05-21.md"),
    "v487_selinux": Path("docs/reports/NATIVE_INIT_V487_SELINUX_INIT_HANDOFF_2026-05-21.md"),
    "v860_pm_property": Path("docs/reports/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_2026-05-25.md"),
    "v861_pm_domain": Path("docs/reports/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_2026-05-25.md"),
    "v867_pm_init_live": Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md"),
    "v868_pm_esoc": Path("docs/reports/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_2026-05-25.md"),
    "v895_irq": Path("docs/reports/NATIVE_INIT_V895_MDM2AP_IRQ_SNAPSHOT_PROOF_2026-05-26.md"),
    "v896_android_contract": Path("docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md"),
    "v904_runtime_parity": Path("docs/reports/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_2026-05-26.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v904-manifest", type=Path, default=DEFAULT_V904_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
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
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def selected_lines(text: str, pattern: str, limit: int = 18) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen:
            continue
        if regex.search(line):
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def collect_report_evidence() -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for name, path in REPORT_PATHS.items():
        text = read_text(path)
        reports[name] = {
            "path": str(path),
            "exists": bool(text),
            "decision_lines": selected_lines(text, r"\bdecision\b|Result|Interpretation|Next", limit=12),
            "selinux_lines": selected_lines(text, r"attr/current|selinux|context|kernel", limit=12),
            "pm_lines": selected_lines(text, r"pm-service|per_mgr|pm_proxy_helper|subsys_esoc0|D-state", limit=12),
            "irq_lines": selected_lines(text, r"GPIO 142|mdm status|IRQ|IMG_XFER_DONE|Android dmesg|PCIe", limit=12),
        }
    return reports


def collect_source_support(source_text: str) -> dict[str, Any]:
    mdm_context_mapping = has(
        source_text,
        r'streq\(target,\s*"/vendor/bin/mdm_helper"\).*?vendor_mdm_helper',
    )
    ks_context_mapping = has(
        source_text,
        r'streq\(target,\s*"/vendor/bin/ks"\).*?vendor_mdm_helper',
    )
    return {
        "helper_source_exists": bool(source_text),
        "execns_version": (re.search(r'#define\s+EXECNS_VERSION\s+"([^"]+)"', source_text) or ["", ""])[1],
        "has_mdm_helper_identity_contract": has(source_text, r"apply_mdm_helper_identity_contract"),
        "has_peripheral_manager_identity_contract": has(source_text, r"apply_peripheral_manager_identity_contract"),
        "has_per_mgr_ioprio_contract": has(source_text, r"apply_peripheral_manager_ioprio_rt4_contract"),
        "has_mdm_helper_only_mode": has(source_text, r"wifi-companion-mdm-helper-only-deep-capture"),
        "has_mdm_helper_ks_mode": has(source_text, r"wifi-companion-mdm-helper-ks-image-contract-preflight"),
        "has_property_service_shim": has(source_text, r"start_property_service_shim"),
        "has_pm_init_contract_mode": has(source_text, r"wifi-companion-peripheral-manager-init-contract-start-only"),
        "has_mdm_helper_selinux_mapping": mdm_context_mapping,
        "has_ks_selinux_mapping": ks_context_mapping,
        "has_android_default_selinux_context_function": has(source_text, r"android_default_selinux_context_for_target"),
        "mdm_context_source_lines": selected_lines(
            source_text,
            r"mdm_helper|vendor_mdm_helper|android_default_selinux_context_for_target|apply_mdm_helper_identity_contract",
            limit=22,
        ),
    }


def classify(
    v904: dict[str, Any],
    v896: dict[str, Any],
    reports: dict[str, Any],
    source_support: dict[str, Any],
) -> dict[str, Any]:
    android_recap_redundant = (
        v896.get("pass") is True
        and has(read_text(REPORT_PATHS["v896_android_contract"]), r"GPIO 142 `mdm status` IRQ count `1`")
        and has(read_text(REPORT_PATHS["v896_android_contract"]), r"Android dmesg shows PCIe RC1 link")
    )
    selinux_transition_blocked = (
        has(read_text(REPORT_PATHS["v487_selinux"]), r"postexec current\s*\|\s*kernel")
        or has(read_text(REPORT_PATHS["v487_selinux"]), r"kernel-stuck")
    )
    pm_init_full_retry_unsafe = has(read_text(REPORT_PATHS["v867_pm_init_live"]), r"pm_proxy_helper.*D-state|reboot was required")
    pm_service_property_clean = has(read_text(REPORT_PATHS["v860_pm_property"]), r"property denial total.*`0`")
    pm_service_no_subsys_hold = has(read_text(REPORT_PATHS["v860_pm_property"]), r"holds `/dev/subsys_esoc0`\s*\|\s*`false`")
    mdm_runtime_gap = (
        v904.get("pass") is True
        and ((v904.get("classification") or {}).get("native_negative") is True)
    )
    source_gap = (
        not source_support["has_mdm_helper_selinux_mapping"]
        or not source_support["has_ks_selinux_mapping"]
    )
    viable_next = (
        mdm_runtime_gap
        and source_support["has_property_service_shim"]
        and source_support["has_mdm_helper_only_mode"]
        and source_support["has_peripheral_manager_identity_contract"]
        and pm_service_property_clean
        and pm_service_no_subsys_hold
    )
    lanes = {
        "android_dmesg_or_magisk_recapture": {
            "status": "deprioritized",
            "reason": "V896 already contains the positive Android IRQ/PCIe/mdm_helper/ks contract; GPIO135/PMIC fine timing can be recaptured later but is not the current blocker.",
            "redundant_now": android_recap_redundant,
        },
        "selinux_domain_transition": {
            "status": "blocked-as-primary-repair",
            "reason": "V478-V487 show native children remain in kernel context even after accepted procattr writes.",
            "blocked": selinux_transition_blocked,
        },
        "full_peripheral_manager_init_replay": {
            "status": "blocked-as-live-retry",
            "reason": "V867 full PM init-contract replay leaves pm_proxy_helper in D-state and requires reboot cleanup.",
            "unsafe_repeat": pm_init_full_retry_unsafe,
        },
        "pm_service_light_before_mdm_helper": {
            "status": "usable-as-lower-risk-input",
            "reason": "V860/V861 show pm-service property/domain replay is clean but does not hold subsystem fds; it may still provide process/property side effects before mdm_helper without pm_proxy_helper.",
            "property_clean": pm_service_property_clean,
            "no_subsys_hold": pm_service_no_subsys_hold,
        },
        "mdm_helper_property_shim_capture": {
            "status": "selected",
            "reason": "V904 native mdm_helper is observable but reaches no esoc/MHI surface; the next source unit should add a fail-closed runtime-contract capture with property shim and optional pm-service-light ordering.",
            "source_gap": source_gap,
            "viable_next": viable_next,
        },
    }
    if viable_next:
        decision = "v905-runtime-repair-design-mdm-helper-property-shim-first"
        passed = True
        reason = (
            "Android dmesg/Magisk recapture is not the next blocker; V905 selects "
            "a fail-closed mdm_helper runtime-contract helper mode with property shim, "
            "mdm_helper/ks context mapping source support, and pm-service-light ordering while excluding pm_proxy_helper."
        )
        next_step = (
            "V906 source/build-only: add wifi-companion-mdm-helper-runtime-contract-capture; "
            "no live actor start, no subsystem-open controller, no Wi-Fi HAL, no scan/connect."
        )
    else:
        decision = "v905-runtime-repair-design-incomplete"
        passed = False
        reason = (
            "Required V904/V896/V860 source evidence is incomplete; do not proceed to live repair."
        )
        next_step = "repair missing host evidence before implementing a helper mode"
    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "lanes": lanes,
        "signals": {
            "android_recap_redundant": android_recap_redundant,
            "selinux_transition_blocked": selinux_transition_blocked,
            "pm_init_full_retry_unsafe": pm_init_full_retry_unsafe,
            "pm_service_property_clean": pm_service_property_clean,
            "pm_service_no_subsys_hold": pm_service_no_subsys_hold,
            "mdm_runtime_gap": mdm_runtime_gap,
            "source_gap": source_gap,
            "viable_next": viable_next,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    lane_rows = [
        [name, lane["status"], lane["reason"]]
        for name, lane in classification["lanes"].items()
    ]
    signal_rows = [
        [name, value]
        for name, value in classification["signals"].items()
    ]
    source = manifest["source_support"]
    source_rows = [
        ["execns_version", source.get("execns_version")],
        ["has_mdm_helper_identity_contract", source.get("has_mdm_helper_identity_contract")],
        ["has_mdm_helper_selinux_mapping", source.get("has_mdm_helper_selinux_mapping")],
        ["has_ks_selinux_mapping", source.get("has_ks_selinux_mapping")],
        ["has_property_service_shim", source.get("has_property_service_shim")],
        ["has_pm_init_contract_mode", source.get("has_pm_init_contract_mode")],
    ]
    return "\n".join([
        "# V905 mdm_helper Runtime Repair Design Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- android_boot_executed: `{manifest['android_boot_executed']}`",
        f"- actor_start_executed: `{manifest['actor_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Decision Lanes",
        "",
        markdown_table(["lane", "status", "reason"], lane_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
        "",
        "## Helper Source Support",
        "",
        markdown_table(["field", "value"], source_rows),
        "",
        "## Interpretation",
        "",
        "- The Magisk/Android dmesg path is useful only if GPIO135/PMIC fine timing becomes necessary; V896 already proves the Android positive MDM2AP IRQ and PCIe path.",
        "- SELinux domain parity is a real delta, but previous native proofs show procattr writes do not transition children out of `kernel`.",
        "- Full PeripheralManager init-contract replay should not be repeated because `pm_proxy_helper` produced an unkillable D-state in V867.",
        "- The next minimal source unit should add a bounded `mdm_helper` runtime-contract capture with property shim support, explicit source mappings for `mdm_helper`/`ks`, optional `pm-service` light ordering, and no controller `/dev/subsys_esoc0` open.",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V905 mdm_helper Runtime Repair Design Report",
        "",
        "## Result",
        "",
        markdown_table(
            ["Unit", "Evidence", "Decision"],
            [[
                "host-only classifier",
                "`tmp/wifi/v905-mdm-helper-runtime-repair-design/manifest.json`",
                f"`{manifest['decision']}`",
            ]],
        ),
        "",
        "V905 reconciles the proposed Android dmesg/Magisk direction with the newer V896-V904 evidence. The Android recapture is not the current blocker; the next useful work is a source/build-only runtime-contract capture mode for `mdm_helper`.",
        "",
        "## Findings",
        "",
        "- V896 already contains the Android positive evidence needed for this branch: GPIO 142 `mdm status` IRQ count reaches `1`, Android dmesg shows PCIe RC1 link initialization, and Android actors hold `/dev/esoc-0` plus the MHI pipe.",
        "- V904 shows native direct `mdm_helper` is observable but stays in `kernel` context and never reaches `/dev/esoc-0`, `ks`, MHI, or subsystem fd surfaces.",
        "- V478-V487 show accepted SELinux procattr writes do not produce a native child domain transition, so SELinux is not a safe primary repair gate yet.",
        "- V867 shows full PeripheralManager init-contract replay with `pm_proxy_helper` can enter D-state and require reboot cleanup; that path must not be repeated blindly.",
        "- Current helper source has `mdm_helper` identity support and property-shim infrastructure, but lacks explicit `mdm_helper`/`ks` default SELinux mappings.",
        "",
        "## Selected Next Unit",
        "",
        "V906 should be source/build-only. Add `wifi-companion-mdm-helper-runtime-contract-capture` with these constraints:",
        "",
        "- start no live actor during V906; build and static-verify only;",
        "- materialize existing node/path parity and property-service shim support;",
        "- add default source mappings for `/vendor/bin/mdm_helper` and `/vendor/bin/ks` to `u:r:vendor_mdm_helper:s0`, while recording that runtime transition may still remain `kernel`;",
        "- optionally start `pm-service` in a light ordering before `mdm_helper` in the later live gate, but do not start `pm_proxy_helper`;",
        "- do not open `/dev/subsys_esoc0` from the controller; only observe whether `mdm_helper`/`ks` naturally reach `/dev/esoc-0`, MHI, GPIO142, `mdm3`, WLFW/BDF, or `wlan0`;",
        "- keep service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, module load/unload, boot image writes, partition writes, GPIO/sysfs/debugfs writes blocked.",
        "",
        "## Guardrails",
        "",
        "- No device contact, Android boot, ADB command, Magisk module, actor start, eSoC ioctl, subsystem open, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi bring-up occurred in V905.",
        "",
        "## Validation",
        "",
        "Executed:",
        "",
        "```bash",
        "python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_runtime_repair_design_v905.py",
        "python3 scripts/revalidation/native_wifi_mdm_helper_runtime_repair_design_v905.py",
        "```",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v904 = load_json(args.v904_manifest)
    v896 = load_json(args.v896_manifest)
    source_text = read_text(args.helper_source)
    reports = collect_report_evidence()
    source_support = collect_source_support(source_text)
    classification = classify(v904, v896, reports, source_support)
    manifest = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "v904_manifest": str(args.v904_manifest),
        "v896_manifest": str(args.v896_manifest),
        "helper_source": str(args.helper_source),
        "reports": reports,
        "source_support": source_support,
        "classification": classification,
        "device_contact": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "magisk_module_executed": False,
        "live_esoc_ioctl_executed": False,
        "subsystem_open_executed": False,
        "actor_start_executed": False,
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
    write_private_text(
        repo_path("docs/reports/NATIVE_INIT_V905_MDM_HELPER_RUNTIME_REPAIR_DESIGN_2026-05-26.md"),
        render_report(manifest),
    )
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
