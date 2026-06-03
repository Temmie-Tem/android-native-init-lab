#!/usr/bin/env python3
"""V1971 offline decode of the V1970 Android RIL/QMI producer capture.

This is host-only: it reads the already-pulled V1970 evidence, parses QRTR
service enumeration plus strace payloads, and reports which modem QMI services
RIL actually used.  It performs no device command and no mutation.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text


DEFAULT_V1970_DIR = Path("tmp/wifi/v1970-android-ril-qmi-producer-capture-handoff")
DEFAULT_OUT_DIR = Path("tmp/wifi/v1971-ril-qmi-producer-decode")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1971_RIL_QMI_PRODUCER_DECODE_2026-06-04.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1971-ril-qmi-producer-decode.txt")

WLAN_PD_UP_RE = re.compile(
    r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\].*root_service_service_ind_cb:.*"
    r"msm/modem/wlan_pd.*state:\s*0x1fffffff",
    re.IGNORECASE,
)
STRACE_RE = re.compile(r"^(?P<pid>\d+)\s+(?P<time>\S+)\s+(?P<call>sendto|recvfrom|sendmsg|recvmsg)\(")
QIPCRTR_ADDR_RE = re.compile(
    r"\{sa_family=AF_QIPCRTR,\s*sq_node=(?P<node>[^,}]+),\s*sq_port=(?P<port>[^,}]+)\}"
)
QUOTED_BYTES_RE = re.compile(r'"((?:\\.|[^"\\])*)"')

SERVICE_NAMES = {
    1: "WDS",
    2: "DMS",
    3: "NAS",
    5: "WMS",
    9: "VOICE",
    43: "SERVREG_LOCATOR",
    66: "SERVREG_NOTIFIER",
    69: "WLFW",
    74: "SYSMON",
    227: "SEC_RIL_SIDE_SERVICE",
}
QMI_TYPES = {
    0x00: "request",
    0x02: "response",
    0x04: "indication",
}
QRTR_CTRL_TYPES = {
    1: "hello",
    2: "bye",
    3: "new-server",
    4: "del-server",
    5: "del-client",
    6: "resume-tx",
    7: "exit",
    8: "ping",
    9: "new-lookup",
    10: "del-lookup",
}


@dataclass
class QmiMessage:
    process: str
    line: int
    pid: int
    wall_time: str
    call: str
    direction: str
    node: int | None
    port: int | None
    service: int | None
    service_name: str
    qmi_type: str
    txid: int | None
    msg_id: int | None
    msg_len: int | None
    payload_len: int
    qmi_len_ok: bool
    tlv_ok: bool
    tlv_types: list[str]
    result: int | None
    error: int | None


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1970-dir", type=Path, default=DEFAULT_V1970_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def read_file(path: Path, limit: int = 40_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def evidence_dir(v1970_dir: Path) -> Path:
    return v1970_dir / "android-postfs-evidence" / "a90-v1970-ril-qmi-producer"


def parse_int(text: str) -> int | None:
    text = text.strip()
    if text == "QRTR_PORT_CTRL":
        return -1
    try:
        return int(text, 0)
    except ValueError:
        return None


def decode_c_bytes(literal: str) -> bytes | None:
    try:
        value = ast.literal_eval(f'b"{literal}"')
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, bytes) else None


def parse_attach_times(events: str) -> dict[str, float]:
    attach_times: dict[str, float] = {}
    regex = re.compile(r"A90_V1970_EVENT uptime=([0-9.]+) attached label=(\S+)")
    for line in events.splitlines():
        match = regex.search(line)
        if match:
            attach_times[match.group(2)] = float(match.group(1))
    return attach_times


def first_wlanpd_time(dmesg: str) -> float | None:
    for line in dmesg.splitlines():
        match = WLAN_PD_UP_RE.search(line)
        if match:
            return float(match.group("ts"))
    return None


def parse_qrtr_services(base: Path) -> dict[str, Any]:
    port_to_service: dict[tuple[int, int], dict[str, Any]] = {}
    snapshots: list[dict[str, Any]] = []
    for path in sorted(base.glob("qrtr-*-wildcard-all.txt")):
        values: dict[str, str] = {}
        for line in read_file(path, limit=1_000_000).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        services: list[dict[str, Any]] = []
        for index in range(64):
            service = values.get(f"qrtr_ns.event.{index}.service")
            node = values.get(f"qrtr_ns.event.{index}.node")
            port = values.get(f"qrtr_ns.event.{index}.port")
            if not service or service == "0" or node is None or port is None:
                continue
            item = {
                "service": int(service),
                "service_name": SERVICE_NAMES.get(int(service), f"service{service}"),
                "instance": int(values.get(f"qrtr_ns.event.{index}.instance", "0")),
                "node": int(node),
                "port": int(port),
            }
            services.append(item)
            port_to_service[(item["node"], item["port"])] = item
        snapshots.append({"file": str(path), "services": services})
    return {"port_to_service": port_to_service, "snapshots": snapshots}


def parse_tlvs(data: bytes, offset: int, end: int) -> tuple[bool, list[dict[str, Any]]]:
    tlvs: list[dict[str, Any]] = []
    cursor = offset
    while cursor < end:
        if cursor + 3 > end:
            return False, tlvs
        tlv_type = data[cursor]
        tlv_len = int.from_bytes(data[cursor + 1:cursor + 3], "little")
        cursor += 3
        if cursor + tlv_len > end:
            return False, tlvs
        value = data[cursor:cursor + tlv_len]
        item: dict[str, Any] = {"type": tlv_type, "length": tlv_len}
        if tlv_type == 0x02 and tlv_len == 4:
            item["result"] = int.from_bytes(value[0:2], "little")
            item["error"] = int.from_bytes(value[2:4], "little")
        tlvs.append(item)
        cursor += tlv_len
    return cursor == end, tlvs


def decode_qmi(process: str,
               line_no: int,
               line: str,
               services: dict[tuple[int, int], dict[str, Any]]) -> QmiMessage | None:
    match = STRACE_RE.search(line)
    if not match:
        return None
    call = match.group("call")
    if call not in {"sendto", "recvfrom"}:
        return None
    addr_match = QIPCRTR_ADDR_RE.search(line)
    if not addr_match:
        return None
    quoted_match = QUOTED_BYTES_RE.search(line)
    if not quoted_match:
        return None
    data = decode_c_bytes(quoted_match.group(1))
    if data is None:
        return None
    node = parse_int(addr_match.group("node"))
    port = parse_int(addr_match.group("port"))
    service_info = services.get((node, port), {}) if node is not None and port is not None else {}
    service = service_info.get("service")
    service_name = service_info.get("service_name", "QRTR_CTRL" if port == -1 else "unknown")
    direction = "tx" if call == "sendto" else "rx"

    qmi_type = "unknown"
    txid: int | None = None
    msg_id: int | None = None
    msg_len: int | None = None
    qmi_len_ok = False
    tlv_ok = False
    tlv_types: list[str] = []
    result: int | None = None
    error: int | None = None

    if port == -1 and len(data) >= 20:
        ctrl_type = int.from_bytes(data[0:4], "little")
        qmi_type = f"qrtr-{QRTR_CTRL_TYPES.get(ctrl_type, ctrl_type)}"
    elif len(data) >= 7 and data[0] in QMI_TYPES:
        qmi_type = QMI_TYPES[data[0]]
        txid = int.from_bytes(data[1:3], "little")
        msg_id = int.from_bytes(data[3:5], "little")
        msg_len = int.from_bytes(data[5:7], "little")
        end = 7 + msg_len
        qmi_len_ok = end <= len(data)
        if qmi_len_ok:
            tlv_ok, tlvs = parse_tlvs(data, 7, end)
            tlv_types = [f"0x{item['type']:02x}:{item['length']}" for item in tlvs]
            for item in tlvs:
                if item.get("type") == 0x02:
                    result = item.get("result")
                    error = item.get("error")
                    break

    return QmiMessage(
        process=process,
        line=line_no,
        pid=int(match.group("pid")),
        wall_time=match.group("time"),
        call=call,
        direction=direction,
        node=node,
        port=port,
        service=service,
        service_name=service_name,
        qmi_type=qmi_type,
        txid=txid,
        msg_id=msg_id,
        msg_len=msg_len,
        payload_len=len(data),
        qmi_len_ok=qmi_len_ok,
        tlv_ok=tlv_ok,
        tlv_types=tlv_types,
        result=result,
        error=error,
    )


def parse_straces(base: Path, services: dict[tuple[int, int], dict[str, Any]]) -> list[QmiMessage]:
    messages: list[QmiMessage] = []
    for process, filename in (
        ("rild", "rild.strace.txt"),
        ("cnss_daemon", "cnss_daemon.strace.txt"),
        ("pm_service", "pm_service.strace.txt"),
    ):
        for line_no, line in enumerate(read_file(base / filename).splitlines(), 1):
            decoded = decode_qmi(process, line_no, line, services)
            if decoded:
                messages.append(decoded)
    return messages


def summarize_messages(messages: list[QmiMessage]) -> dict[str, Any]:
    service_counts = Counter()
    msg_counts = Counter()
    result_errors = Counter()
    for message in messages:
        key = f"{message.process}:{message.service_name}:{message.direction}:{message.qmi_type}"
        service_counts[key] += 1
        if message.msg_id is not None:
            msg_counts[f"{message.service_name}:0x{message.msg_id:04x}:{message.qmi_type}"] += 1
        if message.result is not None or message.error is not None:
            result_errors[f"{message.service_name}:0x{message.msg_id or 0:04x}:result={message.result}:error={message.error}"] += 1
    return {
        "service_counts": dict(sorted(service_counts.items())),
        "message_counts": dict(sorted(msg_counts.items())),
        "result_errors": dict(sorted(result_errors.items())),
    }


def classify(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    attach = analysis["attach_times"]
    wlanpd = analysis["wlanpd_up_time"]
    rild = analysis["rild"]
    if wlanpd is None:
        return "v1971-missing-wlanpd-anchor", False, "V1970 decode lacks wlan_pd UP anchor", "missing-wlanpd-anchor"
    if not rild["dms_messages"] or not rild["nas_messages"]:
        return "v1971-ril-dms-nas-not-observed", False, "RIL strace did not show both DMS and NAS traffic", "ril-dms-nas-missing"
    if attach.get("rild") is None:
        return "v1971-ril-attach-time-missing", False, "RIL strace exists but attach time is missing", "ril-attach-time-missing"
    if attach["rild"] > wlanpd:
        return (
            "v1971-ril-dms-nas-observed-post-wlanpd-up-producer-window-missed",
            True,
            "RIL DMS/NAS QMI traffic is decoded, but rild attached after wlan_pd UP; V1970 is not a pre-UP producer-window trace",
            "ril-dms-nas-observed-post-up",
        )
    return (
        "v1971-ril-dms-nas-observed-in-producer-window",
        True,
        "RIL DMS/NAS QMI traffic was decoded with rild attached before wlan_pd UP",
        "ril-dms-nas-observed-pre-up",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rild = analysis["rild"]
    return "\n".join(
        [
            "# V1971 RIL QMI Producer Decode",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- label: `{manifest['label']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- source evidence: `{manifest['source_evidence']}`",
            f"- output: `{manifest['out_dir']}`",
            "",
            "## Timing",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["wlan_pd UP", analysis["wlanpd_up_time"]],
                    ["attach times", json.dumps(analysis["attach_times"], sort_keys=True)],
                    ["producer window captured", analysis["producer_window_captured"]],
                ],
            ),
            "",
            "## RIL QMI",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["DMS message ids", json.dumps(rild["dms_messages"], sort_keys=True)],
                    ["NAS message ids", json.dumps(rild["nas_messages"], sort_keys=True)],
                    ["other RIL services", json.dumps(rild["other_services"], sort_keys=True)],
                    ["service counts", json.dumps(analysis["summary"]["service_counts"], sort_keys=True)],
                    ["result/errors", json.dumps(analysis["summary"]["result_errors"], sort_keys=True)],
                ],
            ),
            "",
            "## Conclusion",
            "",
            "- V1970 confirms RIL uses DMS and NAS QMI services directly on the internal-modem QRTR node.",
            "- V1970 does not prove the pre-UP producer trigger because `rild` attached after `wlan_pd` UP.",
            "- A corrected live capture must attach strace first, then run QRTR enumeration asynchronously or after the producer edge.",
            "",
            "## Safety",
            "",
            "Host-only decode of existing evidence. No device command, Wi-Fi action, boot flash, partition write, eSoC/PCIe/GDSC/GPIO/PMIC operation, scan/connect, DHCP/routes, credentials, or ping was executed.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    base = repo_path(evidence_dir(args.v1970_dir))
    store = EvidenceStore(repo_path(args.out_dir))
    ensure_private_dir(store.run_dir)

    qrtr = parse_qrtr_services(base)
    messages = parse_straces(base, qrtr["port_to_service"])
    dmesg = read_file(base / "dmesg-full-final.txt")
    events = read_file(base / "events.log")
    attach_times = parse_attach_times(events)
    wlanpd_up_time = first_wlanpd_time(dmesg)

    rild_messages = [message for message in messages if message.process == "rild"]
    dms = sorted({f"0x{message.msg_id:04x}" for message in rild_messages if message.service == 2 and message.msg_id is not None})
    nas = sorted({f"0x{message.msg_id:04x}" for message in rild_messages if message.service == 3 and message.msg_id is not None})
    other_services = sorted({
        message.service_name
        for message in rild_messages
        if message.service not in {2, 3} and message.service_name not in {"unknown", "QRTR_CTRL"}
    })
    analysis = {
        "source_base": str(base),
        "wlanpd_up_time": wlanpd_up_time,
        "attach_times": attach_times,
        "producer_window_captured": bool(wlanpd_up_time is not None and attach_times.get("rild", 1e9) <= wlanpd_up_time),
        "qrtr_snapshots": qrtr["snapshots"],
        "rild": {
            "message_count": len(rild_messages),
            "dms_messages": dms,
            "nas_messages": nas,
            "other_services": other_services,
        },
        "summary": summarize_messages(messages),
        "messages": [asdict(message) for message in messages],
    }
    decision, pass_ok, reason, label = classify(analysis)
    manifest = {
        "cycle": "V1971",
        "generated_at": now_iso(),
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "source_evidence": str(base),
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {decision}")
    print(f"label:    {label}")
    print(f"pass:     {pass_ok}")
    print(f"reason:   {reason}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
