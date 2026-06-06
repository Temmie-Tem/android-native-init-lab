#!/usr/bin/env python3
"""V1024 host-only classifier for Android PM/eSoC fast-fd evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text
from native_wifi_android_pm_esoc_timing_v1022 import count_samples, proc_block_has_fd


DEFAULT_OUT_DIR = Path("tmp/wifi/v1024-fast-fd-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1024-fast-fd-android-timing-handoff.txt")
DEFAULT_V1020_MANIFEST = Path("tmp/wifi/v1020-after-fd-subsys-window-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--handoff-dir", type=Path)
    parser.add_argument("--v1020-manifest", type=Path, default=DEFAULT_V1020_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path)
    return payload


def selected_handoff_dir(args: argparse.Namespace) -> Path | None:
    if args.handoff_dir:
        return repo_path(args.handoff_dir)
    pointer = repo_path(LATEST_POINTER)
    if pointer.exists():
        value = pointer.read_text(encoding="utf-8").strip()
        if value:
            return repo_path(value)
    candidates = sorted(repo_path("tmp/wifi").glob("v1024-fast-fd-android-timing-handoff-live-*"))
    return candidates[-1] if candidates else None


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def timeline_present(manifest: dict[str, Any], *names: str) -> bool:
    timeline = ((manifest.get("classification") or {}).get("timeline") or {})
    return all(bool((timeline.get(name) or {}).get("present")) for name in names)


def timeline_value(manifest: dict[str, Any], name: str) -> Any:
    return (((manifest.get("classification") or {}).get("timeline") or {}).get(name) or {}).get("time")


def build_classification(handoff_dir: Path | None, v1020_manifest_path: Path) -> dict[str, Any]:
    if handoff_dir is None:
        return {
            "decision": "v1024-handoff-evidence-missing",
            "pass": False,
            "reason": "no V1024 handoff evidence directory is available",
            "next_step": "run V1024 fast-fd Android handoff",
        }

    early_dir = handoff_dir / "v1022-early-android-pm-esoc-timing"
    late_dir = handoff_dir / "v1022-late-android-pm-esoc-timing"
    early_manifest = load_json(early_dir / "manifest.json")
    late_manifest = load_json(late_dir / "manifest.json")
    wrapper_manifest = load_json(handoff_dir / "manifest.json")
    v1020 = load_json(v1020_manifest_path)
    early_sample = read_text(early_dir / "android/commands/sample-loop.txt")

    early_fd = {
        "sample_count": count_samples(early_sample),
        "pm_proxy_helper_process_seen": "pm_proxy_helper" in early_sample,
        "pm_proxy_helper_subsys_modem_fd": proc_block_has_fd(early_sample, r"pm_proxy_helper", r"/dev/subsys_modem"),
        "pm_proxy_helper_subsys_esoc0_fd": proc_block_has_fd(early_sample, r"pm_proxy_helper", r"/dev/subsys_esoc0"),
        "pm_proxy_helper_esoc0_fd": proc_block_has_fd(early_sample, r"pm_proxy_helper", r"/dev/esoc-0"),
        "pm_service_subsys_modem_fd": proc_block_has_fd(early_sample, r"pm-service", r"/dev/subsys_modem"),
        "mdm_helper_esoc0_fd": proc_block_has_fd(early_sample, r"mdm_helper", r"/dev/esoc-0"),
    }
    late_chain = {
        "wlfw_chain": timeline_present(late_manifest, "wlfw_start", "subsys_esoc0_get", "wlan_pd", "icnss_qmi", "fw_ready", "wlan0"),
        "per_proxy_helper_start": timeline_value(late_manifest, "per_proxy_helper_start"),
        "per_mgr_start": timeline_value(late_manifest, "per_mgr_start"),
        "per_proxy_start": timeline_value(late_manifest, "per_proxy_start"),
        "mdm_helper_start": timeline_value(late_manifest, "mdm_helper_start"),
        "wlfw_start": timeline_value(late_manifest, "wlfw_start"),
        "subsys_esoc0_get": timeline_value(late_manifest, "subsys_esoc0_get"),
        "fw_ready": timeline_value(late_manifest, "fw_ready"),
        "wlan0": timeline_value(late_manifest, "wlan0"),
    }
    native_delta = {
        "v1020_decision": v1020.get("decision"),
        "v1020_mdm_helper_esoc0_fd_seen": bool(v1020.get("mdm_helper_start_executed")) and bool(v1020.get("subsys_esoc0_open_attempted")),
        "v1020_pm_proxy_helper_start_executed": bool(v1020.get("pm_proxy_helper_start_executed")),
        "v1020_pm_proxy_started": bool(v1020.get("analysis", {}).get("post_surface", {}).get("pm_proxy_started")),
        "v1020_subsys_open_attempted": bool(v1020.get("subsys_esoc0_open_attempted")),
        "v1020_wlfw_observed": bool(v1020.get("wlfw_precondition_observed")),
    }
    pm_contract = (
        early_fd["pm_proxy_helper_process_seen"]
        and early_fd["pm_proxy_helper_subsys_modem_fd"]
        and early_fd["pm_service_subsys_modem_fd"]
        and early_fd["mdm_helper_esoc0_fd"]
    )
    if pm_contract and late_chain["wlfw_chain"] and bool(wrapper_manifest.get("native_rollback_verified")):
        decision = "v1024-android-pm-esoc-fd-contract-captured"
        pass_ok = True
        reason = "same handoff captured Android PM fd contract early and WLFW/FW-ready/wlan0 chain late"
        next_step = "V1025 source/build helper support for Android PM full-contract gate before native subsystem retry"
    elif late_chain["wlfw_chain"]:
        decision = "v1024-android-wlfw-chain-only"
        pass_ok = True
        reason = "WLFW chain was captured, but early PM fd contract is incomplete"
        next_step = "use a pre-ADB sampler or tighter target fd loop before another native retry"
    else:
        decision = "v1024-android-contract-incomplete"
        pass_ok = False
        reason = "V1024 did not capture enough Android PM/eSoC contract evidence"
        next_step = "rerun V1024 handoff or move to a Magisk post-fs-data sampler"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "handoff_dir": str(handoff_dir),
        "wrapper": {
            "path": wrapper_manifest.get("_path"),
            "decision": wrapper_manifest.get("decision"),
            "pass": wrapper_manifest.get("pass"),
            "native_rollback_verified": wrapper_manifest.get("native_rollback_verified"),
        },
        "early": {
            "path": early_manifest.get("_path"),
            "decision": early_manifest.get("decision"),
            "pass": early_manifest.get("pass"),
            "fd": early_fd,
        },
        "late": {
            "path": late_manifest.get("_path"),
            "decision": late_manifest.get("decision"),
            "pass": late_manifest.get("pass"),
            "chain": late_chain,
        },
        "native_delta": native_delta,
    }


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    fd_rows = [[key, value] for key, value in c.get("early", {}).get("fd", {}).items()]
    chain_rows = [[key, value] for key, value in c.get("late", {}).get("chain", {}).items()]
    native_rows = [[key, value] for key, value in c.get("native_delta", {}).items()]
    return "\n".join(
        [
            "# V1024 Fast FD Contract Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            f"- handoff_dir: `{c.get('handoff_dir', '-')}`",
            "",
            "## Early FD Contract",
            "",
            markdown_table(["item", "value"], fd_rows),
            "",
            "## Late WLFW Chain",
            "",
            markdown_table(["item", "value"], chain_rows),
            "",
            "## Native Delta",
            "",
            markdown_table(["item", "value"], native_rows),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    handoff_dir = selected_handoff_dir(args)
    if args.command == "plan":
        classification = {
            "decision": "v1024-fast-fd-contract-classifier-plan-ready",
            "pass": True,
            "reason": "plan-only; no evidence parsed",
            "next_step": "run classifier after V1024 handoff evidence exists",
            "handoff_dir": str(handoff_dir) if handoff_dir else "",
        }
    else:
        classification = build_classification(handoff_dir, repo_path(args.v1020_manifest))
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_command_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    write_private_text(repo_path("tmp/wifi/latest-v1024-fast-fd-contract-classifier.txt"), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
