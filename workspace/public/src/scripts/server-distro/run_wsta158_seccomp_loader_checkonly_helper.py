#!/usr/bin/env python3
"""WSTA158 host-only seccomp loader helper check-only build/proof.

Builds a separate aarch64 helper linked with the WSTA156 non-loaded filter
object.  The helper's default contract is check-only: it enumerates linked
filter lengths and refuses load requests unless a future explicit loader gate
implements the load path.  This unit does not load BPF, load seccomp, chroot,
touch the device, or enforce seccomp.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
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


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA156_MANIFEST = wsta3.DEFAULT_SECCOMP_FILTER_MANIFEST
DEFAULT_WSTA156_OBJECT = wsta3.DEFAULT_SECCOMP_FILTER_OBJECT
PASS_DECISION = "wsta158-seccomp-loader-checkonly-helper-pass"
SUMMARY_NAME = "wsta158_result.json"
MANIFEST_NAME = "wsta158_seccomp_loader_helper_manifest.json"
HELPER_SOURCE_NAME = "a90_seccomp_loader_checkonly.c"
HELPER_BINARY_NAME = "a90-seccomp-loader-checkonly"
CHECK_STDOUT_NAME = "loader_check_only_stdout.txt"
SERVICE_STDOUT_NAME = "loader_service_check_stdout.txt"
APPLY_STDOUT_NAME = "loader_apply_block_stdout.txt"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


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
        "chroot": False,
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
        "artifact": result.get("artifact", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def service_symbol(service: str) -> str:
    return service.replace("-", "_")


def policy_services(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    values = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    return [item for item in values if isinstance(item, dict)]


def validate_filter_inputs(manifest: dict[str, Any], object_path: Path) -> dict[str, bool]:
    checks = wsta3.validate_seccomp_filter_manifest(manifest, object_path)
    return {
        **checks,
        "object_sha_matches_manifest": checks.get("object_sha_matches_manifest") is True,
        "service_names_expected": {
            str(item.get("service")) for item in policy_services(manifest)
        } == {
            "dpublic-smoke-httpd",
            "cloudflared-quick-tunnel",
            "dropbear-admin-usb",
            "dpublic-hud-intent",
        },
    }


def emit_helper_source(manifest: dict[str, Any]) -> str:
    declarations = [
        "extern struct sock_filter a90_wsta156_dpublic_smoke_httpd_filter[];",
        "extern const unsigned short a90_wsta156_dpublic_smoke_httpd_filter_len;",
        "extern struct sock_filter a90_wsta156_cloudflared_quick_tunnel_filter[];",
        "extern const unsigned short a90_wsta156_cloudflared_quick_tunnel_filter_len;",
        "extern struct sock_filter a90_wsta156_dropbear_admin_usb_filter[];",
        "extern const unsigned short a90_wsta156_dropbear_admin_usb_filter_len;",
        "extern struct sock_filter a90_wsta156_dpublic_hud_intent_filter[];",
        "extern const unsigned short a90_wsta156_dpublic_hud_intent_filter_len;",
        "extern const unsigned int a90_wsta156_service_count;",
        "extern const unsigned int a90_wsta156_audit_arch_aarch64;",
    ]
    table = []
    for service in policy_services(manifest):
        name = str(service["service"])
        launcher = "dpublic-hud" if name == "dpublic-hud-intent" else name
        sym = service_symbol(name)
        table.append(
            "  {"
            f"\"{launcher}\", \"{name}\", \"{service.get('profile_name')}\", "
            f"a90_wsta156_{sym}_filter, &a90_wsta156_{sym}_filter_len"
            "},"
        )
    return "\n".join([
        "/* Auto-generated by WSTA158. Check-only helper; no seccomp load in this unit. */",
        "#include <linux/filter.h>",
        "#include <stdio.h>",
        "#include <string.h>",
        "",
        *declarations,
        "",
        "struct a90_profile {",
        "  const char *launcher_service;",
        "  const char *policy_service;",
        "  const char *profile_name;",
        "  struct sock_filter *filter;",
        "  const unsigned short *filter_len;",
        "};",
        "",
        "static const struct a90_profile profiles[] = {",
        *table,
        "};",
        "",
        "static const struct a90_profile *find_profile(const char *name) {",
        "  size_t i;",
        "  for (i = 0; i < sizeof(profiles) / sizeof(profiles[0]); ++i) {",
        "    if (strcmp(name, profiles[i].launcher_service) == 0 ||",
        "        strcmp(name, profiles[i].policy_service) == 0) {",
        "      return &profiles[i];",
        "    }",
        "  }",
        "  return NULL;",
        "}",
        "",
        "static void print_profile(const struct a90_profile *profile) {",
        "  printf(\"A90WSTA158_PROFILE service=%s policy_service=%s profile=%s len=%hu\\n\",",
        "         profile->launcher_service, profile->policy_service,",
        "         profile->profile_name, *profile->filter_len);",
        "}",
        "",
        "int main(int argc, char **argv) {",
        "  const char *service = NULL;",
        "  int apply = 0;",
        "  size_t i;",
        "  for (i = 1; i < (size_t)argc; ++i) {",
        "    if (strcmp(argv[i], \"--service\") == 0 && i + 1 < (size_t)argc) {",
        "      service = argv[++i];",
        "    } else if (strcmp(argv[i], \"--apply\") == 0) {",
        "      apply = 1;",
        "    } else if (strcmp(argv[i], \"--check-only\") == 0) {",
        "      continue;",
        "    } else {",
        "      printf(\"a90_seccomp_loader_decision=blocked-unknown-arg\\n\");",
        "      return 64;",
        "    }",
        "  }",
        "  printf(\"A90WSTA158_LOADER_CHECK_ONLY=1\\n\");",
        "  printf(\"A90WSTA158_SECCOMP_LOAD=0\\n\");",
        "  printf(\"A90WSTA158_LINKED_SERVICE_COUNT=%u\\n\", a90_wsta156_service_count);",
        "  printf(\"A90WSTA158_AUDIT_ARCH_AARCH64=%u\\n\", a90_wsta156_audit_arch_aarch64);",
        "  if (apply) {",
        "    printf(\"a90_seccomp_loader_decision=blocked-allow-load-required\\n\");",
        "    return 65;",
        "  }",
        "  if (service != NULL) {",
        "    const struct a90_profile *profile = find_profile(service);",
        "    if (profile == NULL) {",
        "      printf(\"a90_seccomp_loader_decision=blocked-unknown-service\\n\");",
        "      return 64;",
        "    }",
        "    print_profile(profile);",
        "  } else {",
        "    for (i = 0; i < sizeof(profiles) / sizeof(profiles[0]); ++i) {",
        "      print_profile(&profiles[i]);",
        "    }",
        "  }",
        "  printf(\"a90_seccomp_loader_decision=check-only\\n\");",
        "  return 0;",
        "}",
        "",
    ])


def run_command(command: list[str], *, cwd: Path = REPO_ROOT, timeout: float = 30.0) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "ok": completed.returncode == 0,
    }


def build_helper(gcc: str, helper_source: Path, filter_object: Path, binary: Path) -> dict[str, Any]:
    command = [
        gcc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-Werror",
        str(helper_source),
        str(filter_object),
        "-o",
        str(binary),
    ]
    return run_command(command, timeout=60.0)


def check_outputs(stdout: str, *, service_only: bool) -> dict[str, bool]:
    return {
        "check_only_marker": "A90WSTA158_LOADER_CHECK_ONLY=1" in stdout,
        "load_zero_marker": "A90WSTA158_SECCOMP_LOAD=0" in stdout,
        "service_count_marker": "A90WSTA158_LINKED_SERVICE_COUNT=4" in stdout,
        "decision_check_only": "a90_seccomp_loader_decision=check-only" in stdout,
        "hud_profile_present": "policy_service=dpublic-hud-intent" in stdout,
        "all_profiles_present": (
            service_only
            or all(
                marker in stdout
                for marker in (
                    "policy_service=dpublic-smoke-httpd",
                    "policy_service=cloudflared-quick-tunnel",
                    "policy_service=dropbear-admin-usb",
                    "policy_service=dpublic-hud-intent",
                )
            )
        ),
    }


def build_manifest(filter_manifest_path: Path,
                   filter_object_path: Path,
                   helper_source: Path,
                   helper_binary: Path,
                   file_output: str,
                   check_run: dict[str, Any],
                   service_run: dict[str, Any],
                   apply_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "a90-wsta158-seccomp-loader-checkonly-helper-v1",
        "state": "SECCOMP_LOADER_HELPER_CHECK_ONLY_LINKED",
        "source_filter_manifest": rel(filter_manifest_path),
        "source_filter_object": rel(filter_object_path),
        "helper_source": rel(helper_source),
        "helper_binary": rel(helper_binary),
        "helper_sha256": sha256_file(helper_binary),
        "helper_file": file_output,
        "default_mode": "check-only",
        "load_enabled": False,
        "enforced": False,
        "qemu_runs": {
            "check_only": {
                "returncode": check_run.get("returncode"),
                "stdout_artifact": rel(helper_source.with_name(CHECK_STDOUT_NAME)),
            },
            "service_check": {
                "returncode": service_run.get("returncode"),
                "stdout_artifact": rel(helper_source.with_name(SERVICE_STDOUT_NAME)),
            },
            "apply_block": {
                "returncode": apply_run.get("returncode"),
                "stdout_artifact": rel(helper_source.with_name(APPLY_STDOUT_NAME)),
            },
        },
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, bool]:
    return {
        "schema_ok": manifest.get("schema") == "a90-wsta158-seccomp-loader-checkonly-helper-v1",
        "state_ok": manifest.get("state") == "SECCOMP_LOADER_HELPER_CHECK_ONLY_LINKED",
        "default_check_only": manifest.get("default_mode") == "check-only",
        "load_disabled": manifest.get("load_enabled") is False,
        "enforced_false": manifest.get("enforced") is False,
        "helper_is_aarch64_static": "ELF 64-bit LSB executable, ARM aarch64" in str(manifest.get("helper_file"))
        and "statically linked" in str(manifest.get("helper_file")),
        "helper_sha_present": isinstance(manifest.get("helper_sha256"), str)
        and len(str(manifest.get("helper_sha256"))) == 64,
        "redaction_clean": manifest.get("redaction", {}).get("public_url_value_logged") is False
        and manifest.get("redaction", {}).get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta158-seccomp-loader-checkonly-helper-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    filter_manifest_path = resolve_path(args.wsta156_filter_manifest_json)
    filter_object_path = resolve_path(args.wsta156_filter_object)
    gcc_path = shutil.which(args.aarch64_gcc)
    qemu_path = shutil.which(args.qemu_aarch64)
    result: dict[str, Any] = {
        "scope": "WSTA158 host-only seccomp loader helper check-only proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_seccomp_loader_checkonly_helper),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "filter_manifest_private": is_under(filter_manifest_path, PRIVATE_ROOT),
            "filter_manifest_present": filter_manifest_path.is_file(),
            "filter_object_private": is_under(filter_object_path, PRIVATE_ROOT),
            "filter_object_present": filter_object_path.is_file(),
            "aarch64_gcc_present": bool(gcc_path),
            "qemu_aarch64_present": bool(qemu_path),
        },
    }
    for key, decision in (
        ("explicit_gate", "wsta158-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta158-blocked-nonprivate-run-dir"),
        ("filter_manifest_private", "wsta158-blocked-filter-manifest-nonprivate"),
        ("filter_manifest_present", "wsta158-blocked-filter-manifest-missing"),
        ("filter_object_private", "wsta158-blocked-filter-object-nonprivate"),
        ("filter_object_present", "wsta158-blocked-filter-object-missing"),
        ("aarch64_gcc_present", "wsta158-blocked-aarch64-gcc-missing"),
        ("qemu_aarch64_present", "wsta158-blocked-qemu-aarch64-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if key.endswith("_present"):
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    filter_manifest = load_json(filter_manifest_path)
    input_checks = validate_filter_inputs(filter_manifest, filter_object_path)
    result["input_checks"] = input_checks
    result["checks"].update({f"input_{key}": value for key, value in input_checks.items()})
    if not all(input_checks.values()):
        result["decision"] = "wsta158-blocked-filter-artifact-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    run_dir.mkdir(parents=True, exist_ok=True)
    helper_source = run_dir / HELPER_SOURCE_NAME
    helper_binary = run_dir / HELPER_BINARY_NAME
    helper_source.write_text(emit_helper_source(filter_manifest), encoding="utf-8")
    build = build_helper(args.aarch64_gcc, helper_source, filter_object_path, helper_binary)
    result["build"] = build
    result["checks"]["build_ok"] = build.get("ok") is True and helper_binary.is_file()
    if not result["checks"]["build_ok"]:
        result["decision"] = "wsta158-blocked-helper-build-failed"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    file_output = subprocess.check_output(["file", str(helper_binary)], text=True).strip()
    check_run = run_command([args.qemu_aarch64, str(helper_binary), "--check-only"], timeout=10.0)
    service_run = run_command(
        [args.qemu_aarch64, str(helper_binary), "--service", "dpublic-hud", "--check-only"],
        timeout=10.0,
    )
    apply_run = run_command(
        [args.qemu_aarch64, str(helper_binary), "--service", "dpublic-hud", "--apply"],
        timeout=10.0,
    )
    (run_dir / CHECK_STDOUT_NAME).write_text(str(check_run.get("stdout") or ""), encoding="utf-8")
    (run_dir / SERVICE_STDOUT_NAME).write_text(str(service_run.get("stdout") or ""), encoding="utf-8")
    (run_dir / APPLY_STDOUT_NAME).write_text(str(apply_run.get("stdout") or ""), encoding="utf-8")
    qemu_checks = {
        "check_run_ok": check_run.get("returncode") == 0,
        "service_run_ok": service_run.get("returncode") == 0,
        "apply_blocks_65": apply_run.get("returncode") == 65,
        "apply_no_load_marker": "A90WSTA158_SECCOMP_LOAD=0" in str(apply_run.get("stdout") or ""),
        "apply_blocks_allow_load": "blocked-allow-load-required" in str(apply_run.get("stdout") or ""),
        **{f"check_{key}": value for key, value in check_outputs(str(check_run.get("stdout") or ""), service_only=False).items()},
        **{f"service_{key}": value for key, value in check_outputs(str(service_run.get("stdout") or ""), service_only=True).items()},
    }
    result["qemu_checks"] = qemu_checks
    result["checks"].update({f"qemu_{key}": value for key, value in qemu_checks.items()})
    manifest = build_manifest(
        filter_manifest_path,
        filter_object_path,
        helper_source,
        helper_binary,
        file_output,
        check_run,
        service_run,
        apply_run,
    )
    manifest_checks = validate_manifest(manifest)
    result["artifact"] = {
        "manifest": rel(run_dir / MANIFEST_NAME),
        "helper_source": rel(helper_source),
        "helper_binary": rel(helper_binary),
        "helper_sha256": manifest["helper_sha256"],
        "helper_file": manifest["helper_file"],
        "load_enabled": False,
        "enforced": False,
    }
    result["manifest_checks"] = manifest_checks
    result["checks"].update({f"manifest_{key}": value for key, value in manifest_checks.items()})
    result["decision"] = (
        PASS_DECISION
        if all(qemu_checks.values()) and all(manifest_checks.values())
        else "wsta158-blocked-helper-proof-invalid"
    )
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(run_dir / MANIFEST_NAME, manifest)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta156-filter-manifest-json", type=Path, default=DEFAULT_WSTA156_MANIFEST)
    parser.add_argument("--wsta156-filter-object", type=Path, default=DEFAULT_WSTA156_OBJECT)
    parser.add_argument("--aarch64-gcc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--qemu-aarch64", default="qemu-aarch64")
    parser.add_argument("--emit-seccomp-loader-checkonly-helper", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta158-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
