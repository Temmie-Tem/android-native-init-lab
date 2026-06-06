#!/usr/bin/env python3
"""V1940 host-only post-service180 SERVREG producer-gap classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1940"
OUT_DIR = repo_path("tmp/wifi/v1940-post180-servreg-producer-gap")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1940_POST180_SERVREG_PRODUCER_GAP_2026-06-04.md")

ANDROID_DMESG = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/dmesg-filtered.txt"
)
ANDROID_LOGCAT = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt"
)
NATIVE_DMESG = repo_path(
    "tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/test-v1393-dmesg.stdout.txt"
)
NATIVE_INNER_MANIFEST = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/manifest.json")
NATIVE_V1937_MANIFEST = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json")
V1939_MANIFEST = repo_path("tmp/wifi/v1939-servnotif-root-indication-gap/manifest.json")
V1919_MANIFEST = repo_path("tmp/wifi/v1919-modem-jsn-rfs-gate/manifest.json")

SOURCE_ROOT = repo_path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
SERVICE_NOTIFIER = SOURCE_ROOT / "drivers/soc/qcom/service-notifier.c"
ICNSS = SOURCE_ROOT / "drivers/soc/qcom/icnss.c"


DMESG_PATTERNS = {
    "modem_ssctl": re.compile(r"modem's SSCTL service", re.IGNORECASE),
    "service180": re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE),
    "service74": re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE),
    "wlanpd_ind": re.compile(r"root_service_service_ind_cb: Indication received from msm/modem/wlan_pd", re.IGNORECASE),
    "wlanpd_ack": re.compile(r"send_ind_ack: Indication ACKed .* service msm/modem/wlan_pd, instance 180", re.IGNORECASE),
    "audio_ind": re.compile(r"root_service_service_ind_cb: Indication received from msm/adsp/audio_pd", re.IGNORECASE),
    "audio_ack": re.compile(r"send_ind_ack: Indication ACKed .* service msm/adsp/audio_pd, instance 74", re.IGNORECASE),
    "restart_pd": re.compile(r"Initiate PD restart|service_notif_pd_restart|restart[_ -]?pd", re.IGNORECASE),
}
LOGCAT_PATTERNS = {
    "wlanmdsp": re.compile(r"wlanmdsp\.mbn", re.IGNORECASE),
    "modemuw_jsn": re.compile(r"modemuw\.jsn", re.IGNORECASE),
    "any_jsn": re.compile(r"\.jsn\b", re.IGNORECASE),
    "restart_pd": re.compile(r"service_notif_pd_restart|restart[_ -]?pd|Initiate PD restart", re.IGNORECASE),
}
DMESG_TIME_RE = re.compile(r"^\[\s*(\d+\.\d+)\]")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "present", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def first_line(text: str, pattern: re.Pattern[str]) -> str:
    for line in text.splitlines():
        if pattern.search(line):
            return line
    return ""


def count_lines(text: str, pattern: re.Pattern[str]) -> int:
    return sum(1 for line in text.splitlines() if pattern.search(line))


def line_time(line: str) -> float | None:
    match = DMESG_TIME_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def summarize_dmesg(path: Path) -> dict[str, Any]:
    text = read_text(path)
    counts = {name: count_lines(text, pattern) for name, pattern in DMESG_PATTERNS.items()}
    first = {name: first_line(text, pattern) for name, pattern in DMESG_PATTERNS.items()}
    times = {name: line_time(line) for name, line in first.items()}
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": len(text),
        "counts": counts,
        "first": first,
        "times": times,
    }


def summarize_logcat(path: Path) -> dict[str, Any]:
    text = read_text(path)
    counts = {name: count_lines(text, pattern) for name, pattern in LOGCAT_PATTERNS.items()}
    first = {name: first_line(text, pattern) for name, pattern in LOGCAT_PATTERNS.items()}
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": len(text),
        "counts": counts,
        "first": first,
    }


def source_line(path: Path, pattern: str) -> dict[str, Any]:
    text = read_text(path)
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return {"path": rel(path), "line": index, "text": line.strip()}
    return {"path": rel(path), "line": None, "text": ""}


def source_summary() -> dict[str, Any]:
    return {
        "servreg_ind_handler": source_line(SERVICE_NOTIFIER, r"root_service_service_ind_cb"),
        "servreg_state_updated_msg": source_line(SERVICE_NOTIFIER, r"SERVREG_NOTIF_STATE_UPDATED_IND_MSG"),
        "servreg_ind_log": source_line(SERVICE_NOTIFIER, r"Indication received from %s"),
        "servreg_ack_sender": source_line(SERVICE_NOTIFIER, r"static void send_ind_ack"),
        "servreg_ack_log": source_line(SERVICE_NOTIFIER, r"Indication ACKed for transid"),
        "servreg_new_server": source_line(SERVICE_NOTIFIER, r"static int service_notifier_new_server"),
        "servreg_register_listener": source_line(SERVICE_NOTIFIER, r"register_notif_listener"),
        "icnss_register_notifier": source_line(ICNSS, r"service_notif_register_notifier"),
        "icnss_restart_pd": source_line(ICNSS, r"service_notif_pd_restart"),
    }


def parsed_evidence() -> dict[str, Any]:
    inner = load_json(NATIVE_INNER_MANIFEST)
    native = load_json(NATIVE_V1937_MANIFEST)
    v1939 = load_json(V1939_MANIFEST)
    v1919 = load_json(V1919_MANIFEST)
    inner_gate = inner.get("gate") if isinstance(inner.get("gate"), dict) else {}
    native_details = native.get("details") if isinstance(native.get("details"), dict) else {}
    v1939_class = v1939.get("classification") if isinstance(v1939.get("classification"), dict) else {}
    v1919_android = v1919.get("android") if isinstance(v1919.get("android"), dict) else {}
    return {
        "inner_manifest": rel(NATIVE_INNER_MANIFEST),
        "native_manifest": rel(NATIVE_V1937_MANIFEST),
        "v1939_manifest": rel(V1939_MANIFEST),
        "v1919_manifest": rel(V1919_MANIFEST),
        "native_tftp_running": boolish(inner_gate.get("tftp_running")),
        "native_requested_wlanmdsp": intish(inner_gate.get("requested_wlanmdsp")),
        "native_servnotif_early_state": inner_gate.get("servnotif_early_state", ""),
        "native_servnotif_late_state": inner_gate.get("servnotif_late_listener_state", ""),
        "native_servnotif_late_indication": intish(inner_gate.get("servnotif_late_listener_indication_seen")),
        "native_wlfw69": boolish(native_details.get("wlfw69")),
        "native_wlan_pd": boolish(native_details.get("wlan_pd")),
        "native_wlanmdsp": boolish(native_details.get("wlanmdsp")),
        "native_wlan0": boolish(native_details.get("wlan0")),
        "v1939_pass": bool(v1939.get("pass")),
        "v1939_label": v1939.get("label", ""),
        "v1939_native_missing_wlanpd_ind": boolish(v1939_class.get("native_missing_wlanpd_ind")),
        "android_v1919_no_pre_jsn": intish(v1919_android.get("pre_wlanmdsp_jsn_count")) == 0,
        "android_v1919_no_modemuw": intish(v1919_android.get("pre_wlanmdsp_modemuw_count")) == 0,
        "android_v1919_wlanmdsp_count": intish(v1919_android.get("wlanmdsp_count")),
        "v1919_label": v1919.get("label", ""),
    }


def classify(android_dmesg: dict[str, Any],
             android_logcat: dict[str, Any],
             native_dmesg: dict[str, Any],
             parsed: dict[str, Any],
             source: dict[str, Any]) -> dict[str, Any]:
    android_post180_chain = (
        android_dmesg["counts"]["modem_ssctl"] > 0
        and android_dmesg["counts"]["service180"] > 0
        and android_dmesg["counts"]["wlanpd_ind"] > 0
        and android_dmesg["counts"]["wlanpd_ack"] > 0
        and android_logcat["counts"]["wlanmdsp"] > 0
    )
    android_ind_after_180 = (
        android_dmesg["times"]["service180"] is not None
        and android_dmesg["times"]["wlanpd_ind"] is not None
        and android_dmesg["times"]["wlanpd_ind"] > android_dmesg["times"]["service180"]
    )
    android_no_jsn_or_restart = (
        parsed["android_v1919_no_pre_jsn"]
        and parsed["android_v1919_no_modemuw"]
        and android_dmesg["counts"]["restart_pd"] == 0
        and android_logcat["counts"]["restart_pd"] == 0
    )
    native_same_upstream = (
        native_dmesg["counts"]["modem_ssctl"] > 0
        and native_dmesg["counts"]["service180"] > 0
        and parsed["native_tftp_running"]
    )
    native_missing_producer = (
        parsed["v1939_pass"]
        and parsed["v1939_native_missing_wlanpd_ind"]
        and native_dmesg["counts"]["wlanpd_ind"] == 0
        and native_dmesg["counts"]["wlanpd_ack"] == 0
        and parsed["native_servnotif_early_state"] == "uninit"
        and parsed["native_servnotif_late_state"] == "uninit"
        and parsed["native_servnotif_late_indication"] == 0
    )
    native_no_downstream = (
        parsed["native_requested_wlanmdsp"] == 0
        and not parsed["native_wlfw69"]
        and not parsed["native_wlan_pd"]
        and not parsed["native_wlanmdsp"]
        and not parsed["native_wlan0"]
    )
    source_ok = all(
        source[name]["line"] is not None
        for name in (
            "servreg_ind_handler",
            "servreg_state_updated_msg",
            "servreg_ack_sender",
            "servreg_new_server",
            "icnss_register_notifier",
            "icnss_restart_pd",
        )
    )

    if (
        android_post180_chain
        and android_ind_after_180
        and android_no_jsn_or_restart
        and native_same_upstream
        and native_missing_producer
        and native_no_downstream
        and source_ok
    ):
        label = "post180-remote-servreg-stateup-producer-missing"
        reason = (
            "Android and native both reach modem SSCTL/service180, but only Android later receives "
            "the passive SERVREG state-up indication for msm/modem/wlan_pd instance 180; Android "
            "does so without pre-wlanmdsp JSN or restart-PD evidence, while native has tftp running "
            "but no wlan_pd indication, wlanmdsp request, WLFW69, or wlan0"
        )
        passed = True
    elif native_same_upstream and native_missing_producer and native_no_downstream:
        label = "post180-producer-gap-comparator-incomplete"
        reason = "native reaches service180/tftp and lacks the wlan_pd indication, but Android/source exclusion coverage is incomplete"
        passed = False
    else:
        label = "post180-servreg-producer-classifier-incomplete"
        reason = "required post-service180 chain evidence is missing"
        passed = False

    return {
        "label": label,
        "decision": f"v1940-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_post180_chain": android_post180_chain,
        "android_ind_after_180": android_ind_after_180,
        "android_no_jsn_or_restart": android_no_jsn_or_restart,
        "native_same_upstream": native_same_upstream,
        "native_missing_producer": native_missing_producer,
        "native_no_downstream": native_no_downstream,
        "source_ok": source_ok,
    }


def count_rows(android_dmesg: dict[str, Any],
               android_logcat: dict[str, Any],
               native_dmesg: dict[str, Any],
               parsed: dict[str, Any]) -> list[list[str]]:
    rows = [
        ["modem_ssctl", android_dmesg["counts"]["modem_ssctl"], native_dmesg["counts"]["modem_ssctl"], "same upstream modem SSCTL publication"],
        ["service180", android_dmesg["counts"]["service180"], native_dmesg["counts"]["service180"], "same SERVREG instance 180 server publication"],
        ["service74", android_dmesg["counts"]["service74"], native_dmesg["counts"]["service74"], "sibling clean-DSP path present but not sufficient"],
        ["wlanpd_ind", android_dmesg["counts"]["wlanpd_ind"], native_dmesg["counts"]["wlanpd_ind"], "missing remote WLAN-PD state-up producer edge"],
        ["wlanpd_ack", android_dmesg["counts"]["wlanpd_ack"], native_dmesg["counts"]["wlanpd_ack"], "ACK only follows received state-up indication"],
        ["wlanmdsp_request", android_logcat["counts"]["wlanmdsp"], parsed["native_requested_wlanmdsp"], "downstream firmware request"],
        ["pre_wlanmdsp_jsn", 0, "n/a", f"V1919 label={parsed['v1919_label']}"],
        ["restart_pd_text", android_dmesg["counts"]["restart_pd"] + android_logcat["counts"]["restart_pd"], native_dmesg["counts"]["restart_pd"], "no evidence Android uses forbidden host restart-PD path"],
    ]
    return [[str(cell) for cell in row] for row in rows]


def timing_rows(android_dmesg: dict[str, Any], native_dmesg: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in ("modem_ssctl", "service180", "service74", "wlanpd_ind", "wlanpd_ack", "audio_ind", "audio_ack"):
        rows.append(
            [
                name,
                str(android_dmesg["times"].get(name)),
                str(native_dmesg["times"].get(name)),
                android_dmesg["first"].get(name) or native_dmesg["first"].get(name) or "missing",
            ]
        )
    return rows


def source_rows(source: dict[str, Any]) -> list[list[str]]:
    return [[name, item["path"], str(item["line"]), item["text"]] for name, item in source.items()]


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    android_dmesg = manifest["android_dmesg"]
    android_logcat = manifest["android_logcat"]
    native_dmesg = manifest["native_dmesg"]
    parsed = manifest["parsed"]
    source = manifest["source"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["Android post-180 chain", classification["android_post180_chain"], "modem SSCTL + service180 + wlan_pd indication/ACK + wlanmdsp"],
        ["Android order", classification["android_ind_after_180"], f"service180={android_dmesg['times']['service180']} wlanpd_ind={android_dmesg['times']['wlanpd_ind']}"],
        ["Android exclusions", classification["android_no_jsn_or_restart"], "no pre-wlanmdsp JSN/modemuw and no restart-PD text"],
        ["Native same upstream", classification["native_same_upstream"], f"tftp_running={parsed['native_tftp_running']}"],
        ["Native producer missing", classification["native_missing_producer"], f"early={parsed['native_servnotif_early_state']} late={parsed['native_servnotif_late_state']} ind={parsed['native_servnotif_late_indication']}"],
        ["Native downstream absent", classification["native_no_downstream"], f"requested_wlanmdsp={parsed['native_requested_wlanmdsp']} wlfw69={parsed['native_wlfw69']} wlan0={parsed['native_wlan0']}"],
        ["Source passive path", classification["source_ok"], "SERVREG state-up indication handler plus ACK; restart-PD source exists but is excluded"],
    ]
    return "\n".join(
        [
            "# Native Init V1940 Post-180 SERVREG Producer Gap",
            "",
            "## Summary",
            "",
            "- Cycle: `V1940`",
            "- Type: host-only classifier over existing Android-good/native captures and service-notifier source",
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
            "## Counts",
            "",
            markdown_table(["marker", "Android", "Native", "meaning"], count_rows(android_dmesg, android_logcat, native_dmesg, parsed)),
            "",
            "## Timing",
            "",
            markdown_table(["marker", "Android time", "Native time", "first line"], timing_rows(android_dmesg, native_dmesg)),
            "",
            "## Source Anchors",
            "",
            markdown_table(["anchor", "path", "line", "text"], source_rows(source)),
            "",
            "## Interpretation",
            "",
            "- The normal Android path has modem SSCTL and service180 before the WLAN-PD state indication; native reaches those same upstream publications.",
            "- The missing edge is not service74, modem SSCTL, tftp availability, JSN/RFS config, or host restart-PD text in the retained captures.",
            "- The missing edge is the remote SERVREG state-up producer for `msm/modem/wlan_pd` instance 180. Without that indication, native never ACKs WLAN-PD state-up, requests `wlanmdsp.mbn`, publishes WLFW69, or creates `wlan0`.",
            "- Next live unit should be read-only and observe the service180/SERVREG RX producer side and modem child-PD state timing. Do not invoke `service_notif_pd_restart`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/PCIe/GDSC, PMIC/GPIO, or regulator paths.",
            "",
            "## Inputs",
            "",
            f"- Android dmesg: `{android_dmesg['path']}`",
            f"- Android logcat: `{android_logcat['path']}`",
            f"- Native dmesg: `{native_dmesg['path']}`",
            f"- Native inner manifest: `{parsed['inner_manifest']}`",
            f"- Native V1937 manifest: `{parsed['native_manifest']}`",
            f"- V1939 manifest: `{parsed['v1939_manifest']}`",
            f"- V1919 JSN/RFS manifest: `{parsed['v1919_manifest']}`",
            "",
            "## Safety Scope",
            "",
            "Host-only parser. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.",
            "",
        ]
    )


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    android_dmesg = summarize_dmesg(ANDROID_DMESG)
    android_logcat = summarize_logcat(ANDROID_LOGCAT)
    native_dmesg = summarize_dmesg(NATIVE_DMESG)
    parsed = parsed_evidence()
    source = source_summary()
    classification = classify(android_dmesg, android_logcat, native_dmesg, parsed, source)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "classification": classification,
        "android_dmesg": android_dmesg,
        "android_logcat": android_logcat,
        "native_dmesg": native_dmesg,
        "parsed": parsed,
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
