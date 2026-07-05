#!/usr/bin/env python3
"""WSTA137 host-only summary for the D-public native HUD presenter live proof.

The live work already happened in a private run directory: V3398 was flashed
through the checked helper, a fresh bounded intent was validated, the native KMS
presenter presented it, and stale/forbidden intent reject paths were exercised.
This script performs no device action.  It re-reads the private transcripts and
emits a compact redacted proof JSON that WSTA108 can consume.
"""

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
PASS_DECISION = "wsta137-dpublic-native-hud-presenter-live-pass"
RESULT_NAME = "wsta137_dpublic_native_presenter_live.json"

INIT_VERSION = "0.11.154"
INIT_BUILD = "v3398-dpublic-hud-presenter"
INIT_ELF_SHA256 = "e3283697503d35584fb8a2cac7a401761e3862dcb725fa8a2828354c884acd8f"
BOOT_SHA256 = "b18be6a39eb41fb71a5256db3b23d5c648631fb164061b98b35a35ffba9f3a0c"
HELPER_BOOT_IMAGE = "workspace/private/inputs/boot_images/boot_linux_v3398_dpublic_hud_presenter.img"
INTENT_SCHEMA = "a90-dpublic-hud-intent-v1"
STALE_AFTER_MS = 2000


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
        "native_status_v3397": source_run_dir / "native-status-v3397.txt",
        "reload": source_run_dir / "reload-v3398.txt",
        "version_after_reload": source_run_dir / "version-v3398-after-reload-2.txt",
        "status_after_reload": source_run_dir / "status-v3398-after-reload-2.txt",
        "flash": source_run_dir / "flash-v3398-checked-helper.txt",
        "selftest_after_flash": source_run_dir / "selftest-v3398-after-flash.txt",
        "validate": source_run_dir / "dpublic-hud-presenter-validate-2.txt",
        "present": source_run_dir / "dpublic-hud-presenter-present.txt",
        "forbidden": source_run_dir / "dpublic-hud-presenter-forbidden-reject.txt",
        "stale": source_run_dir / "dpublic-hud-presenter-stale-reject.txt",
        "post_health": source_run_dir / "post-proof-cleanup-health.txt",
    }
    texts = {name: read_text(path) if path.is_file() else "" for name, path in files.items()}

    validate_age = extract_int(r"intent\.age_ms=(\d+)", texts["validate"])
    present_age = extract_int(r"intent\.age_ms=(\d+)", texts["present"])
    validate_sequence = extract_int(r"intent\.sequence=(\d+)", texts["validate"])
    present_sequence = extract_int(r"intent\.sequence=(\d+)", texts["present"])
    crtc = extract_int(r"presented framebuffer 1080x2400 on crtc=(\d+)", texts["present"])
    stale_age = extract_int(r"intent\.reject=stale age_ms=(\d+)", texts["stale"])

    proof = {
        "schema": "a90-wsta137-dpublic-native-presenter-live-v1",
        "source_run_dir": rel(source_run_dir),
        "candidate": {
            "init_version": INIT_VERSION,
            "init_build": INIT_BUILD,
            "boot_image": HELPER_BOOT_IMAGE,
            "boot_sha256": BOOT_SHA256,
        },
        "native_return": {
            "from_debian_to_v3397_clean": (
                "A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)" in texts["native_status_v3397"]
                and "selftest: pass=12 warn=1 fail=0" in texts["native_status_v3397"]
            ),
        },
        "hot_reload_attempt": {
            "reached_v3398_banner": f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})" in texts["reload"],
            "init_elf_sha_match": (
                f"A90RELOAD sha={INIT_ELF_SHA256} expected_sha_match=1" in texts["reload"]
            ),
            "returned_to_v3397_clean": (
                "version: 0.11.153 build=v3397-wsta-execute-gate-screen" in texts["version_after_reload"]
                and "selftest: pass=12 warn=1 fail=0" in texts["status_after_reload"]
            ),
        },
        "checked_flash": {
            "helper": "native_init_flash.py",
            "used_checked_helper": "native-init-flash" in texts["flash"],
            "local_sha_match": f"local image sha256: {BOOT_SHA256}" in texts["flash"],
            "remote_sha_match": f"remote image sha256: {BOOT_SHA256}" in texts["flash"],
            "boot_readback_sha_match": f"boot block prefix sha256: {BOOT_SHA256}" in texts["flash"],
            "booted_v3398": f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})" in texts["flash"],
            "boot_ok": "boot: BOOT OK" in texts["flash"],
            "selftest_fail_zero": "selftest: pass=12 warn=1 fail=0" in texts["flash"],
            "transport_serial_ready": "transport.serial=ready" in texts["flash"],
            "transport_tcpctl_ready": "transport.tcpctl=ready" in texts["flash"],
        },
        "validate_proof": {
            "intent_schema": INTENT_SCHEMA,
            "sequence": validate_sequence,
            "age_ms": validate_age,
            "intent_valid": "intent.valid=1" in texts["validate"],
            "forbidden_fields_reject": "policy.forbidden_fields=reject" in texts["validate"],
            "unknown_fields_reject": "policy.unknown_fields=reject" in texts["validate"],
            "stale_after_ms": STALE_AFTER_MS,
            "stale_after_marker": f"policy.stale_after_ms={STALE_AFTER_MS}" in texts["validate"],
            "presenter_owner_native_root": "presenter.owner=native-init-root" in texts["validate"],
            "debian_direct_kms_zero": "presenter.debian_direct_kms=0" in texts["validate"],
            "validate_only": "present.skipped=validate-only" in texts["validate"],
        },
        "present_proof": {
            "sequence": present_sequence,
            "age_ms": present_age,
            "intent_valid": "intent.valid=1" in texts["present"],
            "present_begin_frame_rc_zero": "present.begin_frame_rc=0" in texts["present"],
            "present_rc_zero": "present.rc=0" in texts["present"],
            "present_done": "present.done=1" in texts["present"],
            "framebuffer": "1080x2400",
            "crtc": crtc,
        },
        "reject_proof": {
            "forbidden_command_rejected": "intent.reject=forbidden-key key=command" in texts["forbidden"],
            "forbidden_rc": -1 if "rc=-1" in texts["forbidden"] else None,
            "stale_rejected": "intent.reject=stale" in texts["stale"],
            "stale_rc": -110 if "rc=-110" in texts["stale"] else None,
            "stale_age_ms": stale_age,
            "stale_after_ms": STALE_AFTER_MS,
        },
        "final_health": {
            "v3398_resident": f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})" in texts["post_health"],
            "selftest_fail_zero": "selftest: pass=12 warn=1 fail=0" in texts["post_health"],
            "transport_serial_ready": "transport.serial=ready" in texts["post_health"],
            "transport_tcpctl_ready": "transport.tcpctl=ready" in texts["post_health"],
            "autohud_stopped_after_present": "autohud: stopped" in texts["post_health"],
        },
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    proof["checks"] = validate_proof(proof)
    proof["decision"] = PASS_DECISION if all(proof["checks"].values()) else "wsta137-dpublic-native-hud-presenter-live-fail"
    return proof


def validate_proof(proof: dict[str, Any]) -> dict[str, bool]:
    checked_flash = proof.get("checked_flash") if isinstance(proof.get("checked_flash"), dict) else {}
    validate = proof.get("validate_proof") if isinstance(proof.get("validate_proof"), dict) else {}
    present = proof.get("present_proof") if isinstance(proof.get("present_proof"), dict) else {}
    reject = proof.get("reject_proof") if isinstance(proof.get("reject_proof"), dict) else {}
    final_health = proof.get("final_health") if isinstance(proof.get("final_health"), dict) else {}
    candidate = proof.get("candidate") if isinstance(proof.get("candidate"), dict) else {}
    return {
        "candidate_is_v3398": (
            candidate.get("init_version") == INIT_VERSION
            and candidate.get("init_build") == INIT_BUILD
            and candidate.get("boot_sha256") == BOOT_SHA256
        ),
        "checked_flash_used": bool(checked_flash.get("used_checked_helper")),
        "checked_flash_sha_matched": bool(
            checked_flash.get("local_sha_match")
            and checked_flash.get("remote_sha_match")
            and checked_flash.get("boot_readback_sha_match")
        ),
        "checked_flash_boot_health_clean": bool(
            checked_flash.get("booted_v3398")
            and checked_flash.get("boot_ok")
            and checked_flash.get("selftest_fail_zero")
            and checked_flash.get("transport_serial_ready")
            and checked_flash.get("transport_tcpctl_ready")
        ),
        "validate_fresh_intent_passed": bool(
            validate.get("intent_valid")
            and validate.get("sequence")
            and isinstance(validate.get("age_ms"), int)
            and validate.get("age_ms") < STALE_AFTER_MS
            and validate.get("forbidden_fields_reject")
            and validate.get("unknown_fields_reject")
            and validate.get("stale_after_marker")
            and validate.get("presenter_owner_native_root")
            and validate.get("debian_direct_kms_zero")
            and validate.get("validate_only")
        ),
        "present_fresh_intent_passed": bool(
            present.get("intent_valid")
            and present.get("sequence")
            and isinstance(present.get("age_ms"), int)
            and present.get("age_ms") < STALE_AFTER_MS
            and present.get("present_begin_frame_rc_zero")
            and present.get("present_rc_zero")
            and present.get("present_done")
            and present.get("framebuffer") == "1080x2400"
            and present.get("crtc") == 133
        ),
        "reject_paths_passed": bool(
            reject.get("forbidden_command_rejected")
            and reject.get("forbidden_rc") == -1
            and reject.get("stale_rejected")
            and reject.get("stale_rc") == -110
            and isinstance(reject.get("stale_age_ms"), int)
            and reject.get("stale_age_ms") > STALE_AFTER_MS
        ),
        "final_health_clean": bool(
            final_health.get("v3398_resident")
            and final_health.get("selftest_fail_zero")
            and final_health.get("transport_serial_ready")
            and final_health.get("transport_tcpctl_ready")
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"wsta137-dpublic-native-presenter-live-summary-{utc_stamp()}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    source_run_dir = resolve_path(args.source_run_dir)
    result: dict[str, Any] = {
        "schema": "a90-wsta137-live-summary-run-v1",
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "source_run_dir": rel(source_run_dir),
        "started_utc": utc_stamp(),
        "decision": "wsta137-dpublic-native-hud-presenter-live-blocked",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT) or not is_under(source_run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta137-blocked-nonprivate-path"
        result["ended_utc"] = utc_stamp()
        return result
    if not source_run_dir.is_dir():
        result["decision"] = "wsta137-blocked-source-run-dir-missing"
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
