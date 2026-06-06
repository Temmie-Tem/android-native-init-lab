#!/usr/bin/env python3
"""V1990 light native wlanmdsp request/serve/load handoff."""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_ipc_service69_integration_v1937 as parent
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1990"
OUT_DIR = repo_path("tmp/wifi/v1990-light-native-wlanmdsp-trace-handoff")
HANDOFF_DIR = OUT_DIR / "v1989-handoff"
HANDOFF_REPORT = OUT_DIR / "v1989-handoff-report.md"
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1990_LIGHT_NATIVE_WLANMDSP_TRACE_HANDOFF_2026-06-04.md")
V1989_OUT = repo_path("tmp/wifi/v1989-light-native-wlanmdsp-trace-test-boot")
V1989_INIT = V1989_OUT / "init_v1989_light_native_wlanmdsp_trace"
V1989_BOOT = V1989_OUT / "boot_linux_v1989_light_native_wlanmdsp_trace.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1989/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.177 (v1989-light-native-wlanmdsp-trace)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1989.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1989.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1989-helper.result"

ORIGINAL_COLLECT_DETAILS = parent.collect_details
ANDROID_V1982_REPORT = repo_path(
    "docs/reports/NATIVE_INIT_V1982_V1753_MINIMAL_ANDROID_GOOD_BASELINE_RERUN_2026-06-04.md"
)


def intish(value: object) -> int:
    return parent.parent.base.intish(value)


def boolish(value: object) -> bool:
    return parent.parent.base.boolish(value)


def rel(path: Path) -> str:
    return parent.parent.base.rel(path)


def grep_lines(paths: list[Path], pattern: str, limit: int = 8) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if regex.search(line):
                lines.append(f"{rel(path)}: {line[:500]}")
                if len(lines) >= limit:
                    return lines
    return lines


def grep_count(paths: list[Path], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    total = 0
    for path in paths:
        if not path.exists():
            continue
        total += sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if regex.search(line))
    return total


def helper_fields() -> dict[str, str]:
    return parent.parent.base.v1847.runner().fwbase.parse_helper_fields(HANDOFF_DIR)


def field_any_positive(fields: dict[str, str], suffix: str, prefixes: tuple[str, ...]) -> bool:
    return any(intish(fields.get(f"{prefix}.{suffix}")) > 0 for prefix in prefixes)


def collect_wlanmdsp_trace(fields: dict[str, str]) -> dict[str, Any]:
    evidence_paths = [
        HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        HANDOFF_DIR / "test-v1393-log.stdout.txt",
        HANDOFF_DIR / "test-v1393-log-hide-on-busy.stdout.txt",
        HANDOFF_DIR / "test-v1393-dmesg.stdout.txt",
        HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ]
    dmesg_paths = [HANDOFF_DIR / "test-v1393-dmesg.stdout.txt"]
    prefixes = (
        "wlan_pd_firmware_serve_gate",
        "wlan_pd_service_window_trigger",
        "wlan_pd_service_object_visible_trigger",
    )
    requested_field = field_any_positive(fields, "requested_wlanmdsp", prefixes)
    tftp_running = field_any_positive(fields, "tftp_running", prefixes)
    served_nonzero = field_any_positive(fields, "served_wlanmdsp_nonzero", prefixes)
    tftp_request_pattern = r"(tftp_server|tftp-server|tqftp).*wlanmdsp\.mbn|wlanmdsp\.mbn.*(tftp_server|tftp-server|tqftp)"
    wlanmdsp_mbn_lines = grep_count(evidence_paths, r"\bwlanmdsp\.mbn\b")
    tftp_wlanmdsp_lines = grep_count(evidence_paths, tftp_request_pattern)
    wlanmdsp_failure_lines = grep_count(evidence_paths, r"wlanmdsp\.mbn.*(fail|error|timeout|no such|not found|denied)")
    wlan_pd_up_lines = grep_count(dmesg_paths, r"root_service_service_ind_cb.*msm/modem/wlan_pd.*0x1fffffff|wlan_pd.*0x1fffffff|wlan_pd.*\bUP\b")
    pil_load_lines = grep_count(dmesg_paths, r"(subsys-pil-tz|q6v5|pil|modem).*wlanmdsp|wlanmdsp.*(load|loaded|auth|pil)")
    wlfw69_lines = grep_count(dmesg_paths, r"(service 69|service=69|WLFW.*69|wlfw.*69|QMI Server Connected.*69)")
    bdf_lines = grep_count(dmesg_paths, r"\bBDF\b|board data")
    wlan0_lines = grep_count(dmesg_paths, r"\bwlan0\b")
    degraded_external_lines = grep_count(dmesg_paths, r"esoc0_boot_failed|pcie_initialized|mhi_enable|MHI.*(state|enabled|init)|LTSSM")
    requested = requested_field or tftp_wlanmdsp_lines > 0
    served = served_nonzero or (tftp_wlanmdsp_lines > 0 and wlanmdsp_failure_lines == 0)
    loaded_or_up = pil_load_lines > 0 or wlan_pd_up_lines > 0 or wlfw69_lines > 0 or wlan0_lines > 0
    light_observer = {
        "start_order": fields.get("wifi_companion_start.order", ""),
        "servloc_domain_list_probe": intish(fields.get("wifi_companion_start.servloc_domain_list_probe")),
        "service_notifier_listener_probe": intish(fields.get("wifi_companion_start.service_notifier_listener_probe")),
        "qrtr_readback_allowed": intish(fields.get("wifi_companion_qrtr_readback.allowed")),
        "qrtr_readback_send_attempted": intish(fields.get("wifi_companion_qrtr_readback.send_attempted")),
        "qrtr_readback_result": fields.get("wifi_companion_qrtr_readback.result", ""),
    }
    light_observer["ok"] = (
        light_observer["servloc_domain_list_probe"] == 0
        and light_observer["service_notifier_listener_probe"] == 0
        and light_observer["qrtr_readback_send_attempted"] == 0
    )
    rfs_bridge = {
        "root": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.root", ""),
        "host_root": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.host_root", ""),
        "source_asset": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.source_asset", ""),
        "source_asset_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.source_asset.exists")),
        "source_asset_is_reg": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.source_asset.is_reg")),
        "source_asset_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.source_asset.nonzero")),
        "readonly_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly.exists")),
        "readonly_is_dir": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly.is_dir")),
        "readonly_is_symlink": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly.is_symlink")),
        "readonly_readlink": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly.readlink", ""),
        "readonly_vendor_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly_vendor.exists")),
        "readonly_vendor_is_dir": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly_vendor.is_dir")),
        "readonly_vendor_is_symlink": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly_vendor.is_symlink")),
        "readonly_vendor_readlink": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readonly_vendor.readlink", ""),
        "exact_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.exact.absolute", ""),
        "exact_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.exact.exists")),
        "exact_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.exact.nonzero")),
        "exact_open_rc": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.exact.open_rc", ""),
        "exact_open_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.exact.open_errno", ""),
        "rootfs_namespace_only": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.rootfs_namespace_only")),
        "sda29_write": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.sda29_write")),
    }
    rfs_bridge["ok"] = (
        rfs_bridge["exact_exists"] > 0
        and rfs_bridge["exact_nonzero"] > 0
        and str(rfs_bridge["exact_open_rc"]) == "0"
        and rfs_bridge["rootfs_namespace_only"] == 1
        and rfs_bridge["sda29_write"] == 0
    )
    return {
        "requested_field": requested_field,
        "requested": requested,
        "tftp_running": tftp_running,
        "served_nonzero": served_nonzero,
        "served": served,
        "loaded_or_up": loaded_or_up,
        "wlanmdsp_mbn_lines": wlanmdsp_mbn_lines,
        "tftp_wlanmdsp_lines": tftp_wlanmdsp_lines,
        "wlanmdsp_failure_lines": wlanmdsp_failure_lines,
        "wlan_pd_up_lines": wlan_pd_up_lines,
        "pil_load_lines": pil_load_lines,
        "wlfw69_lines": wlfw69_lines,
        "bdf_lines": bdf_lines,
        "wlan0_lines": wlan0_lines,
        "degraded_external_lines": degraded_external_lines,
        "light_observer": light_observer,
        "rfs_bridge": rfs_bridge,
        "first_wlanmdsp_lines": grep_lines(evidence_paths, tftp_request_pattern, limit=6),
        "first_load_lines": grep_lines(dmesg_paths, r"root_service_service_ind_cb.*wlan_pd|wlan_pd.*0x1fffffff|(subsys-pil-tz|q6v5|pil|modem).*wlanmdsp|wlanmdsp.*(load|loaded|auth|pil)", limit=6),
        "first_degraded_external_lines": grep_lines(dmesg_paths, r"esoc0_boot_failed|pcie_initialized|mhi_enable|MHI.*(state|enabled|init)|LTSSM", limit=4),
    }


def android_v1982_context() -> dict[str, str]:
    if not ANDROID_V1982_REPORT.exists():
        return {"exists": "0"}
    text = ANDROID_V1982_REPORT.read_text(encoding="utf-8", errors="replace")
    values: dict[str, str] = {"exists": "1", "report": rel(ANDROID_V1982_REPORT)}
    for key, pattern in {
        "wlan_pd_up": r"wlan_pd UP marker \| ([0-9.]+)",
        "bdf": r"first BDF marker \| ([0-9.]+)",
        "wlan0": r"wlan0 \| ([0-9.]+)",
        "requested_wlanmdsp": r"requested_wlanmdsp \| ([0-9]+)",
        "wlanmdsp_line_count": r"wlanmdsp_line_count \| ([0-9]+)",
    }.items():
        match = re.search(pattern, text)
        values[key] = match.group(1) if match else ""
    line_match = re.search(r"`([^`]*tftp_server:[^`]*wlanmdsp\.mbn[^`]*)`", text)
    values["first_wlanmdsp_line"] = line_match.group(1)[:500] if line_match else ""
    return values


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1989",
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
        "a90_android_execns_probe v363",
        "wlan_pd_firmware_serve_gate.requested_wlanmdsp=%d",
        "wlan_pd_service_object_visible_trigger.requested_wlanmdsp=%d",
        "wlan_pd_post_pm_lower_handoff_klog",
        "tftp_server",
        "libqmi_get_service_list_lookup_call",
        "wlfw_client_init_instance_call",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1989_INIT, init_required), (V1989_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in init_forbidden if path == V1989_INIT and token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def configure_handoff_globals() -> None:
    v1847 = parent.parent.base.v1847
    v1847.V1846_OUT = V1989_OUT
    v1847.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v1847.DEFAULT_OUT_DIR = HANDOFF_DIR
    v1847.DEFAULT_REPORT_PATH = HANDOFF_REPORT
    v1847.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    v1847.TEST_LOG_PATH = TEST_LOG_PATH
    v1847.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    v1847.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    v1847.DMESG_PATTERN = (
        "A90v1989|A90v641|sibling fwssctl|wifi-v641-fwssctl|"
        "wlanmdsp|wlan_pd|tftp_server|tqftp|rmt_storage|pd-mapper|"
        "root_service_service_ind_cb|subsys-pil-tz|pil|q6v5|4080000.qcom,mss|"
        "Brought out of reset|QMI Server Connected|WLFW|BDF|wlan0|cnss-daemon|"
        "service 69|service 74|service 180|libqmi_|wlfw_client_init_instance|"
        "esoc0|mdm3|RC1|pcie|MHI|LTSSM"
    )


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = helper_fields()
    trace = collect_wlanmdsp_trace(fields)
    trace["loaded_or_up"] = bool(
        details.get("wlan_pd")
        or details.get("wlfw69")
        or details.get("wlan0")
        or trace.get("pil_load_lines")
        or trace.get("wlan_pd_up_lines")
    )
    details["wlanmdsp_trace"] = trace
    details["android_v1982"] = android_v1982_context()
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    rollback = handoff.get("post_rollback_verification") or {}
    hook_ok = all(item.get("ok") for item in hook.values())
    prearm_ok = any(step["name"] == "arm-clean-dsp-flag" and step["ok"] for step in steps)
    handoff_ok = bool(handoff.get("pass"))
    rollback_ok = bool(rollback.get("version_ok")) and bool(rollback.get("selftest_fail_zero"))
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    light_ok = bool((trace.get("light_observer") or {}).get("ok"))
    combined = (
        bool(details.get("service74"))
        and bool(details.get("pm_open_subsys_modem"))
        and bool(details.get("holder_opened"))
        and parent.parent.base.hit_from_details(details, "wlfw_service_request") > 0
    )
    publication_progress = bool(details.get("wlfw69") or details.get("wlan_pd") or details.get("wlanmdsp") or details.get("wlan0"))
    if not hook_ok or not prearm_ok or not handoff_ok or not rollback_ok:
        label = "native-wlanmdsp-light-handoff-failed"
        reason = "artifact hook, clean-DSP prearm, V1989 handoff, or rollback verification failed"
        passed = False
    elif not light_ok:
        label = "native-wlanmdsp-light-observer-safety-regression"
        reason = "V1989 light contract regressed: QRTR readback, servloc probe, or service-notifier listener was attempted"
        passed = False
    elif not combined:
        label = "native-wlanmdsp-prereq-regression"
        reason = "current native PM/CNSS prerequisites did not reproduce under the light observer"
        passed = False
    elif publication_progress or trace.get("loaded_or_up"):
        if trace.get("requested") and trace.get("served"):
            label = "native-wlanmdsp-requested-served-publication-progress"
            reason = "native requested/served wlanmdsp and reached WLAN-PD/WLFW/wlan0 progress; stop before HAL/scan/connect"
        else:
            label = "native-wlanmdsp-publication-progress-without-captured-request"
            reason = "native reached WLAN-PD/WLFW/wlan0 progress but the light tftp window did not capture the request line"
        passed = True
    elif trace.get("requested") and trace.get("served"):
        label = "native-wlanmdsp-requested-served-pd-still-down"
        reason = "native requested and apparently served wlanmdsp.mbn, but WLAN-PD/WLFW publication still did not start"
        passed = True
    elif trace.get("requested"):
        label = "native-wlanmdsp-request-serve-failed"
        reason = "native requested wlanmdsp.mbn but the serve/load edge failed or timed out"
        passed = True
    else:
        label = "native-wlanmdsp-not-requested-light"
        reason = "native reproduced current AP-side PM/CNSS prerequisites, but the internal modem never requested wlanmdsp.mbn"
        passed = True
    return {
        "label": label,
        "decision": f"v1990-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "prearm_ok": prearm_ok,
        "handoff_ok": handoff_ok,
        "rollback_ok": rollback_ok,
        "light_ok": light_ok,
        "combined": combined,
        "publication_progress": publication_progress,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    light = trace["light_observer"]
    rfs_bridge = trace["rfs_bridge"]
    android = details["android_v1982"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["rfs_bridge", rfs_bridge["ok"], f"exact_exists={rfs_bridge['exact_exists']} nonzero={rfs_bridge['exact_nonzero']} open_rc={rfs_bridge['exact_open_rc']} source_nonzero={rfs_bridge['source_asset_nonzero']} vendor_dir={rfs_bridge['readonly_vendor_is_dir']} vendor_link={rfs_bridge['readonly_vendor_readlink']}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["wlanmdsp_request", trace["requested"], f"field={trace['requested_field']} mbn_lines={trace['wlanmdsp_mbn_lines']} tftp_lines={trace['tftp_wlanmdsp_lines']} failures={trace['wlanmdsp_failure_lines']}"],
        ["wlanmdsp_serve_load", trace["served"], f"served_nonzero={trace['served_nonzero']} pil_load={trace['pil_load_lines']} wlan_pd_up={trace['wlan_pd_up_lines']} wlfw69={trace['wlfw69_lines']} wlan0={trace['wlan0_lines']}"],
        ["degraded_external_watch", trace["degraded_external_lines"], "pcie_initialized/mhi_enable/esoc0_boot_failed/LTSSM only; no eSoC/PCIe action was taken"],
        ["android_v1982", android.get("requested_wlanmdsp", ""), f"wlan_pd={android.get('wlan_pd_up')} BDF={android.get('bdf')} wlan0={android.get('wlan0')} lines={android.get('wlanmdsp_line_count')}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1990 Light Native Wlanmdsp Trace Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1990`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
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
        "## Degraded External Watch",
        "",
        *(f"- `{line}`" for line in trace["first_degraded_external_lines"]),
        *([] if trace["first_degraded_external_lines"] else ["- `none`"]),
        "",
        "## Android Comparator",
        "",
        f"- Report: `{android.get('report', rel(ANDROID_V1982_REPORT))}`",
        f"- Timeline: WLAN-PD UP `{android.get('wlan_pd_up')}`, BDF `{android.get('bdf')}`, wlan0 `{android.get('wlan0')}`.",
        f"- Request evidence: requested_wlanmdsp `{android.get('requested_wlanmdsp')}`, wlanmdsp line count `{android.get('wlanmdsp_line_count')}`.",
        f"- First Android line: `{android.get('first_wlanmdsp_line', '')}`",
        "",
        "## Interpretation",
        "",
        "- If label is `native-wlanmdsp-not-requested-light`, the remaining wall is before the tftp request: the internal modem never advances to the WLAN PD code-image request stage.",
        "- If label is `native-wlanmdsp-request-serve-failed`, the next bounded target is the native tftp/rfs served path for `wlanmdsp.mbn`.",
        "- If label is `native-wlanmdsp-requested-served-pd-still-down`, the target moves deeper inside modem-side PD load/bring-up and should escalate to modem-side DIAG rather than more AP-side strace/QRTR matrix.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, or service-notifier listener was run in the V1989 init argv.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1989 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def write_result(store: EvidenceStore,
                 handoff: dict[str, Any],
                 hook: dict[str, Any],
                 steps: list[dict[str, Any]],
                 handoff_rc: int,
                 created: str | None = None) -> dict[str, Any]:
    details = collect_details(handoff)
    classification = classify(handoff, hook, steps, details)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": created or dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "handoff_rc": handoff_rc,
        "handoff_manifest": rel(HANDOFF_DIR / "manifest.json"),
        "artifact_hook": hook,
        "classification": classification,
        "details": details,
        "steps": steps,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    return manifest


def patch_parent_module() -> None:
    parent.CYCLE = CYCLE
    parent.OUT_DIR = OUT_DIR
    parent.HANDOFF_DIR = HANDOFF_DIR
    parent.HANDOFF_REPORT = HANDOFF_REPORT
    parent.REPORT_PATH = REPORT_PATH
    parent.V1936_OUT = V1989_OUT
    parent.V1936_INIT = V1989_INIT
    parent.V1936_BOOT = V1989_BOOT
    parent.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    parent.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    parent.TEST_LOG_PATH = TEST_LOG_PATH
    parent.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    parent.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    parent.artifact_hook_check = artifact_hook_check
    parent.configure_handoff_globals = configure_handoff_globals
    parent.collect_details = collect_details
    parent.classify = classify
    parent.render_report = render_report
    parent.write_result = write_result


def main(argv: list[str] | None = None) -> int:
    patch_parent_module()
    return parent.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
