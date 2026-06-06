#!/usr/bin/env python3
"""v267 QRTR nameservice packet layout artifact generator.

Host-only. Generates QRTR control packet bytes for review, but never opens a
socket, contacts the device, or transmits QRTR/QMI packets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v267-qrtr-packet-layout")
QRTR_PORT_CTRL = 0xFFFFFFFE
QRTR_TYPE_NEW_LOOKUP = 10
QRTR_TYPE_DEL_LOOKUP = 11
QRTR_CTRL_PKT_SIZE = 20

REFERENCE_URLS = {
    "linux_qrtr_uapi": "https://codebrowser.dev/linux/include/linux/qrtr.h.html",
    "linux_qrtr_ns": "https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_u32(name: str, value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be uint32 integer: {value!r}") from exc
    if parsed < 0 or parsed > 0xFFFFFFFF:
        raise argparse.ArgumentTypeError(f"{name} outside uint32 range: {parsed}")
    return parsed


def packet_bytes(cmd: int, service: int, instance: int) -> bytes:
    return struct.pack("<IIIII", cmd, service, instance, 0, 0)


def packet_record(name: str, cmd: int, service: int, instance: int) -> dict[str, Any]:
    raw = packet_bytes(cmd, service, instance)
    fields = struct.unpack("<IIIII", raw)
    return {
        "name": name,
        "cmd": cmd,
        "service": service,
        "instance": instance,
        "node": 0,
        "port": 0,
        "length": len(raw),
        "hex": raw.hex(),
        "field_words_le": list(fields),
        "offsets": {
            "cmd": "0..3",
            "service": "4..7",
            "instance": "8..11",
            "node": "12..15",
            "port": "16..19",
        },
    }


def build_checks(args: argparse.Namespace, new_lookup: dict[str, Any], del_lookup: dict[str, Any]) -> list[dict[str, Any]]:
    wildcard = args.service == 0 and args.instance == 0
    return [
        {
            "name": "new-lookup-cmd",
            "pass": new_lookup["cmd"] == QRTR_TYPE_NEW_LOOKUP,
            "severity": "critical",
            "detail": str(new_lookup["cmd"]),
        },
        {
            "name": "del-lookup-cmd",
            "pass": del_lookup["cmd"] == QRTR_TYPE_DEL_LOOKUP,
            "severity": "critical",
            "detail": str(del_lookup["cmd"]),
        },
        {
            "name": "packet-lengths",
            "pass": new_lookup["length"] == QRTR_CTRL_PKT_SIZE and del_lookup["length"] == QRTR_CTRL_PKT_SIZE,
            "severity": "critical",
            "detail": json.dumps({"new": new_lookup["length"], "del": del_lookup["length"]}, sort_keys=True),
        },
        {
            "name": "service-instance-explicit",
            "pass": isinstance(args.service, int) and isinstance(args.instance, int),
            "severity": "critical",
            "detail": json.dumps({"service": args.service, "instance": args.instance}, sort_keys=True),
        },
        {
            "name": "wildcard-blocked",
            "pass": not wildcard or args.allow_wildcard_lookup,
            "severity": "critical",
            "detail": json.dumps({"wildcard": wildcard, "allow_wildcard_lookup": args.allow_wildcard_lookup}, sort_keys=True),
        },
        {
            "name": "host-only-no-transmit",
            "pass": True,
            "severity": "critical",
            "detail": "no socket, bridge command, or QRTR/QMI transmission",
        },
    ]


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-packet-layout-blocked", "packet layout check failed: " + ", ".join(failed)
    return True, "qrtr-packet-layout-ready", "QRTR nameservice control packet layout is ready for review without transmission"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], "PASS" if item["pass"] else "FAIL", item["severity"], item["detail"]] for item in manifest["checks"]]
    packet_rows = []
    for packet in manifest["packets"]:
        packet_rows.append([
            packet["name"],
            str(packet["cmd"]),
            str(packet["service"]),
            str(packet["instance"]),
            str(packet["length"]),
            packet["hex"],
        ])
    ref_rows = [[key, value] for key, value in manifest["references"].items()]
    return "".join([
        "# v267 QRTR Nameservice Packet Layout\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        "- QRTR/QMI packet transmission: `not executed`\n",
        "- Wi-Fi scan/connect/link-up: `not executed`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], check_rows),
        "\n\n## Packets\n\n",
        markdown_table(["packet", "cmd", "service", "instance", "length", "hex"], packet_rows),
        "\n\n## Field Offsets\n\n",
        "- `cmd`: bytes `0..3`, little-endian uint32\n",
        "- `service`: bytes `4..7`, little-endian uint32\n",
        "- `instance`: bytes `8..11`, little-endian uint32\n",
        "- `node`: bytes `12..15`, zero for NEW_LOOKUP/DEL_LOOKUP requests\n",
        "- `port`: bytes `16..19`, zero for NEW_LOOKUP/DEL_LOOKUP requests\n\n",
        "## References\n\n",
        markdown_table(["reference", "url"], ref_rows),
        "\n\n## Guardrails\n\n",
        "- This tool does not open QRTR sockets.\n",
        "- This tool does not run bridge commands.\n",
        "- This tool does not send QRTR nameservice packets or QMI requests.\n",
        "- Actual transmission remains explicit-approval-gated.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--service", type=lambda value: parse_u32("service", value), required=True)
    parser.add_argument("--instance", type=lambda value: parse_u32("instance", value), required=True)
    parser.add_argument("--allow-wildcard-lookup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    new_lookup = packet_record("QRTR_TYPE_NEW_LOOKUP", QRTR_TYPE_NEW_LOOKUP, args.service, args.instance)
    del_lookup = packet_record("QRTR_TYPE_DEL_LOOKUP", QRTR_TYPE_DEL_LOOKUP, args.service, args.instance)
    checks = build_checks(args, new_lookup, del_lookup)
    pass_ok, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-packet-layout",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "constants": {
            "QRTR_PORT_CTRL": QRTR_PORT_CTRL,
            "QRTR_TYPE_NEW_LOOKUP": QRTR_TYPE_NEW_LOOKUP,
            "QRTR_TYPE_DEL_LOOKUP": QRTR_TYPE_DEL_LOOKUP,
            "QRTR_CTRL_PKT_SIZE": QRTR_CTRL_PKT_SIZE,
        },
        "packets": [new_lookup, del_lookup],
        "checks": checks,
        "references": REFERENCE_URLS,
        "guardrails": [
            "host-only packet layout",
            "no bridge command",
            "no QRTR socket open",
            "no QRTR/QMI packet transmission",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("new-lookup.hex", new_lookup["hex"] + "\n")
    store.write_text("del-lookup.hex", del_lookup["hex"] + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
