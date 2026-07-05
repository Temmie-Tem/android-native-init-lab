#!/usr/bin/env python3
"""WSTA149 host-only summary for the D-public HUD intent syscall trace proof."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta149_dpublic_hud_intent_syscall_trace as wsta149  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
PASS_DECISION = wsta149.PASS_DECISION
RESULT_NAME = "wsta149_dpublic_hud_intent_syscall_trace_live.json"
ATOMIC_RENAME_SYSCALLS = wsta149.ATOMIC_RENAME_SYSCALLS
NETWORK_SYSCALLS = wsta149.NETWORK_SYSCALLS


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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


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
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_source_result(source: dict[str, Any]) -> dict[str, bool]:
    checks = source.get("checks") if isinstance(source.get("checks"), dict) else {}
    profile = source.get("syscall_profile") if isinstance(source.get("syscall_profile"), dict) else {}
    trace_artifacts = (
        profile.get("trace_artifacts")
        if isinstance(profile.get("trace_artifacts"), dict)
        else {}
    )
    syscalls = profile.get("syscall_names") if isinstance(profile.get("syscall_names"), list) else []
    final_version = source.get("final_version") if isinstance(source.get("final_version"), dict) else {}
    final_selftest = source.get("final_selftest") if isinstance(source.get("final_selftest"), dict) else {}
    safety_record = source.get("safety") if isinstance(source.get("safety"), dict) else {}
    no_device_mutation = all(
        safety_record.get(key) is False
        for key in (
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
            "drm_open",
            "kms_setcrtc",
        )
    )
    return {
        "source_decision_pass": source.get("decision") == wsta149.PASS_DECISION,
        "source_no_mutating_device_action": no_device_mutation,
        "strace_image_sha_match": source.get("local_image_sha256") == wsta149.WSTA115_STRACE_IMAGE_SHA256,
        "identity_and_launcher_proven": bool(
            checks.get("service_identity_ok")
            and checks.get("launcher_exec_logged")
            and profile.get("no_new_privs")
            and profile.get("cap_eff_zero")
        ),
        "intent_write_proven": bool(
            checks.get("intent_written")
            and checks.get("intent_schema_ok")
            and profile.get("intent_path") == wsta149.REMOTE_INTENT_JSON
            and profile.get("intent_sequence") == wsta149.INTENT_SEQUENCE
        ),
        "atomic_path_proven": bool(
            checks.get("atomic_rename_observed")
            and profile.get("atomic_rename_observed")
            and "fsync" in syscalls
            and any(name in syscalls for name in wsta149.ATOMIC_RENAME_SYSCALLS)
        ),
        "no_network_syscalls": bool(
            checks.get("network_syscalls_absent")
            and profile.get("network_syscalls_absent")
            and not any(name in syscalls for name in wsta149.NETWORK_SYSCALLS)
        ),
        "no_drm_or_ioctl": bool(
            checks.get("drm_syscalls_absent")
            and profile.get("ioctl_syscall_absent")
            and profile.get("drm_trace_absent")
            and "ioctl" not in syscalls
        ),
        "trace_artifacts_saved": bool(checks.get("trace_artifact_saved") and trace_artifacts.get("all_saved")),
        "final_health_clean": bool(
            checks.get("final_selftest_fail_zero")
            and "v3402-dpublic-hud-presenter-restart-policy" in str(final_version.get("text") or "")
            and "selftest: pass=12 warn=1 fail=0" in str(final_selftest.get("text") or "")
        ),
        "redaction_clean": bool(
            source.get("public_url_value_logged") is not True
            and int(source.get("secret_values_logged") or 0) == 0
            and profile.get("public_url_value_logged") is False
            and int(profile.get("secret_values_logged") or 0) == 0
        ),
    }


def summarize_source(source: dict[str, Any], source_path: Path) -> dict[str, Any]:
    profile = source.get("syscall_profile") if isinstance(source.get("syscall_profile"), dict) else {}
    trace_artifacts = (
        profile.get("trace_artifacts")
        if isinstance(profile.get("trace_artifacts"), dict)
        else {}
    )
    proof = {
        "schema": "a90-wsta149-dpublic-hud-intent-syscall-trace-live-v1",
        "source_json": rel(source_path),
        "source_run_dir": source.get("run_dir"),
        "service": "dpublic-hud",
        "scope": "hud-intent-producer-only",
        "intent_path": profile.get("intent_path"),
        "intent_sequence": profile.get("intent_sequence"),
        "command_shape": profile.get("command_shape"),
        "uid": 3904,
        "gid": 3904,
        "no_new_privs": bool(profile.get("no_new_privs")),
        "cap_eff_zero": bool(profile.get("cap_eff_zero")),
        "public_default_off": bool(profile.get("public_default_off")),
        "native_presenter_owner": bool(profile.get("native_presenter_owner")),
        "atomic_rename_observed": bool(profile.get("atomic_rename_observed")),
        "network_syscalls_absent": bool(profile.get("network_syscalls_absent")),
        "ioctl_syscall_absent": bool(profile.get("ioctl_syscall_absent")),
        "drm_trace_absent": bool(profile.get("drm_trace_absent")),
        "core_syscalls_observed": bool(profile.get("core_syscalls_observed")),
        "core_syscalls": list(profile.get("core_syscalls") or []),
        "syscall_count": int(profile.get("syscall_count") or 0),
        "syscall_names": list(profile.get("syscall_names") or []),
        "trace_artifacts_saved": bool(trace_artifacts.get("all_saved")),
        "raw_trace_sha256": (
            trace_artifacts.get("raw_trace", {}).get("sha256")
            if isinstance(trace_artifacts.get("raw_trace"), dict)
            else None
        ),
        "syscall_list_sha256": (
            trace_artifacts.get("syscall_list", {}).get("sha256")
            if isinstance(trace_artifacts.get("syscall_list"), dict)
            else None
        ),
        "intent_json_sha256": (
            trace_artifacts.get("intent_json", {}).get("sha256")
            if isinstance(trace_artifacts.get("intent_json"), dict)
            else None
        ),
        "checks": validate_source_result(source),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    proof["decision"] = PASS_DECISION if all(proof["checks"].values()) else "wsta149-dpublic-hud-intent-syscall-trace-live-fail"
    return proof


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta149-dpublic-hud-intent-syscall-trace-summary-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA149 host-only D-public HUD intent syscall trace summary",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety(),
        "checks": {
            "explicit_gate": bool(args.summarize_wsta149_hud_intent_trace),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta149-summary-blocked-explicit-gate-required"
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta149-summary-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    source_json = resolve_path(args.source_json)
    if not source_json.is_file():
        result["decision"] = "wsta149-summary-blocked-source-json-missing"
        result["source_json"] = rel(source_json)
        result["ended_utc"] = utc_stamp()
        return result
    source = load_json(source_json)
    proof = summarize_source(source, source_json)
    result["proof"] = proof
    result["decision"] = proof["decision"]
    result["checks"].update({
        "source_json_present": True,
        "source_result_valid": proof["decision"] == PASS_DECISION,
        "redaction_clean": bool(proof["checks"].get("redaction_clean")),
    })
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / RESULT_NAME, proof)
    write_json(run_dir / "wsta149_summary_result.json", result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-json", type=Path, required=True)
    parser.add_argument("--summarize-wsta149-hud-intent-trace", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
