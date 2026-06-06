#!/usr/bin/env python3
"""V709 host-only classifier for V708 CNSS retry stall evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v709-v708-stall-classifier")
DEFAULT_V708_MANIFEST = Path(
    "tmp/wifi/v708-provider-first-cnss-v120-orchestrated-run-2/"
    "arm-v700-v119-provider-first-cnss/live/manifest.json"
)
DEFAULT_V708_HELPER = Path(
    "tmp/wifi/v708-provider-first-cnss-v120-orchestrated-run-2/"
    "arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt"
)

BLOCK_BEGIN_RE = re.compile(r"^A90_EXECNS_(?:CNSS_PROC|PATH)_(?P<name>[A-Za-z0-9_]+)_BEGIN\b")
BLOCK_END_RE = re.compile(r"^A90_EXECNS_(?:CNSS_PROC|PATH)_(?P<name>[A-Za-z0-9_]+)_END\b")
TASK_WCHAN_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_wchan")
TASK_SYSCALL_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_syscall")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v708-manifest", type=Path, default=DEFAULT_V708_MANIFEST)
    parser.add_argument("--v708-helper", type=Path, default=DEFAULT_V708_HELPER)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def parse_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        begin = BLOCK_BEGIN_RE.match(line)
        if begin:
            current = begin.group("name")
            blocks.setdefault(current, [])
            continue
        end = BLOCK_END_RE.match(line)
        if end and current == end.group("name"):
            current = None
            continue
        if current is not None:
            blocks.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in blocks.items()}


def first_line(blocks: dict[str, str], name: str) -> str:
    text = blocks.get(name, "")
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_tasks(blocks: dict[str, str]) -> list[dict[str, str]]:
    by_tid: dict[str, dict[str, str]] = {}
    for name, value in blocks.items():
        wchan = TASK_WCHAN_RE.search(name)
        if wchan:
            by_tid.setdefault(wchan.group("tid"), {})["wchan"] = first_line(blocks, name)
            continue
        syscall = TASK_SYSCALL_RE.search(name)
        if syscall:
            by_tid.setdefault(syscall.group("tid"), {})["syscall"] = first_line(blocks, name)
    return [{"tid": tid, **values} for tid, values in sorted(by_tid.items(), key=lambda item: int(item[0]))]


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    live = manifest.get("live") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    result: dict[str, int] = {}
    for key in (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "kernel_warning",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ):
        try:
            result[key] = int(counts.get(key, 0) or 0)
        except ValueError:
            result[key] = 0
    for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlfw", "bdf"):
        try:
            result[f"marker_{key}"] = int(markers.get(key, 0) or 0)
        except ValueError:
            result[f"marker_{key}"] = 0
    return result


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v708_manifest)
    helper_text = read_text(args.v708_helper)
    blocks = parse_blocks(helper_text)
    tasks = parse_tasks(blocks)
    main_wchan = first_line(blocks, "wifi_stall_cnss_wchan")
    main_syscall = first_line(blocks, "wifi_stall_cnss_syscall")
    stack = blocks.get("wifi_stall_cnss_stack", "")
    qrtr = blocks.get("wifi_stall_proc_net_qrtr", "")
    netlink = blocks.get("wifi_stall_proc_net_netlink", "")
    counts = marker_counts(manifest)
    return {
        "manifest_path": str(repo_path(args.v708_manifest)),
        "helper_path": str(repo_path(args.v708_helper)),
        "manifest_decision": manifest.get("decision", ""),
        "manifest_pass": manifest.get("pass"),
        "cnss_retry_stall_captured": bool(manifest.get("cnss_retry_stall_captured")),
        "counts": counts,
        "main_wchan": main_wchan,
        "main_syscall": main_syscall,
        "main_stack": stack,
        "tasks": tasks,
        "task_wchan_counts": {
            name: sum(1 for task in tasks if task.get("wchan") == name)
            for name in sorted({task.get("wchan", "") for task in tasks if task.get("wchan")})
        },
        "qrtr_surface": qrtr,
        "netlink_has_cnss_pid": " 986 " in netlink or re.search(r"\b986\b", netlink) is not None,
        "netlink_sample": "\n".join(netlink.splitlines()[:12]),
        "block_count": len(blocks),
    }


def decide(command: str, surface: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v709-v708-stall-classifier-plan-ready",
            True,
            "plan-only; no live command executed",
            "run V709 host-only classifier against V708 evidence",
        )
    if not surface:
        return "v709-v708-stall-evidence-missing", False, "V708 evidence missing", "rerun V708 or provide evidence paths"
    counts = surface.get("counts") or {}
    if not surface.get("cnss_retry_stall_captured"):
        return (
            "v709-v708-stall-capture-missing",
            False,
            "V708 manifest does not prove cnss retry stall capture",
            "fix helper v120 capture parsing before another live run",
        )
    if (
        surface.get("main_wchan") == "do_sys_poll"
        and counts.get("service_notifier_180", 0) > 0
        and counts.get("service_notifier_74", 0) > 0
        and counts.get("qmi_server_connected", 0) == 0
        and counts.get("wlfw_start", 0) == 0
        and counts.get("wlan0", 0) == 0
    ):
        return (
            "v709-cnss-retry-polling-pre-wlfw-kernel-event-gap",
            True,
            "cnss-daemon retry is alive in poll/futex wait after service180/74 and provider registration, while WLFW/QMI/BDF/wlan0 remain absent",
            "classify missing kernel ICNSS/WLFW event source before Wi-Fi HAL or scan/connect",
        )
    return (
        "v709-cnss-retry-stall-surface-captured",
        True,
        f"wchan={surface.get('main_wchan')} syscall={surface.get('main_syscall')} counts={counts}",
        "inspect stall surface before another live mutation",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest.get("surface") or {}
    counts = surface.get("counts") or {}
    task_rows = [
        [task.get("tid", ""), task.get("wchan", ""), task.get("syscall", "")]
        for task in surface.get("tasks") or []
    ]
    count_rows = [[key, str(value)] for key, value in sorted(counts.items())]
    return "\n".join([
        "# V709 V708 Stall Classifier",
        "",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next: {manifest.get('next')}",
        f"- evidence: `{manifest.get('evidence_dir')}`",
        "",
        "## Stall Surface",
        "",
        f"- manifest_decision: `{surface.get('manifest_decision', '')}`",
        f"- cnss_retry_stall_captured: `{surface.get('cnss_retry_stall_captured', '')}`",
        f"- main_wchan: `{surface.get('main_wchan', '')}`",
        f"- main_syscall: `{surface.get('main_syscall', '')}`",
        f"- task_wchan_counts: `{surface.get('task_wchan_counts', {})}`",
        f"- qrtr_surface: `{surface.get('qrtr_surface', '')}`",
        f"- netlink_has_cnss_pid: `{surface.get('netlink_has_cnss_pid', '')}`",
        "",
        "## Tasks",
        "",
        markdown_table(["tid", "wchan", "syscall"], task_rows) if task_rows else "- not captured",
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], count_rows) if count_rows else "- not captured",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    surface = None if args.command == "plan" else build_surface(args)
    decision, pass_ok, reason, next_step = decide(args.command, surface)
    return {
        "cycle": "v709",
        "created_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next": next_step,
        "evidence_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "surface": surface or {},
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "dhcp_or_external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"dhcp_or_external_ping_executed: {manifest['dhcp_or_external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
