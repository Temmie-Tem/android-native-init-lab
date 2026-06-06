#!/usr/bin/env python3
"""Host-only V1737 classifier for the WLAN-PD start trigger gap."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1737-wlan-pd-start-trigger-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1737_WLAN_PD_START_TRIGGER_CLASSIFIER_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V829_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v829-servloc-domain-list-probe-retry-20260525-113735" / "manifest.json"
V833_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V833_ANDROID_SERVNOTIF_POSITIVE_CONTROL_LIVE_2026-05-25.md"
V1680_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1680-wlan-pd-firmware-serve-modem-holder-handoff" / "manifest.json"
V1703_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1703_CNSS_WLFW_DOWNSTREAM_STATIC_2026-06-02.md"
V1734_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1734-wlan-pd-up-delta-classifier" / "manifest.json"
V1736_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
V1736_HELPER = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "test-v1393-helper-result.stdout.txt"


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: Any) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ok"}


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$"):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value
    return values


def uprobe_time(kv: dict[str, str], key: str) -> float | None:
    line = kv.get(key, "")
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    return float(match.group(1)) if match else None


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def collect_evidence() -> dict[str, Any]:
    v829 = load_json(V829_MANIFEST)
    v1680 = load_json(V1680_MANIFEST)
    v1734 = load_json(V1734_MANIFEST)
    v1736 = load_json(V1736_MANIFEST)
    v1736_kv = parse_kv(read_text(V1736_HELPER))
    v833_report = read_text(V833_REPORT)
    v1703_report = read_text(V1703_REPORT)

    v829_servloc = v829.get("live", {}).get("servloc", {})
    v1680_gate = v1680.get("gate", {})
    v1736_gate = v1736.get("gate", {})

    return {
        "v829": {
            "decision": v829.get("decision"),
            "pass": boolish(v829.get("pass")),
            "domain_count": intish(v829_servloc.get("domain_count")),
            "domain_name": (v829_servloc.get("domains") or [{}])[0].get("name"),
            "domain_instance": (v829_servloc.get("domains") or [{}])[0].get("instance_id"),
            "response_success": intish(v829_servloc.get("response_success")),
            "qmi_result": intish(v829_servloc.get("qmi_result")),
            "no_esoc0": not boolish(v829.get("esoc0_open_executed")),
            "no_scan_connect": not boolish(v829.get("scan_connect_executed")),
        },
        "v833": {
            "report": str(V833_REPORT.relative_to(REPO_ROOT)),
            "positive_control_up": "canonical state | `up`" in v833_report
            or "corrected interpretation: `state-up`" in v833_report,
            "raw_up_state": "0x1fffffff" in v833_report,
            "no_wifi_bringup": "Wi-Fi bring-up | not executed" in v833_report,
        },
        "v1680": {
            "decision": v1680.get("decision"),
            "pass": boolish(v1680.get("pass")),
            "label": v1680_gate.get("label"),
            "tftp_running": intish(v1680_gate.get("tftp_running")),
            "requested_wlanmdsp": intish(v1680_gate.get("requested_wlanmdsp")),
            "served_wlanmdsp_nonzero": intish(v1680_gate.get("served_wlanmdsp_nonzero")),
            "rollback_ok": boolish(v1680.get("rollback", {}).get("ok")),
        },
        "v1703": {
            "report": str(V1703_REPORT.relative_to(REPO_ROOT)),
            "wlfw_service_request_mapped": "`wlfw_service_request@0xd9fc`" in v1703_report,
            "ind_register_downstream_mapped": "`wlfw_send_ind_register_req@0xf32c`" in v1703_report,
            "blocks_before_qmi_ind_register_interpretation": "block is before WLFW QMI client/service readiness" in v1703_report,
        },
        "v1734": {
            "decision": v1734.get("decision"),
            "pass": boolish(v1734.get("pass")),
            "label": v1734.get("label"),
            "android_wlfw_request_to_wlan_pd_up_ms": v1734.get("android_good", {}).get("wlfw_request_to_wlan_pd_up_ms"),
            "android_wlan_pd_up_to_icnss_qmi_ms": v1734.get("android_good", {}).get("wlan_pd_up_to_icnss_qmi_ms"),
            "native_modem_reset_and_qrtr_seen": boolish(v1734.get("checks", {}).get("native_modem_reset_and_qrtr_seen")),
            "native_no_wlanmdsp_request": boolish(v1734.get("checks", {}).get("native_no_wlanmdsp_request")),
        },
        "v1736": {
            "decision": v1736.get("decision"),
            "pass": boolish(v1736.get("pass")),
            "rollback_ok": boolish(v1736.get("rollback", {}).get("ok")),
            "service_window_label": v1736_gate.get("service_window_label"),
            "nonlog_label": v1736_gate.get("nonlog_label"),
            "wlfw_start_hits": intish(v1736_gate.get("wlfw_start_hit_count")),
            "wlfw_service_request_hits": intish(v1736_gate.get("wlfw_service_request_hit_count")),
            "worker_success_hits": intish(v1736_gate.get("wlfw_worker_create_success_hit_count")),
            "wlfw_ind_register_qmi_hits": intish(v1736_gate.get("wlfw_ind_register_qmi_hit_count")),
            "wlfw_cap_qmi_hits": intish(v1736_gate.get("wlfw_cap_qmi_hit_count")),
            "wlfw_service69_seen": intish(v1736_gate.get("wlfw_service69_seen")),
            "requested_wlanmdsp": intish(v1736_gate.get("requested_wlanmdsp")),
            "late_listener_result": v1736_gate.get("late_listener_result"),
            "late_listener_state": v1736_gate.get("late_listener_state"),
            "late_listener_indication_seen": intish(v1736_gate.get("late_listener_indication_seen")),
            "late_listener_hold_ms": intish(v1736_gate.get("late_listener_hold_ms")),
            "observer_monotonic_ms": intish(v1736_gate.get("observer_monotonic_ms")),
            "wlfw_start_s": uprobe_time(v1736_kv, "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.first_hit_line"),
            "wlfw_service_request_s": uprobe_time(
                v1736_kv,
                "wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.first_hit_line",
            ),
            "no_esoc0": intish(v1736_gate.get("no_esoc0")),
            "no_forced_rc1": intish(v1736_gate.get("no_forced_rc1")),
            "no_fake_online": intish(v1736_gate.get("no_fake_online")),
            "no_scan_connect": intish(v1736_gate.get("no_scan_connect")),
            "no_credentials": intish(v1736_gate.get("no_credentials")),
            "no_dhcp_routes": intish(v1736_gate.get("no_dhcp_routes")),
            "no_external_ping": intish(v1736_gate.get("no_external_ping")),
        },
    }


def classify(evidence: dict[str, Any]) -> tuple[str, str, dict[str, bool]]:
    checks = {
        "domain_mapping_present": evidence["v829"]["pass"]
        and evidence["v829"]["domain_name"] == "msm/modem/wlan_pd"
        and evidence["v829"]["domain_instance"] == 180,
        "listener_model_positive_control_up": evidence["v833"]["positive_control_up"]
        and evidence["v833"]["raw_up_state"],
        "firmware_serve_route_not_requested": evidence["v1680"]["pass"]
        and evidence["v1680"]["label"] == "firmware-not-requested"
        and evidence["v1680"]["tftp_running"] == 1
        and evidence["v1680"]["requested_wlanmdsp"] == 0,
        "cnss_downstream_static_mapped": evidence["v1703"]["wlfw_service_request_mapped"]
        and evidence["v1703"]["ind_register_downstream_mapped"],
        "android_good_up_after_wlfw_request": evidence["v1734"]["pass"]
        and evidence["v1734"]["label"] == "modem-side-wlan-pd-start-gap"
        and evidence["v1734"]["android_wlfw_request_to_wlan_pd_up_ms"] is not None,
        "native_cnss_worker_reached": evidence["v1736"]["pass"]
        and evidence["v1736"]["wlfw_start_hits"] > 0
        and evidence["v1736"]["wlfw_service_request_hits"] > 0
        and evidence["v1736"]["worker_success_hits"] > 0,
        "native_waits_before_wlfw_qmi": evidence["v1736"]["wlfw_ind_register_qmi_hits"] == 0
        and evidence["v1736"]["wlfw_cap_qmi_hits"] == 0,
        "native_wlan_pd_stays_uninit": evidence["v1736"]["late_listener_result"] == "listener-response-success"
        and evidence["v1736"]["late_listener_state"] == "uninit"
        and evidence["v1736"]["late_listener_indication_seen"] == 0,
        "native_no_wlfw69_or_firmware_request": evidence["v1736"]["wlfw_service69_seen"] == 0
        and evidence["v1736"]["requested_wlanmdsp"] == 0,
        "hard_stops_preserved": all(
            evidence["v1736"][key] == 1
            for key in (
                "no_esoc0",
                "no_forced_rc1",
                "no_fake_online",
                "no_scan_connect",
                "no_credentials",
                "no_dhcp_routes",
                "no_external_ping",
            )
        ),
    }
    if all(checks.values()):
        return (
            "v1737-modem-side-wlan-pd-start-trigger-gap-pass",
            "modem-side-wlan-pd-start-trigger-gap",
            checks,
        )
    return "v1737-host-evidence-incomplete", "host-evidence-incomplete", checks


def render_report(manifest: dict[str, Any]) -> str:
    evidence = manifest["evidence"]
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1737 WLAN-PD Start Trigger Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1737`",
            "- Type: host-only WLAN-PD start trigger classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Label: `{manifest['label']}`",
            "- Evidence: `tmp/wifi/v1737-wlan-pd-start-trigger-classifier`",
            "",
            "## Closed Premises",
            "",
            f"- service-locator domain: `{evidence['v829']['domain_name']}` instance `{evidence['v829']['domain_instance']}`",
            "- listener model: Android V833 positive-control returns WLAN-PD `UP` for the same listener request",
            f"- CNSS static path: `wlfw_service_request` mapped, indication/capability QMI calls downstream mapped: `{evidence['v1703']['ind_register_downstream_mapped']}`",
            f"- firmware serve route: V1680 label `{evidence['v1680']['label']}`, tftp running `{evidence['v1680']['tftp_running']}`, requested `wlanmdsp` `{evidence['v1680']['requested_wlanmdsp']}`",
            "",
            "## Native V1736",
            "",
            f"- decision: `{evidence['v1736']['decision']}`",
            f"- service-window label: `{evidence['v1736']['service_window_label']}`",
            f"- non-log label: `{evidence['v1736']['nonlog_label']}`",
            f"- `wlfw_start` / `wlfw_service_request` / worker success hits: `{evidence['v1736']['wlfw_start_hits']}` / `{evidence['v1736']['wlfw_service_request_hits']}` / `{evidence['v1736']['worker_success_hits']}`",
            f"- first `wlfw_start` / `wlfw_service_request` trace times: `{evidence['v1736']['wlfw_start_s']}` s / `{evidence['v1736']['wlfw_service_request_s']}` s",
            f"- WLFW indication-register QMI / capability QMI hits: `{evidence['v1736']['wlfw_ind_register_qmi_hits']}` / `{evidence['v1736']['wlfw_cap_qmi_hits']}`",
            f"- late listener: `{evidence['v1736']['late_listener_result']}`, state `{evidence['v1736']['late_listener_state']}`, indication `{evidence['v1736']['late_listener_indication_seen']}`, hold `{evidence['v1736']['late_listener_hold_ms']}` ms",
            f"- WLFW service 69 / requested `wlanmdsp`: `{evidence['v1736']['wlfw_service69_seen']}` / `{evidence['v1736']['requested_wlanmdsp']}`",
            f"- observer monotonic ms: `{evidence['v1736']['observer_monotonic_ms']}`",
            "",
            "## Android-good Delta",
            "",
            f"- V1734 Android `wlfw_service_request` to WLAN-PD UP: `{evidence['v1734']['android_wlfw_request_to_wlan_pd_up_ms']}` ms",
            f"- V1734 Android WLAN-PD UP to ICNSS QMI: `{evidence['v1734']['android_wlan_pd_up_to_icnss_qmi_ms']}` ms",
            "- Native now reaches the same CNSS worker but still never sees WLAN-PD UP, WLFW service 69, or a `wlanmdsp` request.",
            "",
            "## Classification",
            "",
            "V1736 confirms the latest correction: missing native `wlfw_start` logs were a measurement artifact. `cnss-daemon` reaches `wlfw_start`, starts `wlfw_service_request`, and creates the worker. The block is after CNSS worker creation but before WLFW QMI indication registration/capability calls, because WLFW service 69 never appears and WLAN-PD remains `UNINIT`.",
            "",
            "The remaining start trigger is modem-side: native has domain mapping, a valid service-notifier endpoint, tftp running, and internal modem reset/QRTR, but the modem never starts `msm/modem/wlan_pd` and never asks for `wlanmdsp.mbn`.",
            "",
            "## Next Gate",
            "",
            "- V1738 should be host-only/source-only first: classify the Android-good modem-side WLAN-PD start trigger surface before any mutation.",
            "- Inputs should stay bounded to existing Android-good dmesg/trace evidence, ICNSS/CNSS source or disassembly, service-locator/servreg evidence, and firmware-serve evidence.",
            "- Candidate outcomes: `pd-trigger-request-surface-identified`, `pd-trigger-is-modem-autoload-missing`, `pd-trigger-evidence-incomplete`.",
            "- Do not add PM/service-window actors, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "## Checks",
            "",
            checks,
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start services, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1737 WLAN-PD start trigger classifier (2026-06-03)",
            "",
            "- V1737 host-only classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - label: `{manifest['label']}`;",
            "  - V1736 proved native `wlfw_start` / `wlfw_service_request` / worker creation are reached;",
            "  - WLFW indication-register/capability QMI calls remain unhit because WLFW service 69 never appears;",
            "  - WLAN-PD listener still returns `UNINIT` after the hold window and no `wlanmdsp` request reaches the firmware-serve route;",
            "  - V829 domain mapping and V833 Android positive-control close the pd-mapper/listener-model hypotheses.",
            "",
            "  Next candidate:",
            "",
            "  - V1738 host-only/source-only modem-side WLAN-PD start trigger surface classifier;",
            "  - inspect Android-good evidence and ICNSS/CNSS source/disassembly for what moves `msm/modem/wlan_pd` from `UNINIT` to `UP`; identify a concrete read-only observation or mutation target before any live write;",
            "  - forbidden: PM/service-window actor expansion, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1737_WLAN_PD_START_TRIGGER_CLASSIFIER_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    heading = "## V1737 WLAN-PD start trigger classifier"
    if heading in current:
        pattern = re.compile(
            r"\n## V1737 WLAN-PD start trigger classifier \(2026-06-03\)\n.*?(?=\n## |\Z)",
            re.S,
        )
        updated = pattern.sub(entry, current.rstrip())
        NEXT_WORK_PATH.write_text(updated.rstrip() + "\n", encoding="utf-8")
    else:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    evidence = collect_evidence()
    decision, label, checks = classify(evidence)
    pass_ok = all(checks.values())
    manifest = {
        "cycle": "V1737",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "evidence": evidence,
        "checks": checks,
        "next_gate": "V1738 host-only/source-only modem-side WLAN-PD start trigger surface classifier"
        if pass_ok
        else "refresh missing host evidence",
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": decision, "pass": pass_ok}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
