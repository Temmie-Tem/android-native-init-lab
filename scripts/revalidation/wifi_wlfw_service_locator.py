#!/usr/bin/env python3
"""v274 host-only WLFW service id locator.

The locator correlates local cnss-daemon WLFW strings with public Qualcomm
kernel WLAN firmware service definitions. It does not open QRTR sockets, send
nameservice packets, send QMI payloads, or execute device commands.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v274-wlfw-service-locator")
DEFAULT_VENDOR_ROOT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source")
DEFAULT_V273_MANIFEST = Path("tmp/wifi/v273-qrtr-readback-matrix-live-20260519-110229/manifest.json")
DEFAULT_V272_MANIFEST = Path("tmp/wifi/v272-qmi-service-object-extractor/manifest.json")

WLFW_SERVICE_ID = 0x45
WLFW_SERVICE_VERSION = 0x01
SOURCE_REFERENCES = [
    {
        "name": "android-kernel-coral-cnss2-wlfw-header",
        "url": "https://android.googlesource.com/kernel/msm/+/c2aee3401467314b48882a22d71906f380a5c17a/drivers/net/wireless/cnss2/wlan_firmware_service_v01.h",
        "evidence": "defines WLFW_SERVICE_ID_V01 0x45 and WLFW_SERVICE_VERS_V01 0x01",
    },
    {
        "name": "android-kernel-msm-soc-wlfw-header",
        "url": "https://android.googlesource.com/kernel/msm.git/+/7601617b4549fa3c1a237fb11cac04c54b182466/drivers/soc/qcom/wlan_firmware_service_v01.h",
        "evidence": "defines WLFW_SERVICE_ID_V01 0x45 and WLFW_SERVICE_VERS_V01 0x01",
    },
]
LOCAL_WLFW_NEEDLES = (
    "Failed to start wlfw service",
    "WLFW service connected",
    "wlfw_service_request",
    "wlfw_send_cap_req",
    "wlfw_send_bdf_download_req",
    "wlfw_send_ind_register_req",
    "wlfw_handle_initiate_cal_download_ind",
    "wlfw_handle_initiate_cal_update_ind",
)
LOCAL_WLAN_NEEDLES = (
    "wlan_service_request",
    "Failed to start wlan service",
    "Failed to request wlan service",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    return payload if isinstance(payload, dict) else {}


def run_host_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {"command": command, "rc": result.returncode, "ok": result.returncode == 0, "text": result.stdout, "error": ""}
    except Exception as exc:  # noqa: BLE001 - preserve host evidence failures
        return {"command": command, "rc": None, "ok": False, "text": "", "error": str(exc)}


def lines_matching(text: str, needles: tuple[str, ...], limit: int = 80) -> list[str]:
    lines: list[str] = []
    lowered_needles = [needle.lower() for needle in needles]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if any(needle.lower() in lowered for needle in lowered_needles):
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def all_needles_present(text: str, needles: tuple[str, ...]) -> dict[str, bool]:
    lowered = text.lower()
    return {needle: needle.lower() in lowered for needle in needles}


def service_object_names(v272: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for item in v272.get("service_objects", []):
        if isinstance(item, dict):
            value = item.get("service_name")
            if value:
                names.add(str(value))
    return names


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def render_summary(manifest: dict[str, Any]) -> str:
    local_rows = [
        [needle, "yes" if present else "no"]
        for needle, present in manifest["local_evidence"]["wlfw_needles"].items()
    ]
    lines = [
        "# WLFW Service Locator\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- wlfw_service_id: `{manifest['wlfw']['service_id_decimal']}` / `{manifest['wlfw']['service_id_hex']}`\n",
        f"- wlfw_service_version: `{manifest['wlfw']['service_version']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend(
        [
            "\n## Local WLFW String Coverage\n\n",
            markdown_table(["needle", "present"], local_rows),
            "\n\n## Guardrails\n\n",
        ]
    )
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    store.mkdir("captures")

    vendor_root = repo_path(args.vendor_root)
    cnss_daemon = vendor_root / "bin/cnss-daemon"
    libqmiservices = vendor_root / "lib64/libqmiservices.so"
    v273_manifest = load_json(repo_path(args.v273_manifest))
    v272_manifest = load_json(repo_path(args.v272_manifest))

    cnss_strings = run_host_command(["strings", str(cnss_daemon)], timeout=args.host_timeout)
    lib_symbols = run_host_command(["readelf", "-Ws", str(libqmiservices)], timeout=args.host_timeout)
    store.write_text("captures/cnss-strings.txt", str(cnss_strings.get("text") or cnss_strings.get("error") or ""))
    store.write_text("captures/libqmiservices-symbols.txt", str(lib_symbols.get("text") or lib_symbols.get("error") or ""))

    cnss_text = str(cnss_strings.get("text") or "")
    lib_text = str(lib_symbols.get("text") or "")
    wlfw_needles = all_needles_present(cnss_text, LOCAL_WLFW_NEEDLES)
    wlan_needles = all_needles_present(cnss_text, LOCAL_WLAN_NEEDLES)
    exported_service_names = service_object_names(v272_manifest)
    lib_has_wlfw = bool(re.search(r"\bwlfw_.*service_object|\bwlfw_qmi_idl_service_object", lib_text, re.IGNORECASE))

    checks: list[dict[str, Any]] = []
    add_check(checks, "v273-ready", v273_manifest.get("decision") == "qrtr-readback-matrix-timeout" and v273_manifest.get("pass") is True, f"decision={v273_manifest.get('decision')} pass={v273_manifest.get('pass')}")
    add_check(checks, "v272-ready", v272_manifest.get("decision") == "qmi-service-object-ids-extracted" and v272_manifest.get("pass") is True, f"decision={v272_manifest.get('decision')} pass={v272_manifest.get('pass')}")
    add_check(checks, "cnss-daemon-exists", cnss_daemon.exists(), str(cnss_daemon))
    add_check(checks, "source-wlfw-service-id-known", WLFW_SERVICE_ID == 0x45 and WLFW_SERVICE_VERSION == 1, f"id=0x{WLFW_SERVICE_ID:x} version={WLFW_SERVICE_VERSION}")
    add_check(checks, "local-wlfw-string-coverage", sum(1 for present in wlfw_needles.values() if present) >= 5, json.dumps(wlfw_needles, sort_keys=True))
    add_check(checks, "local-wlan-string-coverage", any(wlan_needles.values()), json.dumps(wlan_needles, sort_keys=True), severity="warning")
    add_check(checks, "local-exported-wlfw-object-absent", "wlfw" not in exported_service_names and not lib_has_wlfw, "WLFW object absent in libqmiservices evidence", severity="warning")

    critical_pass = all(item["pass"] for item in checks if item["severity"] == "critical")
    decision = "wlfw-service-id-source-backed" if critical_pass else "wlfw-service-locator-incomplete"
    reason = (
        "public kernel headers identify WLFW service id 0x45 and local cnss-daemon strings match WLFW flows"
        if critical_pass
        else "critical WLFW service-id evidence is incomplete"
    )
    manifest = {
        "created": now_iso(),
        "mode": "wlfw-service-locator",
        "decision": decision,
        "pass": critical_pass,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {
            "vendor_root": str(vendor_root),
            "cnss_daemon": str(cnss_daemon),
            "libqmiservices": str(libqmiservices),
            "v273_manifest": str(repo_path(args.v273_manifest)),
            "v272_manifest": str(repo_path(args.v272_manifest)),
        },
        "host_metadata": collect_host_metadata(),
        "references": SOURCE_REFERENCES,
        "checks": checks,
        "wlfw": {
            "service_id_decimal": WLFW_SERVICE_ID,
            "service_id_hex": f"0x{WLFW_SERVICE_ID:x}",
            "service_version": WLFW_SERVICE_VERSION,
            "next_matrix": f"wlfw:{WLFW_SERVICE_ID}:0,1",
        },
        "local_evidence": {
            "wlfw_needles": wlfw_needles,
            "wlan_needles": wlan_needles,
            "wlfw_lines": lines_matching(cnss_text, LOCAL_WLFW_NEEDLES),
            "wlan_lines": lines_matching(cnss_text, LOCAL_WLAN_NEEDLES),
            "exported_service_names": sorted(exported_service_names),
            "lib_has_wlfw_symbol": lib_has_wlfw,
        },
        "next_candidates": [
            "v275 explicit-approval QRTR nameservice readback for WLFW service 0x45 instance 0/1, no QMI payload",
            "If WLFW readback is also silent, analyze CNSS/runtime endpoint registration conditions before payload work",
            "QMI request payloads remain blocked until service visibility and payload contract are proven",
        ],
        "guardrails": [
            "host-only evidence correlation",
            "no Android code execution",
            "no device command executed",
            "no QRTR socket opened",
            "no QRTR nameservice packet sent",
            "no QMI payload sent",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT)
    parser.add_argument("--v273-manifest", type=Path, default=DEFAULT_V273_MANIFEST)
    parser.add_argument("--v272-manifest", type=Path, default=DEFAULT_V272_MANIFEST)
    parser.add_argument("--host-timeout", type=int, default=30)
    parser.add_argument("command", choices=("analyze",), nargs="?", default="analyze")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = analyze(args)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": manifest["out_dir"]}, ensure_ascii=False, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
