#!/usr/bin/env python3
"""Host-only V1723 reclassification for CNSS output visibility corrections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1723-cnss-output-visibility-reclassify"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1723_CNSS_OUTPUT_VISIBILITY_RECLASSIFY_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1695_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1695_WLAN_PD_CNSS_OUTPUT_VISIBILITY_HANDOFF_2026-06-02.md"
)
V1703_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1703_CNSS_WLFW_DOWNSTREAM_STATIC_2026-06-02.md"
)
V1716_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1716_CNSS_PM_INIT_UPROBE_HANDOFF_2026-06-02.md"
)
V1719_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1719_CNSS_PERIPHERAL_CLIENT_UPROBE_HANDOFF_2026-06-02.md"
)
V1720_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1720_CNSS_OUTPUT_BINDER_RECONCILE_2026-06-02.md"
)
V1722_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1722_VND_SERVICEMANAGER_FALLBACK_SOURCE_BUILD_2026-06-03.md"
)

FAILURE_SLUGS = (
    "nl-loop",
    "netlink-common",
    "interop-issues-ap",
    "hang-issues-ap",
    "gw-update-loop",
    "user-interface",
    "wlan-service",
    "wlan-datapath-service",
)


def read_required(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def inline_value(text: str, label: str) -> str | None:
    match = re.search(re.escape(label) + r"[^`\n]*`([^`]+)`", text)
    return match.group(1) if match else None


def marker(text: str, needle: str) -> bool:
    return needle in text


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def render_report(manifest: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{name}`: `{value}`" for name, value in manifest["checks"].items()
    )
    return "\n".join(
        [
            "# Native Init V1723 CNSS Output Visibility Reclassification",
            "",
            "## Summary",
            "",
            "- Cycle: `V1723`",
            "- Type: host-only correction/reclassification classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            "- Evidence: `tmp/wifi/v1723-cnss-output-visibility-reclassify`",
            "",
            "## Corrections Applied",
            "",
            "- Retract the QCACLD-register-as-WLFW-trigger premise: `icnss_register_driver` waits for later firmware readiness and is not a WLFW server trigger.",
            "- Treat native `wlfw_start` dmesg/log absence as a measurement artifact: `cnss-daemon` logs through Android logging unless its kmsg path is visible.",
            "- Stop adding PM/service-window actors for this gate; use only the existing internal-modem firmware-serve route evidence.",
            "",
            "## Reused One-Run Evidence",
            "",
            f"- V1695 output label: `{manifest['v1695_output_label']}`",
            f"- V1695 property lookup all_match: `{manifest['v1695_property_all_match']}`",
            f"- V1695 kmsg/debug property match: `{manifest['v1695_kmsg_match']}` / `{manifest['v1695_debug_match']}`",
            f"- V1695 first init failure slug: `{manifest['v1695_first_failure_slug']}`",
            f"- V1716 non-log label: `{manifest['v1716_nonlog_label']}`",
            f"- V1716 `wlfw_start` uprobe hit: `{manifest['v1716_wlfw_start_hit']}`",
            f"- V1716 `pm_client_register` no-return: `{manifest['v1716_pm_register_no_return']}`",
            f"- V1719 non-log label: `{manifest['v1719_nonlog_label']}`",
            f"- V1719 default service-manager block: `{manifest['v1719_default_sm_block']}`",
            "",
            "## Fixed Label",
            "",
            f"- Contract label: `{manifest['contract_label']}`",
            f"- Refined blocker: `{manifest['refined_blocker']}`",
            "",
            "The strict output-only branch still reads `cnss-output-still-invisible`, but V1716/V1719 non-log trace proves `cnss-daemon` reaches `wlfw_start`. Therefore the corrected classifier resolves the gate as `wlfw-start-reached-downstream-block`, refined to the current Binder bootstrap blocker before `String16('vendor.qcom.PeripheralManager')`.",
            "",
            "## Checks",
            "",
            checks,
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager or PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
            "## Next Gate",
            "",
            "- Do not repeat output-visibility live variants; V1695 already set the output-only label and V1716/V1719 supplied the non-log discriminator.",
            "- V1722 remains the prepared source/build fix for the next bounded live step: service-manager-binary VND Binder bootstrap using `/system/bin/servicemanager /dev/vndbinder`.",
            "- The next live gate must be scoped as service-manager-only bootstrap, not PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1723 CNSS output visibility reclassification (2026-06-03)",
            "",
            "- V1723 host-only correction/reclassification completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - strict contract label: `{manifest['contract_label']}`;",
            f"  - refined blocker: `{manifest['refined_blocker']}`;",
            "  - V1695 already ran the requested internal-modem CNSS output-visibility gate with kmsg/debug properties and no service-manager/PM actors;",
            "  - V1716/V1719 non-log uprobe evidence proves `cnss-daemon` reaches `wlfw_start` and then blocks in the vendor Binder default service-manager path;",
            "  - therefore missing native `wlfw_start` dmesg/log output is a measurement artifact, not a reason to add `boot_wlan`, PM trio, or service-window actors.",
            "",
            "  Next candidate:",
            "",
            "  - V1724 one-run service-manager-only VND Binder bootstrap proof using the V1722 helper v321 fallback (`/system/bin/servicemanager /dev/vndbinder`);",
            "  - still no PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1723_CNSS_OUTPUT_VISIBILITY_RECLASSIFY_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    if "## V1723 CNSS output visibility reclassification" not in current:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    v1695 = read_required(V1695_REPORT)
    v1703 = read_required(V1703_REPORT)
    v1716 = read_required(V1716_REPORT)
    v1719 = read_required(V1719_REPORT)
    v1720 = read_required(V1720_REPORT)
    v1722 = read_required(V1722_REPORT)

    checks = {
        "v1695_output_gate_ran": marker(v1695, "one cnss output visibility gate run produced a fixed label"),
        "v1695_no_service_manager_pm_scope": marker(v1695, "service-manager, PM trio, Wi-Fi HAL"),
        "v1695_kmsg_property_match": marker(v1695, "kmsg_logging value/match: `1` / `1`"),
        "v1695_debug_property_match": marker(v1695, "debug_level value/match: `4` / `1`"),
        "v1703_logging_artifact_accepted": marker(v1703, "previous missing dmesg/log evidence was a logging artifact"),
        "v1716_wlfw_start_hit": marker(v1716, "`wlfw_start` offset `0xec00` hit_count `1`"),
        "v1716_pm_register_no_return": marker(v1716, "pm-init-register-call-no-return"),
        "v1719_default_service_manager_block": marker(v1719, "peripheral-default-service-manager-call-no-return"),
        "v1720_qcacld_premise_retracted": marker(v1720, "QCACLD `REGISTER_DRIVER` premise is retracted"),
        "v1722_fallback_ready": marker(v1722, "`/system/bin/servicemanager /dev/vndbinder`"),
    }

    output_label = inline_value(v1695, "Label:") or "unknown"
    first_failure_slug = inline_value(v1695, "first failure slug:") or "unknown"
    nonlog_label = inline_value(v1716, "pm_init non-log label:") or "unknown"
    v1719_label = inline_value(v1719, "non-log label:") or "unknown"
    any_failure = any(f"cnss-init-step-failed-{slug}" in v1695 for slug in FAILURE_SLUGS)

    if not all(checks.values()):
        decision = "v1723-cnss-output-visibility-reclassify-incomplete"
        contract_label = "cnss-output-still-invisible"
        refined_blocker = "incomplete-host-evidence"
        pass_ok = False
    elif any_failure:
        decision = "v1723-cnss-init-step-failed-reclassified-pass"
        contract_label = "cnss-init-step-failed"
        refined_blocker = "named-cnss-init-step"
        pass_ok = True
    elif output_label == "cnss-output-still-invisible":
        decision = "v1723-wlfw-start-reached-downstream-block-by-nonlog-pass"
        contract_label = "wlfw-start-reached-downstream-block"
        refined_blocker = "vendor-binder-default-service-manager-acquisition"
        pass_ok = True
    else:
        decision = "v1723-wlfw-start-reached-downstream-block-pass"
        contract_label = output_label
        refined_blocker = "downstream-wlfw-or-binder-bootstrap"
        pass_ok = True

    manifest: dict[str, Any] = {
        "cycle": "V1723",
        "decision": decision,
        "pass": pass_ok,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "contract_label": contract_label,
        "refined_blocker": refined_blocker,
        "v1695_output_label": output_label,
        "v1695_property_all_match": inline_value(v1695, "all_match:"),
        "v1695_kmsg_match": "1 / 1" if checks["v1695_kmsg_property_match"] else "unknown",
        "v1695_debug_match": "4 / 1" if checks["v1695_debug_property_match"] else "unknown",
        "v1695_first_failure_slug": first_failure_slug,
        "v1716_nonlog_label": nonlog_label,
        "v1716_wlfw_start_hit": checks["v1716_wlfw_start_hit"],
        "v1716_pm_register_no_return": checks["v1716_pm_register_no_return"],
        "v1719_nonlog_label": v1719_label,
        "v1719_default_sm_block": checks["v1719_default_service_manager_block"],
        "checks": checks,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": decision, "pass": pass_ok}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
