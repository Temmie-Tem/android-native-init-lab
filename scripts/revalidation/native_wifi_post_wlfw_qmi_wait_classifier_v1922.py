#!/usr/bin/env python3
"""V1922 host-only post-WLFW QMI wait classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1922"
OUT_DIR = repo_path("tmp/wifi/v1922-post-wlfw-qmi-wait")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1922_POST_WLFW_QMI_WAIT_2026-06-04.md")

ANDROID_DMESG = {
    "v1899": repo_path("tmp/wifi/v1899-android-cnss-qrtr-stateup-live-20260603-195822/android-postfs-evidence/a90-v1899-cnss-qrtr/dmesg-filtered.txt"),
    "v1909": repo_path("tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346/android-postfs-evidence/a90-v1909-servloc-domain/dmesg-filtered.txt"),
}
ANDROID_LOGCAT = {
    "v1753": repo_path("tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq/logcat-filtered.txt"),
}
NATIVE_V1920_MANIFEST = repo_path("tmp/wifi/v1920-clean-dsp-pm-open-integration/manifest.json")
NATIVE_V1920_INNER = repo_path("tmp/wifi/v1920-clean-dsp-pm-open-integration/v1847-handoff/manifest.json")
NATIVE_V1920_HELPER = repo_path("tmp/wifi/v1920-clean-dsp-pm-open-integration/v1847-handoff/test-v1393-helper-result.stdout.txt")

TIME_RE = re.compile(r"\[\s*(\d+\.\d+)\]")
HELPER_TRACE_TIME_RE = re.compile(r"\s(\d+\.\d+):\s")
ANDROID_PATTERNS = {
    "service74": re.compile(r"service_notifier_new_server:.*\b74 service\b", re.IGNORECASE),
    "service180": re.compile(r"service_notifier_new_server:.*\b180 service\b", re.IGNORECASE),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE),
    "wlfw_request": re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE),
    "wlan_pd": re.compile(r"root_service_service_ind_cb: Indication received from msm/modem/wlan_pd", re.IGNORECASE),
    "qmi_server": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "wlanmdsp": re.compile(r"wlanmdsp\.mbn", re.IGNORECASE),
    "fw_ready": re.compile(r"WLAN FW is ready", re.IGNORECASE),
    "wlan0": re.compile(r"\bwlan0\b", re.IGNORECASE),
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_kv_text(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in read_text(path).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "present"}


def first_marker(text: str, pattern: re.Pattern[str]) -> dict[str, Any]:
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not pattern.search(line):
            continue
        match = TIME_RE.search(line)
        return {
            "present": True,
            "line_no": line_no,
            "time": float(match.group(1)) if match else None,
            "line": line.strip()[:500],
        }
    return {"present": False, "line_no": None, "time": None, "line": ""}


def parse_android_path(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return {
        "path": rel(path),
        "exists": path.exists(),
        "line_count": len(text.splitlines()),
        "markers": {name: first_marker(text, pattern) for name, pattern in ANDROID_PATTERNS.items()},
    }


def any_android_marker(timelines: list[dict[str, Any]], marker: str) -> bool:
    return any(item["markers"][marker]["present"] for item in timelines)


def helper_hit(fields: dict[str, str], name: str) -> int:
    return intish(fields.get(f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}.hit_count"))


def helper_first_line(fields: dict[str, str], name: str) -> str:
    return fields.get(f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}.first_hit_line", "")


def helper_first_time(fields: dict[str, str], name: str) -> float | None:
    match = HELPER_TRACE_TIME_RE.search(helper_first_line(fields, name))
    return float(match.group(1)) if match else None


def positive_count_list(value: object) -> bool:
    return any(intish(part.strip()) > 0 for part in str(value or "").split(",") if part.strip())


def native_summary() -> dict[str, Any]:
    outer = load_json(NATIVE_V1920_MANIFEST)
    inner = load_json(NATIVE_V1920_INNER)
    classification = outer.get("classification") if isinstance(outer.get("classification"), dict) else {}
    gate = inner.get("gate") if isinstance(inner.get("gate"), dict) else {}
    fields = parse_kv_text(NATIVE_V1920_HELPER)
    pm_open = (
        classification.get("open_context_path") == "/dev/subsys_modem"
        and intish(classification.get("open_context_fd")) >= 0
    ) or (
        gate.get("open_context_path") == "/dev/subsys_modem"
        and intish(gate.get("open_context_fd")) >= 0
    )
    wlfw_start = boolish(fields.get("wlan_pd_service_window_trigger.wlfw_start_seen")) or helper_hit(fields, "wlfw_start") > 0
    wlfw_request = boolish(fields.get("wlan_pd_service_window_trigger.wlfw_service_request_seen")) or helper_hit(fields, "wlfw_service_request") > 0
    wlfw_worker = helper_hit(fields, "wlfw_worker_pthread_create_success") > 0
    ind_qmi = helper_hit(fields, "wlfw_ind_register_qmi") > 0
    cap_qmi = helper_hit(fields, "wlfw_cap_qmi") > 0
    holder_started = boolish(fields.get("wlan_pd_modem_holder.start_attempted"))
    holder_opened = boolish(fields.get("wlan_pd_modem_holder.opened"))
    service74 = boolish(classification.get("service74")) or positive_count_list(classification.get("raw_service74_text_counts"))
    service180 = boolish(classification.get("service180")) or positive_count_list(classification.get("raw_service180_text_counts"))
    wlan_pd = positive_count_list(gate.get("raw_wlan_pd_text_counts")) or boolish(classification.get("wlan_pd"))
    wlanmdsp = intish(fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp")) > 0 or boolish(classification.get("wlanmdsp"))
    wlfw69 = intish(fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen")) > 0 or boolish(classification.get("wlfw69"))
    return {
        "outer_manifest": rel(NATIVE_V1920_MANIFEST),
        "inner_manifest": rel(NATIVE_V1920_INNER),
        "helper_result": rel(NATIVE_V1920_HELPER),
        "outer_label": outer.get("label", ""),
        "inner_label": inner.get("label", ""),
        "order": fields.get("wifi_companion_start.order", ""),
        "child_started": fields.get("wifi_companion_start.child_started", ""),
        "service74": service74,
        "service180": service180,
        "pm_open_subsys_modem": pm_open,
        "open_context_path": classification.get("open_context_path") or gate.get("open_context_path", ""),
        "open_context_fd": classification.get("open_context_fd") or gate.get("open_context_fd", ""),
        "holder_started": holder_started,
        "holder_opened": holder_opened,
        "holder_fd": fields.get("wlan_pd_modem_holder.fd", ""),
        "holder_postflight_safe": boolish(fields.get("wlan_pd_modem_holder.postflight_safe")),
        "wlfw_start": wlfw_start,
        "wlfw_request": wlfw_request,
        "wlfw_worker": wlfw_worker,
        "wlfw_ind_register_qmi": ind_qmi,
        "wlfw_cap_qmi": cap_qmi,
        "wlfw_start_time": helper_first_time(fields, "wlfw_start"),
        "wlfw_request_time": helper_first_time(fields, "wlfw_service_request"),
        "wlfw_worker_time": helper_first_time(fields, "wlfw_worker_pthread_create_success"),
        "wlfw_ind_register_qmi_time": helper_first_time(fields, "wlfw_ind_register_qmi"),
        "wlfw_cap_qmi_time": helper_first_time(fields, "wlfw_cap_qmi"),
        "wlfw_start_line": helper_first_line(fields, "wlfw_start"),
        "wlfw_request_line": helper_first_line(fields, "wlfw_service_request"),
        "wlfw_worker_line": helper_first_line(fields, "wlfw_worker_pthread_create_success"),
        "wlfw_ind_register_qmi_line": helper_first_line(fields, "wlfw_ind_register_qmi"),
        "wlfw_cap_qmi_line": helper_first_line(fields, "wlfw_cap_qmi"),
        "wlfw_nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "service_window_label": fields.get("wlan_pd_service_window_trigger.label", ""),
        "service_object_label": fields.get("wlan_pd_service_object_visible_trigger.label", ""),
        "servnotif_late_state": fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name", ""),
        "servnotif_late_indication": fields.get("wifi_companion_service_notifier_late_listener.indication_seen", ""),
        "servloc_result": fields.get("wifi_companion_servloc_domain_list.result", ""),
        "qrtr_readback_result": fields.get("wifi_companion_qrtr_readback.result", ""),
        "wlfw69": wlfw69,
        "wlan_pd": wlan_pd,
        "wlanmdsp": wlanmdsp,
        "wlan0": boolish(classification.get("wlan0")) or boolish(gate.get("lower_wlan0_present")),
    }


def android_summary() -> dict[str, Any]:
    dmesg = {name: parse_android_path(path) for name, path in ANDROID_DMESG.items()}
    logcat = {name: parse_android_path(path) for name, path in ANDROID_LOGCAT.items()}
    timelines = list(dmesg.values()) + list(logcat.values())
    return {
        "dmesg": dmesg,
        "logcat": logcat,
        "service74": any_android_marker(timelines, "service74"),
        "service180": any_android_marker(timelines, "service180"),
        "wlfw_start": any_android_marker(timelines, "wlfw_start"),
        "wlfw_request": any_android_marker(timelines, "wlfw_request"),
        "wlan_pd": any_android_marker(timelines, "wlan_pd"),
        "qmi_server": any_android_marker(timelines, "qmi_server"),
        "wlanmdsp": any_android_marker(timelines, "wlanmdsp"),
        "fw_ready": any_android_marker(timelines, "fw_ready"),
        "wlan0": any_android_marker(timelines, "wlan0"),
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    android_full = (
        android["service74"]
        and android["service180"]
        and android["wlfw_start"]
        and android["wlfw_request"]
        and android["wlan_pd"]
        and android["qmi_server"]
        and android["wlanmdsp"]
        and android["wlan0"]
    )
    native_combined = (
        native["service74"]
        and native["service180"]
        and native["pm_open_subsys_modem"]
        and native["holder_opened"]
        and native["wlfw_start"]
        and native["wlfw_request"]
        and native["wlfw_worker"]
    )
    native_post_wlfw_block = (
        not native["wlfw_ind_register_qmi"]
        and not native["wlfw_cap_qmi"]
        and not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
    )
    if android_full and native_combined and native_post_wlfw_block:
        label = "service74-pm-open-holder-wlfw-worker-qmi-service-wait"
        reason = "native V1920 has service74/service180, PM /dev/subsys_modem open, holder open, and WLFW worker creation, but the worker waits before WLFW indication/capability QMI and Android advances to wlan_pd/wlanmdsp/wlan0"
    elif android_full and native_combined:
        label = "post-wlfw-progress-review"
        reason = "native reaches the combined post-WLFW surface but some lower marker progressed or needs manual review"
    elif android_full:
        label = "combined-prereq-regressed"
        reason = "native evidence no longer proves service74/service180 plus PM open plus holder open plus WLFW worker"
    else:
        label = "android-baseline-incomplete"
        reason = "normal Android baseline does not prove the full internal WLAN-PD chain from retained captures"
    return {
        "label": label,
        "decision": f"v1922-{label}-host-pass",
        "pass": label != "android-baseline-incomplete",
        "reason": reason,
        "android_full": android_full,
        "native_combined": native_combined,
        "native_post_wlfw_block": native_post_wlfw_block,
    }


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    classification = manifest["classification"]
    rows = [
        ["label", classification["label"], classification["reason"]],
        ["Android full", android["wlfw_request"], f"wlan_pd={android['wlan_pd']} wlanmdsp={android['wlanmdsp']} wlan0={android['wlan0']}"],
        ["Native combined", native["wlfw_worker"], f"service74={native['service74']} pm_open={native['pm_open_subsys_modem']} holder={native['holder_opened']}"],
        ["Native post-WLFW", native["wlfw_ind_register_qmi"], f"ind_qmi={native['wlfw_ind_register_qmi']} cap_qmi={native['wlfw_cap_qmi']} wlfw69={native['wlfw69']} wlan_pd={native['wlan_pd']} wlanmdsp={native['wlanmdsp']}"],
    ]
    lines = [
        "# Native Init V1922 Post-WLFW QMI Wait\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Decision: `{classification['decision']}`\n",
        f"- Label: `{classification['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {classification['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n\n",
        "## Matrix\n\n",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "\n\n## Native Edge\n\n",
        f"- Order: `{native['order']}`\n",
        f"- PM open: `{native['open_context_path']}` fd `{native['open_context_fd']}`\n",
        f"- Holder: started/opened/postflight `{native['holder_started']}` / `{native['holder_opened']}` / `{native['holder_postflight_safe']}` fd `{native['holder_fd']}`\n",
        f"- WLFW start/request/worker times: `{native['wlfw_start_time']}` / `{native['wlfw_request_time']}` / `{native['wlfw_worker_time']}`\n",
        f"- WLFW QMI ind/cap: `{native['wlfw_ind_register_qmi']}` / `{native['wlfw_cap_qmi']}`\n",
        f"- Labels: `{native['wlfw_nonlog_label']}` / `{native['service_window_label']}` / `{native['service_object_label']}`\n",
        f"- Late service-notifier state/indication: `{native['servnotif_late_state']}` / `{native['servnotif_late_indication']}`\n\n",
        "## First Native Lines\n\n",
        f"- wlfw_start: `{native['wlfw_start_line']}`\n",
        f"- wlfw_service_request: `{native['wlfw_request_line']}`\n",
        f"- worker_create_success: `{native['wlfw_worker_line']}`\n",
        f"- ind_register_qmi: `{native['wlfw_ind_register_qmi_line']}`\n",
        f"- cap_qmi: `{native['wlfw_cap_qmi_line']}`\n\n",
        "## Interpretation\n\n",
        "- The requested service74 + CNSS worker + PM-service integration is already present in V1920 evidence; the blocker is later than `wlfw_service_request` worker creation.\n",
        "- The next bounded unit should characterize the worker's wait for WLFW QMI service availability versus Android's normal WLFW69/WLAN-PD publication window.\n",
        "- Still no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` control, forced RC1/case, PMIC/GPIO/GDSC/regulator writes, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE.\n",
    ]
    return "".join(lines)


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    store.mkdir("host")
    android = android_summary()
    native = native_summary()
    classification = classify(android, native)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "pass": bool(classification["pass"]),
        "decision": classification["decision"],
        "label": classification["label"],
        "reason": classification["reason"],
        "classification": classification,
        "android": android,
        "native": native,
        "host_metadata": host_metadata,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_report(manifest))
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={manifest['label']} "
        f"native_combined={classification['native_combined']} "
        f"post_wlfw_block={classification['native_post_wlfw_block']} "
        f"out_dir={manifest['out_dir']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
