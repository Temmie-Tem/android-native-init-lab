#!/usr/bin/env python3
"""V934 host-only fresh-pid CNSS/service-manager attribution classifier.

V931/V933 post dmesg tails can include earlier CNSS runs. This classifier
attributes dmesg lines to the current helper-spawned child PIDs before deciding
whether Binder, service-manager, or lower MDM/SDX50M readiness remains the
blocker.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v934-cnss-fresh-pid-attribution")
LATEST_POINTER = Path("tmp/wifi/latest-v934-cnss-fresh-pid-attribution.txt")
DEFAULT_V927_DIR = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live")
DEFAULT_V931_DIR = Path("tmp/wifi/v931-cnss-service-manager-matrix-live")
DEFAULT_V933_DIR = Path("tmp/wifi/v933-cnss-service-manager-before-cnss-live")
DEFAULT_V601_MANIFEST = Path("tmp/wifi/v601-modem-holder-service-manager/manifest.json")
DEFAULT_V603_MANIFEST = Path("tmp/wifi/v603-qrtr-first-service-manager-live/manifest.json")


@dataclass(frozen=True)
class FreshCase:
    label: str
    decision: str
    order: str
    cnss_pid: int | None
    mdm_helper_pid: int | None
    mdm_helper_thread_pids: list[int]
    current_cnss_dmesg_lines: int
    current_cnss_binder_failures: int
    stale_cnss_binder_failures: int
    current_cnss_cld80211: int
    current_cnss_wlfw: int
    current_cnss_bdf: int
    current_cnss_wlan0: int
    current_mdm_queue_failures: int
    any_mdm_queue_failures: int
    mdm_helper_esoc0_fd_seen: bool
    service_manager_started: bool
    wlfw_precondition_observed: bool
    subsys_esoc0_open_attempted: bool


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v927-dir", type=Path, default=DEFAULT_V927_DIR)
    parser.add_argument("--v931-dir", type=Path, default=DEFAULT_V931_DIR)
    parser.add_argument("--v933-dir", type=Path, default=DEFAULT_V933_DIR)
    parser.add_argument("--v601-manifest", type=Path, default=DEFAULT_V601_MANIFEST)
    parser.add_argument("--v603-manifest", type=Path, default=DEFAULT_V603_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace").replace("\0", "\n")


def contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})


def last_int(pattern: str, text: str) -> int | None:
    matches = re.findall(pattern, text)
    if not matches:
        return None
    return int(matches[-1])


def child_pid(child: str, text: str) -> int | None:
    return last_int(rf"wifi_hal_composite_start\.child\.{re.escape(child)}\.pid=(\d+)", text)


def child_thread_pids(child: str, text: str) -> list[int]:
    capture_marker = f"capture.wifi_hal_composite_{child}.fd_links"
    lines = text.splitlines()
    capture_indices = [idx for idx, line in enumerate(lines) if capture_marker in line]
    if not capture_indices:
        return []
    start = max(0, capture_indices[0] - 80)
    end = min(len(lines), capture_indices[-1] + 260)
    pids = {int(value) for value in re.findall(r"\[anon:stack_and_tls:(\d+)\]", "\n".join(lines[start:end]))}
    return sorted(pids)


def pid_lines(dmesg: str, comm: str, pid: int | None) -> list[str]:
    if pid is None:
        return []
    pattern = re.compile(rf"\b{re.escape(comm)}:\s*{pid}\]", re.IGNORECASE)
    return [line for line in dmesg.splitlines() if pattern.search(line)]


def mdm_lines(dmesg: str, pids: set[int]) -> list[str]:
    rows: list[str] = []
    for line in dmesg.splitlines():
        if "mdm_helper:" not in line:
            continue
        if any(re.search(rf"\b{pid}\]", line) for pid in pids):
            rows.append(line)
    return rows


def count(rows: list[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for row in rows if regex.search(row))


def all_binder_failures(dmesg: str) -> int:
    return count(dmesg.splitlines(), r"cnss-daemon.*(?:transaction failed|returned -22|ioctl 40046210)")


def case_from_dir(label: str, run_dir: Path) -> FreshCase:
    manifest = load_json(run_dir / "manifest.json")
    helper = read_text(run_dir / "native/mdm-helper-cnss-before-esoc.txt")
    dmesg = read_text(run_dir / "native/post-dmesg-wifi-esoc-tail.txt")
    data = contract(manifest)
    cnss_pid = child_pid("cnss_daemon", helper)
    mdm_pid = child_pid("mdm_helper", helper)
    mdm_threads = child_thread_pids("mdm_helper", helper)
    cnss_rows = pid_lines(dmesg, "cnss-daemon", cnss_pid)
    mdm_pid_set = {pid for pid in [mdm_pid, *mdm_threads] if pid is not None}
    mdm_rows_current = mdm_lines(dmesg, mdm_pid_set)
    current_binder = count(cnss_rows, r"transaction failed|returned -22|ioctl 40046210")
    total_binder = all_binder_failures(dmesg)
    return FreshCase(
        label=label,
        decision=str(manifest.get("decision")),
        order=str(data.get("service_manager_order") or "none"),
        cnss_pid=cnss_pid,
        mdm_helper_pid=mdm_pid,
        mdm_helper_thread_pids=mdm_threads,
        current_cnss_dmesg_lines=len(cnss_rows),
        current_cnss_binder_failures=current_binder,
        stale_cnss_binder_failures=max(0, total_binder - current_binder),
        current_cnss_cld80211=count(cnss_rows, r"cld80211"),
        current_cnss_wlfw=count(cnss_rows, r"wlfw"),
        current_cnss_bdf=count(cnss_rows, r"BDF|bdwlan|regdb"),
        current_cnss_wlan0=count(cnss_rows, r"\bwlan0\b"),
        current_mdm_queue_failures=count(mdm_rows_current, r"unable to queue event for SDX50M"),
        any_mdm_queue_failures=count(dmesg.splitlines(), r"mdm_helper.*unable to queue event for SDX50M"),
        mdm_helper_esoc0_fd_seen=str(data.get("mdm_helper_esoc0_fd_seen") or "0") == "1",
        service_manager_started=str(data.get("service_manager_started") or "0") == "1",
        wlfw_precondition_observed=bool(manifest.get("wlfw_precondition_observed")),
        subsys_esoc0_open_attempted=bool(manifest.get("subsys_esoc0_open_attempted")),
    )


def service_manager_reference(label: str, manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    live = manifest.get("live") or {}
    counts = live.get("v603_counts") or live.get("v601_counts") or {}
    return {
        "label": label,
        "decision": manifest.get("decision"),
        "service_manager_start_executed": manifest.get("service_manager_start_executed"),
        "binder_transaction_failed": counts.get("binder_transaction_failed"),
        "service_notifier_180": counts.get("service_notifier_180"),
        "wlfw_start": counts.get("wlfw_start"),
        "wlan0": counts.get("wlan0"),
    }


def decide(cases: list[FreshCase]) -> tuple[str, bool, str, str]:
    by_label = {case.label: case for case in cases}
    v927 = by_label["v927-no-service-manager"]
    v931 = by_label["v931-after-mdm-helper-esoc-fd"]
    v933 = by_label["v933-before-cnss"]
    if (
        v927.current_cnss_binder_failures > 0
        and v931.current_cnss_binder_failures == 0
        and v933.current_cnss_binder_failures == 0
        and v931.current_cnss_wlfw == 0
        and v933.current_cnss_wlfw == 0
        and not v931.subsys_esoc0_open_attempted
        and not v933.subsys_esoc0_open_attempted
    ):
        return (
            "v934-fresh-pid-binder-cleared-wlfw-still-missing",
            True,
            (
                "Fresh child-pid attribution shows service-manager matrix runs cleared current cnss-daemon Binder failures. "
                "The remaining blocker is below Binder: mdm_helper/SDX50M queue readiness or another lower WLFW precondition."
            ),
            (
                "plan V935 host-only mdm_helper SDX50M queue/property-context classifier; do not run another service-manager "
                "ordering live gate until the lower mdm_helper queue gap is classified"
            ),
        )
    return (
        "v934-fresh-pid-attribution-review",
        False,
        f"cases={[asdict(case) for case in cases]}",
        "inspect fresh-pid attribution before another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        case_from_dir("v927-no-service-manager", args.v927_dir),
        case_from_dir("v931-after-mdm-helper-esoc-fd", args.v931_dir),
        case_from_dir("v933-before-cnss", args.v933_dir),
    ]
    decision, pass_ok, reason, next_step = decide(cases)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v927_dir": str(repo_path(args.v927_dir)),
            "v931_dir": str(repo_path(args.v931_dir)),
            "v933_dir": str(repo_path(args.v933_dir)),
            "v601_manifest": str(repo_path(args.v601_manifest)),
            "v603_manifest": str(repo_path(args.v603_manifest)),
        },
        "cases": [asdict(case) for case in cases],
        "service_manager_references": [
            service_manager_reference("v601", args.v601_manifest),
            service_manager_reference("v603", args.v603_manifest),
        ],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    case_rows = [
        [
            case["label"],
            case["order"],
            case["cnss_pid"],
            case["current_cnss_binder_failures"],
            case["stale_cnss_binder_failures"],
            case["current_cnss_cld80211"],
            case["current_cnss_wlfw"],
            case["current_mdm_queue_failures"],
            case["any_mdm_queue_failures"],
            case["subsys_esoc0_open_attempted"],
        ]
        for case in manifest["cases"]
    ]
    ref_rows = [
        [
            item["label"],
            item["decision"],
            item["service_manager_start_executed"],
            item["binder_transaction_failed"],
            item["service_notifier_180"],
            item["wlfw_start"],
            item["wlan0"],
        ]
        for item in manifest["service_manager_references"]
    ]
    return "\n".join(
        [
            "# V934 CNSS Fresh-PID Attribution Summary",
            "",
            f"decision: `{manifest['decision']}`",
            f"pass: `{manifest['pass']}`",
            f"reason: {manifest['reason']}",
            f"next: {manifest['next_step']}",
            "",
            "## Current Child PID Matrix",
            "",
            markdown_table(
                [
                    "case",
                    "order",
                    "cnss_pid",
                    "current_binder_fail",
                    "stale_binder_fail",
                    "current_cld80211",
                    "current_wlfw",
                    "current_mdm_queue_fail",
                    "any_mdm_queue_fail",
                    "subsys_open",
                ],
                case_rows,
            ),
            "",
            "## Historical Service-Manager References",
            "",
            markdown_table(
                [
                    "case",
                    "decision",
                    "service_manager",
                    "binder_failed",
                    "service180",
                    "wlfw",
                    "wlan0",
                ],
                ref_rows,
            ),
            "",
            "## Guardrails",
            "",
            "- host-only classifier",
            "- no device command",
            "- no daemon start",
            "- no service-manager start",
            "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or partition write",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
