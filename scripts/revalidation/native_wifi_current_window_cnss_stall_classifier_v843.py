#!/usr/bin/env python3
"""V843 host-only classifier for the current-window V840 CNSS stall snapshot.

V842 selected a current-window `cnss-daemon` stall snapshot.  V840 already
captured that snapshot with helper v130, so V843 parses the latest evidence
instead of rerunning the live proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v843-current-window-cnss-stall-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v843-current-window-cnss-stall-classifier.txt")
DEFAULT_V842_MANIFEST = Path("tmp/wifi/v842-cnss-prewlfw-contract-classifier/manifest.json")
DEFAULT_V840_MANIFEST = Path("tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json")
DEFAULT_V840_HELPER = Path("tmp/wifi/v840-provider-first-prearmed-listener-live/native/companion-start-only-with-holder.txt")

EXPECTED_V842 = "v842-current-window-cnss-stall-snapshot-selected"
EXPECTED_V840 = "v840-provider-first-prearmed-no-indication"

BLOCK_BEGIN_RE = re.compile(r"^A90_EXECNS_(?:CNSS_PROC|PATH)_(?P<name>[A-Za-z0-9_]+)_BEGIN\b")
BLOCK_END_RE = re.compile(r"^A90_EXECNS_(?:CNSS_PROC|PATH)_(?P<name>[A-Za-z0-9_]+)_END\b")
TASK_WCHAN_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_wchan")
TASK_SYSCALL_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_syscall")
TASK_STATUS_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_status")
TASK_STAT_RE = re.compile(r"wifi_hal_composite_cnss_daemon_retry_stall_task_(?P<tid>[0-9]+)_stat")
FD_TARGET_RE = re.compile(r"^capture\.wifi_hal_composite_cnss_daemon_retry\.fd_links\.entry_(?P<index>[0-9]+)\.target=(?P<target>.*)$")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v842-manifest", type=Path, default=DEFAULT_V842_MANIFEST)
    parser.add_argument("--v840-manifest", type=Path, default=DEFAULT_V840_MANIFEST)
    parser.add_argument("--v840-helper", type=Path, default=DEFAULT_V840_HELPER)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(repo_path(path))}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(repo_path(path)), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(repo_path(path)), "error": "not-json-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(repo_path(path)))
    return data


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def input_item(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": data.get("path"),
        "exists": data.get("exists", False),
        "decision": data.get("decision", ""),
        "pass": bool_value(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
    }


def parse_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
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
    for line in blocks.get(name, "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def parse_task_surface(blocks: dict[str, str]) -> list[dict[str, str]]:
    tasks: dict[str, dict[str, str]] = {}
    for name in blocks:
        for pattern, field in (
            (TASK_STATUS_RE, "status"),
            (TASK_STAT_RE, "stat"),
            (TASK_WCHAN_RE, "wchan"),
            (TASK_SYSCALL_RE, "syscall"),
        ):
            match = pattern.match(name)
            if match:
                tasks.setdefault(match.group("tid"), {})[field] = first_line(blocks, name)
                break
    return [{"tid": tid, **values} for tid, values in sorted(tasks.items(), key=lambda item: int(item[0]))]


def parse_fd_targets(text: str) -> list[str]:
    targets: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = FD_TARGET_RE.match(line.strip())
        if match:
            targets.append((int(match.group("index")), match.group("target").strip()))
    return [target for _, target in sorted(targets)]


def parse_retry_pid(v840: dict[str, Any], helper_text: str) -> str:
    for pattern in (
        r"^capture\.wifi_hal_composite_cnss_daemon_retry\.stall_snapshot\.pid=(\d+)$",
        r"^wifi_hal_composite_start\.child\.cnss_daemon_retry\.pid=(\d+)$",
    ):
        match = re.search(pattern, helper_text, re.MULTILINE)
        if match:
            return match.group(1)
    return str(
        nested(
            v840,
            "provider_first_prearmed",
            "provider_manifest",
            "live",
            "v655_surface",
            "children",
            "cnss_daemon_retry",
            "pid",
        )
        or ""
    )


def marker_counts(v840: dict[str, Any]) -> dict[str, int]:
    provider = nested(v840, "provider_first_prearmed", "provider_manifest") or {}
    live = provider.get("live") if isinstance(provider.get("live"), dict) else {}
    counts = live.get("v655_counts") if isinstance(live.get("v655_counts"), dict) else {}
    markers = nested(live, "markers", "counts") or {}
    result: dict[str, int] = {}
    for key in (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
        "kernel_warning",
    ):
        result[key] = int_value(counts.get(key))
    for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlfw", "bdf"):
        result[f"marker_{key}"] = int_value(markers.get(key))
    return result


def build_surface(v840: dict[str, Any], helper_text: str) -> dict[str, Any]:
    blocks = parse_blocks(helper_text)
    tasks = parse_task_surface(blocks)
    fd_targets = parse_fd_targets(helper_text)
    qrtr = blocks.get("wifi_stall_proc_net_qrtr", "")
    netlink = blocks.get("wifi_stall_proc_net_netlink", "")
    unix = blocks.get("wifi_stall_proc_net_unix", "")
    counts = marker_counts(v840)
    task_wchan_counts = {
        name: sum(1 for task in tasks if task.get("wchan") == name)
        for name in sorted({task.get("wchan", "") for task in tasks if task.get("wchan")})
    }
    syscall_counts = {
        name: sum(1 for task in tasks if task.get("syscall", "").startswith(name))
        for name in ("73 ", "98 ")
    }
    retry_pid = parse_retry_pid(v840, helper_text)
    return {
        "block_count": len(blocks),
        "counts": counts,
        "main_wchan": first_line(blocks, "wifi_stall_cnss_wchan"),
        "main_syscall": first_line(blocks, "wifi_stall_cnss_syscall"),
        "main_stack": blocks.get("wifi_stall_cnss_stack", ""),
        "main_stat": first_line(blocks, "wifi_stall_cnss_stat"),
        "main_sched_first": first_line(blocks, "wifi_stall_cnss_sched"),
        "tasks": tasks,
        "task_count": len(tasks),
        "task_wchan_counts": task_wchan_counts,
        "task_syscall_prefix_counts": syscall_counts,
        "fd_targets": fd_targets,
        "fd_count": len(fd_targets),
        "socket_fd_count": sum(1 for target in fd_targets if target.startswith("socket:[")),
        "vndbinder_fd_count": sum(1 for target in fd_targets if target.endswith("/dev/vndbinder") or "/dev/vndbinder" in target),
        "cnss_user_socket": "/data/vendor/wifi/sockets/cnss_user_server" in unix,
        "qrtr_surface": qrtr.strip(),
        "qrtr_missing": "open-error=No such file or directory" in qrtr,
        "netlink_has_retry_pid": bool(retry_pid and re.search(rf"\b{re.escape(str(retry_pid))}\b", netlink)),
        "netlink_sample": "\n".join(netlink.splitlines()[:12]),
        "unix_sample": "\n".join(unix.splitlines()[:12]),
        "retry_pid": retry_pid,
        "stall_snapshot_captured": "wifi_companion_start.child.cnss_daemon_retry.stall_snapshot_captured=1" in helper_text,
    }


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v842 = load_json(args.v842_manifest)
    v840 = load_json(args.v840_manifest)
    helper_text = read_text(args.v840_helper)
    surface = build_surface(v840, helper_text) if helper_text else {}
    counts = surface.get("counts") if isinstance(surface.get("counts"), dict) else {}
    polling_stall = (
        surface.get("stall_snapshot_captured") is True
        and surface.get("main_wchan") == "do_sys_poll"
        and str(surface.get("main_syscall", "")).startswith("73 ")
        and int_value(counts.get("service_notifier_180")) > 0
        and int_value(counts.get("service_notifier_74")) > 0
        and int_value(counts.get("cnss_daemon_netlink")) > 0
        and int_value(counts.get("cnss_daemon_cld80211")) > 0
        and int_value(counts.get("wlfw_start")) == 0
        and int_value(counts.get("wlan_pd")) == 0
        and int_value(counts.get("wlan0")) == 0
    )
    futex_workers = int_value((surface.get("task_wchan_counts") or {}).get("futex_wait_queue_me")) > 0
    cnss_socket_ready = bool(surface.get("cnss_user_socket"))
    netlink_ready = bool(surface.get("netlink_has_retry_pid"))
    qrtr_proc_gap = bool(surface.get("qrtr_missing"))
    return {
        "inputs": {
            "v842": input_item(v842),
            "v840": input_item(v840),
            "v840_helper": {
                "path": str(repo_path(args.v840_helper)),
                "exists": bool(helper_text),
                "bytes": len(helper_text),
            },
        },
        "surface": surface,
        "derived": {
            "polling_stall_after_provider_first": polling_stall,
            "futex_worker_threads_present": futex_workers,
            "cnss_user_socket_present": cnss_socket_ready,
            "netlink_entry_for_retry_pid": netlink_ready,
            "proc_net_qrtr_missing_in_namespace": qrtr_proc_gap,
            "selected_next_gate": "v844-icnss-wlfw-event-source-classifier",
        },
        "candidate_matrix": [
            candidate(
                "repeat provider-first CNSS retry",
                "reject",
                "V840 already captured the retry alive in poll/futex wait with no WLFW/BDF/wlan0 progression",
                "do not rerun without changing observability or event-source hypothesis",
            ),
            candidate(
                "Wi-Fi HAL / scan / connect / DHCP / external ping",
                "blocked",
                "native still lacks wlfw_start, WLAN-PD UP, BDF, wiphy, and wlan0",
                "keep final bring-up blocked until lower event source advances",
            ),
            candidate(
                "CNSS daemon launcher contract",
                "closed",
                "V842 closes coarse command/identity/domain/capability/fd contract; V843 confirms the process is alive waiting",
                "do not redesign launcher before resolving missing event source",
            ),
            candidate(
                "ICNSS/WLFW event source",
                "select-next",
                "cnss-daemon waits in poll/futex with CNSS socket and netlink surfaces, so the missing input is the kernel/platform WLFW event source",
                "V844 should classify source-backed ICNSS/WLFW event publication prerequisites before any HAL/connect action",
            ),
        ],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = analysis["inputs"]
    add_check(
        checks,
        "v842-input",
        "pass" if inputs["v842"].get("exists") and inputs["v842"].get("pass") and inputs["v842"].get("decision") == EXPECTED_V842 else "blocked",
        "blocker",
        f"decision={inputs['v842'].get('decision')} pass={inputs['v842'].get('pass')} expected={EXPECTED_V842}",
        "refresh V842 before using V843",
    )
    add_check(
        checks,
        "v840-input",
        "pass" if inputs["v840"].get("exists") and inputs["v840"].get("pass") and inputs["v840"].get("decision") == EXPECTED_V840 else "blocked",
        "blocker",
        f"decision={inputs['v840'].get('decision')} pass={inputs['v840'].get('pass')} expected={EXPECTED_V840}",
        "refresh V840 before parsing current-window stall evidence",
    )
    add_check(
        checks,
        "v840-helper-transcript",
        "pass" if inputs["v840_helper"].get("exists") else "blocked",
        "blocker",
        str(inputs["v840_helper"]),
        "provide V840 helper transcript before parsing stall snapshot",
    )
    derived = analysis["derived"]
    add_check(
        checks,
        "provider-first-polling-stall",
        "pass" if derived["polling_stall_after_provider_first"] else "blocked",
        "blocker",
        str(analysis["surface"].get("counts", {})),
        "rerun a bounded current-window stall snapshot only if the existing one is incomplete",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V843 reads existing V840 evidence only",
        "keep V843 non-mutating",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v843-current-window-cnss-stall-plan-ready",
            True,
            "plan-only; no device command, daemon start, Wi-Fi action, credential, route, ping, or flash executed",
            "run V843 host-only classifier against V840 snapshot",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v843-current-window-cnss-stall-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting V844",
        )
    return (
        "v843-cnss-retry-poll-futex-prewlfw-event-gap",
        True,
        "current V840 cnss-daemon retry is alive in poll/futex wait with CNSS socket/netlink surfaces, while WLFW/WLAN-PD/BDF/wlan0 remain absent",
        "V844 should classify the missing source-backed ICNSS/WLFW event publication prerequisite before Wi-Fi HAL or scan/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["analysis"]["surface"]
    derived = manifest["analysis"]["derived"]
    task_rows = [
        [task.get("tid", ""), task.get("wchan", ""), task.get("syscall", "")]
        for task in surface.get("tasks", [])
    ]
    return "\n".join([
        "# V843 Current-Window CNSS Stall Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Derived",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in derived.items()]),
        "",
        "## Stall Surface",
        "",
        markdown_table(["signal", "value"], [
            ["retry_pid", surface.get("retry_pid", "")],
            ["main_wchan", surface.get("main_wchan", "")],
            ["main_syscall", surface.get("main_syscall", "")],
            ["task_wchan_counts", surface.get("task_wchan_counts", {})],
            ["fd_count", surface.get("fd_count", "")],
            ["socket_fd_count", surface.get("socket_fd_count", "")],
            ["vndbinder_fd_count", surface.get("vndbinder_fd_count", "")],
            ["cnss_user_socket", surface.get("cnss_user_socket", "")],
            ["netlink_has_retry_pid", surface.get("netlink_has_retry_pid", "")],
            ["qrtr_surface", surface.get("qrtr_surface", "")],
        ]),
        "",
        "## Tasks",
        "",
        markdown_table(["tid", "wchan", "syscall"], task_rows) if task_rows else "- not captured",
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted((surface.get("counts") or {}).items())]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in manifest["analysis"]["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    checks = build_checks(analysis)
    decision, passed, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v843",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
