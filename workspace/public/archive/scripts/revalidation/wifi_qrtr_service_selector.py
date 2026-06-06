#!/usr/bin/env python3
"""v271 host-only QRTR/QMI service evidence selector.

This tool does not open QRTR sockets, run device commands, start Wi-Fi daemons,
or send QMI payloads. It correlates prior v270 readback evidence with vendor
binary strings/symbols so the next QRTR/QMI step is based on service evidence
instead of the arbitrary service=1, instance=1 lookup used in v269/v270.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v271-qrtr-service-selector")
DEFAULT_V270_PRIMARY_MANIFEST = Path("tmp/wifi/v270-qrtr-ns-readback-live-20260519-103623/manifest.json")
DEFAULT_V270_LONG_MANIFEST = Path("tmp/wifi/v270-qrtr-ns-readback-live-long-20260519-103732/manifest.json")
DEFAULT_VENDOR_ROOT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source")

QMI_SERVICE_OBJECT_RE = re.compile(r"\b([A-Za-z0-9_]+)_get_service_object_internal_v([0-9]+)\b")
QMI_CLIENT_SYMBOL_RE = re.compile(r"\b(qmi_(?:client|idl)_[A-Za-z0-9_]+)\b")
CNSS_FAMILY_PATTERNS: dict[str, tuple[str, ...]] = {
    "dms": ("dms", "get mac address", "DMS"),
    "wlfw": ("wlfw", "WLFW"),
    "wlan": ("wlan_service", "wlan service", "WLAN"),
    "cnss-socket": ("/data/vendor/wifi/sockets", "cnss_user"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def run_host_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    started = now_iso()
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
        return {
            "command": command,
            "started": started,
            "rc": result.returncode,
            "ok": result.returncode == 0,
            "text": result.stdout,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 - evidence preserves exact host failure
        return {
            "command": command,
            "started": started,
            "rc": None,
            "ok": False,
            "text": "",
            "error": str(exc),
        }


def write_capture(store: EvidenceStore, name: str, capture: dict[str, Any]) -> None:
    text = capture.get("text") or capture.get("error") or ""
    store.write_text(f"captures/{name}.txt", str(text))


def text_lines_containing(text: str, needles: tuple[str, ...], limit: int = 80) -> list[str]:
    out: list[str] = []
    lowered_needles = [needle.lower() for needle in needles]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lowered_line = line.lower()
        if any(needle.lower() in lowered_line for needle in lowered_needles):
            out.append(line)
        if len(out) >= limit:
            break
    return out


def service_objects_from_text(text: str) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    services: list[dict[str, str]] = []
    for match in QMI_SERVICE_OBJECT_RE.finditer(text):
        key = (match.group(1), match.group(2))
        if key in seen:
            continue
        seen.add(key)
        services.append({"name": match.group(1), "version": match.group(2)})
    return sorted(services, key=lambda item: (item["name"], item["version"]))


def symbols_from_text(text: str, pattern: re.Pattern[str]) -> list[str]:
    return sorted(set(pattern.findall(text)))


def helper_keys(manifest: dict[str, Any]) -> dict[str, str]:
    helper = manifest.get("helper_run")
    if isinstance(helper, dict) and isinstance(helper.get("helper_keys"), dict):
        return {str(key): str(value) for key, value in helper["helper_keys"].items()}
    return {}


def v270_readback_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    keys = helper_keys(manifest)
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "service": keys.get("service"),
        "instance": keys.get("instance"),
        "events": keys.get("readback.events"),
        "service_events": keys.get("readback.service_events"),
        "end_of_list": keys.get("readback.end_of_list"),
        "timeout": keys.get("readback.timeout"),
        "qmi_attempted": keys.get("qmi_attempted"),
    }


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def classify_candidate(
    name: str,
    evidence: list[str],
    strength: str,
    blocker: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "evidence_strength": strength,
        "evidence": evidence,
        "blocker": blocker,
        "next_action": next_action,
    }


def build_candidate_rows(candidates: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in candidates:
        rows.append(
            [
                item["name"],
                item["evidence_strength"],
                "<br>".join(item["evidence"]) if item["evidence"] else "none",
                item["blocker"],
                item["next_action"],
            ]
        )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# QRTR Service Selector\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- vendor_root: `{manifest['inputs']['vendor_root']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend(
        [
            "\n## v270 Readback Evidence\n\n",
            markdown_table(
                ["run", "decision", "service", "instance", "events", "service_events", "timeout", "qmi_attempted"],
                [
                    [
                        "primary",
                        str(manifest["v270"]["primary"].get("decision")),
                        str(manifest["v270"]["primary"].get("service")),
                        str(manifest["v270"]["primary"].get("instance")),
                        str(manifest["v270"]["primary"].get("events")),
                        str(manifest["v270"]["primary"].get("service_events")),
                        str(manifest["v270"]["primary"].get("timeout")),
                        str(manifest["v270"]["primary"].get("qmi_attempted")),
                    ],
                    [
                        "long",
                        str(manifest["v270"]["long"].get("decision")),
                        str(manifest["v270"]["long"].get("service")),
                        str(manifest["v270"]["long"].get("instance")),
                        str(manifest["v270"]["long"].get("events")),
                        str(manifest["v270"]["long"].get("service_events")),
                        str(manifest["v270"]["long"].get("timeout")),
                        str(manifest["v270"]["long"].get("qmi_attempted")),
                    ],
                ],
            ),
            "\n\n## Candidate Services\n\n",
            markdown_table(
                ["candidate", "strength", "evidence", "blocker", "next action"],
                build_candidate_rows(manifest["candidates"]),
            ),
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
    libqmi_cci = vendor_root / "lib64/libqmi_cci.so"
    primary_manifest_path = repo_path(args.v270_primary_manifest)
    long_manifest_path = repo_path(args.v270_long_manifest)

    primary_manifest = load_json(primary_manifest_path)
    long_manifest = load_json(long_manifest_path)
    primary_v270 = v270_readback_summary(primary_manifest)
    long_v270 = v270_readback_summary(long_manifest)

    captures: dict[str, dict[str, Any]] = {}
    for name, command in (
        ("cnss-strings", ["strings", str(cnss_daemon)]),
        ("cnss-readelf-symbols", ["aarch64-linux-gnu-readelf", "-Ws", str(cnss_daemon)]),
        ("cnss-readelf-relocs", ["aarch64-linux-gnu-readelf", "-Wr", str(cnss_daemon)]),
        ("qmiservices-strings", ["strings", str(libqmiservices)]),
        ("qmiservices-readelf-symbols", ["aarch64-linux-gnu-readelf", "-Ws", str(libqmiservices)]),
        ("qmi-cci-strings", ["strings", str(libqmi_cci)]),
        ("qmi-cci-readelf-symbols", ["aarch64-linux-gnu-readelf", "-Ws", str(libqmi_cci)]),
    ):
        capture = run_host_command(command, timeout=args.host_timeout)
        captures[name] = capture
        write_capture(store, name, capture)

    cnss_text = captures["cnss-strings"].get("text", "") + "\n" + captures["cnss-readelf-symbols"].get("text", "")
    qmiservices_text = captures["qmiservices-strings"].get("text", "") + "\n" + captures["qmiservices-readelf-symbols"].get("text", "")
    qmi_cci_text = captures["qmi-cci-strings"].get("text", "") + "\n" + captures["qmi-cci-readelf-symbols"].get("text", "")

    cnss_qmi_symbols = symbols_from_text(cnss_text, QMI_CLIENT_SYMBOL_RE)
    qmi_cci_symbols = symbols_from_text(qmi_cci_text, QMI_CLIENT_SYMBOL_RE)
    service_objects = service_objects_from_text(qmiservices_text)
    service_names = {item["name"] for item in service_objects}
    family_lines = {
        name: text_lines_containing(cnss_text, patterns)
        for name, patterns in CNSS_FAMILY_PATTERNS.items()
    }

    checks: list[dict[str, Any]] = []
    for key, path in (
        ("cnss-daemon", cnss_daemon),
        ("libqmiservices", libqmiservices),
        ("libqmi_cci", libqmi_cci),
    ):
        add_check(checks, f"{key}-exists", path.exists(), str(path))
    add_check(
        checks,
        "v270-primary-timeout-zero-events",
        primary_v270.get("decision") == "qrtr-ns-readback-timeout"
        and primary_v270.get("pass") is True
        and str(primary_v270.get("service")) == "1"
        and str(primary_v270.get("instance")) == "1"
        and str(primary_v270.get("events")) == "0"
        and str(primary_v270.get("qmi_attempted")) == "0",
        json.dumps(primary_v270, sort_keys=True),
    )
    add_check(
        checks,
        "v270-long-timeout-zero-events",
        long_v270.get("decision") == "qrtr-ns-readback-timeout"
        and long_v270.get("pass") is True
        and str(long_v270.get("service")) == "1"
        and str(long_v270.get("instance")) == "1"
        and str(long_v270.get("events")) == "0"
        and str(long_v270.get("qmi_attempted")) == "0",
        json.dumps(long_v270, sort_keys=True),
    )
    add_check(
        checks,
        "cnss-imports-qmi-client",
        any(symbol.startswith("qmi_client_") for symbol in cnss_qmi_symbols),
        ", ".join(cnss_qmi_symbols[:20]) or "none",
    )
    add_check(
        checks,
        "cnss-imports-dms-service-object",
        "dms" in service_names and "dms_get_service_object_internal_v01" in cnss_text,
        "dms in libqmiservices and cnss references dms_get_service_object_internal_v01",
    )
    add_check(
        checks,
        "cnss-has-wlfw-evidence",
        bool(family_lines["wlfw"]),
        "; ".join(family_lines["wlfw"][:8]) or "none",
        severity="warning",
    )
    add_check(
        checks,
        "qmi-cci-has-service-id-helper",
        "qmi_idl_get_service_id" in qmi_cci_symbols or "qmi_idl_get_service_id" in qmi_cci_text,
        ", ".join(symbol for symbol in qmi_cci_symbols if symbol.startswith("qmi_idl_")) or "none",
    )

    candidates = [
        classify_candidate(
            "service=1 instance=1",
            [
                "v269/v270 send path works",
                "v270 1s and 3s readback returned zero events",
            ],
            "negative",
            "no nameservice response for selected arbitrary service/instance",
            "deprioritize until actual service IDs are extracted",
        ),
        classify_candidate(
            "dms",
            [
                "cnss-daemon references dms_get_service_object_internal_v01",
                "libqmiservices exports dms_get_service_object_internal_v01",
                "cnss-daemon logs DMS MAC-address flow",
            ],
            "strong",
            "numeric QMI service id/instance not extracted in native evidence yet",
            "extract service id via service object + qmi_idl_get_service_id without sending QMI payload",
        ),
        classify_candidate(
            "wlfw",
            [
                "cnss-daemon strings include WLFW/wlfw_service_request",
                "likely Qualcomm WLAN firmware service boundary",
            ],
            "strong-but-unresolved",
            "service object symbol not exported by libqmiservices in current evidence",
            "locate embedded/private service object or Android source mapping before live lookup",
        ),
        classify_candidate(
            "wlan",
            [
                "cnss-daemon strings include wlan_service_request and WLAN service messages",
            ],
            "medium",
            "ambiguous whether this is QMI service, local socket service, or daemon internal label",
            "keep as secondary candidate after WLFW/DMS object extraction",
        ),
    ]

    critical_pass = all(item["pass"] for item in checks if item["severity"] == "critical")
    decision = "qrtr-service-selector-ready" if critical_pass else "qrtr-service-selector-incomplete"
    reason = (
        "service=1 readback is negative; DMS/WLFW/WLAN evidence requires service-object ID extraction before more live packets"
        if critical_pass
        else "critical prerequisite evidence is missing"
    )
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-service-selector",
        "decision": decision,
        "pass": critical_pass,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {
            "vendor_root": str(vendor_root),
            "cnss_daemon": str(cnss_daemon),
            "libqmiservices": str(libqmiservices),
            "libqmi_cci": str(libqmi_cci),
            "v270_primary_manifest": str(primary_manifest_path),
            "v270_long_manifest": str(long_manifest_path),
        },
        "host_metadata": collect_host_metadata(),
        "v270": {
            "primary": primary_v270,
            "long": long_v270,
        },
        "captures": {
            name: {
                "command": capture["command"],
                "rc": capture["rc"],
                "ok": capture["ok"],
                "error": capture["error"],
                "text_file": f"captures/{name}.txt",
            }
            for name, capture in captures.items()
        },
        "symbol_evidence": {
            "cnss_qmi_symbols": cnss_qmi_symbols,
            "qmi_cci_symbols": qmi_cci_symbols,
            "libqmiservices_service_objects": service_objects,
            "cnss_family_lines": family_lines,
        },
        "checks": checks,
        "candidates": candidates,
        "next_candidates": [
            "v272 QMI service-object ID extractor plan: execute no-payload service-object introspection only",
            "WLFW service object locator if exported symbols remain absent",
            "Only after numeric IDs are evidence-based, consider another explicit-approval QRTR nameservice lookup",
        ],
        "guardrails": [
            "host-only analysis",
            "no QRTR socket opened",
            "no QRTR nameservice packet sent",
            "no QMI payload sent",
            "no device command executed",
            "no cnss-daemon/cnss_diag/HAL/supplicant/wificond/hostapd start",
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
    parser.add_argument("--v270-primary-manifest", type=Path, default=DEFAULT_V270_PRIMARY_MANIFEST)
    parser.add_argument("--v270-long-manifest", type=Path, default=DEFAULT_V270_LONG_MANIFEST)
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
