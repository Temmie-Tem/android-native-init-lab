#!/usr/bin/env python3
"""WSTA147 host-only summary for the D-public HUD restart live proof."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
PASS_DECISION = "wsta147-dpublic-hud-restart-live-pass"
RESULT_NAME = "wsta147_dpublic_hud_restart_live.json"

INIT_VERSION = "0.11.158"
INIT_BUILD = "v3402-dpublic-hud-presenter-restart-policy"
BOOT_SHA256 = "57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1"
BOOT_IMAGE = "workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img"
RESTART_POLICY = "restart-stop-start-stale-pid-cleanup"
PRE_RESTART_SEQUENCE = 14701
POST_RESTART_SEQUENCE = 14702
FAKE_STALE_PID = 999999


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return int(match.group(1), 10)


def safety() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "debian_direct_kms": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def collect_from_source(source_run_dir: Path) -> dict[str, Any]:
    files = {
        "flash": source_run_dir / "flash-v3402.txt",
        "start": source_run_dir / "service-start.txt",
        "intent_14701": source_run_dir / "intent-14701-create.txt",
        "status_14701": source_run_dir / "service-status-after-intent-14701.txt",
        "files_14701": source_run_dir / "service-files-after-intent-14701.txt",
        "restart": source_run_dir / "service-restart.txt",
        "intent_14702": source_run_dir / "intent-14702-create.txt",
        "status_14702": source_run_dir / "service-status-after-intent-14702.txt",
        "files_14702": source_run_dir / "service-files-after-intent-14702.txt",
        "stop_after_restart": source_run_dir / "service-stop-after-restart.txt",
        "fake_stale": source_run_dir / "fake-stale-pidfile.txt",
        "start_stale": source_run_dir / "service-start-stale-cleanup.txt",
        "stop_final": source_run_dir / "service-stop-final.txt",
        "status_final": source_run_dir / "service-status-after-final-stop.txt",
        "final_selftest": source_run_dir / "final-selftest-v3402.txt",
        "final_status": source_run_dir / "final-status-v3402.txt",
    }
    texts = {name: read_text(path) if path.is_file() else "" for name, path in files.items()}
    start_pid = extract_int(r"A90WSTA140 start\.pid=(\d+)", texts["start"])
    restart_stop_pid = extract_int(r"A90WSTA140 stop\.pid=(\d+) release_drm=1", texts["restart"])
    restart_start_pid = extract_int(r"A90WSTA140 start\.pid=(\d+)", texts["restart"])
    stale_start_pid = extract_int(r"A90WSTA140 start\.pid=(\d+)", texts["start_stale"])
    proof = {
        "schema": "a90-wsta147-dpublic-hud-restart-live-v1",
        "source_run_dir": rel(source_run_dir),
        "candidate": {
            "init_version": INIT_VERSION,
            "init_build": INIT_BUILD,
            "boot_image": BOOT_IMAGE,
            "boot_sha256": BOOT_SHA256,
        },
        "checked_flash": {
            "helper": "native_init_flash.py",
            "used_checked_helper": "native-init-flash" in texts["flash"],
            "from_native": "requesting recovery from native init bridge" in texts["flash"],
            "local_sha_match": f"local image sha256: {BOOT_SHA256}" in texts["flash"],
            "remote_sha_match": f"remote image sha256: {BOOT_SHA256}" in texts["flash"],
            "boot_readback_sha_match": f"boot block prefix sha256: {BOOT_SHA256}" in texts["flash"],
            "booted_v3402": f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})" in texts["flash"],
            "boot_ok": "boot: BOOT OK" in texts["flash"],
            "selftest_fail_zero": "selftest: pass=12 warn=1 fail=0" in texts["flash"],
            "verify_native_passed": "cmdv1 verify passed: version/status rc=0 status=ok" in texts["flash"],
        },
        "pre_restart": {
            "start_pid": start_pid,
            "start_done": "A90WSTA140 start.done=1" in texts["start"],
            "shared_run_mounted": "shared_run_dir=mounted path=/run/a90-dpublic fstype=tmpfs" in texts["start"],
            "restart_policy_marker": f"A90WSTA146 restart_policy={RESTART_POLICY}" in texts["start"],
            "intent_sequence": PRE_RESTART_SEQUENCE
            if f"\"sequence\":{PRE_RESTART_SEQUENCE}" in texts["intent_14701"] else None,
            "presented": "presented framebuffer 1080x2400 on crtc=133" in texts["intent_14701"],
            "status_running": "A90WSTA140 status.state=running" in texts["status_14701"],
            "status_pid": extract_int(r"A90WSTA140 status\.pid=(\d+)", texts["status_14701"]),
            "status_drm_fd": "A90WSTA140 status.drm_fd=1" in texts["status_14701"],
            "status_restart_policy": f"A90WSTA146 status.restart_policy={RESTART_POLICY}" in texts["status_14701"],
            "status_file_sequence": extract_int(r"last_sequence=(\d+)", texts["files_14701"]),
            "status_file_present_rc": extract_int(r"present_rc=(-?\d+)", texts["files_14701"]),
        },
        "restart": {
            "policy": RESTART_POLICY if f"A90WSTA146 restart.policy={RESTART_POLICY}" in texts["restart"] else None,
            "stop_pid": restart_stop_pid,
            "stop_released_drm": "A90WSTA140 stop.pid=" in texts["restart"] and "release_drm=1" in texts["restart"],
            "stop_term": "handoff_display drm_owner_pid=" in texts["restart"] and "action=term" in texts["restart"],
            "stop_done": "A90WSTA140 stop.done=1" in texts["restart"],
            "stop_rc": extract_int(r"A90WSTA146 restart\.stop_rc=(-?\d+)", texts["restart"]),
            "start_pid": restart_start_pid,
            "start_done": "A90WSTA140 start.done=1" in texts["restart"],
            "start_rc": extract_int(r"A90WSTA146 restart\.start_rc=(-?\d+)", texts["restart"]),
            "done": "A90WSTA146 restart.done=1 rc=0" in texts["restart"],
        },
        "post_restart": {
            "intent_sequence": POST_RESTART_SEQUENCE
            if f"\"sequence\":{POST_RESTART_SEQUENCE}" in texts["intent_14702"] else None,
            "presented": "presented framebuffer 1080x2400 on crtc=133" in texts["intent_14702"],
            "status_running": "A90WSTA140 status.state=running" in texts["status_14702"],
            "status_pid": extract_int(r"A90WSTA140 status\.pid=(\d+)", texts["status_14702"]),
            "status_drm_fd": "A90WSTA140 status.drm_fd=1" in texts["status_14702"],
            "status_file_sequence": extract_int(r"last_sequence=(\d+)", texts["files_14702"]),
            "status_file_present_rc": extract_int(r"present_rc=(-?\d+)", texts["files_14702"]),
        },
        "stop_after_restart": {
            "stop_pid": extract_int(r"A90WSTA140 stop\.pid=(\d+) release_drm=1", texts["stop_after_restart"]),
            "stop_done": "A90WSTA140 stop.done=1" in texts["stop_after_restart"],
        },
        "stale_pid_cleanup": {
            "fake_pid": FAKE_STALE_PID if str(FAKE_STALE_PID) in texts["fake_stale"] else None,
            "stale_cleanup_marker": f"A90WSTA146 start.stale_pid={FAKE_STALE_PID} action=unlink" in texts["start_stale"],
            "start_pid": stale_start_pid,
            "start_done": "A90WSTA140 start.done=1" in texts["start_stale"],
            "final_stop_done": "A90WSTA140 stop.done=1" in texts["stop_final"],
            "final_status_stopped": "A90WSTA140 status.state=stopped rc=-2" in texts["status_final"],
        },
        "final_health": {
            "v3402_resident": f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})" in texts["final_status"],
            "boot_ok": "boot: BOOT OK" in texts["final_status"],
            "selftest_fail_zero": "selftest: pass=12 warn=1 fail=0" in texts["final_selftest"]
            and "selftest: pass=12 warn=1 fail=0" in texts["final_status"],
            "transport_serial_ready": "transport.serial=ready" in texts["final_status"],
            "transport_ncm_ready": "transport.ncm=ready" in texts["final_status"],
            "transport_tcpctl_ready": "transport.tcpctl=ready" in texts["final_status"],
        },
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    proof["checks"] = validate_proof(proof)
    proof["decision"] = PASS_DECISION if all(proof["checks"].values()) else "wsta147-dpublic-hud-restart-live-fail"
    return proof


def validate_proof(proof: dict[str, Any]) -> dict[str, bool]:
    candidate = proof.get("candidate") if isinstance(proof.get("candidate"), dict) else {}
    checked_flash = proof.get("checked_flash") if isinstance(proof.get("checked_flash"), dict) else {}
    pre = proof.get("pre_restart") if isinstance(proof.get("pre_restart"), dict) else {}
    restart = proof.get("restart") if isinstance(proof.get("restart"), dict) else {}
    post = proof.get("post_restart") if isinstance(proof.get("post_restart"), dict) else {}
    stop = proof.get("stop_after_restart") if isinstance(proof.get("stop_after_restart"), dict) else {}
    stale = proof.get("stale_pid_cleanup") if isinstance(proof.get("stale_pid_cleanup"), dict) else {}
    final_health = proof.get("final_health") if isinstance(proof.get("final_health"), dict) else {}
    return {
        "candidate_is_v3402": (
            candidate.get("init_version") == INIT_VERSION
            and candidate.get("init_build") == INIT_BUILD
            and candidate.get("boot_sha256") == BOOT_SHA256
        ),
        "checked_flash_used_and_clean": bool(
            checked_flash.get("used_checked_helper")
            and checked_flash.get("from_native")
            and checked_flash.get("local_sha_match")
            and checked_flash.get("remote_sha_match")
            and checked_flash.get("boot_readback_sha_match")
            and checked_flash.get("booted_v3402")
            and checked_flash.get("boot_ok")
            and checked_flash.get("selftest_fail_zero")
            and checked_flash.get("verify_native_passed")
        ),
        "pre_restart_presented_with_drm": bool(
            pre.get("start_pid")
            and pre.get("start_done")
            and pre.get("shared_run_mounted")
            and pre.get("restart_policy_marker")
            and pre.get("intent_sequence") == PRE_RESTART_SEQUENCE
            and pre.get("presented")
            and pre.get("status_running")
            and pre.get("status_pid") == pre.get("start_pid")
            and pre.get("status_drm_fd")
            and pre.get("status_restart_policy")
            and pre.get("status_file_sequence") == PRE_RESTART_SEQUENCE
            and pre.get("status_file_present_rc") == 0
        ),
        "restart_stop_start_proven": bool(
            restart.get("policy") == RESTART_POLICY
            and restart.get("stop_pid") == pre.get("start_pid")
            and restart.get("stop_released_drm")
            and restart.get("stop_term")
            and restart.get("stop_done")
            and restart.get("stop_rc") == 0
            and restart.get("start_pid")
            and restart.get("start_pid") != pre.get("start_pid")
            and restart.get("start_done")
            and restart.get("start_rc") == 0
            and restart.get("done")
        ),
        "post_restart_presented_with_drm": bool(
            post.get("intent_sequence") == POST_RESTART_SEQUENCE
            and post.get("presented")
            and post.get("status_running")
            and post.get("status_pid") == restart.get("start_pid")
            and post.get("status_drm_fd")
            and post.get("status_file_sequence") == POST_RESTART_SEQUENCE
            and post.get("status_file_present_rc") == 0
        ),
        "stop_after_restart_clean": bool(
            stop.get("stop_pid") == restart.get("start_pid")
            and stop.get("stop_done")
        ),
        "stale_pid_cleanup_proven": bool(
            stale.get("fake_pid") == FAKE_STALE_PID
            and stale.get("stale_cleanup_marker")
            and stale.get("start_pid")
            and stale.get("start_done")
            and stale.get("final_stop_done")
            and stale.get("final_status_stopped")
        ),
        "final_health_clean": bool(
            final_health.get("v3402_resident")
            and final_health.get("boot_ok")
            and final_health.get("selftest_fail_zero")
            and final_health.get("transport_serial_ready")
            and final_health.get("transport_ncm_ready")
            and final_health.get("transport_tcpctl_ready")
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"wsta147-dpublic-hud-restart-summary-{utc_stamp()}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    source_run_dir = resolve_path(args.source_run_dir)
    result: dict[str, Any] = {
        "schema": "a90-wsta147-live-summary-run-v1",
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "source_run_dir": rel(source_run_dir),
        "started_utc": utc_stamp(),
        "decision": "wsta147-dpublic-hud-restart-live-blocked",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT) or not is_under(source_run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta147-blocked-nonprivate-path"
        result["ended_utc"] = utc_stamp()
        return result
    if not source_run_dir.is_dir():
        result["decision"] = "wsta147-blocked-source-run-dir-missing"
        result["ended_utc"] = utc_stamp()
        return result

    proof = collect_from_source(source_run_dir)
    result.update(proof)
    result["run_id"] = run_id
    result["run_dir"] = rel(run_dir)
    result["source_run_dir"] = rel(source_run_dir)
    result["safety"] = safety()
    result["ended_utc"] = utc_stamp()
    write_json(run_dir / RESULT_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-run-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 1


if __name__ == "__main__":
    raise SystemExit(main())
