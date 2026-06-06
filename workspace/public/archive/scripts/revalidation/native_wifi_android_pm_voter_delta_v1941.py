#!/usr/bin/env python3
"""V1941 host-only Android PM-voter delta classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1941"
OUT_DIR = repo_path("tmp/wifi/v1941-android-pm-voter-delta")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1941_ANDROID_PM_VOTER_DELTA_2026-06-04.md")

ANDROID_LOGCAT = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt"
)
NATIVE_HELPER = repo_path(
    "tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/test-v1393-helper-result.stdout.txt"
)
NATIVE_MANIFEST = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json")
V1940_MANIFEST = repo_path("tmp/wifi/v1940-post180-servreg-producer-gap/manifest.json")


ANDROID_MARKERS = {
    "pm_proxy_vote": re.compile(r"PM-PROXY-THREAD voting for modem", re.IGNORECASE),
    "modem_online": re.compile(r"modem new state: is on-line", re.IGNORECASE),
    "cnss_register": re.compile(r"cnss-daemon registered", re.IGNORECASE),
    "cnss_vote": re.compile(r"cnss-daemon voting for modem", re.IGNORECASE),
    "wlfw_service_request": re.compile(r"wlfw_service_request", re.IGNORECASE),
    "qcril_register": re.compile(r"QCRIL registered", re.IGNORECASE),
    "qcril_modem_vote": re.compile(r"QCRIL voting for modem", re.IGNORECASE),
    "qcril_sdx50m_vote": re.compile(r"QCRIL voting for SDX50M", re.IGNORECASE),
    "wlanmdsp": re.compile(r"wlanmdsp\.mbn", re.IGNORECASE),
}
NATIVE_MARKERS = {
    "pm_register_ret": re.compile(r"pm_init_pm_client_register_retcheck.*rc=0x0", re.IGNORECASE),
    "pm_connect_ret": re.compile(r"pm_init_pm_client_connect_retcheck.*rc=0x0", re.IGNORECASE),
    "pm_return_zero": re.compile(r"pm_init_return_path.*rc=0x0", re.IGNORECASE),
    "qcril": re.compile(r"\bQCRIL\b", re.IGNORECASE),
    "pm_proxy_thread": re.compile(r"PM-PROXY-THREAD", re.IGNORECASE),
    "voting_for_modem_text": re.compile(r"voting for modem", re.IGNORECASE),
    "wlfw_service_request": re.compile(r"wlfw_service_request", re.IGNORECASE),
}
LOGCAT_TIME_RE = re.compile(r"^(\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d{3})")


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


def count_lines(text: str, pattern: re.Pattern[str]) -> int:
    return sum(1 for line in text.splitlines() if pattern.search(line))


def first_line_info(text: str, pattern: re.Pattern[str]) -> dict[str, Any]:
    for index, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            match = LOGCAT_TIME_RE.search(line)
            return {
                "line_no": index,
                "time": match.group(1) if match else "",
                "text": line,
            }
    return {"line_no": None, "time": "", "text": ""}


def summarize_android() -> dict[str, Any]:
    text = read_text(ANDROID_LOGCAT)
    counts = {name: count_lines(text, pattern) for name, pattern in ANDROID_MARKERS.items()}
    first = {name: first_line_info(text, pattern) for name, pattern in ANDROID_MARKERS.items()}
    return {
        "path": rel(ANDROID_LOGCAT),
        "exists": ANDROID_LOGCAT.exists(),
        "bytes": len(text),
        "counts": counts,
        "first": first,
    }


def summarize_native() -> dict[str, Any]:
    text = read_text(NATIVE_HELPER)
    counts = {name: count_lines(text, pattern) for name, pattern in NATIVE_MARKERS.items()}
    first = {name: first_line_info(text, pattern) for name, pattern in NATIVE_MARKERS.items()}
    manifest = load_json(NATIVE_MANIFEST)
    details = manifest.get("details") if isinstance(manifest.get("details"), dict) else {}
    return {
        "path": rel(NATIVE_HELPER),
        "manifest": rel(NATIVE_MANIFEST),
        "exists": NATIVE_HELPER.exists(),
        "bytes": len(text),
        "counts": counts,
        "first": first,
        "pm_open_subsys_modem": boolish(details.get("pm_open_subsys_modem")),
        "holder_opened": boolish(details.get("holder_opened")),
        "wlfw69": boolish(details.get("wlfw69")),
        "wlan_pd": boolish(details.get("wlan_pd")),
        "wlanmdsp": boolish(details.get("wlanmdsp")),
        "wlan0": boolish(details.get("wlan0")),
    }


def parsed_context() -> dict[str, Any]:
    v1940 = load_json(V1940_MANIFEST)
    classification = v1940.get("classification") if isinstance(v1940.get("classification"), dict) else {}
    return {
        "v1940_manifest": rel(V1940_MANIFEST),
        "v1940_pass": bool(v1940.get("pass")),
        "v1940_label": v1940.get("label", ""),
        "post180_gap": boolish(classification.get("native_missing_producer")),
        "native_same_upstream": boolish(classification.get("native_same_upstream")),
    }


def line_before(first: dict[str, Any], left: str, right: str) -> bool:
    left_no = first.get(left, {}).get("line_no")
    right_no = first.get(right, {}).get("line_no")
    return isinstance(left_no, int) and isinstance(right_no, int) and left_no < right_no


def classify(android: dict[str, Any], native: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    android_cnss_vote = (
        android["counts"]["pm_proxy_vote"] > 0
        and android["counts"]["modem_online"] > 0
        and android["counts"]["cnss_register"] > 0
        and android["counts"]["cnss_vote"] > 0
        and line_before(android["first"], "cnss_vote", "wlanmdsp")
    )
    native_cnss_pm_success = (
        native["counts"]["pm_register_ret"] > 0
        and native["counts"]["pm_connect_ret"] > 0
        and native["counts"]["pm_return_zero"] > 0
        and native["pm_open_subsys_modem"]
        and native["holder_opened"]
    )
    android_qcril_delta = (
        android["counts"]["qcril_register"] > 0
        and android["counts"]["qcril_modem_vote"] > 0
        and line_before(android["first"], "qcril_modem_vote", "wlanmdsp")
    )
    qcril_sdx50m_coupled = android["counts"]["qcril_sdx50m_vote"] > 0
    native_qcril_absent = (
        native["counts"]["qcril"] == 0
        and native["counts"]["pm_proxy_thread"] == 0
        and native["counts"]["voting_for_modem_text"] == 0
    )
    native_downstream_absent = not native["wlfw69"] and not native["wlan_pd"] and not native["wlanmdsp"] and not native["wlan0"]
    post180_gap_confirmed = context["v1940_pass"] and context["post180_gap"] and context["native_same_upstream"]

    if (
        android_cnss_vote
        and native_cnss_pm_success
        and android_qcril_delta
        and qcril_sdx50m_coupled
        and native_qcril_absent
        and native_downstream_absent
        and post180_gap_confirmed
    ):
        label = "android-qcril-vote-visible-native-absent-sdx50m-coupled"
        reason = (
            "native already proves cnss-daemon PM client register/connect success and /dev/subsys_modem open, "
            "while normal Android shows an additional QCRIL modem vote before wlanmdsp; that vote is coupled to "
            "SDX50M in the same normal log, so it is a read-only source/diff lead, not a permissible direct trigger"
        )
        passed = True
    elif android_cnss_vote and native_cnss_pm_success and native_downstream_absent:
        label = "android-pm-voter-delta-review"
        reason = "cnss PM parity is proven but the QCRIL/voter delta or post180 context is incomplete"
        passed = False
    else:
        label = "android-pm-voter-delta-incomplete"
        reason = "required Android PM voter or native cnss PM success evidence is missing"
        passed = False

    return {
        "label": label,
        "decision": f"v1941-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_cnss_vote": android_cnss_vote,
        "native_cnss_pm_success": native_cnss_pm_success,
        "android_qcril_delta": android_qcril_delta,
        "qcril_sdx50m_coupled": qcril_sdx50m_coupled,
        "native_qcril_absent": native_qcril_absent,
        "native_downstream_absent": native_downstream_absent,
        "post180_gap_confirmed": post180_gap_confirmed,
    }


def marker_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows = [
        ["android_pm_proxy_vote", android["counts"]["pm_proxy_vote"], android["first"]["pm_proxy_vote"]["time"], android["first"]["pm_proxy_vote"]["text"]],
        ["android_cnss_vote", android["counts"]["cnss_vote"], android["first"]["cnss_vote"]["time"], android["first"]["cnss_vote"]["text"]],
        ["android_qcril_modem_vote", android["counts"]["qcril_modem_vote"], android["first"]["qcril_modem_vote"]["time"], android["first"]["qcril_modem_vote"]["text"]],
        ["android_qcril_sdx50m_vote", android["counts"]["qcril_sdx50m_vote"], android["first"]["qcril_sdx50m_vote"]["time"], android["first"]["qcril_sdx50m_vote"]["text"]],
        ["android_wlanmdsp", android["counts"]["wlanmdsp"], android["first"]["wlanmdsp"]["time"], android["first"]["wlanmdsp"]["text"]],
        ["native_pm_register_ret0", native["counts"]["pm_register_ret"], "", native["first"]["pm_register_ret"]["text"]],
        ["native_pm_connect_ret0", native["counts"]["pm_connect_ret"], "", native["first"]["pm_connect_ret"]["text"]],
        ["native_pm_return0", native["counts"]["pm_return_zero"], "", native["first"]["pm_return_zero"]["text"]],
        ["native_qcril_text", native["counts"]["qcril"], "", native["first"]["qcril"]["text"] or "missing"],
    ]
    return [[str(cell) for cell in row] for row in rows]


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    android = manifest["android"]
    native = manifest["native"]
    context = manifest["context"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["Android cnss PM vote", classification["android_cnss_vote"], "PM-PROXY online, cnss-daemon registered/voted before wlanmdsp"],
        ["Native cnss PM success", classification["native_cnss_pm_success"], "pm_client_register/connect/return rc=0 plus /dev/subsys_modem holder"],
        ["Android QCRIL delta", classification["android_qcril_delta"], "QCRIL modem vote appears before wlanmdsp"],
        ["QCRIL SDX50M coupling", classification["qcril_sdx50m_coupled"], "same Android window also votes SDX50M; direct execution is forbidden"],
        ["Native QCRIL absent", classification["native_qcril_absent"], "no QCRIL/PM-PROXY/voting text in native helper evidence"],
        ["Native downstream absent", classification["native_downstream_absent"], f"wlfw69={native['wlfw69']} wlan0={native['wlan0']}"],
        ["Post-180 gap", classification["post180_gap_confirmed"], context["v1940_label"]],
    ]
    return "\n".join(
        [
            "# Native Init V1941 Android PM Voter Delta",
            "",
            "## Summary",
            "",
            "- Cycle: `V1941`",
            "- Type: host-only classifier over normal Android PerMgrSrv logcat and native V1937 cnss PM uprobes",
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
            "## Marker Rows",
            "",
            markdown_table(["marker", "count", "time", "first line"], marker_rows(android, native)),
            "",
            "## Interpretation",
            "",
            "- This does not make QCRIL a permitted direct trigger. The normal Android line that votes QCRIL for modem is immediately coupled to a QCRIL vote for SDX50M.",
            "- The useful result is narrower: native already matches the cnss-daemon PM-client success path, so the next host/source comparison should extract what QCRIL contributes to internal-modem WLAN-PD state-up without starting QCRIL on native.",
            "- Any live follow-up must stay read-only and must not open `/dev/subsys_esoc0`, start SDX50M/eSoC/PCIe paths, invoke Wi-Fi HAL, scan/connect, use credentials, DHCP/routes, external ping, or call restart-PD.",
            "",
            "## Inputs",
            "",
            f"- Android logcat: `{android['path']}`",
            f"- Native helper: `{native['path']}`",
            f"- Native manifest: `{native['manifest']}`",
            f"- V1940 manifest: `{context['v1940_manifest']}`",
            "",
            "## Safety Scope",
            "",
            "Host-only parser. No live device command, flash, reboot, QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.",
            "",
        ]
    )


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    android = summarize_android()
    native = summarize_native()
    context = parsed_context()
    classification = classify(android, native, context)
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
        "context": context,
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
