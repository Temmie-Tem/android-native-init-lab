#!/usr/bin/env python3
"""V1992 RFS bridge wlanmdsp request/serve/load handoff."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_light_wlanmdsp_trace_handoff_v1990 as prev


CYCLE = "V1992"
OUT_DIR = prev.repo_path("tmp/wifi/v1992-rfs-bridge-wlanmdsp-handoff")
HANDOFF_DIR = OUT_DIR / "v1991-handoff"
HANDOFF_REPORT = OUT_DIR / "v1991-handoff-report.md"
REPORT_PATH = prev.repo_path("docs/reports/NATIVE_INIT_V1992_RFS_BRIDGE_WLANMDSP_HANDOFF_2026-06-04.md")
V1991_OUT = prev.repo_path("tmp/wifi/v1991-rfs-bridge-wlanmdsp-trace-test-boot")
V1991_INIT = V1991_OUT / "init_v1991_rfs_bridge_wlanmdsp_trace"
V1991_BOOT = V1991_OUT / "boot_linux_v1991_rfs_bridge_wlanmdsp_trace.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1991/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.178 (v1991-rfs-bridge-wlanmdsp-trace)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1991.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1991.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1991-helper.result"

ORIGINAL_CLASSIFY = prev.classify


def rel(path: Path) -> str:
    return prev.rel(path)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1991",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v365",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "%s.source_asset.nonzero=%d",
        "%s.exact.open_rc=%d",
        "%s.rootfs_namespace_only=1",
        "wlan_pd_firmware_serve_gate.requested_wlanmdsp=%d",
        "tftp_server",
        "libqmi_get_service_list_lookup_call",
        "wlfw_client_init_instance_call",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1991_INIT, init_required), (V1991_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in init_forbidden if path == V1991_INIT and token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    bridge_ok = bool(bridge.get("ok"))
    if (
        base.get("hook_ok")
        and base.get("prearm_ok")
        and base.get("handoff_ok")
        and base.get("rollback_ok")
        and base.get("light_ok")
        and not bridge_ok
    ):
        label = "native-rfs-bridge-not-established"
        return {
            **base,
            "label": label,
            "decision": f"v1992-{label}-rollback-blocked",
            "pass": False,
            "reason": "RFS bridge did not make the exact modem tftp path exist/open in the helper namespace",
            "rfs_bridge_ok": bridge_ok,
        }
    label = str(base.get("label") or "native-wlanmdsp-unknown")
    passed = bool(base.get("pass"))
    return {
        **base,
        "label": label,
        "decision": f"v1992-{label}-rollback-{'pass' if passed else 'blocked'}",
        "rfs_bridge_ok": bridge_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    light = trace["light_observer"]
    bridge = trace["rfs_bridge"]
    android = details["android_v1982"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["rfs_bridge", classification.get("rfs_bridge_ok"), f"exact_exists={bridge['exact_exists']} nonzero={bridge['exact_nonzero']} open_rc={bridge['exact_open_rc']} source_nonzero={bridge['source_asset_nonzero']} sda29_write={bridge['sda29_write']}"],
        ["bridge_links", bridge["readonly_readlink"], f"readonly_dir={bridge['readonly_is_dir']} vendor_dir={bridge['readonly_vendor_is_dir']} vendor_link={bridge['readonly_vendor_readlink']}"],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["wlanmdsp_request", trace["requested"], f"field={trace['requested_field']} tftp_lines={trace['tftp_wlanmdsp_lines']} failures={trace['wlanmdsp_failure_lines']}"],
        ["wlanmdsp_serve_load", trace["served"], f"served_nonzero={trace['served_nonzero']} pil_load={trace['pil_load_lines']} wlan_pd_up={trace['wlan_pd_up_lines']} wlfw69={trace['wlfw69_lines']} wlan0={trace['wlan0_lines']}"],
        ["degraded_external_watch", trace["degraded_external_lines"], "pcie_initialized/mhi_enable/esoc0_boot_failed/LTSSM only"],
        ["android_v1982", android.get("requested_wlanmdsp", ""), f"wlan_pd={android.get('wlan_pd_up')} BDF={android.get('bdf')} wlan0={android.get('wlan0')} lines={android.get('wlanmdsp_line_count')}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1992 RFS Bridge Wlanmdsp Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1992`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## First Native Wlanmdsp Lines",
        "",
        *(f"- `{line}`" for line in trace["first_wlanmdsp_lines"]),
        *([] if trace["first_wlanmdsp_lines"] else ["- `none`"]),
        "",
        "## First Native Load/UP Lines",
        "",
        *(f"- `{line}`" for line in trace["first_load_lines"]),
        *([] if trace["first_load_lines"] else ["- `none`"]),
        "",
        "## Branch",
        "",
        "- `(a)` bridge plus request/load/UP maps to `native-wlanmdsp-requested-served-publication-progress`.",
        "- `(b)` bridge established but no request maps to `native-wlanmdsp-not-requested-light`.",
        "- `(c)` requested+served but no WLAN-PD/WLFW/wlan0 maps to `native-wlanmdsp-requested-served-pd-still-down`.",
        "- `native-wlanmdsp-request-serve-failed` means the bridge did not fix serving and the exact tftp/open path remains the target.",
        "",
        "## Android Comparator",
        "",
        f"- Report: `{android.get('report', rel(prev.ANDROID_V1982_REPORT))}`",
        f"- Timeline: WLAN-PD UP `{android.get('wlan_pd_up')}`, BDF `{android.get('bdf')}`, wlan0 `{android.get('wlan0')}`.",
        f"- Request evidence: requested_wlanmdsp `{android.get('requested_wlanmdsp')}`, wlanmdsp line count `{android.get('wlanmdsp_line_count')}`.",
        f"- First Android line: `{android.get('first_wlanmdsp_line', '')}`",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, or service-notifier listener was run in the V1991 init argv.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1991 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev.CYCLE = CYCLE
    prev.OUT_DIR = OUT_DIR
    prev.HANDOFF_DIR = HANDOFF_DIR
    prev.HANDOFF_REPORT = HANDOFF_REPORT
    prev.REPORT_PATH = REPORT_PATH
    prev.V1989_OUT = V1991_OUT
    prev.V1989_INIT = V1991_INIT
    prev.V1989_BOOT = V1991_BOOT
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev.TEST_LOG_PATH = TEST_LOG_PATH
    prev.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev.artifact_hook_check = artifact_hook_check
    prev.classify = classify
    prev.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    patch_prev_module()
    return prev.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
