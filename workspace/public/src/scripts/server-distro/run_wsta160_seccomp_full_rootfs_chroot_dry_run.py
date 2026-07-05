#!/usr/bin/env python3
"""WSTA160 host-only full-rootfs seccomp launcher chroot dry-run.

Prepares a private full WSTA rootfs with the WSTA153 policy, WSTA156 filter
artifact, and WSTA158 check-only helper staged, then enters the private copy
through ``unshare -r chroot``.  Inside the chroot, the launcher uses its default
absolute seccomp paths, including
``/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly``.  The run proves
the helper check-only path executes before actual seccomp load/enforcement stays
blocked.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
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
DEFAULT_SOURCE_ROOTFS = wsta3.DEFAULT_SOURCE_ROOTFS
DEFAULT_WSTA153_POLICY = wsta3.DEFAULT_SECCOMP_POLICY_SOURCE
DEFAULT_WSTA156_MANIFEST = wsta3.DEFAULT_SECCOMP_FILTER_MANIFEST
DEFAULT_WSTA156_OBJECT = wsta3.DEFAULT_SECCOMP_FILTER_OBJECT
DEFAULT_WSTA158_MANIFEST = wsta3.DEFAULT_SECCOMP_LOADER_HELPER_MANIFEST
DEFAULT_WSTA158_HELPER = wsta3.DEFAULT_SECCOMP_LOADER_HELPER
PASS_DECISION = "wsta160-seccomp-full-rootfs-chroot-dry-run-pass"
SUMMARY_NAME = "wsta160_result.json"
DRY_RUN_STDOUT_NAME = "full_rootfs_chroot_dry_run_stdout.txt"
ENFORCE_STDOUT_NAME = "full_rootfs_chroot_enforce_stdout.txt"


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
    wsta3.write_json(path, payload)


def safety_flags() -> dict[str, Any]:
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
        "host_private_chroot": True,
        "device_chroot": False,
        "seccomp_filter_built": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "bpf_load": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "proof": result.get("proof", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def make_fake_setpriv(rootfs: Path) -> Path:
    fakebin = rootfs / "fakebin"
    fakebin.mkdir(parents=True, exist_ok=True)
    fake = fakebin / "setpriv"
    fake.write_text(
        "#!/bin/sh\n"
        "echo \"fake_setpriv_args=$*\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake


def stage_full_rootfs(rootfs: Path,
                      policy_path: Path,
                      filter_manifest: Path,
                      filter_object: Path,
                      helper_manifest: Path,
                      helper_binary: Path) -> dict[str, Any]:
    return {
        "service_identities": wsta3.stage_service_identities(rootfs),
        "service_launcher": wsta3.stage_no_new_privs_launcher(rootfs),
        "service_hardening_policy": wsta3.stage_service_hardening_policy(rootfs),
        "seccomp_launcher_policy": wsta3.stage_seccomp_launcher_policy(rootfs, policy_path, require=True),
        "seccomp_filter_artifact": wsta3.stage_seccomp_filter_artifact(
            rootfs,
            filter_manifest,
            filter_object,
            require=True,
        ),
        "seccomp_loader_helper": wsta3.stage_seccomp_loader_helper(
            rootfs,
            helper_manifest,
            helper_binary,
            require=True,
        ),
        "service_hardening_stage_marker": wsta3.stage_service_hardening_stage_marker(rootfs),
    }


def run_chroot_launcher(unshare_cmd: str, rootfs: Path, *, enforce: bool) -> dict[str, Any]:
    env_items = [
        "PATH=/fakebin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN=1",
    ]
    if enforce:
        env_items.append("A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1")
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


def marker_value(stdout: str, key: str) -> str | None:
    prefix = key + "="
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def validate_proof(dry_run: dict[str, Any], enforce_run: dict[str, Any]) -> dict[str, bool]:
    dry_stdout = str(dry_run.get("stdout") or "")
    enforce_stdout = str(enforce_run.get("stdout") or "")
    return {
        "dry_run_returncode_zero": dry_run.get("returncode") == 0,
        "dry_run_helper_present": marker_value(dry_stdout, "A90WSTA159_SECCOMP_HELPER_PRESENT") == "1",
        "dry_run_exec_reached": "a90_service_launcher_decision=exec" in dry_stdout,
        "dry_run_fake_setpriv_called": "fake_setpriv_args=--no-new-privs --reuid a90hud --regid a90hud" in dry_stdout,
        "enforce_returncode_65": enforce_run.get("returncode") == 65,
        "enforce_helper_present": marker_value(enforce_stdout, "A90WSTA159_SECCOMP_HELPER_PRESENT") == "1",
        "enforce_helper_check_only_ok": marker_value(enforce_stdout, "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK") == "1",
        "enforce_loader_check_only_marker": marker_value(enforce_stdout, "A90WSTA158_LOADER_CHECK_ONLY") == "1",
        "enforce_loader_load_zero": marker_value(enforce_stdout, "A90WSTA158_SECCOMP_LOAD") == "0",
        "enforce_loader_hud_profile": "service=dpublic-hud policy_service=dpublic-hud-intent" in enforce_stdout,
        "enforce_blocks_unimplemented": (
            "a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented" in enforce_stdout
        ),
        "enforce_blocks_before_exec": (
            "fake_setpriv_args=" not in enforce_stdout
            and "a90_service_launcher_decision=exec" not in enforce_stdout
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta160-seccomp-full-rootfs-chroot-dry-run-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    paths = {
        "source_rootfs": resolve_path(args.source_rootfs),
        "policy_json": resolve_path(args.wsta153_seccomp_policy_json),
        "filter_manifest": resolve_path(args.wsta156_filter_manifest_json),
        "filter_object": resolve_path(args.wsta156_filter_object),
        "helper_manifest": resolve_path(args.wsta158_loader_helper_manifest_json),
        "helper_binary": resolve_path(args.wsta158_loader_helper),
    }
    unshare_path = shutil.which(args.unshare)
    result: dict[str, Any] = {
        "scope": "WSTA160 host-only full-rootfs seccomp launcher chroot dry-run",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.execute_full_rootfs_chroot_dry_run),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "source_rootfs_private": is_under(paths["source_rootfs"], PRIVATE_ROOT),
            "source_rootfs_present": paths["source_rootfs"].is_dir(),
            "policy_json_private": is_under(paths["policy_json"], PRIVATE_ROOT),
            "policy_json_present": paths["policy_json"].is_file(),
            "filter_manifest_private": is_under(paths["filter_manifest"], PRIVATE_ROOT),
            "filter_manifest_present": paths["filter_manifest"].is_file(),
            "filter_object_private": is_under(paths["filter_object"], PRIVATE_ROOT),
            "filter_object_present": paths["filter_object"].is_file(),
            "helper_manifest_private": is_under(paths["helper_manifest"], PRIVATE_ROOT),
            "helper_manifest_present": paths["helper_manifest"].is_file(),
            "helper_binary_private": is_under(paths["helper_binary"], PRIVATE_ROOT),
            "helper_binary_present": paths["helper_binary"].is_file(),
            "unshare_present": bool(unshare_path),
        },
    }
    for key, decision in (
        ("explicit_gate", "wsta160-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta160-blocked-nonprivate-run-dir"),
        ("source_rootfs_private", "wsta160-blocked-source-rootfs-nonprivate"),
        ("source_rootfs_present", "wsta160-blocked-source-rootfs-missing"),
        ("policy_json_private", "wsta160-blocked-policy-json-nonprivate"),
        ("policy_json_present", "wsta160-blocked-policy-json-missing"),
        ("filter_manifest_private", "wsta160-blocked-filter-manifest-nonprivate"),
        ("filter_manifest_present", "wsta160-blocked-filter-manifest-missing"),
        ("filter_object_private", "wsta160-blocked-filter-object-nonprivate"),
        ("filter_object_present", "wsta160-blocked-filter-object-missing"),
        ("helper_manifest_private", "wsta160-blocked-helper-manifest-nonprivate"),
        ("helper_manifest_present", "wsta160-blocked-helper-manifest-missing"),
        ("helper_binary_private", "wsta160-blocked-helper-binary-nonprivate"),
        ("helper_binary_present", "wsta160-blocked-helper-binary-missing"),
        ("unshare_present", "wsta160-blocked-unshare-missing"),
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
    stage = stage_full_rootfs(
        rootfs,
        paths["policy_json"],
        paths["filter_manifest"],
        paths["filter_object"],
        paths["helper_manifest"],
        paths["helper_binary"],
    )
    wsta3.d4c.verify_rootfs(rootfs)
    result["stage"] = stage
    result["checks"]["rootfs_copy_staged"] = rootfs.is_dir()
    result["checks"]["service_launcher_staged"] = stage["service_launcher"].get("seccomp_helper_check_call_present") is True
    result["checks"]["helper_default_path_staged"] = (rootfs / wsta3.TARGET_SECCOMP_LOADER_HELPER).is_file()
    fake_setpriv = make_fake_setpriv(rootfs)
    dry_run = run_chroot_launcher(args.unshare, rootfs, enforce=False)
    enforce_run = run_chroot_launcher(args.unshare, rootfs, enforce=True)
    proof_checks = validate_proof(dry_run, enforce_run)
    result["proof"] = {
        "rootfs": rel(rootfs),
        "fake_setpriv": "/" + str(fake_setpriv.relative_to(rootfs)),
        "default_helper_path_inside_chroot": "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER),
        "dry_run_stdout_artifact": rel(run_dir / DRY_RUN_STDOUT_NAME),
        "enforce_stdout_artifact": rel(run_dir / ENFORCE_STDOUT_NAME),
        "dry_run_returncode": dry_run.get("returncode"),
        "enforce_returncode": enforce_run.get("returncode"),
        "filter_load_enabled": False,
        "seccomp_enforced": False,
    }
    result["proof_checks"] = proof_checks
    result["checks"].update({f"proof_{key}": value for key, value in proof_checks.items()})
    result["decision"] = PASS_DECISION if all(proof_checks.values()) else "wsta160-blocked-proof-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    (run_dir / DRY_RUN_STDOUT_NAME).write_text(str(dry_run.get("stdout") or ""), encoding="utf-8")
    (run_dir / ENFORCE_STDOUT_NAME).write_text(str(enforce_run.get("stdout") or ""), encoding="utf-8")
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-rootfs", type=Path, default=DEFAULT_SOURCE_ROOTFS)
    parser.add_argument("--wifi-env", type=Path, default=wsta3.DEFAULT_WIFI_ENV)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--wsta156-filter-manifest-json", type=Path, default=DEFAULT_WSTA156_MANIFEST)
    parser.add_argument("--wsta156-filter-object", type=Path, default=DEFAULT_WSTA156_OBJECT)
    parser.add_argument("--wsta158-loader-helper-manifest-json", type=Path, default=DEFAULT_WSTA158_MANIFEST)
    parser.add_argument("--wsta158-loader-helper", type=Path, default=DEFAULT_WSTA158_HELPER)
    parser.add_argument("--unshare", default="unshare")
    parser.add_argument("--execute-full-rootfs-chroot-dry-run", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta160-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
