#!/usr/bin/env python3
"""V1943 host-only classifier for the Android QCRIL PM-voter source lead."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1943"
OUT_DIR = repo_path("tmp/wifi/v1943-qcril-owner-classifier")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1943_QCRIL_OWNER_CLASSIFIER_2026-06-04.md")
ANDROID_LOGCAT = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt"
)
V1941_REPORT = repo_path("docs/reports/NATIVE_INIT_V1941_ANDROID_PM_VOTER_DELTA_2026-06-04.md")
V1942_MANIFEST = repo_path("tmp/wifi/v1942-qcril-radio-vendor-artifact-export/manifest.json")
V1942_REPORT = repo_path("docs/reports/NATIVE_INIT_V1942_QCRIL_RADIO_VENDOR_ARTIFACT_EXPORT_2026-06-04.md")
V1942_VENDOR_SOURCE = repo_path("tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source")

LOGCAT_RE = re.compile(
    r"^(?P<time>\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d{3})\s+"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[VDIWEF])\s+"
    r"(?P<tag>[^:]+):\s+(?P<msg>.*)$"
)
KEYWORDS = (
    "QCRIL",
    "PM-PROXY",
    "PerMgr",
    "peripheral",
    "voting for modem",
    "voting for SDX50M",
    "subsys_modem",
    "/dev/subsys_modem",
    "wlan_pd",
    "wlanmdsp",
    "SSCTL",
    "servreg",
    "SDX50M",
    "modem",
)
QTI_QCRIL_DIRECT_PATHS = {
    "bin/qcrild",
    "lib64/libqcrilNr.so",
    "lib64/libqcrilFramework.so",
    "lib64/libqcrilDataModule.so",
    "lib64/libril-qc-hal-qmi.so",
    "lib64/libril-qcril-hook-oem.so",
    "lib/libqcrilNr.so",
    "lib/libqcrilFramework.so",
    "lib/libril-qc-hal-qmi.so",
    "lib/libril-qcril-hook-oem.so",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def first_index(lines: list[str], needle: str) -> int | None:
    lowered = needle.lower()
    for index, line in enumerate(lines, start=1):
        if lowered in line.lower():
            return index
    return None


def parse_logcat() -> dict[str, Any]:
    lines = read_text(ANDROID_LOGCAT).splitlines()
    qcril_rows: list[dict[str, Any]] = []
    qcril_non_permgr_rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if "QCRIL" not in line:
            continue
        match = LOGCAT_RE.match(line)
        row = {
            "line": line_number,
            "time": match.group("time") if match else "",
            "pid": match.group("pid") if match else "",
            "tid": match.group("tid") if match else "",
            "tag": match.group("tag").strip() if match else "",
            "msg": match.group("msg") if match else line,
            "text": line,
        }
        qcril_rows.append(row)
        if row["tag"] != "PerMgrSrv":
            qcril_non_permgr_rows.append(row)

    wlanmdsp_line = first_index(lines, "wlanmdsp.mbn")
    qcril_modem_vote_line = first_index(lines, "QCRIL voting for modem")
    qcril_sdx_vote_line = first_index(lines, "QCRIL voting for SDX50M")
    qcril_register_line = first_index(lines, "QCRIL registered")
    return {
        "path": rel(ANDROID_LOGCAT),
        "exists": ANDROID_LOGCAT.exists(),
        "qcril_rows": qcril_rows,
        "qcril_non_permgr_rows": qcril_non_permgr_rows,
        "wlanmdsp_line": wlanmdsp_line,
        "qcril_register_line": qcril_register_line,
        "qcril_modem_vote_line": qcril_modem_vote_line,
        "qcril_sdx_vote_line": qcril_sdx_vote_line,
        "qcril_before_wlanmdsp": all(
            isinstance(line_number, int) and isinstance(wlanmdsp_line, int) and line_number < wlanmdsp_line
            for line_number in (qcril_register_line, qcril_modem_vote_line, qcril_sdx_vote_line)
        ),
        "qcril_permgr_only": bool(qcril_rows) and not qcril_non_permgr_rows,
    }


def run_strings(path: Path) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["strings", "-a", str(path)],
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except FileNotFoundError:
        return "strings-unavailable", ""
    except subprocess.TimeoutExpired:
        return "strings-timeout", ""
    if result.returncode != 0:
        return f"strings-rc-{result.returncode}", result.stdout
    return "ok", result.stdout


def run_readelf_symbols(path: Path) -> tuple[str, list[str]]:
    try:
        result = subprocess.run(
            ["readelf", "-Ws", str(path)],
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except FileNotFoundError:
        return "readelf-unavailable", []
    except subprocess.TimeoutExpired:
        return "readelf-timeout", []
    if result.returncode != 0:
        return f"readelf-rc-{result.returncode}", []
    matches: list[str] = []
    symbol_re = re.compile(r"(pm_client|Peripheral|peripheral|register|connect|vote|radio|modem|SDX50M)", re.IGNORECASE)
    for line in result.stdout.splitlines():
        if symbol_re.search(line):
            matches.append(line.strip()[:240])
            if len(matches) >= 30:
                break
    return "ok", matches


def summarize_vendor_source() -> dict[str, Any]:
    manifest = load_json(V1942_MANIFEST)
    pulled_files = manifest.get("pulled_files") if isinstance(manifest.get("pulled_files"), list) else []
    pulled_paths = [str(item.get("relative_path", "")) for item in pulled_files if isinstance(item, dict)]
    missing = manifest.get("missing_or_skipped_files") if isinstance(manifest.get("missing_or_skipped_files"), list) else []
    missing_by_path = {
        str(item.get("path", "")): str(item.get("reason", ""))
        for item in missing
        if isinstance(item, dict)
    }

    string_counts: dict[str, dict[str, int]] = {}
    string_samples: dict[str, list[str]] = {}
    symbol_samples: dict[str, dict[str, Any]] = {}
    for relative_path in pulled_paths:
        full_path = V1942_VENDOR_SOURCE / relative_path
        if not full_path.exists() or not full_path.is_file():
            continue
        status, strings_text = run_strings(full_path)
        counts = {
            keyword: len(re.findall(re.escape(keyword), strings_text, flags=re.IGNORECASE))
            for keyword in KEYWORDS
        }
        string_counts[relative_path] = {keyword: count for keyword, count in counts.items() if count}
        samples: list[str] = []
        if status == "ok":
            for line in strings_text.splitlines():
                if any(keyword.lower() in line.lower() for keyword in KEYWORDS):
                    samples.append(line[:240])
                    if len(samples) >= 8:
                        break
        string_samples[relative_path] = samples
        symbol_status, symbols = run_readelf_symbols(full_path)
        symbol_samples[relative_path] = {"status": symbol_status, "symbols": symbols}

    qti_qcril_present = sorted(QTI_QCRIL_DIRECT_PATHS.intersection(pulled_paths))
    qti_qcril_missing = sorted(path for path in QTI_QCRIL_DIRECT_PATHS if missing_by_path.get(path) == "stat-failed")
    samsung_radio_paths = sorted(path for path in pulled_paths if "vendor.samsung.hardware.radio" in path)
    peripheral_paths = sorted(path for path in pulled_paths if "peripheral_client" in path or path == "bin/pm-service")
    rild_paths = sorted(path for path in pulled_paths if path.endswith("/rild") or path == "bin/rild")
    qcril_string_paths = sorted(path for path, counts in string_counts.items() if counts.get("QCRIL", 0) > 0)
    wlan_pd_string_paths = sorted(path for path, counts in string_counts.items() if counts.get("wlan_pd", 0) > 0 or counts.get("wlanmdsp", 0) > 0)

    return {
        "manifest": rel(V1942_MANIFEST),
        "report": rel(V1942_REPORT),
        "vendor_source": rel(V1942_VENDOR_SOURCE),
        "v1942_pass": bool(manifest.get("pass")),
        "v1942_label": manifest.get("label", ""),
        "pulled_paths": pulled_paths,
        "missing_by_path": missing_by_path,
        "qti_qcril_present": qti_qcril_present,
        "qti_qcril_missing": qti_qcril_missing,
        "samsung_radio_paths": samsung_radio_paths,
        "peripheral_paths": peripheral_paths,
        "rild_paths": rild_paths,
        "qcril_string_paths": qcril_string_paths,
        "wlan_pd_string_paths": wlan_pd_string_paths,
        "string_counts": string_counts,
        "string_samples": string_samples,
        "symbol_samples": symbol_samples,
    }


def classify(android: dict[str, Any], vendor: dict[str, Any]) -> dict[str, Any]:
    android_qcril_edge = (
        android["qcril_permgr_only"]
        and android["qcril_before_wlanmdsp"]
        and isinstance(android["qcril_modem_vote_line"], int)
        and isinstance(android["qcril_sdx_vote_line"], int)
    )
    qti_qcril_absent = not vendor["qti_qcril_present"] and len(vendor["qti_qcril_missing"]) >= 6
    samsung_radio_present = bool(vendor["samsung_radio_paths"])
    peripheral_client_present = "bin/pm-service" in vendor["peripheral_paths"] and any(
        "libperipheral_client.so" in path for path in vendor["peripheral_paths"]
    )
    no_explicit_wlan_strings = not vendor["wlan_pd_string_paths"]
    no_qcril_strings_in_export = not vendor["qcril_string_paths"]

    if (
        vendor["v1942_pass"]
        and android_qcril_edge
        and qti_qcril_absent
        and samsung_radio_present
        and peripheral_client_present
        and no_explicit_wlan_strings
    ):
        label = "peripheral-manager-qcril-client-name-samsung-radio-source-lead"
        reason = (
            "Android's QCRIL evidence is emitted by PerMgrSrv as a client-name vote before wlanmdsp; "
            "the read-only vendor export has Samsung radio HAL/rild plus pm-service/libperipheral_client, "
            "but no QTI qcrild/libqcril artifacts and no explicit wlan_pd/wlanmdsp strings in exported voter artifacts"
        )
        passed = True
    elif android_qcril_edge and qti_qcril_absent:
        label = "qcril-owner-source-review"
        reason = "Android QCRIL PM voter edge is real, but vendor ownership evidence is incomplete"
        passed = False
    else:
        label = "qcril-owner-classification-incomplete"
        reason = "required Android QCRIL edge or V1942 source evidence is missing"
        passed = False

    return {
        "label": label,
        "decision": f"v1943-{label}-host-{'pass' if passed else 'review'}",
        "pass": passed,
        "reason": reason,
        "android_qcril_edge": android_qcril_edge,
        "qti_qcril_absent": qti_qcril_absent,
        "samsung_radio_present": samsung_radio_present,
        "peripheral_client_present": peripheral_client_present,
        "no_explicit_wlan_strings": no_explicit_wlan_strings,
        "no_qcril_strings_in_export": no_qcril_strings_in_export,
    }


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    android = manifest["android"]
    vendor = manifest["vendor"]
    android_rows = [
        [row["line"], row["time"], row["tag"], row["msg"]]
        for row in android["qcril_rows"]
    ]
    source_rows = [
        ["QTI QCRIL present", ", ".join(vendor["qti_qcril_present"]) or "none", "direct qcrild/libqcril artifacts copied"],
        ["QTI QCRIL missing", str(len(vendor["qti_qcril_missing"])), ", ".join(vendor["qti_qcril_missing"][:6])],
        ["Samsung radio HAL", str(len(vendor["samsung_radio_paths"])), ", ".join(vendor["samsung_radio_paths"][:5])],
        ["Peripheral manager", str(len(vendor["peripheral_paths"])), ", ".join(vendor["peripheral_paths"])],
        ["rild", str(len(vendor["rild_paths"])), ", ".join(vendor["rild_paths"]) or "none"],
        ["QCRIL strings", str(len(vendor["qcril_string_paths"])), ", ".join(vendor["qcril_string_paths"]) or "none"],
        ["WLAN-PD strings", str(len(vendor["wlan_pd_string_paths"])), ", ".join(vendor["wlan_pd_string_paths"]) or "none"],
    ]
    string_rows: list[list[str]] = []
    for path, counts in vendor["string_counts"].items():
        if counts:
            rendered = ", ".join(f"{keyword}={count}" for keyword, count in counts.items())
            string_rows.append([path, rendered, " | ".join(vendor["string_samples"].get(path, [])[:3])])
    symbol_rows: list[list[str]] = []
    for path in vendor["peripheral_paths"] + vendor["samsung_radio_paths"][:3] + vendor["rild_paths"]:
        sample = vendor["symbol_samples"].get(path, {})
        symbols = sample.get("symbols", []) if isinstance(sample, dict) else []
        symbol_rows.append([path, sample.get("status", "") if isinstance(sample, dict) else "", " | ".join(symbols[:3])])

    lines = [
        "# Native Init V1943 QCRIL Owner Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: host-only classifier over Android PerMgrSrv QCRIL lines and V1942 vendor export",
        f"- Decision: `{classification['decision']}`",
        f"- Label: `{classification['label']}`",
        f"- Pass: `{classification['pass']}`",
        f"- Reason: {classification['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["Android QCRIL edge", classification["android_qcril_edge"], "PerMgrSrv-only QCRIL register/vote before wlanmdsp"],
                ["QTI QCRIL absent", classification["qti_qcril_absent"], "direct qcrild/libqcril paths stat-failed in V1942"],
                ["Samsung radio present", classification["samsung_radio_present"], "vendor.samsung.hardware.radio artifacts copied"],
                ["Peripheral client present", classification["peripheral_client_present"], "pm-service plus libperipheral_client copied"],
                ["No explicit WLAN strings", classification["no_explicit_wlan_strings"], "no wlan_pd/wlanmdsp strings in exported voter artifacts"],
                ["No QCRIL strings", classification["no_qcril_strings_in_export"], "QCRIL appears as PerMgrSrv client name in logcat, not in copied artifacts"],
            ],
        ),
        "",
        "## Android QCRIL Lines",
        "",
        markdown_table(["line", "time", "tag", "message"], android_rows or [["none", "", "", ""]]),
        "",
        "## Vendor Source Ownership",
        "",
        markdown_table(["area", "value", "detail"], source_rows),
        "",
        "## String Evidence",
        "",
        markdown_table(["path", "keyword counts", "sample"], string_rows or [["none", "", ""]]),
        "",
        "## Symbol Samples",
        "",
        markdown_table(["path", "readelf", "sample"], symbol_rows or [["none", "", ""]]),
        "",
        "## Interpretation",
        "",
        "- The V1941 `QCRIL voting for modem` evidence is not a native permission to start QCRIL; it is a `PerMgrSrv` log for a client named `QCRIL`.",
        "- V1942 shows this vendor image does not expose the expected QTI `qcrild`/`libqcril*` artifacts on `sda29`; the available source lead is Samsung radio HAL/rild using the same peripheral-manager client interface.",
        "- Keep the next step host-only: callgraph/disassembly of Samsung radio HAL/rild to identify which `libperipheral_client` call sequence produces the modem vote, while excluding SDX50M/eSoC/PCIe side effects.",
        "",
        "## Inputs",
        "",
        f"- Android logcat: `{android['path']}`",
        f"- V1941 report: `{rel(V1941_REPORT)}`",
        f"- V1942 manifest: `{vendor['manifest']}`",
        f"- V1942 report: `{vendor['report']}`",
        f"- V1942 vendor source: `{vendor['vendor_source']}`",
        "",
        "## Safety Scope",
        "",
        "Host-only parser. No live device command, flash, reboot, QCRIL/radio start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.",
        "",
    ]
    return "\n".join(str(line) for line in lines)


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    android = parse_logcat()
    vendor = summarize_vendor_source()
    classification = classify(android, vendor)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "android": android,
        "vendor": vendor,
        "classification": classification,
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"{'PASS' if classification['pass'] else 'FAIL'} out_dir={OUT_DIR} decision={classification['decision']} reason={classification['reason']}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
