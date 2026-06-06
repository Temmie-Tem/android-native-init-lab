#!/usr/bin/env python3
"""Host-only V1738 classifier for the modem-side WLAN-PD trigger surface."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1738-wlan-pd-trigger-surface-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1738_WLAN_PD_TRIGGER_SURFACE_CLASSIFIER_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V966_SUMMARY = REPO_ROOT / "tmp" / "wifi" / "v966-android-wlfw-start-attribution" / "summary.md"
V1331_DMESG = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1331-android-sdx50m-timing-handoff"
    / "v1331-android-sdx50m-timing-recapture-run"
    / "android"
    / "commands"
    / "v1331-dmesg-filtered.txt"
)
V1331_PROPS = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1331-android-sdx50m-timing-handoff"
    / "v1331-android-sdx50m-timing-recapture-run"
    / "android"
    / "commands"
    / "v1331-props.txt"
)
V1736_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
V1737_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1737-wlan-pd-start-trigger-classifier" / "manifest.json"

ICNSS_QMI = REPO_ROOT / "kernel_build" / "SM-A908N_KOR_12_Opensource" / "Kernel" / "drivers" / "soc" / "qcom" / "icnss_qmi.c"
ICNSS_C = REPO_ROOT / "kernel_build" / "SM-A908N_KOR_12_Opensource" / "Kernel" / "drivers" / "soc" / "qcom" / "icnss.c"
SERVICE_NOTIFIER_C = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "drivers"
    / "soc"
    / "qcom"
    / "service-notifier.c"
)


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


def timestamp(text: str, pattern: str) -> float | None:
    match = re.search(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\].*" + pattern, text, re.I | re.M)
    return float(match.group(1)) if match else None


def line_number(path: Path, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for number, line in enumerate(read_text(path).splitlines(), 1):
        if regex.search(line):
            return number
    return None


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def contains_no_active_restart_android(*texts: str) -> bool:
    combined = "\n".join(texts)
    return re.search(r"restart[_ -]?pd|RESTART_PD|service_notif_pd_restart|QMI_SERVREG_NOTIF_RESTART_PD", combined, re.I) is None


def collect_evidence() -> dict[str, Any]:
    v966 = read_text(V966_SUMMARY)
    v1331_dmesg = read_text(V1331_DMESG)
    v1331_props = read_text(V1331_PROPS)
    v1736 = load_json(V1736_MANIFEST)
    v1737 = load_json(V1737_MANIFEST)
    icnss_qmi = read_text(ICNSS_QMI)
    icnss_c = read_text(ICNSS_C)
    service_notifier = read_text(SERVICE_NOTIFIER_C)
    v1736_gate = v1736.get("gate", {})

    return {
        "android_good": {
            "v966_decision_present": "v966-android-cnss-wlfw-start-window-attributed" in v966,
            "wlfw_start_s": timestamp(v1331_dmesg, r"cnss-daemon wlfw_start"),
            "wlfw_service_request_s": timestamp(v1331_dmesg, r"cnss-daemon wlfw_service_request"),
            "wlan_pd_up_s": timestamp(v1331_dmesg, r"root_service_service_ind_cb:.*msm/modem/wlan_pd.*0x1fffffff")
            or timestamp(v966, r"wlan_pd_indication\s*\|\s*([0-9.]+)"),
            "icnss_qmi_s": timestamp(v1331_dmesg, r"icnss_qmi:\s*QMI Server Connected"),
            "bdf_regdb_s": timestamp(v1331_dmesg, r"BDF file\s*:\s*regdb\.bin"),
            "wlan0_s": timestamp(v1331_dmesg, r"dev\s*:\s*wlan0\s*:"),
            "rmt_storage_running": "init.svc.vendor.rmt_storage=running" in v1331_props,
            "tftp_server_running": "init.svc.vendor.tftp_server=running" in v1331_props,
            "pd_mapper_running": "init.svc.vendor.pd_mapper=running" in v1331_props,
            "no_restart_pd_marker": contains_no_active_restart_android(v966, v1331_dmesg, v1331_props),
        },
        "native_v1736": {
            "decision": v1736.get("decision"),
            "pass": boolish(v1736.get("pass")),
            "wlfw_start_hits": intish(v1736_gate.get("wlfw_start_hit_count")),
            "wlfw_service_request_hits": intish(v1736_gate.get("wlfw_service_request_hit_count")),
            "worker_success_hits": intish(v1736_gate.get("wlfw_worker_create_success_hit_count")),
            "wlfw_ind_register_qmi_hits": intish(v1736_gate.get("wlfw_ind_register_qmi_hit_count")),
            "wlfw_cap_qmi_hits": intish(v1736_gate.get("wlfw_cap_qmi_hit_count")),
            "late_listener_state": v1736_gate.get("late_listener_state"),
            "late_listener_indication_seen": intish(v1736_gate.get("late_listener_indication_seen")),
            "wlfw_service69_seen": intish(v1736_gate.get("wlfw_service69_seen")),
            "requested_wlanmdsp": intish(v1736_gate.get("requested_wlanmdsp")),
            "tftp_running": intish(v1736_gate.get("tftp_running")),
            "hard_stops": {
                key: intish(v1736_gate.get(key))
                for key in (
                    "no_esoc0",
                    "no_forced_rc1",
                    "no_fake_online",
                    "no_scan_connect",
                    "no_credentials",
                    "no_dhcp_routes",
                    "no_external_ping",
                )
            },
        },
        "v1737": {
            "decision": v1737.get("decision"),
            "pass": boolish(v1737.get("pass")),
            "label": v1737.get("label"),
        },
        "source": {
            "icnss_qmi_path": str(ICNSS_QMI.relative_to(REPO_ROOT)),
            "icnss_c_path": str(ICNSS_C.relative_to(REPO_ROOT)),
            "service_notifier_path": str(SERVICE_NOTIFIER_C.relative_to(REPO_ROOT)),
            "wlfw_new_server_line": line_number(ICNSS_QMI, r"static int wlfw_new_server"),
            "qmi_add_lookup_line": line_number(ICNSS_QMI, r"qmi_add_lookup\(&priv->qmi,\s*WLFW_SERVICE_ID_V01"),
            "icnss_register_driver_waits_fw_ready_line": line_number(ICNSS_C, r"FW is not ready yet"),
            "service_notifier_register_listener_line": line_number(SERVICE_NOTIFIER_C, r"static int register_notif_listener"),
            "service_notifier_restart_pd_line": line_number(SERVICE_NOTIFIER_C, r"int service_notif_pd_restart"),
            "icnss_trigger_recovery_line": line_number(ICNSS_C, r"int icnss_trigger_recovery"),
            "icnss_fw_lookup_is_passive": "qmi_add_lookup(&priv->qmi, WLFW_SERVICE_ID_V01" in icnss_qmi
            and "static int wlfw_new_server" in icnss_qmi,
            "register_driver_waits_fw_ready": "FW is not ready yet" in icnss_c
            and "icnss_driver_event_register_driver" in icnss_c,
            "restart_pd_api_exists": "QMI_SERVREG_NOTIF_RESTART_PD_REQ_V01" in service_notifier
            and "service_notif_pd_restart" in service_notifier,
            "listener_register_is_state_query": "REGISTER_LISTENER_REQ" in service_notifier
            and "curr_state" in service_notifier,
        },
    }


def classify(evidence: dict[str, Any]) -> tuple[str, str, dict[str, bool]]:
    native = evidence["native_v1736"]
    source = evidence["source"]
    android = evidence["android_good"]
    checks = {
        "v1737_basis_passed": evidence["v1737"]["pass"]
        and evidence["v1737"]["label"] == "modem-side-wlan-pd-start-trigger-gap",
        "android_good_reaches_wlan_pd_and_wlan0": all(
            android[key] is not None
            for key in ("wlfw_start_s", "wlfw_service_request_s", "icnss_qmi_s", "bdf_regdb_s", "wlan0_s")
        ),
        "android_companion_services_running": android["rmt_storage_running"]
        and android["tftp_server_running"]
        and android["pd_mapper_running"],
        "android_no_restart_pd_marker": android["no_restart_pd_marker"],
        "native_cnss_worker_reached": native["pass"]
        and native["wlfw_start_hits"] > 0
        and native["wlfw_service_request_hits"] > 0
        and native["worker_success_hits"] > 0,
        "native_stops_before_wlfw_qmi": native["wlfw_ind_register_qmi_hits"] == 0
        and native["wlfw_cap_qmi_hits"] == 0,
        "native_no_wlan_pd_or_service69_or_wlanmdsp": native["late_listener_state"] == "uninit"
        and native["late_listener_indication_seen"] == 0
        and native["wlfw_service69_seen"] == 0
        and native["requested_wlanmdsp"] == 0,
        "icnss_fw_lookup_is_passive": source["icnss_fw_lookup_is_passive"],
        "listener_register_is_state_query": source["listener_register_is_state_query"],
        "register_driver_waits_fw_ready": source["register_driver_waits_fw_ready"],
        "restart_pd_is_explicit_recovery_api_only": source["restart_pd_api_exists"]
        and evidence["android_good"]["no_restart_pd_marker"],
        "hard_stops_preserved": all(value == 1 for value in native["hard_stops"].values()),
    }
    if all(checks.values()):
        return (
            "v1738-pd-trigger-is-modem-autoload-missing-pass",
            "pd-trigger-is-modem-autoload-missing",
            checks,
        )
    return "v1738-pd-trigger-evidence-incomplete", "pd-trigger-evidence-incomplete", checks


def render_report(manifest: dict[str, Any]) -> str:
    evidence = manifest["evidence"]
    android = evidence["android_good"]
    native = evidence["native_v1736"]
    source = evidence["source"]
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1738 WLAN-PD Trigger Surface Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1738`",
            "- Type: host-only/source-only modem-side WLAN-PD trigger surface classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Label: `{manifest['label']}`",
            "- Evidence: `tmp/wifi/v1738-wlan-pd-trigger-surface-classifier`",
            "",
            "## Android-good Surface",
            "",
            f"- `wlfw_start` / `wlfw_service_request`: `{android['wlfw_start_s']}` s / `{android['wlfw_service_request_s']}` s",
            f"- ICNSS QMI / BDF / `wlan0`: `{android['icnss_qmi_s']}` s / `{android['bdf_regdb_s']}` s / `{android['wlan0_s']}` s",
            f"- companion services running: rmt_storage `{android['rmt_storage_running']}`, tftp_server `{android['tftp_server_running']}`, pd_mapper `{android['pd_mapper_running']}`",
            f"- restart-PD marker in current Android-good evidence: `{not android['no_restart_pd_marker']}`",
            "",
            "## Native V1736 Surface",
            "",
            f"- `wlfw_start` / `wlfw_service_request` / worker success hits: `{native['wlfw_start_hits']}` / `{native['wlfw_service_request_hits']}` / `{native['worker_success_hits']}`",
            f"- WLFW indication-register QMI / capability QMI hits: `{native['wlfw_ind_register_qmi_hits']}` / `{native['wlfw_cap_qmi_hits']}`",
            f"- WLAN-PD listener state / indication: `{native['late_listener_state']}` / `{native['late_listener_indication_seen']}`",
            f"- WLFW service 69 / requested `wlanmdsp`: `{native['wlfw_service69_seen']}` / `{native['requested_wlanmdsp']}`",
            f"- tftp running: `{native['tftp_running']}`",
            "",
            "## Source Surface",
            "",
            f"- `{source['icnss_qmi_path']}`: `wlfw_new_server` line `{source['wlfw_new_server_line']}`, `qmi_add_lookup(WLFW_SERVICE_ID)` line `{source['qmi_add_lookup_line']}`",
            f"- `{source['icnss_c_path']}`: driver registration waits on FW-ready line `{source['icnss_register_driver_waits_fw_ready_line']}`",
            f"- `{source['service_notifier_path']}`: listener registration line `{source['service_notifier_register_listener_line']}`, explicit restart-PD API line `{source['service_notifier_restart_pd_line']}`",
            "",
            "## Classification",
            "",
            "The available AP-side source surfaces are passive for initial WLAN-PD bring-up: ICNSS registers a WLFW service lookup and reacts to `wlfw_new_server`; service-notifier registers/listens and reports current state; QCACLD registration waits for FW-ready. The only explicit PD mutation surface found in this source set is `service_notif_pd_restart`, but current Android-good evidence does not show a restart-PD marker and that path remains outside the active read-only branch.",
            "",
            "V1738 therefore classifies the current blocker as modem-side autoload missing in native: Android reaches WLAN-PD/WLFW with the companion services running, while native reaches the CNSS worker and has tftp running but receives no WLAN-PD UP, no WLFW service 69, and no `wlanmdsp` request.",
            "",
            "## Next Gate",
            "",
            "- V1739 should be read-only Android-good firmware request capture planning/source-build only first.",
            "- The useful discriminator is whether Android-good `tftp_server` or `rmt_storage` observes a `wlanmdsp.mbn`/modem PD image request before WLAN-PD UP, and which served path is used.",
            "- If Android-good firmware request evidence exists, mirror only that read-only visibility in native before any mutation.",
            "- Do not send restart-PD, do not add PM/service-window actors, do not use `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
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
            "## V1738 WLAN-PD trigger surface classifier (2026-06-03)",
            "",
            "- V1738 host-only/source-only classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - label: `{manifest['label']}`;",
            "  - ICNSS WLFW service lookup and service-notifier listener paths are passive for initial bring-up;",
            "  - QCACLD driver registration waits for FW-ready and is not a WLFW trigger;",
            "  - the only explicit PD mutation surface in the inspected source is restart-PD, but Android-good evidence does not show it and it remains excluded;",
            "  - native reaches the CNSS worker but still sees no WLAN-PD UP, no WLFW service 69, and no `wlanmdsp` request.",
            "",
            "  Next candidate:",
            "",
            "  - V1739 read-only Android-good firmware request capture plan/source-build first;",
            "  - determine whether Android-good `tftp_server` or `rmt_storage` observes a `wlanmdsp.mbn`/PD image request before WLAN-PD UP and which path serves it;",
            "  - no restart-PD, PM/service-window actor expansion, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1738_WLAN_PD_TRIGGER_SURFACE_CLASSIFIER_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    heading = "## V1738 WLAN-PD trigger surface classifier"
    if heading in current:
        pattern = re.compile(
            r"\n## V1738 WLAN-PD trigger surface classifier \(2026-06-03\)\n.*?(?=\n## |\Z)",
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
        "cycle": "V1738",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "evidence": evidence,
        "checks": checks,
        "next_gate": "V1739 read-only Android-good firmware request capture plan/source-build",
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": decision, "pass": pass_ok}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
