#!/usr/bin/env python3
"""V552 bounded companion socket family mapper.

This reuses the V551 QRTR window snapshot and expects helper v78, which captures
additional `/proc/net/*` socket tables while the companion daemons are alive.
It maps child `socket:[inode]` fds to captured socket table families without
QRTR nameservice transmit, QMI payload, Wi-Fi HAL start, scan/connect, or ping.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_qrtr_window_v551 as v551


base = v551.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v552-companion-socket-family")
base.DEFAULT_HELPER_SHA256 = "6d381a2bdc548fc45c4d89262d02bd2d61bdb2696ba2267be1251feb7522ef88"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v78"
base.PROOF_VERSION = "V552"
base.PROOF_SLUG = "v552-companion-socket-family"
base.LIVE_HELPER_STEP_NAME = "v552-helper-run"
base.APPROVAL_PHRASE = (
    "approve v552 companion socket family mapper only; "
    "no QRTR nameservice transmit, no QMI payload, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

FD_SOCKET_RE = re.compile(
    r"^capture\.wifi_hal_composite_(?P<child>qrtr_ns|tftp_server|pd_mapper|cnss_diag|cnss_daemon)"
    r"\.fd_links\.entry_(?P<entry>[0-9]+)\.target=socket:\[(?P<inode>[0-9]+)\]$"
)

SOCKET_TABLES = {
    "netlink": "wifi_companion_net_netlink",
    "unix": "wifi_companion_net_unix",
    "packet": "wifi_companion_net_packet",
    "tcp": "wifi_companion_net_tcp",
    "udp": "wifi_companion_net_udp",
}

_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_classify = base.classify


def _section_lines(text: str, label: str) -> list[str]:
    begin = f"A90_EXECNS_CNSS_PROC_{label}_BEGIN"
    end = f"A90_EXECNS_CNSS_PROC_{label}_END"
    inside = False
    lines: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.startswith(begin):
            inside = True
            continue
        if raw_line.startswith(end):
            inside = False
            continue
        if inside:
            lines.append(raw_line)
    return lines


def _header_inode_index(lines: list[str]) -> int | None:
    for line in lines:
        fields = line.split()
        for index, field in enumerate(fields):
            if field.lower() == "inode":
                return index
    return None


def _section_inode_set(lines: list[str], family: str) -> set[str]:
    inodes: set[str] = set()
    inode_index = _header_inode_index(lines)
    for line in lines:
        fields = line.split()
        if not fields or fields[0].lower() in {"sk", "num", "sl"}:
            continue
        if family == "unix" and fields[0].endswith(":"):
            candidate_index = inode_index if inode_index is not None else 6
        elif family in {"netlink", "packet", "tcp", "udp"}:
            candidate_index = inode_index if inode_index is not None else len(fields) - 1
        else:
            candidate_index = inode_index if inode_index is not None else -1
        if -len(fields) <= candidate_index < len(fields):
            token = fields[candidate_index]
            if token.isdigit():
                inodes.add(token)
    return inodes


def _fd_socket_rows(text: str) -> list[dict[str, str]]:
    table_inodes = {
        family: _section_inode_set(_section_lines(text, label), family)
        for family, label in SOCKET_TABLES.items()
    }
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        match = FD_SOCKET_RE.match(line.strip())
        if not match:
            continue
        inode = match.group("inode")
        families = [family for family, inodes in table_inodes.items() if inode in inodes]
        rows.append({
            "child": match.group("child"),
            "entry": match.group("entry"),
            "inode": inode,
            "family": ",".join(families) if families else "unmapped",
        })
    return rows


def _family_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        family = row["family"]
        counts[family] = counts.get(family, 0) + 1
    return counts


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    live_text = base.step_payload([result.get("live", {})], base.LIVE_HELPER_STEP_NAME)
    rows = _fd_socket_rows(live_text)
    result["socket_family_rows"] = rows
    result["socket_family_counts"] = _family_counts(rows)
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("all_postflight_safe"):
        return decision, pass_ok, reason, next_step, live_executed
    if live_result.get("helper_result") != "companion-window-pass":
        return decision, pass_ok, reason, next_step, live_executed

    rows = live_result.get("socket_family_rows") or []
    counts = live_result.get("socket_family_counts") or {}
    if not rows:
        return (
            "v552-socket-family-no-socket-fds",
            True,
            "no QRTR-related companion socket fd rows were captured",
            "inspect helper fd capture before any QRTR transmit",
            live_executed,
        )
    if counts.get("unmapped", 0):
        return (
            "v552-socket-family-unmapped-sockets",
            True,
            f"some companion socket fds did not map to captured tables: {counts}",
            "extend socket table capture or add fdinfo/sock_diag before QRTR nameservice transmit",
            live_executed,
        )
    return (
        "v552-socket-family-no-qrtr-family",
        True,
        f"companion socket fds mapped to non-QRTR tables only: {counts}",
        "inspect missing Android QRTR/QMI prerequisites such as qmiproxy, sysmon-qmi, and service-notifier before HAL retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        [row["child"], row["entry"], row["inode"], row["family"]]
        for row in (live.get("socket_family_rows") or [])[:160]
    ]
    counts = [[key, value] for key, value in sorted((live.get("socket_family_counts") or {}).items())]
    return "\n".join([
        text,
        "",
        "## Socket Family Counts",
        "",
        base.markdown_table(["family", "count"], counts) if counts else "- none",
        "",
        "## Socket Family Rows",
        "",
        base.markdown_table(["child", "entry", "inode", "family"], rows) if rows else "- none",
    ])


base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
