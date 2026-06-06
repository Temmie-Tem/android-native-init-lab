#!/usr/bin/env python3
"""Host-only V1732 correction classifier for CNSS output and WLAN-PD state-up."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1732-cnss-output-stateup-correction"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1732_CNSS_OUTPUT_STATEUP_CORRECTION_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1681_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1681-wlan-pd-wlfw-trigger-delta-classifier" / "manifest.json"
V1725_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1725-cnss-output-visible-route-handoff" / "manifest.json"
V1727_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1727-wlan-pd-service-manager-bootstrap-handoff" / "manifest.json"
V1729_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1729-wlan-pd-servnotif-late-endpoint-handoff" / "manifest.json"
V1731_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff" / "manifest.json"
V833_DMESG = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v833-android-servnotif-handoff-live-20260525-125136"
    / "v833-android-servnotif-positive-control-run"
    / "android"
    / "commands"
    / "readiness-dmesg-tail.txt"
)
V1725_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1725_CNSS_OUTPUT_VISIBLE_ROUTE_HANDOFF_2026-06-03.md"
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def intish(value: Any) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def timestamp(text: str, pattern: str) -> float | None:
    regex = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\].*" + pattern, re.M | re.I)
    match = regex.search(text)
    return float(match.group(1)) if match else None


def report_inline(text: str, label: str) -> tuple[str | None, str | None, str | None]:
    match = re.search(
        re.escape(label)
        + r"[^`]*expected `([^`]+)`, value `([^`]+)`, match `([^`]+)`",
        text,
    )
    if not match:
        return None, None, None
    return match.group(1), match.group(2), match.group(3)


def report_all_match(text: str) -> str | None:
    match = re.search(r"all property lookups matched:\s*`([^`]+)`", text)
    return match.group(1) if match else None


def delta_ms(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start) * 1000.0, 3)


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android_good"]
    native = manifest["native"]
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1732 CNSS Output and WLAN-PD State-up Correction",
            "",
            "## Summary",
            "",
            "- Cycle: `V1732`",
            "- Type: host-only correction/current-evidence classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            "- Evidence: `tmp/wifi/v1732-cnss-output-stateup-correction`",
            "",
            "## Corrections Fixed",
            "",
            "- Retract the QCACLD-register premise: `boot_wlan` / QCACLD driver registration is not a WLFW server trigger.",
            "- Treat native `wlfw_start` log absence as a measurement artifact unless non-log control-flow evidence also misses `wlfw_start`.",
            "- Stop PM/service-window actor expansion for this branch. The current evidence already reaches `wlfw_start` and `wlfw_service_request` without PM trio or `boot_wlan`.",
            "",
            "## Output Visibility Branch",
            "",
            f"- V1725 strict output label: `{manifest['v1725_label']}`",
            f"- V1725 property lookup matched: `{manifest['v1725_property_lookup_all_match']}`",
            f"- V1725 kmsg property: expected `{manifest['v1725_kmsg_expected']}`, value `{manifest['v1725_kmsg_value']}`, match `{manifest['v1725_kmsg_match']}`",
            f"- V1725 debug property: expected `{manifest['v1725_debug_expected']}`, value `{manifest['v1725_debug_value']}`, match `{manifest['v1725_debug_match']}`",
            f"- V1727 non-log label: `{manifest['v1727_nonlog_label']}`",
            f"- V1727 `wlfw_start` / `wlfw_service_request` / worker-create-success hits: `{manifest['v1727_wlfw_start_hits']}` / `{manifest['v1727_wlfw_request_hits']}` / `{manifest['v1727_worker_success_hits']}`",
            "",
            "Interpretation: the output-only path remains invisible, but non-log evidence proves `cnss-daemon` reaches `wlfw_start`, creates the `wlfw_service_request` worker, and then waits for WLFW QMI. The missing dmesg/log line is not a reason to add `boot_wlan`, PM trio, or more pre-CNSS actors.",
            "",
            "## Android-good State-up Reference",
            "",
            f"- `wlfw_start`: `{android['wlfw_start_s']}` s",
            f"- `wlfw_service_request`: `{android['wlfw_service_request_s']}` s",
            f"- WLAN-PD service-notifier UP: `{android['wlan_pd_up_s']}` s",
            f"- ICNSS QMI connected: `{android['icnss_qmi_s']}` s",
            f"- first BDF request: `{android['first_bdf_s']}` s",
            f"- `wlan0`: `{android['wlan0_s']}` s",
            f"- request-to-WLAN-PD-UP delta: `{android['wlfw_request_to_wlan_pd_up_ms']}` ms",
            f"- WLAN-PD-UP-to-ICNSS-QMI delta: `{android['wlan_pd_up_to_icnss_qmi_ms']}` ms",
            "",
            "## Native Current State",
            "",
            f"- V1731 decision: `{manifest['v1731_decision']}`",
            f"- service-window label: `{native['service_window_label']}`",
            f"- non-log label: `{native['nonlog_label']}`",
            f"- late service-notifier endpoint: `{native['late_endpoint_result']}` node `{native['late_endpoint_node']}` port `{native['late_endpoint_port']}`",
            f"- late listener response: `{native['late_listener_result']}` state `{native['late_listener_response_state']}` / `{native['late_listener_response_state_name']}`",
            f"- late indication seen: `{native['late_listener_indication_seen']}`",
            f"- WLFW service 69 seen: `{native['wlfw_service69_seen']}`",
            f"- requested `wlanmdsp`: `{native['requested_wlanmdsp']}`",
            "",
            "## Fixed Classification",
            "",
            f"- Label: `{manifest['label']}`",
            f"- Missing surface: `{manifest['missing_surface']}`",
            "",
            "Android reaches WLAN-PD UP about one second after `wlfw_service_request`; native reaches the same `wlfw_service_request` worker but the late service-notifier listener still reports `UNINIT`, receives no indication, sees no WLFW service 69, and sees no `wlanmdsp` request. The blocker is therefore modem-side WLAN-PD state-up / image-load request publication, not CNSS output visibility, not QCACLD registration, and not PM-service actor ordering.",
            "",
            "## Checks",
            "",
            checks,
            "",
            "## Next Gate",
            "",
            "- Do not repeat output-visibility, service-manager, PM-trio, `boot_wlan`, eSoC/RC1, or timing-window variants.",
            "- Next useful unit: host-only V1733 modem-side WLAN-PD state-up trigger classifier from Android-good/current native evidence, focused on what causes the modem to move `msm/modem/wlan_pd` from `UNINIT` to `UP` and request or publish WLFW service 69.",
            "- A future live gate should only run after V1733 identifies a concrete non-mutating trigger or observation point.",
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager/PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1732 CNSS output and WLAN-PD state-up correction (2026-06-03)",
            "",
            "- V1732 host-only correction/current-evidence classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - fixed label: `{manifest['label']}`;",
            f"  - missing surface: `{manifest['missing_surface']}`;",
            "  - latest correction accepted: QCACLD/`boot_wlan` is not a WLFW trigger, and native `wlfw_start` dmesg absence is a logging/output artifact;",
            "  - V1725 already ran the strict output-visibility branch and returned `cnss-output-still-invisible`; V1727/V1731 non-log evidence proves `wlfw_start`, `wlfw_service_request`, and worker creation anyway;",
            "  - V1731 late service-notifier listener reaches the endpoint but receives `UNINIT`, no indication, no WLFW service 69, and no `wlanmdsp` request.",
            "",
            "  Next candidate:",
            "",
            "  - V1733 host-only modem-side WLAN-PD state-up trigger classifier: compare Android-good WLAN-PD-UP timing against V1731 native `UNINIT` and identify a concrete non-mutating observation/trigger surface before any live retry;",
            "  - do not add PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1732_CNSS_OUTPUT_STATEUP_CORRECTION_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    if "## V1732 CNSS output and WLAN-PD state-up correction" not in current:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    v1681 = load_json(V1681_MANIFEST)
    v1725 = load_json(V1725_MANIFEST)
    v1727 = load_json(V1727_MANIFEST)
    v1729 = load_json(V1729_MANIFEST)
    v1731 = load_json(V1731_MANIFEST)
    v833_dmesg = read_text(V833_DMESG)
    v1725_report = read_text(V1725_REPORT)

    v1725_gate = v1725.get("gate", {})
    v1727_gate = v1727.get("gate", {})
    v1729_gate = v1729.get("gate", {})
    v1731_gate = v1731.get("gate", {})
    kmsg_expected, kmsg_value, kmsg_match = report_inline(
        v1725_report, "`persist.vendor.cnss-daemon.kmsg_logging`"
    )
    debug_expected, debug_value, debug_match = report_inline(
        v1725_report, "`persist.vendor.cnss-daemon.debug_level`"
    )
    property_all_match = v1725_gate.get("property_lookup_all_match") or report_all_match(v1725_report)

    wlfw_start_s = timestamp(v833_dmesg, r"cnss-daemon wlfw_start")
    wlfw_request_s = timestamp(v833_dmesg, r"cnss-daemon wlfw_service_request")
    wlan_pd_up_s = timestamp(v833_dmesg, r"service-notifier:.*wlan_pd.*state:\s*0x1fffffff")
    icnss_qmi_s = timestamp(v833_dmesg, r"icnss_qmi: QMI Server Connected")
    first_bdf_s = timestamp(v833_dmesg, r"BDF file")
    wlan0_s = timestamp(v833_dmesg, r"dev\s*:\s*wlan0\s*:")

    checks = {
        "v1681_retracted_by_new_evidence": v1681.get("decision") == "v1681-cnss-wlfw-start-trigger-surface-selected",
        "v1725_output_branch_ran": v1725.get("decision") == "v1725-cnss-output-still-invisible-rollback-pass",
        "v1725_properties_matched": property_all_match == "1",
        "v1727_nonlog_wlfw_reached": intish(v1727_gate.get("wlfw_start_hit_count")) >= 1
        and intish(v1727_gate.get("wlfw_service_request_hit_count")) >= 1,
        "v1731_worker_created": intish(v1731_gate.get("wlfw_worker_create_success_hit_count")) >= 1,
        "v1729_late_endpoint_found": v1729_gate.get("late_endpoint_found") == "1",
        "v1731_late_listener_uninit": v1731_gate.get("late_listener_response_success") == "1"
        and v1731_gate.get("late_listener_response_state_name") == "uninit",
        "v1731_no_indication": v1731_gate.get("late_listener_indication_seen") == "0",
        "v1731_no_service69": v1731_gate.get("wlfw_service69_seen") == "0",
        "v1731_no_wlanmdsp": v1731_gate.get("requested_wlanmdsp") == "0",
        "android_good_state_up_chain": all(value is not None for value in (wlfw_start_s, wlfw_request_s, wlan_pd_up_s, icnss_qmi_s, first_bdf_s, wlan0_s)),
    }

    pass_ok = all(checks.values())
    decision = (
        "v1732-cnss-output-artifact-wlan-pd-stateup-gap-pass"
        if pass_ok
        else "v1732-cnss-output-stateup-correction-incomplete"
    )
    manifest: dict[str, Any] = {
        "cycle": "V1732",
        "decision": decision,
        "pass": pass_ok,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "label": "wlfw-start-reached-wlan-pd-uninit-downstream-block" if pass_ok else "incomplete-host-evidence",
        "missing_surface": "modem-side-wlan-pd-state-up-and-wlfw-service69-publication" if pass_ok else "unknown",
        "v1725_label": v1725_gate.get("label"),
        "v1725_property_lookup_all_match": property_all_match,
        "v1725_kmsg_expected": kmsg_expected,
        "v1725_kmsg_value": kmsg_value,
        "v1725_kmsg_match": kmsg_match,
        "v1725_debug_expected": debug_expected,
        "v1725_debug_value": debug_value,
        "v1725_debug_match": debug_match,
        "v1727_nonlog_label": v1727_gate.get("nonlog_label"),
        "v1727_wlfw_start_hits": v1727_gate.get("wlfw_start_hit_count"),
        "v1727_wlfw_request_hits": v1727_gate.get("wlfw_service_request_hit_count"),
        "v1727_worker_success_hits": v1731_gate.get("wlfw_worker_create_success_hit_count"),
        "v1731_decision": v1731.get("decision"),
        "android_good": {
            "wlfw_start_s": wlfw_start_s,
            "wlfw_service_request_s": wlfw_request_s,
            "wlan_pd_up_s": wlan_pd_up_s,
            "icnss_qmi_s": icnss_qmi_s,
            "first_bdf_s": first_bdf_s,
            "wlan0_s": wlan0_s,
            "wlfw_request_to_wlan_pd_up_ms": delta_ms(wlfw_request_s, wlan_pd_up_s),
            "wlan_pd_up_to_icnss_qmi_ms": delta_ms(wlan_pd_up_s, icnss_qmi_s),
        },
        "native": {
            "service_window_label": v1731_gate.get("service_window_label"),
            "nonlog_label": v1731_gate.get("nonlog_label"),
            "late_endpoint_result": v1731_gate.get("late_endpoint_result"),
            "late_endpoint_node": v1731_gate.get("late_endpoint_node"),
            "late_endpoint_port": v1731_gate.get("late_endpoint_port"),
            "late_listener_result": v1731_gate.get("late_listener_result"),
            "late_listener_response_state": v1731_gate.get("late_listener_response_state"),
            "late_listener_response_state_name": v1731_gate.get("late_listener_response_state_name"),
            "late_listener_indication_seen": v1731_gate.get("late_listener_indication_seen"),
            "wlfw_service69_seen": v1731_gate.get("wlfw_service69_seen"),
            "requested_wlanmdsp": v1731_gate.get("requested_wlanmdsp"),
        },
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
