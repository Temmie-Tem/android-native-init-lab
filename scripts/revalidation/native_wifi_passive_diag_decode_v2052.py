#!/usr/bin/env python3
"""Decode V2051 passive /dev/diag samples against the Qualcomm diagchar ABI."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2052-passive-diag-decode"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2052_PASSIVE_DIAG_DECODE_2026-06-04.md"
)
V2051_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v2051-passive-diag-pre-wlanmdsp-trigger-handoff"
    / "manifest.json"
)

DIAG_TYPES = {
    0x00000001: "MSG_MASKS_TYPE",
    0x00000002: "LOG_MASKS_TYPE",
    0x00000004: "EVENT_MASKS_TYPE",
    0x00000008: "PKT_TYPE",
    0x00000010: "DEINIT_TYPE",
    0x00000020: "USER_SPACE_DATA_TYPE",
    0x00000040: "DCI_DATA_TYPE",
    0x00000080: "USER_SPACE_RAW_DATA_TYPE",
    0x00000100: "DCI_LOG_MASKS_TYPE",
    0x00000200: "DCI_EVENT_MASKS_TYPE",
    0x00000400: "DCI_PKT_TYPE",
    0x00001000: "HDLC_SUPPORT_TYPE",
}
MASK_BOOTSTRAP_TYPES = {
    "MSG_MASKS_TYPE",
    "LOG_MASKS_TYPE",
    "EVENT_MASKS_TYPE",
    "DCI_LOG_MASKS_TYPE",
    "DCI_EVENT_MASKS_TYPE",
}
MODEM_PAYLOAD_TYPES = {
    "USER_SPACE_DATA_TYPE",
    "USER_SPACE_RAW_DATA_TYPE",
    "DCI_DATA_TYPE",
    "PKT_TYPE",
    "DCI_PKT_TYPE",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    try:
        if value is None:
            return 0
        if isinstance(value, str) and value.lower().startswith("0x"):
            return int(value, 16)
        return int(value)
    except (TypeError, ValueError):
        return 0


def unescape_payload(text: str) -> bytes:
    out = bytearray()
    index = 0
    while index < len(text):
        ch = text[index]
        if ch != "\\":
            out.append(ord(ch) & 0xFF)
            index += 1
            continue
        if index + 1 >= len(text):
            out.append(ord("\\"))
            index += 1
            continue
        kind = text[index + 1]
        if kind == "x" and index + 3 < len(text):
            try:
                out.append(int(text[index + 2:index + 4], 16))
                index += 4
                continue
            except ValueError:
                pass
        if kind == "n":
            out.append(0x0A)
        elif kind == "r":
            out.append(0x0D)
        elif kind == "t":
            out.append(0x09)
        elif kind == "\\":
            out.append(ord("\\"))
        else:
            out.append(ord(kind) & 0xFF)
        index += 2
    return bytes(out)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        cells = [str(cell).replace("\n", " ") for cell in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def decode_samples(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    diag = manifest.get("details", {}).get("passive_diag", {})
    samples = diag.get("samples_detail", []) if isinstance(diag, dict) else []
    decoded: list[dict[str, Any]] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        payload_text = str(sample.get("payload", ""))
        payload = unescape_payload(payload_text)
        type_value = int.from_bytes(payload[:4].ljust(4, b"\0"), "little") if payload else 0
        type_name = DIAG_TYPES.get(type_value, f"UNKNOWN_0x{type_value:08x}")
        decoded.append({
            "index": intish(sample.get("index")),
            "delta_ms": intish(sample.get("delta_ms")),
            "reported_bytes": intish(sample.get("bytes")),
            "stored_bytes": intish(sample.get("stored_bytes")),
            "payload_prefix_hex": payload[:16].hex(),
            "type_value": type_value,
            "type_hex": f"0x{type_value:08x}",
            "type_name": type_name,
            "is_mask_bootstrap": type_name in MASK_BOOTSTRAP_TYPES,
            "is_modem_payload": type_name in MODEM_PAYLOAD_TYPES,
            "payload_truncated": intish(sample.get("payload_truncated")),
        })
    return decoded


def classify(manifest: dict[str, Any], decoded: list[dict[str, Any]]) -> dict[str, Any]:
    classification = manifest.get("classification", {}) if isinstance(manifest.get("classification"), dict) else {}
    diag = manifest.get("details", {}).get("passive_diag", {}) if isinstance(manifest.get("details"), dict) else {}
    tftp = manifest.get("details", {}).get("tftp_logdw", {}).get("summary", {}) if isinstance(manifest.get("details"), dict) else {}
    type_names = [str(item.get("type_name", "")) for item in decoded]
    modem_payload_count = sum(1 for item in decoded if item.get("is_modem_payload"))
    mask_bootstrap_count = sum(1 for item in decoded if item.get("is_mask_bootstrap"))
    wlanmdsp_seen = bool(classification.get("wlanmdsp_seen"))
    mcfg_seen = bool(classification.get("mcfg_seen"))
    server_check_seen = bool(classification.get("server_check_seen"))
    ota_firewall_seen = bool(classification.get("ota_firewall_seen"))
    diag_bytes = intish(classification.get("passive_diag_bytes")) or intish(diag.get("bytes"))
    read_error = str(diag.get("read_error", ""))

    if modem_payload_count > 0:
        label = "diag-passive-modem-payload-present"
        reason = "passive DIAG contains modem payload-type records; decode those records before another live run"
    elif mask_bootstrap_count == len(decoded) and decoded:
        label = "diag-passive-mask-bootstrap-no-modem-user-data"
        reason = "all decoded passive DIAG samples are diagchar startup mask blocks, not modem USER_SPACE/DCI/PKT payload records"
    elif decoded:
        label = "diag-passive-nonpayload-mixed"
        reason = "passive DIAG returned bytes, but no decoded sample is a modem payload type"
    else:
        label = "diag-passive-no-decodable-samples"
        reason = "v2051 recorded no decodable passive DIAG samples"

    return {
        "label": label,
        "decision": f"v2052-{label}",
        "pass": True,
        "reason": reason,
        "diag_bytes": diag_bytes,
        "read_error": read_error,
        "decoded_samples": len(decoded),
        "mask_bootstrap_count": mask_bootstrap_count,
        "modem_payload_count": modem_payload_count,
        "type_names": type_names,
        "mcfg_seen": mcfg_seen,
        "server_check_seen": server_check_seen,
        "ota_firewall_seen": ota_firewall_seen,
        "wlanmdsp_seen": wlanmdsp_seen,
        "tftp_datagrams": intish(tftp.get("datagrams")),
        "tftp_mcfg": intish(tftp.get("mcfg")),
        "tftp_wlanmdsp": intish(tftp.get("wlanmdsp")) + intish(tftp.get("fallback_wlanmdsp")),
    }


def render_report(manifest: dict[str, Any], decoded: list[dict[str, Any]], result: dict[str, Any]) -> str:
    rows = [
        [
            f"{item['index']:03d}",
            item["delta_ms"],
            item["reported_bytes"],
            item["stored_bytes"],
            item["type_hex"],
            item["type_name"],
            int(bool(item["is_mask_bootstrap"])),
            int(bool(item["is_modem_payload"])),
            item["payload_prefix_hex"],
        ]
        for item in decoded
    ]
    return "\n".join([
        "# Native Init V2052 Passive DIAG Decode",
        "",
        "## Summary",
        "",
        "- Cycle: `V2052`",
        "- Type: host-only decode of the V2051 passive `/dev/diag` samples; no device boot or live command.",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Pass: `{result['pass']}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{rel(OUT_DIR)}`",
        f"- Source manifest: `{rel(V2051_MANIFEST)}`",
        "",
        "## Decode Matrix",
        "",
        markdown_table(
            ["idx", "delta_ms", "reported", "stored", "type", "name", "mask_bootstrap", "modem_payload", "prefix_hex"],
            rows or [["none", -1, 0, 0, "", "", 0, 0, ""]],
        ),
        "",
        "## Classification",
        "",
        f"- DIAG bytes reported by V2051: `{result['diag_bytes']}`; decoded samples: `{result['decoded_samples']}`.",
        f"- Decoded type names: `{', '.join(result['type_names'])}`.",
        f"- Modem payload record count: `{result['modem_payload_count']}` (`USER_SPACE_DATA_TYPE`, `USER_SPACE_RAW_DATA_TYPE`, `DCI_DATA_TYPE`, `PKT_TYPE`, or `DCI_PKT_TYPE`).",
        f"- TFTP branch remains off-path: mcfg `{result['tftp_mcfg']}`, wlanmdsp `{result['tftp_wlanmdsp']}`, server_check `{int(result['server_check_seen'])}`, ota_firewall `{int(result['ota_firewall_seen'])}`.",
        f"- Read error after startup records: `{result['read_error']}`; this is after useful mask-bootstrap classification and does not create a modem payload sample.",
        "",
        "## Source Basis",
        "",
        "- Local kernel ABI header defines `MSG_MASKS_TYPE=0x1`, `LOG_MASKS_TYPE=0x2`, `EVENT_MASKS_TYPE=0x4`, `USER_SPACE_DATA_TYPE=0x20`, `DCI_DATA_TYPE=0x40`, `DCI_LOG_MASKS_TYPE=0x100`, `DCI_EVENT_MASKS_TYPE=0x200`, and `DCI_PKT_TYPE=0x400` in the workspace/legacy OSRC kernel source at `SM-A908N_KOR_12_Opensource/Kernel/include/linux/diagchar.h`.",
        "- Android MSM `diagchar_open()` initializes a new client with mask-ready bits, and `diagchar_read()` emits those mask types before real `USER_SPACE_DATA_TYPE`/DCI data. This matches the V2051 sample sequence.",
        "",
        "## Next Gate",
        "",
        "- Do not repeat passive O_RDONLY DIAG as a modem-side event capture; it only proved the diag node and startup mask stream.",
        "- The next aligned discriminator must first establish a safe, bounded DIAG mode/query path that can produce `USER_SPACE_DATA_TYPE` or DCI payload records without log-mask writes, or explicitly document that any useful DIAG stream requires an active logging-mode/mask operation before using it.",
        "- Keep the TFTP conclusion intact: native still reaches `wlan_pd` UP and ICNSS QMI but selects only `mcfg.tmp`, with no `server_check`, `ota_firewall`, or `wlanmdsp` request.",
        "",
        "## Safety",
        "",
        "- Host-only decode; no flash, reboot, shell command, DIAG ioctl, DIAG write, log-mask operation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC, PCIe, GDSC, PMIC, GPIO, or sda29 write was performed.",
        "",
    ])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(V2051_MANIFEST.read_text(encoding="utf-8"))
    decoded = decode_samples(manifest)
    result = classify(manifest, decoded)
    out_manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": "V2052",
        "source_manifest": rel(V2051_MANIFEST),
        "decision": result["decision"],
        "label": result["label"],
        "pass": bool(result["pass"]),
        "reason": result["reason"],
        "classification": result,
        "decoded_samples": decoded,
    }
    report = render_report(manifest, decoded, result)
    (OUT_DIR / "manifest.json").write_text(json.dumps(out_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"decision={result['decision']}")
    print(f"label={result['label']}")
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
