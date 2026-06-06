#!/usr/bin/env python3
"""V1938 host-only WLAN-PD state-up before WLFW-arrive classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1938"
OUT_DIR = repo_path("tmp/wifi/v1938-wlan-pd-stateup-before-wlfw-arrive")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1938_WLAN_PD_STATEUP_BEFORE_WLFW_ARRIVE_2026-06-04.md")

ANDROID_V1917 = repo_path("tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff/manifest.json")
ANDROID_V1934 = repo_path("tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/manifest.json")
NATIVE_V1937 = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json")
NATIVE_V1937_INNER = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/manifest.json")
SOURCE_ROOT = repo_path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
ICNSS = SOURCE_ROOT / "drivers/soc/qcom/icnss.c"
ICNSS_QMI = SOURCE_ROOT / "drivers/soc/qcom/icnss_qmi.c"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "present"}


def positive_count_list(value: object) -> bool:
    return any(intish(part.strip()) > 0 for part in str(value or "").split(",") if part.strip())


def source_line(path: Path, pattern: str) -> dict[str, Any]:
    text = read_text(path)
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return {"path": rel(path), "line": index, "text": line.strip()}
    return {"path": rel(path), "line": None, "text": ""}


def android_summary() -> dict[str, Any]:
    v1917 = load_json(ANDROID_V1917)
    v1934 = load_json(ANDROID_V1934)
    analysis = ((v1917.get("context") or {}).get("analysis") or {})
    return {
        "v1917_manifest": rel(ANDROID_V1917),
        "v1934_manifest": rel(ANDROID_V1934),
        "v1917_pass": bool(v1917.get("pass")),
        "v1934_pass": bool(v1934.get("pass")),
        "service74": intish(analysis.get("service74_count")) > 0,
        "service180": intish(analysis.get("service180_count")) > 0,
        "wlan_pd_stateup": boolish(analysis.get("android_service_notifier_stateup")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "first_wlan_pd_line": analysis.get("first_wlan_pd_line", ""),
        "label_v1917": v1917.get("label", ""),
        "label_v1934": v1934.get("label", ""),
    }


def native_summary() -> dict[str, Any]:
    outer = load_json(NATIVE_V1937)
    inner = load_json(NATIVE_V1937_INNER)
    details = outer.get("details") if isinstance(outer.get("details"), dict) else {}
    ipc = details.get("icnss_ipc") if isinstance(details.get("icnss_ipc"), dict) else {}
    gate = inner.get("gate") if isinstance(inner.get("gate"), dict) else {}
    classification = outer.get("classification") if isinstance(outer.get("classification"), dict) else {}
    return {
        "outer_manifest": rel(NATIVE_V1937),
        "inner_manifest": rel(NATIVE_V1937_INNER),
        "outer_pass": bool(outer.get("pass")),
        "outer_label": outer.get("label", ""),
        "base_label": classification.get("base_label", ""),
        "service74": boolish(details.get("service74")),
        "service180": boolish(details.get("service180")),
        "pm_open_subsys_modem": boolish(details.get("pm_open_subsys_modem")),
        "holder_opened": boolish(details.get("holder_opened")),
        "icnss_get_service_notify": boolish(ipc.get("get_service_notify_seen")),
        "icnss_wlan_pd_domain": boolish(ipc.get("wlan_pd_domain_seen")),
        "icnss_pd_registration": boolish(ipc.get("pd_notification_registration_seen")),
        "icnss_wlfw_server_arrive": boolish(ipc.get("wlfw_server_arrive_seen")),
        "servnotif_late_state": details.get("servnotif_late_state", ""),
        "servnotif_late_indication": intish(details.get("servnotif_late_indication")),
        "raw_wlan_pd_text": gate.get("raw_wlan_pd_text_counts", ""),
        "raw_wlan_pd_text_positive": boolish(gate.get("raw_wlan_pd_text_positive")),
        "service_notifier_still_uninit": boolish(gate.get("service_notifier_still_uninit")),
        "libqmi_lookup_service69": boolish(details.get("libqmi_lookup_service69_seen")),
        "libqmi_wait_outstanding": boolish(details.get("libqmi_wlfw_wait_outstanding")),
        "libqmi_wait_return": boolish(details.get("libqmi_wlfw_wait_return_seen")),
        "libqmi_new_server69": boolish(details.get("libqmi_new_server_service69_seen")),
        "wlfw69": boolish(details.get("wlfw69")),
        "wlan_pd": boolish(details.get("wlan_pd")),
        "wlanmdsp": boolish(details.get("wlanmdsp")),
        "wlan0": boolish(details.get("wlan0")),
    }


def source_summary() -> dict[str, Any]:
    return {
        "icnss_get_service_location": source_line(ICNSS, r"get_service_location\(ICNSS_SERVICE_LOCATION_CLIENT_NAME"),
        "icnss_pd_registration_log": source_line(ICNSS, r"PD notification registration happened"),
        "icnss_pd_restart": source_line(ICNSS, r"service_notif_pd_restart"),
        "icnss_qmi_wlfw_new_server": source_line(ICNSS_QMI, r"static int wlfw_new_server"),
        "icnss_qmi_wlfw_arrive_log": source_line(ICNSS_QMI, r"WLFW server arrive"),
        "icnss_qmi_event_post": source_line(ICNSS_QMI, r"ICNSS_DRIVER_EVENT_SERVER_ARRIVE"),
        "icnss_qmi_add_lookup": source_line(ICNSS_QMI, r"qmi_add_lookup\(&priv->qmi, WLFW_SERVICE_ID_V01"),
    }


def classify(android: dict[str, Any],
             native: dict[str, Any],
             source: dict[str, Any]) -> dict[str, Any]:
    android_positive = (
        android["v1917_pass"]
        and android["v1934_pass"]
        and android["service74"]
        and android["service180"]
        and android["wlan_pd_stateup"]
    )
    native_registered = (
        native["outer_pass"]
        and native["service74"]
        and native["service180"]
        and native["pm_open_subsys_modem"]
        and native["holder_opened"]
        and native["icnss_get_service_notify"]
        and native["icnss_wlan_pd_domain"]
        and native["icnss_pd_registration"]
    )
    native_no_stateup = (
        native["servnotif_late_state"] == "uninit"
        and native["servnotif_late_indication"] == 0
        and not positive_count_list(native["raw_wlan_pd_text"])
        and native["service_notifier_still_uninit"]
    )
    native_no_wlfw = (
        native["libqmi_lookup_service69"]
        and native["libqmi_wait_outstanding"]
        and not native["libqmi_wait_return"]
        and not native["libqmi_new_server69"]
        and not native["icnss_wlfw_server_arrive"]
        and not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
    )
    source_passive = (
        source["icnss_qmi_add_lookup"]["line"] is not None
        and source["icnss_qmi_wlfw_new_server"]["line"] is not None
        and source["icnss_qmi_event_post"]["line"] is not None
        and source["icnss_pd_restart"]["line"] is not None
    )
    if android_positive and native_registered and native_no_stateup and native_no_wlfw and source_passive:
        label = "wlan-pd-stateup-missing-before-wlfw-arrive"
        reason = "Android advances from ICNSS PD registration to WLAN-PD state-up and WLFW service69 arrival; native reaches PD registration but service-notifier remains UNINIT and no WLFW arrive/new-server69 occurs"
        passed = True
    elif native_registered and native_no_wlfw:
        label = "post-pd-registration-no-wlfw-arrive-review"
        reason = "native reaches ICNSS PD registration and still lacks WLFW arrival, but Android/source comparator coverage is incomplete"
        passed = False
    else:
        label = "wlan-pd-stateup-classifier-incomplete"
        reason = "required Android-positive or native-post-registration evidence is missing"
        passed = False
    return {
        "label": label,
        "decision": f"v1938-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_positive": android_positive,
        "native_registered": native_registered,
        "native_no_stateup": native_no_stateup,
        "native_no_wlfw": native_no_wlfw,
        "source_passive": source_passive,
    }


def render_source_rows(source: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, item in source.items():
        rows.append([name, item["path"], str(item["line"]), item["text"]])
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    source = manifest["source"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["Android positive", classification["android_positive"], f"stateup={android['wlan_pd_stateup']} indications={android['wlan_pd_indication_count']} v1934={android['label_v1934']}"],
        ["Native PD registration", classification["native_registered"], f"notify={native['icnss_get_service_notify']} pd_domain={native['icnss_wlan_pd_domain']} reg={native['icnss_pd_registration']}"],
        ["Native state-up", not classification["native_no_stateup"], f"late_state={native['servnotif_late_state']} indication={native['servnotif_late_indication']} raw_wlan_pd={native['raw_wlan_pd_text']}"],
        ["Native WLFW", not classification["native_no_wlfw"], f"lookup69={native['libqmi_lookup_service69']} wait={native['libqmi_wait_outstanding']} arrive={native['icnss_wlfw_server_arrive']} wlan0={native['wlan0']}"],
        ["Source passive", classification["source_passive"], "WLFW server arrive is qmi_add_lookup callback; restart-PD exists but remains out of scope"],
    ]
    return "\n".join([
        "# Native Init V1938 WLAN-PD State-up Before WLFW Arrive",
        "",
        "## Summary",
        "",
        "- Cycle: `V1938`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "path", "line", "text"], render_source_rows(source)),
        "",
        "## Interpretation",
        "",
        "- Native already reaches the AP-side ICNSS service-location/domain-list path and registers for `msm/modem/wlan_pd` notifications.",
        "- The missing edge before WLFW service69 is the remote WLAN-PD state-up indication; without that, `wlfw_new_server` never posts `SERVER_ARRIVE` and `cnss-daemon` stays in the service69 wait.",
        "- The next live unit should observe remote WLAN-PD state-up inputs only: service-notifier response/indication payload timing, SSCTL/sysmon state for modem child PDs, and relevant RFS/tftp/rmtfs reads. It must not call `service_notif_pd_restart`, start HAL, scan/connect, use credentials, or touch eSoC/PCIe/GDSC.",
        "",
        "## Inputs",
        "",
        f"- Android V1917: `{android['v1917_manifest']}`",
        f"- Android V1934: `{android['v1934_manifest']}`",
        f"- Native V1937: `{native['outer_manifest']}`",
        f"- Native inner: `{native['inner_manifest']}`",
        "",
        "## Safety Scope",
        "",
        "Host-only classifier. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "",
    ])


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    android = android_summary()
    native = native_summary()
    source = source_summary()
    classification = classify(android, native, source)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "classification": classification,
        "android": android,
        "native": native,
        "source": source,
        "host_metadata": collect_host_metadata(),
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"{'PASS' if manifest['pass'] else 'BLOCKED'} label={manifest['label']} out_dir={manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
