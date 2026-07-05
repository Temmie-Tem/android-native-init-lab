#!/usr/bin/env python3
"""WSTA164 host-only chroot proof for seccomp load-env contract.

Stages the WSTA161 gated-apply helper into a private full rootfs and proves the
launcher only forwards the helper's load environment after a second explicit
WSTA164 gate.  The proof never supplies the correct WSTA161 load token: the
strongest path forwards a deliberately wrong token and must still stop before
``A90WSTA161_SECCOMP_LOAD_ATTEMPT=1``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta163_seccomp_helper_apply_gate_chroot_proof as wsta163  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_SOURCE_ROOTFS = wsta3.DEFAULT_SOURCE_ROOTFS
DEFAULT_WSTA153_POLICY = wsta3.DEFAULT_SECCOMP_POLICY_SOURCE
DEFAULT_WSTA156_MANIFEST = wsta3.DEFAULT_SECCOMP_FILTER_MANIFEST
DEFAULT_WSTA156_OBJECT = wsta3.DEFAULT_SECCOMP_FILTER_OBJECT
DEFAULT_WSTA161_MANIFEST = wsta163.DEFAULT_WSTA161_MANIFEST
DEFAULT_WSTA161_HELPER = wsta163.DEFAULT_WSTA161_HELPER
PASS_DECISION = "wsta164-seccomp-load-env-contract-chroot-proof-pass"
SUMMARY_NAME = "wsta164_result.json"
NO_LOAD_GATE_STDOUT_NAME = "helper_apply_no_load_gate_stdout.txt"
MISSING_TOKEN_STDOUT_NAME = "helper_apply_missing_load_token_stdout.txt"
WRONG_TOKEN_STDOUT_NAME = "helper_apply_wrong_load_token_stdout.txt"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


def safety_flags() -> dict[str, Any]:
    flags = wsta163.safety_flags()
    flags["seccomp_load_env_contract_exercised"] = True
    flags["seccomp_load_env_contract_wrong_token_only"] = True
    flags["seccomp_filter_loaded"] = False
    flags["seccomp_enforced"] = False
    flags["secret_values_logged"] = 0
    return flags


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "proof": result.get("proof", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def run_chroot_launcher_load_env(unshare_cmd: str, rootfs: Path, *, scenario: str) -> dict[str, Any]:
    env_items = [
        "PATH=/fakebin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN=1",
        "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_MODE=apply",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE=WSTA163-ALLOW-HELPER-APPLY",
    ]
    if scenario in {"missing-token", "wrong-token"}:
        env_items.append("A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE=WSTA164-ALLOW-SECCOMP-LOAD-ENV")
    if scenario == "wrong-token":
        env_items.append("A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN=wrong-token")
    command = [
        unshare_cmd,
        "-r",
        "chroot",
        str(rootfs),
        "/usr/bin/env",
        "-i",
        *env_items,
        "/usr/local/bin/a90-service-launch",
        "dpublic-hud",
        "/bin/true",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30.0,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def validate_proof(no_gate_run: dict[str, Any],
                   missing_token_run: dict[str, Any],
                   wrong_token_run: dict[str, Any]) -> dict[str, bool]:
    no_gate_stdout = str(no_gate_run.get("stdout") or "")
    missing_stdout = str(missing_token_run.get("stdout") or "")
    wrong_stdout = str(wrong_token_run.get("stdout") or "")
    return {
        "no_gate_returncode_65": no_gate_run.get("returncode") == 65,
        "no_gate_marker_zero": wsta160.marker_value(no_gate_stdout, "A90WSTA164_SECCOMP_LOAD_ENV_GATE") == "0",
        "no_gate_helper_invoked_apply": wsta160.marker_value(no_gate_stdout, "A90WSTA161_LOADER_GATED_APPLY") == "1",
        "no_gate_blocks_load_gate": "a90_seccomp_loader_decision=blocked-load-gate-required" in no_gate_stdout,
        "no_gate_no_load_attempt": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" not in no_gate_stdout,
        "missing_token_returncode_65": missing_token_run.get("returncode") == 65,
        "missing_token_gate_marker_one": (
            wsta160.marker_value(missing_stdout, "A90WSTA164_SECCOMP_LOAD_ENV_GATE") == "1"
        ),
        "missing_token_blocks_before_helper": (
            "a90_service_launcher_decision=blocked-seccomp-helper-load-token-required" in missing_stdout
            and "A90WSTA161_LOADER_GATED_APPLY=1" not in missing_stdout
        ),
        "missing_token_no_load_attempt": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" not in missing_stdout,
        "wrong_token_returncode_65": wrong_token_run.get("returncode") == 65,
        "wrong_token_gate_marker_one": wsta160.marker_value(wrong_stdout, "A90WSTA164_SECCOMP_LOAD_ENV_GATE") == "1",
        "wrong_token_token_present_marker": (
            wsta160.marker_value(wrong_stdout, "A90WSTA164_SECCOMP_LOAD_TOKEN_PRESENT") == "1"
        ),
        "wrong_token_helper_invoked_apply": wsta160.marker_value(wrong_stdout, "A90WSTA161_LOADER_GATED_APPLY") == "1",
        "wrong_token_load_zero": wsta160.marker_value(wrong_stdout, "A90WSTA161_SECCOMP_LOAD") == "0",
        "wrong_token_hud_profile": "service=dpublic-hud policy_service=dpublic-hud-intent" in wrong_stdout,
        "wrong_token_blocks_token": "a90_seccomp_loader_decision=blocked-load-token-required" in wrong_stdout,
        "wrong_token_no_load_attempt": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" not in wrong_stdout,
        "wrong_token_launcher_reports_failed": (
            "a90_service_launcher_decision=blocked-seccomp-helper-apply-failed" in wrong_stdout
        ),
        "wrong_token_blocks_before_exec": (
            "fake_setpriv_args=" not in wrong_stdout
            and "a90_service_launcher_decision=exec" not in wrong_stdout
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta164-seccomp-load-env-contract-chroot-proof-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    paths = {
        "source_rootfs": resolve_path(args.source_rootfs),
        "policy_json": resolve_path(args.wsta153_seccomp_policy_json),
        "filter_manifest": resolve_path(args.wsta156_filter_manifest_json),
        "filter_object": resolve_path(args.wsta156_filter_object),
        "helper_manifest": resolve_path(args.wsta161_loader_helper_manifest_json),
        "helper_binary": resolve_path(args.wsta161_loader_helper),
    }
    unshare_path = shutil.which(args.unshare)
    result: dict[str, Any] = {
        "scope": "WSTA164 host-only seccomp load-env contract chroot proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.execute_load_env_contract_chroot_proof),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "source_rootfs_private": wsta160.is_under(paths["source_rootfs"], PRIVATE_ROOT),
            "source_rootfs_present": paths["source_rootfs"].is_dir(),
            "policy_json_private": wsta160.is_under(paths["policy_json"], PRIVATE_ROOT),
            "policy_json_present": paths["policy_json"].is_file(),
            "filter_manifest_private": wsta160.is_under(paths["filter_manifest"], PRIVATE_ROOT),
            "filter_manifest_present": paths["filter_manifest"].is_file(),
            "filter_object_private": wsta160.is_under(paths["filter_object"], PRIVATE_ROOT),
            "filter_object_present": paths["filter_object"].is_file(),
            "helper_manifest_private": wsta160.is_under(paths["helper_manifest"], PRIVATE_ROOT),
            "helper_manifest_present": paths["helper_manifest"].is_file(),
            "helper_binary_private": wsta160.is_under(paths["helper_binary"], PRIVATE_ROOT),
            "helper_binary_present": paths["helper_binary"].is_file(),
            "unshare_present": bool(unshare_path),
        },
    }
    for key, decision in (
        ("explicit_gate", "wsta164-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta164-blocked-nonprivate-run-dir"),
        ("source_rootfs_private", "wsta164-blocked-source-rootfs-nonprivate"),
        ("source_rootfs_present", "wsta164-blocked-source-rootfs-missing"),
        ("policy_json_private", "wsta164-blocked-policy-json-nonprivate"),
        ("policy_json_present", "wsta164-blocked-policy-json-missing"),
        ("filter_manifest_private", "wsta164-blocked-filter-manifest-nonprivate"),
        ("filter_manifest_present", "wsta164-blocked-filter-manifest-missing"),
        ("filter_object_private", "wsta164-blocked-filter-object-nonprivate"),
        ("filter_object_present", "wsta164-blocked-filter-object-missing"),
        ("helper_manifest_private", "wsta164-blocked-helper-manifest-nonprivate"),
        ("helper_manifest_present", "wsta164-blocked-helper-manifest-missing"),
        ("helper_binary_private", "wsta164-blocked-helper-binary-nonprivate"),
        ("helper_binary_present", "wsta164-blocked-helper-binary-missing"),
        ("unshare_present", "wsta164-blocked-unshare-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if key.endswith("_present"):
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    run_dir.mkdir(parents=True, exist_ok=True)
    rootfs = run_dir / "rootfs"
    wsta3.d4c.verify_rootfs(paths["source_rootfs"])
    wsta3.copy_rootfs(paths["source_rootfs"], rootfs)
    stage = wsta160.stage_full_rootfs(
        rootfs,
        paths["policy_json"],
        paths["filter_manifest"],
        paths["filter_object"],
        paths["helper_manifest"],
        paths["helper_binary"],
    )
    wsta3.d4c.verify_rootfs(rootfs)
    result["stage"] = stage
    launcher = stage.get("service_launcher", {})
    result["checks"]["launcher_has_wsta164_load_gate"] = launcher.get("seccomp_helper_load_env_gate_present") is True
    result["checks"]["launcher_forwards_load_env"] = launcher.get("seccomp_helper_load_env_forwarding_present") is True
    result["checks"]["launcher_does_not_hardcode_wsta161_token"] = (
        launcher.get("seccomp_helper_load_token_literal_absent") is True
    )
    result["checks"]["helper_schema_is_wsta161"] = (
        stage["seccomp_loader_helper"].get("helper_schema")
        == "a90-wsta161-seccomp-loader-gated-apply-helper-v1"
    )
    result["checks"]["helper_apply_code_compiled"] = stage["seccomp_loader_helper"].get("apply_code_compiled") is True
    wsta160.make_fake_setpriv(rootfs)
    no_gate_run = run_chroot_launcher_load_env(args.unshare, rootfs, scenario="no-load-gate")
    missing_token_run = run_chroot_launcher_load_env(args.unshare, rootfs, scenario="missing-token")
    wrong_token_run = run_chroot_launcher_load_env(args.unshare, rootfs, scenario="wrong-token")
    proof_checks = validate_proof(no_gate_run, missing_token_run, wrong_token_run)
    result["proof"] = {
        "rootfs": rel(rootfs),
        "default_helper_path_inside_chroot": "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER),
        "helper_schema": stage["seccomp_loader_helper"].get("helper_schema"),
        "no_load_gate_stdout_artifact": rel(run_dir / NO_LOAD_GATE_STDOUT_NAME),
        "missing_token_stdout_artifact": rel(run_dir / MISSING_TOKEN_STDOUT_NAME),
        "wrong_token_stdout_artifact": rel(run_dir / WRONG_TOKEN_STDOUT_NAME),
        "no_load_gate_returncode": no_gate_run.get("returncode"),
        "missing_token_returncode": missing_token_run.get("returncode"),
        "wrong_token_returncode": wrong_token_run.get("returncode"),
        "correct_wsta161_token_supplied": False,
        "filter_load_enabled": False,
        "seccomp_enforced": False,
    }
    result["proof_checks"] = proof_checks
    result["checks"].update({f"proof_{key}": value for key, value in proof_checks.items()})
    result["decision"] = PASS_DECISION if all(proof_checks.values()) else "wsta164-blocked-proof-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    (run_dir / NO_LOAD_GATE_STDOUT_NAME).write_text(str(no_gate_run.get("stdout") or ""), encoding="utf-8")
    (run_dir / MISSING_TOKEN_STDOUT_NAME).write_text(str(missing_token_run.get("stdout") or ""), encoding="utf-8")
    (run_dir / WRONG_TOKEN_STDOUT_NAME).write_text(str(wrong_token_run.get("stdout") or ""), encoding="utf-8")
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-rootfs", type=Path, default=DEFAULT_SOURCE_ROOTFS)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--wsta156-filter-manifest-json", type=Path, default=DEFAULT_WSTA156_MANIFEST)
    parser.add_argument("--wsta156-filter-object", type=Path, default=DEFAULT_WSTA156_OBJECT)
    parser.add_argument("--wsta161-loader-helper-manifest-json", type=Path, default=DEFAULT_WSTA161_MANIFEST)
    parser.add_argument("--wsta161-loader-helper", type=Path, default=DEFAULT_WSTA161_HELPER)
    parser.add_argument("--unshare", default="unshare")
    parser.add_argument("--execute-load-env-contract-chroot-proof", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta164-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
