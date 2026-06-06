#!/usr/bin/env python3
"""V1939 host-only classifier for the WLAN-PD service-notifier root indication gap."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1939"
OUT_DIR = repo_path("tmp/wifi/v1939-servnotif-root-indication-gap")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1939_SERVNOTIF_ROOT_INDICATION_GAP_2026-06-04.md")

ANDROID_V1917_DMESG = repo_path(
    "tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff/"
    "android-postfs-evidence/a90-v1917-icnss-ipc-log-edge/dmesg-filtered.txt"
)
ANDROID_V1934_DMESG = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/dmesg-filtered.txt"
)
ANDROID_V1934_LOGCAT = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt"
)
NATIVE_V1937_DMESG = repo_path(
    "tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/test-v1393-dmesg.stdout.txt"
)
NATIVE_V1937_MANIFEST = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json")
NATIVE_V1938_MANIFEST = repo_path("tmp/wifi/v1938-wlan-pd-stateup-before-wlfw-arrive/manifest.json")

SOURCE_ROOT = repo_path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
SERVICE_NOTIFIER = SOURCE_ROOT / "drivers/soc/qcom/service-notifier.c"
ICNSS = SOURCE_ROOT / "drivers/soc/qcom/icnss.c"


LINE_PATTERNS = {
    "new_server_180": re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE),
    "new_server_74": re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE),
    "root_ind_wlanpd": re.compile(
        r"root_service_service_ind_cb: Indication received from msm/modem/wlan_pd",
        re.IGNORECASE,
    ),
    "ack_wlanpd_180": re.compile(
        r"send_ind_ack: Indication ACKed .* service msm/modem/wlan_pd, instance 180",
        re.IGNORECASE,
    ),
    "root_ind_audio": re.compile(
        r"root_service_service_ind_cb: Indication received from msm/adsp/audio_pd",
        re.IGNORECASE,
    ),
    "ack_audio_74": re.compile(
        r"send_ind_ack: Indication ACKed .* service msm/adsp/audio_pd, instance 74",
        re.IGNORECASE,
    ),
    "modem_ssctl": re.compile(r"modem's SSCTL service", re.IGNORECASE),
    "wlanmdsp": re.compile(r"wlanmdsp\.mbn", re.IGNORECASE),
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


def summarize_text(path: Path, extra_text: str = "") -> dict[str, Any]:
    text = read_text(path) + ("\n" + extra_text if extra_text else "")
    counts = {name: count_lines(text, pattern) for name, pattern in LINE_PATTERNS.items()}
    first = {name: first_line(text, pattern) for name, pattern in LINE_PATTERNS.items()}
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


def android_summary() -> dict[str, Any]:
    v1917 = summarize_text(ANDROID_V1917_DMESG)
    v1934 = summarize_text(ANDROID_V1934_DMESG, read_text(ANDROID_V1934_LOGCAT))
    return {
        "v1917": v1917,
        "v1934": v1934,
        "new_server_180": v1917["counts"]["new_server_180"] > 0 and v1934["counts"]["new_server_180"] > 0,
        "new_server_74": v1917["counts"]["new_server_74"] > 0 and v1934["counts"]["new_server_74"] > 0,
        "root_ind_wlanpd": v1917["counts"]["root_ind_wlanpd"] > 0 and v1934["counts"]["root_ind_wlanpd"] > 0,
        "ack_wlanpd_180": v1917["counts"]["ack_wlanpd_180"] > 0 and v1934["counts"]["ack_wlanpd_180"] > 0,
        "wlanmdsp": v1934["counts"]["wlanmdsp"] > 0,
    }


def native_summary() -> dict[str, Any]:
    dmesg = summarize_text(NATIVE_V1937_DMESG)
    v1937 = load_json(NATIVE_V1937_MANIFEST)
    v1938 = load_json(NATIVE_V1938_MANIFEST)
    details = v1937.get("details") if isinstance(v1937.get("details"), dict) else {}
    classification = v1938.get("classification") if isinstance(v1938.get("classification"), dict) else {}
    return {
        "dmesg": dmesg,
        "manifest": rel(NATIVE_V1937_MANIFEST),
        "v1938_manifest": rel(NATIVE_V1938_MANIFEST),
        "v1937_pass": bool(v1937.get("pass")),
        "v1938_pass": bool(v1938.get("pass")),
        "v1937_label": v1937.get("label", ""),
        "v1938_label": v1938.get("label", ""),
        "service74": boolish(details.get("service74")),
        "service180": boolish(details.get("service180")),
        "pm_open_subsys_modem": boolish(details.get("pm_open_subsys_modem")),
        "holder_opened": boolish(details.get("holder_opened")),
        "icnss_pd_registration": boolish((details.get("icnss_ipc") or {}).get("pd_notification_registration_seen")),
        "servnotif_late_state": details.get("servnotif_late_state", ""),
        "servnotif_late_indication": intish(details.get("servnotif_late_indication")),
        "wlfw69": boolish(details.get("wlfw69")),
        "wlan_pd": boolish(details.get("wlan_pd")),
        "wlanmdsp": boolish(details.get("wlanmdsp")),
        "wlan0": boolish(details.get("wlan0")),
        "v1938_native_no_stateup": boolish(classification.get("native_no_stateup")),
        "v1938_native_no_wlfw": boolish(classification.get("native_no_wlfw")),
    }


def source_summary() -> dict[str, Any]:
    return {
        "root_service_service_ind_cb": source_line(SERVICE_NOTIFIER, r"static void root_service_service_ind_cb"),
        "state_ind_log": source_line(SERVICE_NOTIFIER, r"Indication received from %s"),
        "send_ind_ack": source_line(SERVICE_NOTIFIER, r"static void send_ind_ack"),
        "ack_log": source_line(SERVICE_NOTIFIER, r"Indication ACKed for transid"),
        "new_server": source_line(SERVICE_NOTIFIER, r"static int service_notifier_new_server"),
        "new_server_log": source_line(SERVICE_NOTIFIER, r"Connection established between QMI handle"),
        "register_listener": source_line(SERVICE_NOTIFIER, r"register_notif_listener"),
        "icnss_domain_log": source_line(ICNSS, r"domain_name: %s, instance_id: %d"),
        "icnss_register_notifier": source_line(ICNSS, r"service_notif_register_notifier"),
        "icnss_restart_pd": source_line(ICNSS, r"service_notif_pd_restart"),
    }


def classify(android: dict[str, Any], native: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    android_positive = (
        android["new_server_180"]
        and android["new_server_74"]
        and android["root_ind_wlanpd"]
        and android["ack_wlanpd_180"]
        and android["wlanmdsp"]
    )
    native_registered = (
        native["v1937_pass"]
        and native["v1938_pass"]
        and native["service74"]
        and native["service180"]
        and native["pm_open_subsys_modem"]
        and native["holder_opened"]
        and native["icnss_pd_registration"]
    )
    dmesg_counts = native["dmesg"]["counts"]
    native_sibling_only = (
        dmesg_counts["new_server_74"] > 0
        and dmesg_counts["root_ind_audio"] > 0
        and dmesg_counts["ack_audio_74"] > 0
    )
    native_missing_wlanpd_ind = (
        dmesg_counts["root_ind_wlanpd"] == 0
        and dmesg_counts["ack_wlanpd_180"] == 0
        and native["servnotif_late_state"] == "uninit"
        and native["servnotif_late_indication"] == 0
    )
    native_no_publication = (
        not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
        and native["v1938_native_no_wlfw"]
    )
    source_ok = all(
        source[name]["line"] is not None
        for name in (
            "root_service_service_ind_cb",
            "state_ind_log",
            "send_ind_ack",
            "ack_log",
            "new_server",
            "icnss_register_notifier",
            "icnss_restart_pd",
        )
    )

    if android_positive and native_registered and native_sibling_only and native_missing_wlanpd_ind and native_no_publication and source_ok:
        label = "native-servnotif-wlanpd-root-indication-missing"
        reason = (
            "Android normal receives and ACKs the service-notifier state indication for "
            "msm/modem/wlan_pd instance 180 before wlanmdsp; native has service74/180 and ICNSS "
            "registration but only the sibling audio_pd indication appears, with no wlan_pd indication "
            "or WLFW69 publication"
        )
        passed = True
    elif native_registered and native_missing_wlanpd_ind:
        label = "native-wlanpd-root-indication-missing-review"
        reason = "native reaches ICNSS/service-notifier registration and lacks the wlan_pd root indication, but comparator/source coverage is incomplete"
        passed = False
    else:
        label = "servnotif-root-indication-gap-incomplete"
        reason = "required Android-positive or native post-registration evidence is missing"
        passed = False

    return {
        "label": label,
        "decision": f"v1939-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_positive": android_positive,
        "native_registered": native_registered,
        "native_sibling_only": native_sibling_only,
        "native_missing_wlanpd_ind": native_missing_wlanpd_ind,
        "native_no_publication": native_no_publication,
        "source_ok": source_ok,
    }


def source_rows(source: dict[str, Any]) -> list[list[str]]:
    return [[name, item["path"], str(item["line"]), item["text"]] for name, item in source.items()]


def count_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in (
        "new_server_180",
        "new_server_74",
        "root_ind_wlanpd",
        "ack_wlanpd_180",
        "root_ind_audio",
        "ack_audio_74",
        "modem_ssctl",
        "wlanmdsp",
    ):
        rows.append(
            [
                name,
                str(android["v1917"]["counts"][name]),
                str(android["v1934"]["counts"][name]),
                str(native["dmesg"]["counts"][name]),
            ]
        )
    return rows


def first_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    interesting = [
        ("android_v1934_wlanpd_ind", android["v1934"]["first"]["root_ind_wlanpd"]),
        ("android_v1934_wlanpd_ack", android["v1934"]["first"]["ack_wlanpd_180"]),
        ("android_v1934_wlanmdsp", android["v1934"]["first"]["wlanmdsp"]),
        ("native_audio_pd_ind", native["dmesg"]["first"]["root_ind_audio"]),
        ("native_audio_pd_ack", native["dmesg"]["first"]["ack_audio_74"]),
        ("native_modem_180", native["dmesg"]["first"]["new_server_180"]),
        ("native_wlanpd_ind", native["dmesg"]["first"]["root_ind_wlanpd"] or "missing"),
    ]
    return [[name, line] for name, line in interesting]


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    source = manifest["source"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["Android positive", classification["android_positive"], "180/74 servers, wlan_pd indication+ACK, wlanmdsp request"],
        ["Native registered", classification["native_registered"], "service74/180, PM open, holder, ICNSS PD registration"],
        ["Native sibling-only", classification["native_sibling_only"], "audio_pd instance74 indication+ACK present"],
        ["Native WLAN-PD indication", not classification["native_missing_wlanpd_ind"], f"late_state={native['servnotif_late_state']} indication={native['servnotif_late_indication']}"],
        ["Native WLFW publication", not classification["native_no_publication"], f"wlfw69={native['wlfw69']} wlan_pd={native['wlan_pd']} wlanmdsp={native['wlanmdsp']} wlan0={native['wlan0']}"],
        ["Source anchors", classification["source_ok"], "state indication callback, ACK, server lookup, ICNSS notifier registration"],
    ]
    return "\n".join(
        [
            "# Native Init V1939 Service-notifier Root Indication Gap",
            "",
            "## Summary",
            "",
            "- Cycle: `V1939`",
            "- Type: host-only classifier over existing normal Android and native V1937/V1938 evidence",
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
            markdown_table(["marker", "Android V1917", "Android V1934", "Native V1937"], count_rows(android, native)),
            "",
            "## First Lines",
            "",
            markdown_table(["marker", "line"], first_rows(android, native)),
            "",
            "## Source Anchors",
            "",
            markdown_table(["anchor", "path", "line", "text"], source_rows(source)),
            "",
            "## Interpretation",
            "",
            "- `service74` in the native combined route is the sibling clean-DSP path: the captured indication is `msm/adsp/audio_pd` instance 74.",
            "- Android's normal internal-modem path receives `msm/modem/wlan_pd` state-up on instance 180 and ACKs it before `wlanmdsp.mbn` is requested.",
            "- Native reaches ICNSS registration for `msm/modem/wlan_pd` but never receives that root-service indication, so WLFW service69 never publishes and `cnss-daemon` remains in the libqmi wait.",
            "- Next live work should observe the remote modem WLAN-PD state-up producer inputs only; do not call `service_notif_pd_restart`, start Wi-Fi HAL, scan/connect, use credentials, or touch eSoC/PCIe/GDSC/PMIC/GPIO.",
            "",
            "## Inputs",
            "",
            f"- Android V1917 dmesg: `{android['v1917']['path']}`",
            f"- Android V1934 dmesg: `{android['v1934']['path']}`",
            f"- Native V1937 dmesg: `{native['dmesg']['path']}`",
            f"- Native V1937 manifest: `{native['manifest']}`",
            f"- Native V1938 manifest: `{native['v1938_manifest']}`",
            "",
            "## Safety Scope",
            "",
            "Host-only parser. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
            "",
        ]
    )


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
