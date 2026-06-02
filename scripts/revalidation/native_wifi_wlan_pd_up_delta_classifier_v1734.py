#!/usr/bin/env python3
"""Host-only V1734 classifier for the WLAN-PD state-up delta."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1734-wlan-pd-up-delta-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1734_WLAN_PD_UP_DELTA_CLASSIFIER_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1680_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1680-wlan-pd-firmware-serve-modem-holder-handoff" / "manifest.json"
V1727_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1727-wlan-pd-service-manager-bootstrap-handoff" / "manifest.json"
V1731_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff" / "manifest.json"
V1732_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1732-cnss-output-stateup-correction" / "manifest.json"

V1680_HELPER = REPO_ROOT / "tmp" / "wifi" / "v1680-wlan-pd-firmware-serve-modem-holder-handoff" / "test-v1393-helper-result.stdout.txt"
V1731_HELPER = REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff" / "test-v1393-helper-result.stdout.txt"
V1731_DMESG = REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff" / "test-v1393-dmesg.stdout.txt"

ANDROID_V833_DMESG = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v833-android-servnotif-handoff-live-20260525-125136"
    / "v833-android-servnotif-positive-control-run"
    / "android"
    / "commands"
    / "readiness-dmesg-tail.txt"
)
ANDROID_V1331_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1331-android-sdx50m-timing-handoff"
    / "v1331-android-sdx50m-timing-recapture-run"
    / "manifest.json"
)
ANDROID_V1555_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1555-android-good-minimal-trace-reference" / "manifest.json"


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


def delta_ms(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start) * 1000.0, 3)


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$"):
            continue
        key, value = line.split("=", 1)
        if re.match(r"^[A-Za-z0-9_.:-]+$", key):
            values[key] = value
    return values


def count_ci(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.I))


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def android_reference() -> dict[str, Any]:
    v833 = read_text(ANDROID_V833_DMESG)
    v1331 = load_json(ANDROID_V1331_MANIFEST)
    v1555 = load_json(ANDROID_V1555_MANIFEST)

    wlfw_start_s = timestamp(v833, r"cnss-daemon wlfw_start")
    wlfw_request_s = timestamp(v833, r"cnss-daemon wlfw_service_request")
    wlan_pd_up_s = timestamp(v833, r"service-notifier:.*msm/modem/wlan_pd.*state:\s*0x1fffffff")
    icnss_qmi_s = timestamp(v833, r"icnss_qmi:\s*QMI Server Connected")
    first_bdf_s = timestamp(v833, r"wlfw_send_bdf_download_req")
    wlan0_s = timestamp(v833, r"dev\s*:\s*wlan0\s*:")
    service180_s = timestamp(v833, r"service_notifier_new_server:.*180 service")
    service74_s = timestamp(v833, r"service_notifier_new_server:.*74 service")

    return {
        "v833_dmesg": str(ANDROID_V833_DMESG.relative_to(REPO_ROOT)),
        "service180_s": service180_s,
        "service74_s": service74_s,
        "wlfw_start_s": wlfw_start_s,
        "wlfw_service_request_s": wlfw_request_s,
        "wlan_pd_up_s": wlan_pd_up_s,
        "icnss_qmi_s": icnss_qmi_s,
        "first_bdf_s": first_bdf_s,
        "wlan0_s": wlan0_s,
        "service180_to_wlfw_start_ms": delta_ms(service180_s, wlfw_start_s),
        "wlfw_request_to_wlan_pd_up_ms": delta_ms(wlfw_request_s, wlan_pd_up_s),
        "wlan_pd_up_to_icnss_qmi_ms": delta_ms(wlan_pd_up_s, icnss_qmi_s),
        "icnss_qmi_to_bdf_ms": delta_ms(icnss_qmi_s, first_bdf_s),
        "v1331_first_markers": v1331.get("first_markers", {}),
        "v1331_service_props": {
            key: v1331.get("props", {}).get(key)
            for key in (
                "init.svc.vendor.qrtr-ns",
                "init.svc.vendor.rmt_storage",
                "init.svc.vendor.tftp_server",
                "init.svc.vendor.pd_mapper",
                "init.svc.cnss_diag",
                "init.svc.cnss-daemon",
                "ro.boottime.vendor.qrtr-ns",
                "ro.boottime.vendor.rmt_storage",
                "ro.boottime.vendor.tftp_server",
                "ro.boottime.vendor.pd_mapper",
                "ro.boottime.cnss_diag",
                "ro.boottime.cnss-daemon",
            )
        },
        "v1555_reaches_wlan0": boolish(v1555.get("pass")),
        "v1555_first_wlan0_s": v1555.get("analysis", {}).get("wlan0_time"),
    }


def native_reference() -> dict[str, Any]:
    v1680 = load_json(V1680_MANIFEST)
    v1727 = load_json(V1727_MANIFEST)
    v1731 = load_json(V1731_MANIFEST)
    v1732 = load_json(V1732_MANIFEST)
    v1680_kv = parse_kv(read_text(V1680_HELPER))
    v1731_kv = parse_kv(read_text(V1731_HELPER))
    v1731_dmesg = read_text(V1731_DMESG)
    gate1731 = v1731.get("gate", {})
    gate1680 = v1680.get("gate", {})
    gate1727 = v1727.get("gate", {})

    return {
        "v1680_decision": v1680.get("decision"),
        "v1680_label": gate1680.get("label"),
        "v1680_tftp_running": gate1680.get("tftp_running"),
        "v1680_requested_wlanmdsp": gate1680.get("requested_wlanmdsp"),
        "v1680_requested_modem": gate1680.get("requested_modem"),
        "v1680_served_wlanmdsp_nonzero": gate1680.get("served_wlanmdsp_nonzero"),
        "v1680_served_modem_mdt_nonzero": gate1680.get("served_modem_mdt_nonzero"),
        "v1680_served_modem_blob_nonzero": gate1680.get("served_modem_blob_nonzero"),
        "v1680_helper_served_wlanmdsp_nonzero": v1680_kv.get("wlan_pd_firmware_serve_gate.served_wlanmdsp_nonzero"),
        "v1680_helper_snapshot_wlanmdsp_paths": {
            key: value
            for key, value in v1680_kv.items()
            if key.endswith(".file.wlanmdsp_mbn.path") or key.endswith(".file.wlanmdsp_mbn.nonzero")
        },
        "v1727_decision": v1727.get("decision"),
        "v1727_service_window_label": gate1727.get("service_window_label"),
        "v1727_nonlog_label": gate1727.get("nonlog_label"),
        "v1727_wlfw_start_hits": gate1727.get("wlfw_start_hit_count"),
        "v1727_wlfw_request_hits": gate1727.get("wlfw_service_request_hit_count"),
        "v1727_worker_success_hits": gate1727.get("wlfw_worker_create_success_hit_count"),
        "v1731_wlfw_start_hits": gate1731.get("wlfw_start_hit_count"),
        "v1731_wlfw_request_hits": gate1731.get("wlfw_service_request_hit_count"),
        "v1731_worker_success_hits": gate1731.get("wlfw_worker_create_success_hit_count"),
        "v1731_decision": v1731.get("decision"),
        "v1731_service_window_label": gate1731.get("service_window_label"),
        "v1731_nonlog_label": gate1731.get("nonlog_label"),
        "v1731_late_endpoint_result": gate1731.get("late_endpoint_result"),
        "v1731_late_endpoint_node": gate1731.get("late_endpoint_node"),
        "v1731_late_endpoint_port": gate1731.get("late_endpoint_port"),
        "v1731_late_listener_result": gate1731.get("late_listener_result"),
        "v1731_late_listener_state": gate1731.get("late_listener_response_state"),
        "v1731_late_listener_state_name": gate1731.get("late_listener_response_state_name"),
        "v1731_late_indication_seen": gate1731.get("late_listener_indication_seen"),
        "v1731_hold_ms": gate1731.get("late_listener_hold_ms"),
        "v1731_wlfw_service69_seen": gate1731.get("wlfw_service69_seen"),
        "v1731_requested_wlanmdsp": gate1731.get("requested_wlanmdsp"),
        "v1731_no_esoc0": gate1731.get("no_esoc0"),
        "v1731_no_forced_rc1": gate1731.get("no_forced_rc1"),
        "v1731_no_scan_connect": gate1731.get("no_scan_connect"),
        "v1731_no_credentials": gate1731.get("no_credentials"),
        "v1731_old_firmware_serve_label": gate1731.get("old_firmware_serve_label"),
        "v1731_modem_loading_s": timestamp(v1731_dmesg, r"modem:\s*loading"),
        "v1731_modem_reset_s": timestamp(v1731_dmesg, r"modem:\s*Brought out of reset"),
        "v1731_qrtr_rx_s": timestamp(v1731_dmesg, r"qrtr:\s*Modem QMI Readiness RX"),
        "v1731_rmt_storage_open_count": count_ci(v1731_dmesg, r"rmt_storage_open_cb: Processing: Open Request"),
        "v1731_service_notifier_180_dmesg_count": count_ci(v1731_dmesg, r"service_notifier_new_server:.*180 service"),
        "v1731_helper_request_wlanmdsp": v1731_kv.get("wlan_pd_service_window_trigger.requested_wlanmdsp")
        or v1731_kv.get("wlan_pd_firmware_serve_gate.requested_wlanmdsp"),
        "v1732_label": v1732.get("label"),
        "v1732_missing_surface": v1732.get("missing_surface"),
    }


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android_good"]
    native = manifest["native"]
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1734 WLAN-PD UP Delta Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1734`",
            "- Type: host-only Android-good/native delta classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            "- Evidence: `tmp/wifi/v1734-wlan-pd-up-delta-classifier`",
            "",
            "## Android-good Reference",
            "",
            f"- service-notifier 180 server: `{android['service180_s']}` s",
            f"- `wlfw_start`: `{android['wlfw_start_s']}` s",
            f"- `wlfw_service_request`: `{android['wlfw_service_request_s']}` s",
            f"- WLAN-PD UP indication: `{android['wlan_pd_up_s']}` s",
            f"- ICNSS QMI connected: `{android['icnss_qmi_s']}` s",
            f"- first BDF request: `{android['first_bdf_s']}` s",
            f"- `wlan0`: `{android['wlan0_s']}` s",
            f"- service180-to-`wlfw_start`: `{android['service180_to_wlfw_start_ms']}` ms",
            f"- `wlfw_service_request`-to-WLAN-PD-UP: `{android['wlfw_request_to_wlan_pd_up_ms']}` ms",
            f"- WLAN-PD-UP-to-ICNSS-QMI: `{android['wlan_pd_up_to_icnss_qmi_ms']}` ms",
            "",
            "## Native Current Delta",
            "",
            f"- V1732 fixed label: `{native['v1732_label']}`",
            f"- V1732 missing surface: `{native['v1732_missing_surface']}`",
            f"- V1727 non-log label: `{native['v1727_nonlog_label']}`",
            f"- V1727 `wlfw_start` / `wlfw_service_request` / worker hits: `{native['v1727_wlfw_start_hits']}` / `{native['v1727_wlfw_request_hits']}` / `{native['v1727_worker_success_hits']}`",
            f"- V1731 `wlfw_start` / `wlfw_service_request` / worker hits: `{native['v1731_wlfw_start_hits']}` / `{native['v1731_wlfw_request_hits']}` / `{native['v1731_worker_success_hits']}`",
            f"- V1731 late listener endpoint: `{native['v1731_late_endpoint_result']}` node `{native['v1731_late_endpoint_node']}` port `{native['v1731_late_endpoint_port']}`",
            f"- V1731 late listener state: `{native['v1731_late_listener_state']}` / `{native['v1731_late_listener_state_name']}`",
            f"- V1731 indication seen: `{native['v1731_late_indication_seen']}` after `{native['v1731_hold_ms']}` ms hold",
            f"- V1731 WLFW service 69: `{native['v1731_wlfw_service69_seen']}`",
            f"- V1731 requested `wlanmdsp`: `{native['v1731_requested_wlanmdsp']}`",
            f"- V1680 firmware-serve label: `{native['v1680_label']}`",
            f"- V1680 tftp running / requested `wlanmdsp` / served `wlanmdsp`: `{native['v1680_tftp_running']}` / `{native['v1680_requested_wlanmdsp']}` / `{native['v1680_served_wlanmdsp_nonzero']}`",
            f"- V1731 modem reset / QRTR RX: `{native['v1731_modem_reset_s']}` s / `{native['v1731_qrtr_rx_s']}` s",
            f"- V1731 rmt_storage open count: `{native['v1731_rmt_storage_open_count']}`",
            "",
            "## Classification",
            "",
            f"- Label: `{manifest['label']}`",
            f"- Next gate: `{manifest['next_gate']}`",
            "",
            "Android-good reaches WLAN-PD UP about one second after `cnss-daemon` starts `wlfw_service_request`. Native reaches the same CNSS worker and brings the internal modem out of reset, but the late service-notifier listener still reports WLAN-PD `UNINIT`, no indication, no WLFW service 69, and no `wlanmdsp` request. V1680 also showed the firmware-serve route running but `firmware-not-requested` and no nonzero `wlanmdsp` at the observed served path. The remaining useful work is therefore an exact internal-modem PD-start observer, not another CNSS output, PM/service-window, `boot_wlan`, restart-PD, or eSoC/RC1 gate.",
            "",
            "## Next Gate Contract",
            "",
            "- Source/build-only first: add a timestamped internal-modem WLAN-PD observer that reuses the V1731 route and records the exact sequence around modem reset, service-notifier endpoint publication, `wlfw_service_request`, tftp/rmt activity, firmware path visibility, WLFW service 69, and WLAN-PD listener state.",
            "- Live gate after source sanity: one rollbackable read-only run, no new actors, no active PD restart request, and no Wi-Fi HAL/scan/connect.",
            "- Fixed labels: `pd-start-trigger-absent`, `pd-firmware-path-invisible`, `pd-state-up-service69`, `pd-state-up-no-service69`, `route-regression`.",
            "- Stop after one label. Do not spin timing variants or add PM/QCACLD/eSoC actors from this result.",
            "",
            "## Checks",
            "",
            checks,
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start service-manager/PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1734 WLAN-PD UP delta classifier (2026-06-03)",
            "",
            "- V1734 host-only Android-good/native delta classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - label: `{manifest['label']}`;",
            f"  - next gate: `{manifest['next_gate']}`;",
            "  - Android-good reaches WLAN-PD UP shortly after `wlfw_service_request`, then ICNSS QMI, BDF, and `wlan0`;",
            "  - native V1731 reaches `wlfw_start` / `wlfw_service_request` and internal modem reset/QRTR, but WLAN-PD remains `UNINIT`, with no indication, no WLFW service 69, and no `wlanmdsp` request;",
            "  - V1680/V1731 firmware-serve evidence still labels the path `firmware-not-requested`; the next unit must observe the exact modem-side PD-start sequence rather than add actors.",
            "",
            "  Next candidate:",
            "",
            "  - V1735 source/build-only timestamped internal-modem WLAN-PD observer reusing the V1731 route;",
            "  - V1736 one rollbackable read-only live run only after V1735 sanity;",
            "  - forbidden: PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1734_WLAN_PD_UP_DELTA_CLASSIFIER_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    heading = "## V1734 WLAN-PD UP delta classifier"
    if heading in current:
        pattern = re.compile(
            r"\n## V1734 WLAN-PD UP delta classifier \(2026-06-03\)\n.*?(?=\n## |\Z)",
            re.S,
        )
        updated = pattern.sub(entry, current.rstrip())
        NEXT_WORK_PATH.write_text(updated.rstrip() + "\n", encoding="utf-8")
    else:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    android = android_reference()
    native = native_reference()
    checks = {
        "android_stateup_chain_present": all(
            android[key] is not None
            for key in ("wlfw_service_request_s", "wlan_pd_up_s", "icnss_qmi_s", "first_bdf_s", "wlan0_s")
        ),
        "android_service180_precedes_wlfw_start": android["service180_s"] is not None
        and android["wlfw_start_s"] is not None
        and android["service180_s"] < android["wlfw_start_s"],
        "native_cnss_worker_reached": (
            intish(native["v1727_wlfw_start_hits"]) > 0
            and intish(native["v1727_wlfw_request_hits"]) > 0
        )
        or (
            intish(native["v1731_wlfw_start_hits"]) > 0
            and intish(native["v1731_wlfw_request_hits"]) > 0
            and intish(native["v1731_worker_success_hits"]) > 0
        ),
        "native_late_listener_uninit": native["v1731_late_listener_state_name"] == "uninit",
        "native_no_late_indication": intish(native["v1731_late_indication_seen"]) == 0,
        "native_no_wlfw69": intish(native["v1731_wlfw_service69_seen"]) == 0,
        "native_no_wlanmdsp_request": intish(native["v1731_requested_wlanmdsp"]) == 0,
        "native_modem_reset_and_qrtr_seen": native["v1731_modem_reset_s"] is not None
        and native["v1731_qrtr_rx_s"] is not None,
        "firmware_serve_route_not_requested": native["v1680_label"] == "firmware-not-requested",
        "served_wlanmdsp_not_nonzero_in_v1680": intish(native["v1680_served_wlanmdsp_nonzero"]) == 0,
        "hard_stops_preserved": all(
            intish(native[key]) == 1
            for key in ("v1731_no_esoc0", "v1731_no_forced_rc1", "v1731_no_scan_connect", "v1731_no_credentials")
        ),
    }
    pass_ok = all(checks.values())
    manifest = {
        "cycle": "V1734",
        "decision": "v1734-wlan-pd-up-delta-modem-pd-start-gap-pass"
        if pass_ok
        else "v1734-wlan-pd-up-delta-classifier-incomplete",
        "pass": pass_ok,
        "label": "modem-side-wlan-pd-start-gap" if pass_ok else "host-evidence-incomplete",
        "next_gate": "V1735 source-build timestamped internal-modem WLAN-PD observer; V1736 one-run read-only live"
        if pass_ok
        else "refresh missing host evidence",
        "android_good": android,
        "native": native,
        "checks": checks,
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
