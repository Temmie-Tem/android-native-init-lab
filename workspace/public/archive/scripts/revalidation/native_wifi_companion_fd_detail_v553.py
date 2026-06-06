#!/usr/bin/env python3
"""V553 bounded companion fd detail mapper.

This reuses the V552 socket-family mapper and expects helper v79, which adds
`fdinfo` capture plus `tcp6`/`udp6`/`raw`/`raw6` tables while the companion
daemons are alive. It still avoids QRTR nameservice transmit, QMI payload,
Wi-Fi HAL start, scan/connect, link-up, and external ping.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_socket_family_v552 as v552


base = v552.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v553-companion-fd-detail")
base.DEFAULT_HELPER_SHA256 = "6fae544321c0c29136bc280757323e66d9a67bc1ac862700b3cd46131641914e"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v79"
base.PROOF_VERSION = "V553"
base.PROOF_SLUG = "v553-companion-fd-detail"
base.LIVE_HELPER_STEP_NAME = "v553-helper-run"
base.APPROVAL_PHRASE = (
    "approve v553 companion fd detail mapper only; "
    "no QRTR nameservice transmit, no QMI payload, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

v552.SOCKET_TABLES.update({
    "tcp6": "wifi_companion_net_tcp6",
    "udp6": "wifi_companion_net_udp6",
    "raw": "wifi_companion_net_raw",
    "raw6": "wifi_companion_net_raw6",
})

FDINFO_RE = re.compile(
    r"^capture\.wifi_hal_composite_(?P<child>qrtr_ns|tftp_server|pd_mapper|cnss_diag|cnss_daemon)"
    r"\.fd_links\.entry_(?P<entry>[0-9]+)\.fdinfo\.(?P<key>pos|flags|mnt_id|ino)=(?P<value>.+)$"
)

_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_classify = base.classify


def _fdinfo_map(text: str) -> dict[tuple[str, str], dict[str, str]]:
    values: dict[tuple[str, str], dict[str, str]] = {}
    for line in text.splitlines():
        match = FDINFO_RE.match(line.strip())
        if not match:
            continue
        key = (match.group("child"), match.group("entry"))
        values.setdefault(key, {})[match.group("key")] = match.group("value").lstrip("?\t ")
    return values


def _detail_rows(rows: list[dict[str, str]], fdinfo: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, str]]:
    detail_rows: list[dict[str, str]] = []
    for row in rows:
        info = fdinfo.get((row["child"], row["entry"]), {})
        detail = dict(row)
        detail["fdinfo_present"] = "1" if info else "0"
        detail["fdinfo_ino"] = info.get("ino", "")
        detail["fdinfo_mnt_id"] = info.get("mnt_id", "")
        detail["fdinfo_flags"] = info.get("flags", "")
        detail_rows.append(detail)
    return detail_rows


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    live_text = base.step_payload([result.get("live", {})], base.LIVE_HELPER_STEP_NAME)
    fdinfo = _fdinfo_map(live_text)
    rows = result.get("socket_family_rows") or []
    detail_rows = _detail_rows(rows, fdinfo)
    result["socket_fd_detail_rows"] = detail_rows
    result["socket_fdinfo_count"] = len(fdinfo)
    result["socket_fdinfo_missing_count"] = sum(1 for row in detail_rows if row.get("fdinfo_present") != "1")
    result["socket_fdinfo_ino_missing_count"] = sum(1 for row in detail_rows if not row.get("fdinfo_ino"))
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
    fdinfo_count = int(live_result.get("socket_fdinfo_count") or 0)
    fdinfo_missing = int(live_result.get("socket_fdinfo_missing_count") or 0)
    fdinfo_ino_missing = int(live_result.get("socket_fdinfo_ino_missing_count") or 0)
    if not rows:
        return (
            "v553-fd-detail-no-socket-fds",
            True,
            "no QRTR-related companion socket fd rows were captured",
            "inspect helper fd capture before any QRTR transmit",
            live_executed,
        )
    if counts.get("unmapped", 0):
        return (
            "v553-fd-detail-unmapped-sockets",
            True,
            f"unmapped socket fds remain after expanded table capture: counts={counts} fdinfo={fdinfo_count} missing_fdinfo={fdinfo_missing} missing_fdinfo_ino={fdinfo_ino_missing}",
            "add bounded socket-domain metadata or QRTR-specific readback before QMI/HAL retry",
            live_executed,
        )
    return (
        "v553-fd-detail-no-unmapped-sockets",
        True,
        f"all companion socket fds mapped after expanded table capture: counts={counts} fdinfo={fdinfo_count} missing_fdinfo={fdinfo_missing} missing_fdinfo_ino={fdinfo_ino_missing}",
        "inspect missing Android QRTR/QMI prerequisites before HAL retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    detail_rows = [
        [
            row["child"],
            row["entry"],
            row["inode"],
            row["family"],
            row.get("fdinfo_ino", ""),
            row.get("fdinfo_mnt_id", ""),
            row.get("fdinfo_flags", ""),
        ]
        for row in (live.get("socket_fd_detail_rows") or [])[:160]
    ]
    return "\n".join([
        text,
        "",
        "## Socket FD Details",
        "",
        f"- fdinfo_count: `{live.get('socket_fdinfo_count', 0)}`",
        f"- fdinfo_missing_count: `{live.get('socket_fdinfo_missing_count', 0)}`",
        f"- fdinfo_ino_missing_count: `{live.get('socket_fdinfo_ino_missing_count', 0)}`",
        "",
        base.markdown_table(
            ["child", "entry", "inode", "family", "fdinfo_ino", "mnt_id", "flags"],
            detail_rows,
        ) if detail_rows else "- none",
    ])


base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
