#!/usr/bin/env python3
"""V944 host-only classifier for V943 mdm_helper queue-timing evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v944-v943-queue-timing-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v944-v943-queue-timing-classifier.txt")
DEFAULT_V943_MANIFEST = Path("tmp/wifi/v943-mdm-helper-queue-timing-capture-live/manifest.json")
DEFAULT_V867_REPORT = Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v943-manifest", type=Path, default=DEFAULT_V943_MANIFEST)
    parser.add_argument("--v867-report", type=Path, default=DEFAULT_V867_REPORT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("helper") or {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("contract") or {}


def timing(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("queue_timing") or {}


def post_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("post_surface") or {}


def val(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_queue_timing.{phase}.{suffix}", "")


def intval(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def fresh_queue_lines(manifest: dict[str, Any]) -> list[str]:
    data = timing(manifest)
    mdm_pid = val(data, "window", "mdm_helper.pid")
    lines = []
    for line in post_surface(manifest).get("wlfw_or_wlan_dmesg_hits", []):
        if "unable to queue event for SDX50M" not in line:
            continue
        lines.append(line)
    fresh: list[str] = []
    if mdm_pid:
        base = int(mdm_pid)
        for line in lines:
            match = re.search(r"mdm_helper:\s*(\d+)\]", line)
            if match and int(match.group(1)) >= base:
                fresh.append(line)
    return fresh or lines[-1:]


def classify(v943: dict[str, Any], v867_report: str) -> dict[str, Any]:
    c = contract(v943)
    t = timing(v943)
    phases = ["after_per_mgr_settle", "after_mdm_helper_spawn", "window", "final"]
    per_mgr_alive = all(val(t, phase, "per_mgr.alive") == "1" for phase in phases)
    per_mgr_no_subsys = all(
        val(t, phase, "per_mgr_subsys_modem_count") == "0"
        and val(t, phase, "per_mgr_subsys_esoc0_count") == "0"
        for phase in phases
    )
    no_proxy_lifecycle = all(
        val(t, phase, "pm_proxy_count") == "0"
        and val(t, phase, "pm_proxy_helper_count") == "0"
        for phase in phases
    )
    mdm_esoc_window = val(t, "window", "mdm_helper_esoc0_count") == "1"
    mdm_esoc_final = val(t, "final", "mdm_helper_esoc0_count") == "1"
    no_ks_mhi = c.get("ks_count.final") == "0" and c.get("fd_mhi_pipe_count.final") == "0"
    fresh_lines = fresh_queue_lines(v943)
    spawn_to_esoc_ms = intval(val(t, "window", "monotonic_ms")) - intval(
        val(t, "after_mdm_helper_spawn", "monotonic_ms")
    )
    window_to_final_ms = intval(val(t, "final", "monotonic_ms")) - intval(val(t, "window", "monotonic_ms"))
    pm_proxy_helper_dstate_risk = "`pm_proxy_helper` remained in D-state" in v867_report

    if (
        bool(v943.get("pass"))
        and per_mgr_alive
        and per_mgr_no_subsys
        and no_proxy_lifecycle
        and mdm_esoc_window
        and mdm_esoc_final
        and no_ks_mhi
        and fresh_lines
        and pm_proxy_helper_dstate_risk
    ):
        decision = "v944-pm-provider-lifetime-gap-selected"
        pass_ok = True
        reason = (
            "fresh queue failure occurs after mdm_helper reaches /dev/esoc-0 while per_mgr is alive but has no subsystem fds and proxy/helper lifecycle is absent"
        )
        next_step = (
            "add source/build-only provider readiness diagnostics or a read-only Android PM timing recapture; do not start pm_proxy_helper or open /dev/subsys_esoc0 yet"
        )
    elif bool(v943.get("pass")) and fresh_lines:
        decision = "v944-queue-timing-classified-needs-review"
        pass_ok = True
        reason = "fresh queue failure is captured, but provider-lifetime correlation is incomplete"
        next_step = "inspect V943 evidence manually before selecting a live PM/proxy direction"
    else:
        decision = "v944-queue-timing-evidence-missing"
        pass_ok = False
        reason = "V943 did not contain fresh SDX50M queue-timing evidence"
        next_step = "repair or rerun V943 before selecting the next lower gate"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "per_mgr_alive": per_mgr_alive,
        "per_mgr_no_subsys": per_mgr_no_subsys,
        "no_proxy_lifecycle": no_proxy_lifecycle,
        "mdm_esoc_window": mdm_esoc_window,
        "mdm_esoc_final": mdm_esoc_final,
        "no_ks_mhi": no_ks_mhi,
        "fresh_queue_lines": fresh_lines,
        "spawn_to_esoc_ms": spawn_to_esoc_ms,
        "window_to_final_ms": window_to_final_ms,
        "pm_proxy_helper_dstate_risk": pm_proxy_helper_dstate_risk,
        "selected_phases": {
            phase: {
                "monotonic_ms": val(t, phase, "monotonic_ms"),
                "per_mgr_state": val(t, phase, "per_mgr.state"),
                "per_mgr_subsys_modem_count": val(t, phase, "per_mgr_subsys_modem_count"),
                "per_mgr_subsys_esoc0_count": val(t, phase, "per_mgr_subsys_esoc0_count"),
                "mdm_helper_state": val(t, phase, "mdm_helper.state"),
                "mdm_helper_esoc0_count": val(t, phase, "mdm_helper_esoc0_count"),
                "pm_proxy_count": val(t, phase, "pm_proxy_count"),
                "pm_proxy_helper_count": val(t, phase, "pm_proxy_helper_count"),
            }
            for phase in phases
        },
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "subsys_esoc0_open_executed": False,
            "esoc_ioctl_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credentials_used": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write": False,
            "partition_write": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["per_mgr_alive", str(c["per_mgr_alive"])],
        ["per_mgr_no_subsys", str(c["per_mgr_no_subsys"])],
        ["no_proxy_lifecycle", str(c["no_proxy_lifecycle"])],
        ["mdm_esoc_window", str(c["mdm_esoc_window"])],
        ["mdm_esoc_final", str(c["mdm_esoc_final"])],
        ["no_ks_mhi", str(c["no_ks_mhi"])],
        ["spawn_to_esoc_ms", str(c["spawn_to_esoc_ms"])],
        ["window_to_final_ms", str(c["window_to_final_ms"])],
        ["pm_proxy_helper_dstate_risk", str(c["pm_proxy_helper_dstate_risk"])],
    ]
    phase_rows = []
    for phase, data in c["selected_phases"].items():
        phase_rows.append(
            [
                phase,
                data["monotonic_ms"],
                data["per_mgr_state"],
                data["per_mgr_subsys_modem_count"],
                data["per_mgr_subsys_esoc0_count"],
                data["mdm_helper_state"],
                data["mdm_helper_esoc0_count"],
                data["pm_proxy_count"],
                data["pm_proxy_helper_count"],
            ]
        )
    return "\n".join(
        [
            "# V944 V943 Queue-Timing Classifier Summary",
            "",
            f"decision: {c['decision']}",
            f"pass: {c['pass']}",
            f"reason: {c['reason']}",
            f"next: {c['next_step']}",
            "",
            "## Markers",
            "",
            markdown_table(["marker", "value"], rows),
            "",
            "## Phases",
            "",
            markdown_table(
                [
                    "phase",
                    "ms",
                    "per_mgr",
                    "pm_subsys_modem",
                    "pm_subsys_esoc0",
                    "mdm",
                    "mdm_esoc0",
                    "pm_proxy",
                    "pm_proxy_helper",
                ],
                phase_rows,
            ),
            "",
            "## Fresh Queue Lines",
            "",
            "```text",
            "\n".join(c["fresh_queue_lines"]),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v943 = load_json(args.v943_manifest)
    v867_report = read_text(args.v867_report)
    classification = classify(v943, v867_report)
    manifest = {
        "schema": "v944-v943-queue-timing-classifier",
        "created_at": now_iso(),
        "inputs": {
            "v943_manifest": str(args.v943_manifest),
            "v867_report": str(args.v867_report),
        },
        "host": collect_host_metadata(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "classification": classification,
        "guardrails": classification["guardrails"],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
