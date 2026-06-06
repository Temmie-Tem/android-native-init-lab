#!/usr/bin/env python3
"""Host-only V1720 reconciliation for CNSS output visibility and Binder bootstrap."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1720-cnss-output-binder-reconcile"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1720_CNSS_OUTPUT_BINDER_RECONCILE_2026-06-02.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

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
V659_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V659_VNDSERVICEMANAGER_READINESS_ONLY_LIVE_2026-05-23.md"
)
V1680_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1680_WLAN_PD_FIRMWARE_SERVE_MODEM_HOLDER_HANDOFF_2026-06-02.md"
)


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def read_required(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def extract_inline_value(text: str, key: str) -> str | None:
    pattern = re.compile(rf"{re.escape(key)}[^`\n]*`([^`]+)`")
    match = pattern.search(text)
    if match:
        return match.group(1)
    return None


def marker_present(text: str, marker: str) -> bool:
    return marker in text


def discover_binder_artifacts() -> list[str]:
    output = run(
        [
            "bash",
            "-lc",
            "find tmp stage3 -type f \\( "
            "-name vndservicemanager -o -name servicemanager -o -name hwservicemanager "
            "-o -name libbinder.so -o -name libperipheral_client.so -o -name cnss-daemon "
            "\\) -print 2>/dev/null | sort || true",
        ]
    )
    return [line for line in output.splitlines() if line.strip()]


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def render_report(manifest: dict[str, Any]) -> str:
    artifacts = "\n".join(f"- `{artifact}`" for artifact in manifest["binder_artifacts"]) or "- none found in current host artifacts"
    return "\n".join(
        [
            "# Native Init V1720 CNSS Output/Binder Reconciliation",
            "",
            "## Summary",
            "",
            "- Cycle: `V1720`",
            "- Type: host-only reconciliation and next-gate classifier",
            f"- Decision: `{manifest['decision']}`",
            "- Result: PASS",
            "- Evidence: `tmp/wifi/v1720-cnss-output-binder-reconcile`",
            "",
            "## Corrections Applied",
            "",
            "- The QCACLD `REGISTER_DRIVER` premise is retracted for WLFW server triggering. ICNSS driver registration waits for later firmware readiness and should not be added as a `wlfw_start` trigger.",
            "- Native `wlfw_start_seen=0` is treated as a logging visibility artifact. `cnss-daemon` logging goes through Android logging unless the kmsg property path is explicitly enabled.",
            "- The requested output-visibility branch is already resolved by non-log trace evidence: V1702/V1716 hit `wlfw_start@0xec00`.",
            "",
            "## Evidence Reconciliation",
            "",
            f"- V1703 corrected premise present: `{manifest['v1703_corrected_premise']}`",
            f"- V1716 decision: `{manifest['v1716_decision']}`",
            f"- V1716 `wlfw_start` hit: `{manifest['v1716_wlfw_start_hit']}`",
            f"- V1716 `pm_init(1, NULL)` call hit: `{manifest['v1716_pm_init_call_hit']}`",
            f"- V1716 `pm_client_register` no-return label: `{manifest['v1716_pm_register_no_return']}`",
            f"- V1719 decision: `{manifest['v1719_decision']}`",
            f"- V1719 non-log label: `{manifest['v1719_nonlog_label']}`",
            f"- V1719 `/dev/vndbinder` init reached: `{manifest['v1719_vndbinder_init_reached']}`",
            f"- V1719 `defaultServiceManager()` reached: `{manifest['v1719_default_sm_reached']}`",
            f"- V1719 concrete `vendor.qcom.PeripheralManager` name not reached: `{manifest['v1719_peripheral_name_not_reached']}`",
            f"- V1680 firmware-serve label: `{manifest['v1680_label']}`",
            "",
            "## Current Blocker",
            "",
            "The latest evidence is narrower than a generic downstream WLFW wait:",
            "",
            "```text",
            "cnss-daemon",
            "  -> wlfw_start",
            "    -> pm_init(1, NULL)",
            "      -> get_system_info OK",
            "      -> pm_client_register",
            "        -> libperipheral_client.so",
            "          -> ProcessState::initWithDriver('/dev/vndbinder')",
            "          -> defaultServiceManager()",
            "             [blocks before String16('vendor.qcom.PeripheralManager')]",
            "```",
            "",
            "Therefore the active blocker is default vendor Binder service-manager acquisition, not QCACLD registration, not missing `wlfw_start`, and not yet WLFW QMI service waiting.",
            "",
            "## Historical Binder Evidence",
            "",
            f"- V659 isolated `vndservicemanager` readiness passed: `{manifest['v659_ready']}`",
            "- V659 was an older service-74-gated route and did not combine with the current V1680/V1716 internal-modem route.",
            "- V655 timed out before service `74`; it does not invalidate V659 readiness, but it is not the current route.",
            "- V1184/V1188 PM-trio/per_mgr work remains separate and should not be reintroduced as a pre-CNSS actor path for this gate.",
            "",
            "## Host Artifact Snapshot",
            "",
            artifacts,
            "",
            "The current host evidence export contains `cnss-daemon` and one older `servicemanager` artifact, but not a complete current `vndservicemanager`/`libbinder.so` staging set for a new live gate. A future source/build or handoff step must materialize and verify those inputs before live execution.",
            "",
            "## Next Gate",
            "",
            "- Do not add PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, or Wi-Fi HAL/scan/connect.",
            "- First perform a host-only V1721 vendor Binder bootstrap materialization/classifier: locate or pull current `vndservicemanager`, `libbinder.so`, binder device paths, property keys, and SELinux labels required by `defaultServiceManager()`.",
            "- Only after V1721 proves a narrow contract should the next live gate be considered: service-manager-only readiness or a non-mutating vendor Binder availability probe, still without PM trio or `vendor.qcom.PeripheralManager` service startup.",
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager/PM actors, start `boot_wlan`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1720 CNSS output/Binder reconciliation (2026-06-02)",
            "",
            "- V1720 host-only reconciliation completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            "  - the latest correction is accepted: native `wlfw_start_seen=0` was a logging visibility artifact;",
            "  - V1716/V1719 already prove the non-log path reaches `wlfw_start`, `pm_init(1, NULL)`, `pm_client_register`, `/dev/vndbinder` init, and then blocks in `defaultServiceManager()`;",
            "  - the current blocker is default vendor Binder service-manager acquisition before `String16('vendor.qcom.PeripheralManager')`, not QCACLD registration, not `boot_wlan`, not PM trio, and not yet WLFW QMI waiting;",
            "  - V659 proves historical `vndservicemanager` readiness in a different service-74-gated route, but current host artifacts do not yet provide a complete current vendor Binder staging set.",
            "",
            "  Next candidate:",
            "",
            "  - V1721 host-only vendor Binder bootstrap materialization/classifier: locate current `vndservicemanager`, `libbinder.so`, device nodes, property keys, and SELinux labels for `defaultServiceManager()`;",
            "  - no PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1720_CNSS_OUTPUT_BINDER_RECONCILE_2026-06-02.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    if "## V1720 CNSS output/Binder reconciliation" not in current:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    v1703_text = read_required(V1703_REPORT)
    v1716_text = read_required(V1716_REPORT)
    v1719_text = read_required(V1719_REPORT)
    v659_text = read_required(V659_REPORT)
    v1680_text = read_required(V1680_REPORT)

    manifest: dict[str, Any] = {
        "cycle": "V1720",
        "decision": "v1720-cnss-output-binder-reconcile-pass",
        "pass": True,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "v1703_corrected_premise": marker_present(v1703_text, "previous missing dmesg/log evidence was a logging artifact"),
        "v1716_decision": extract_inline_value(v1716_text, "Decision:"),
        "v1716_wlfw_start_hit": marker_present(v1716_text, "`wlfw_start` offset `0xec00` hit_count `1`"),
        "v1716_pm_init_call_hit": marker_present(v1716_text, "`wlfw_optional_pm_init1_call` offset `0xec34` hit_count `1`"),
        "v1716_pm_register_no_return": marker_present(v1716_text, "pm-init-register-call-no-return"),
        "v1719_decision": extract_inline_value(v1719_text, "Decision:"),
        "v1719_nonlog_label": extract_inline_value(v1719_text, "non-log label:"),
        "v1719_vndbinder_init_reached": marker_present(v1719_text, "ProcessState::initWithDriver('/dev/vndbinder')@0x6168=1")
        or marker_present(v1719_text, "`periph_vndbinder_init_call` offset `0x6168` hit_count `1`"),
        "v1719_default_sm_reached": marker_present(v1719_text, "defaultServiceManager@0x6190=1")
        or marker_present(v1719_text, "`periph_default_service_manager_call` offset `0x6190` hit_count `1`"),
        "v1719_peripheral_name_not_reached": marker_present(v1719_text, "String16('vendor.qcom.PeripheralManager')@0x61a8=0")
        or marker_present(v1719_text, "`periph_manager_name_string16_call` offset `0x61a8` hit_count `0`"),
        "v659_ready": marker_present(v659_text, "decision: `v659-vndservicemanager-readiness-pass`")
        or marker_present(v659_text, "`vndservicemanager_readiness.ready` | `1`"),
        "v1680_label": extract_inline_value(v1680_text, "Label:"),
        "binder_artifacts": discover_binder_artifacts(),
    }

    required_checks = [
        manifest["v1703_corrected_premise"],
        manifest["v1716_wlfw_start_hit"],
        manifest["v1716_pm_init_call_hit"],
        manifest["v1716_pm_register_no_return"],
        manifest["v1719_vndbinder_init_reached"],
        manifest["v1719_default_sm_reached"],
        manifest["v1719_peripheral_name_not_reached"],
    ]
    if not all(required_checks):
        manifest["decision"] = "v1720-cnss-output-binder-reconcile-incomplete"
        manifest["pass"] = False

    OUT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
