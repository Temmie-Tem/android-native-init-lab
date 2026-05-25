#!/usr/bin/env python3
"""V911 host-only classifier for mdm_helper /dev/esoc-0 fd stall evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v911-mdm-helper-esoc-fd-stall-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v911-mdm-helper-esoc-fd-stall-classifier.txt")
DEFAULT_LIVE_DIR = Path("tmp/wifi/v911-mdm-helper-esoc-fd-stall-live")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--live-dir", type=Path, default=DEFAULT_LIVE_DIR)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.replace("\0", "\n").splitlines():
        if "=" not in line:
            continue
        key, value = line.strip().split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value
    return values


def block(text: str, prefix: str, label: str) -> list[str]:
    pattern = re.compile(
        rf"A90_EXECNS_{prefix}_{re.escape(label)}_BEGIN[^\n]*\n(.*?)\nA90_EXECNS_{prefix}_{re.escape(label)}_END",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        return []
    return match.group(1).strip().splitlines()


def decode_ioctl(value: str) -> dict[str, Any]:
    try:
        code = int(value, 16)
    except ValueError:
        return {"raw": value, "decoded": "unknown"}
    nr = code & 0xff
    type_no = (code >> 8) & 0xff
    size = (code >> 16) & 0x3fff
    direction = (code >> 30) & 0x3
    name = "ESOC_WAIT_FOR_REQ" if code == 0x8004CC02 else "unknown"
    return {
        "raw": value,
        "nr": nr,
        "type": f"0x{type_no:02x}",
        "size": size,
        "direction": direction,
        "decoded": name,
    }


def classify(live_manifest: dict[str, Any], transcript: str) -> dict[str, Any]:
    values = key_values(transcript)
    contract = (live_manifest.get("analysis") or {}).get("helper", {}).get("contract", {})
    final_syscall_lines = block(transcript, "PATH", "mdm_helper_runtime_final_stall_task_776_syscall")
    final_wchan_lines = block(transcript, "PATH", "mdm_helper_runtime_final_stall_task_776_wchan")
    main_wchan_lines = block(transcript, "CNSS_PROC", "mdm_helper_runtime_final_wchan")
    syscall_parts = final_syscall_lines[0].split() if final_syscall_lines else []
    ioctl = decode_ioctl(syscall_parts[2]) if len(syscall_parts) >= 3 and syscall_parts[0] == "29" else {"raw": "", "decoded": "unknown"}
    surface = {
        "live_decision": live_manifest.get("decision", ""),
        "live_pass": live_manifest.get("pass", False),
        "mdm_helper_observable": contract.get("mdm_helper_observable", ""),
        "fd_esoc0_window": contract.get("fd_esoc0_count.window", ""),
        "fd_esoc0_final": contract.get("fd_esoc0_count.final", ""),
        "fd_subsys_esoc0_final": contract.get("fd_subsys_esoc0_count.final", ""),
        "fd_mhi_pipe_final": contract.get("fd_mhi_pipe_count.final", ""),
        "ks_final": contract.get("ks_count.final", ""),
        "mhi_pipe_cmdline_final": contract.get("mhi_pipe_cmdline_count.final", ""),
        "all_postflight_safe": contract.get("all_postflight_safe", ""),
        "esoc0_fd_flags": values.get("capture.mdm_helper_runtime_contract.final_esoc0.fd_links.entry_00.fdinfo.flags", ""),
        "esoc0_fd_mnt_id": values.get("capture.mdm_helper_runtime_contract.final_esoc0.fd_links.entry_00.fdinfo.mnt_id", ""),
        "main_wchan": main_wchan_lines[0] if main_wchan_lines else "",
        "thread_776_wchan": final_wchan_lines[0] if final_wchan_lines else "",
        "thread_776_syscall": final_syscall_lines[0] if final_syscall_lines else "",
        "thread_776_ioctl": ioctl,
        "stall_snapshot_final": {
            "wchan": values.get("capture.mdm_helper_runtime_final.stall_snapshot.wchan_captured", ""),
            "syscall": values.get("capture.mdm_helper_runtime_final.stall_snapshot.syscall_captured", ""),
            "stack": values.get("capture.mdm_helper_runtime_final.stall_snapshot.stack_captured", ""),
            "status": values.get("capture.mdm_helper_runtime_final.stall_snapshot.status_captured", ""),
            "sched": values.get("capture.mdm_helper_runtime_final.stall_snapshot.sched_captured", ""),
            "task": values.get("capture.mdm_helper_runtime_final.stall_snapshot.task_captured", ""),
        },
    }
    pass_ok = (
        surface["live_pass"] is True
        and surface["fd_esoc0_final"] == "1"
        and surface["fd_subsys_esoc0_final"] == "0"
        and surface["fd_mhi_pipe_final"] == "0"
        and surface["ks_final"] == "0"
        and surface["thread_776_wchan"] == "esoc_dev_ioctl"
        and ioctl.get("decoded") == "ESOC_WAIT_FOR_REQ"
        and surface["all_postflight_safe"] == "1"
    )
    return {
        "decision": "v911-mdm-helper-wait-for-req-observed" if pass_ok else "v911-mdm-helper-esoc-fd-stall-review",
        "pass": pass_ok,
        "reason": (
            "mdm_helper owns /dev/esoc-0 and worker thread blocks in ioctl ESOC_WAIT_FOR_REQ; no /dev/subsys_esoc0 fd, ks, MHI, or Wi-Fi link appeared"
            if pass_ok else
            "evidence does not fully match expected ESOC_WAIT_FOR_REQ stall surface"
        ),
        "next_step": (
            "plan a guarded powerup trigger while mdm_helper owns the REQ path, with explicit cleanup/reboot and no Wi-Fi HAL/scan/connect"
            if pass_ok else
            "inspect V911 live transcript before selecting the next gate"
        ),
        "surface": surface,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["classification"]["surface"]
    rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, dict) else value]
            for key, value in surface.items()]
    return "\n".join([
        "# V911 mdm_helper eSoC FD Stall Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Surface",
        "",
        markdown_table(["field", "value"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    live_dir = repo_path(args.live_dir)
    live_manifest_path = live_dir / "manifest.json"
    transcript_path = live_dir / "native/mdm-helper-runtime-contract.txt"
    live_manifest = json.loads(live_manifest_path.read_text(encoding="utf-8"))
    transcript = read_text(transcript_path)
    classification = classify(live_manifest, transcript)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "live_dir": str(args.live_dir),
        "live_manifest": str(live_manifest_path),
        "transcript": str(transcript_path),
        "classification": classification,
        "device_contact": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
