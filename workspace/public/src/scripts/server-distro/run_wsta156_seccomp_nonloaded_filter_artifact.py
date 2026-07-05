#!/usr/bin/env python3
"""WSTA156 host-only non-loaded seccomp filter artifact builder.

Consumes the WSTA153 source policy, resolves observed syscall names against the
aarch64 syscall table, emits classic-BPF ``struct sock_filter`` arrays as C
source, and compiles them to an aarch64 relocatable object.  The artifact is not
loaded, attached, or enforced.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta154_seccomp_launcher_gate_model as wsta154  # noqa: E402


REPO_ROOT = wsta154.REPO_ROOT
PRIVATE_ROOT = wsta154.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta154.DEFAULT_RUN_BASE
DEFAULT_WSTA153_POLICY = wsta154.DEFAULT_WSTA153_POLICY
PASS_DECISION = "wsta156-seccomp-nonloaded-filter-artifact-pass"
SUMMARY_NAME = "wsta156_result.json"
MANIFEST_NAME = "wsta156_seccomp_filter_manifest.json"
C_SOURCE_NAME = "wsta156_seccomp_filters.c"
OBJECT_NAME = "wsta156_seccomp_filters.o"
AUDIT_ARCH_AARCH64 = 0xC00000B7


def rel(path: Path) -> str:
    return wsta154.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta154.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        "seccomp_filter_built": True,
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


def syscall_table(gcc: str = "aarch64-linux-gnu-gcc") -> dict[str, int]:
    completed = subprocess.run(
        [gcc, "-dM", "-E", "-include", "asm/unistd.h", "-"],
        input=b"",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace"))
    table: dict[str, int] = {}
    for line in completed.stdout.decode("utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"#define __NR_([A-Za-z0-9_]+)\s+([0-9]+)", line.strip())
        if match:
            table[match.group(1)] = int(match.group(2))
    return table


def symbol_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def services(policy: dict[str, Any]) -> list[dict[str, Any]]:
    values = policy.get("services") if isinstance(policy.get("services"), list) else []
    return [item for item in values if isinstance(item, dict)]


def resolve_service_syscalls(service: dict[str, Any], table: dict[str, int]) -> dict[str, Any]:
    names = service.get("allowlist") if isinstance(service.get("allowlist"), list) else []
    resolved = []
    missing = []
    for name in names:
        syscall = str(name)
        if syscall in table:
            resolved.append({"name": syscall, "nr": table[syscall]})
        else:
            missing.append(syscall)
    resolved.sort(key=lambda item: (int(item["nr"]), str(item["name"])))
    return {
        "service": service.get("service"),
        "profile_name": service.get("profile_name"),
        "allowlist_count": len(names),
        "resolved_count": len(resolved),
        "missing": missing,
        "syscalls": resolved,
    }


def filter_instruction_count(resolved_count: int) -> int:
    return 2 + (2 * resolved_count) + 1


def emit_service_filter(service: dict[str, Any], resolved: dict[str, Any]) -> str:
    sym = symbol_name(str(service["service"]))
    lines = [
        f"struct sock_filter a90_wsta156_{sym}_filter[] = {{",
        "  BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),",
        "  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),",
        "  BPF_STMT(BPF_RET | BPF_K, A90_SECCOMP_ERRNO_EPERM),",
        "  BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),",
    ]
    for syscall in resolved["syscalls"]:
        lines.extend([
            f"  /* allow {syscall['name']} */",
            f"  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, {syscall['nr']}U, 0, 1),",
            "  BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),",
        ])
    lines.extend([
        "  BPF_STMT(BPF_RET | BPF_K, A90_SECCOMP_ERRNO_EPERM),",
        "};",
        f"const unsigned short a90_wsta156_{sym}_filter_len =",
        f"  (unsigned short)(sizeof(a90_wsta156_{sym}_filter) / sizeof(a90_wsta156_{sym}_filter[0]));",
        "",
    ])
    return "\n".join(lines)


def emit_c_source(policy: dict[str, Any], resolved_services: list[dict[str, Any]]) -> str:
    chunks = [
        "/* Auto-generated by WSTA156. Non-loaded seccomp artifact; do not load from this unit. */",
        "#include <errno.h>",
        "#include <stddef.h>",
        "#include <linux/audit.h>",
        "#include <linux/filter.h>",
        "#include <linux/seccomp.h>",
        "",
        "#define A90_SECCOMP_ERRNO_EPERM (SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA))",
        "",
        "const char a90_wsta156_source_policy_schema[] = \"a90-wsta153-seccomp-policy-source-v1\";",
        f"const unsigned int a90_wsta156_audit_arch_aarch64 = {AUDIT_ARCH_AARCH64}U;",
        f"const unsigned int a90_wsta156_service_count = {len(resolved_services)}U;",
        "",
    ]
    service_by_name = {item.get("service"): item for item in services(policy)}
    for resolved in resolved_services:
        chunks.append(emit_service_filter(service_by_name[resolved["service"]], resolved))
    return "\n".join(chunks)


def build_manifest(policy_path: Path,
                   policy: dict[str, Any],
                   resolved_services: list[dict[str, Any]],
                   c_path: Path,
                   object_path: Path,
                   *,
                   file_output: str) -> dict[str, Any]:
    return {
        "schema": "a90-wsta156-seccomp-nonloaded-filter-artifact-v1",
        "state": "SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED",
        "source_policy_json": rel(policy_path),
        "source_policy_schema": policy.get("schema"),
        "source_policy_state": policy.get("state"),
        "source_policy_enforcement_state": policy.get("enforcement_state"),
        "architecture": "aarch64",
        "audit_arch": {
            "name": "AUDIT_ARCH_AARCH64",
            "value": AUDIT_ARCH_AARCH64,
        },
        "default_action": "ERRNO(EPERM)",
        "loaded": False,
        "enforced": False,
        "artifact_paths": {
            "c_source": rel(c_path),
            "object": rel(object_path),
        },
        "artifact_sha256": {
            "c_source": sha256_file(c_path),
            "object": sha256_file(object_path),
        },
        "object_file": file_output,
        "services": [
            {
                "service": item["service"],
                "profile_name": item["profile_name"],
                "allowlist_count": item["allowlist_count"],
                "resolved_count": item["resolved_count"],
                "instruction_count": filter_instruction_count(item["resolved_count"]),
                "missing_syscalls": item["missing"],
                "syscalls": item["syscalls"],
            }
            for item in resolved_services
        ],
        "service_count": len(resolved_services),
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, bool]:
    services_payload = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    return {
        "schema_ok": manifest.get("schema") == "a90-wsta156-seccomp-nonloaded-filter-artifact-v1",
        "state_compiled_not_loaded": manifest.get("state") == "SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED",
        "source_policy_is_wsta153": manifest.get("source_policy_schema") == "a90-wsta153-seccomp-policy-source-v1",
        "source_policy_not_enforced": manifest.get("source_policy_enforcement_state") == "SOURCE_ONLY_NOT_ENFORCED",
        "aarch64_arch": manifest.get("architecture") == "aarch64",
        "audit_arch_aarch64": manifest.get("audit_arch", {}).get("value") == AUDIT_ARCH_AARCH64,
        "object_is_aarch64_relocatable": "ELF 64-bit LSB relocatable, ARM aarch64" in str(manifest.get("object_file")),
        "service_count_four": len(services_payload) == 4,
        "all_syscalls_resolved": all(
            isinstance(item, dict) and item.get("missing_syscalls") == []
            for item in services_payload
        ),
        "all_instruction_counts_match": all(
            isinstance(item, dict)
            and item.get("instruction_count") == filter_instruction_count(int(item.get("resolved_count") or 0))
            for item in services_payload
        ),
        "loaded_false": manifest.get("loaded") is False,
        "enforced_false": manifest.get("enforced") is False,
        "redaction_clean": not bool(wsta154.wsta153.wsta108.redaction_findings(manifest)),
    }


def compile_object(gcc: str, c_path: Path, object_path: Path) -> dict[str, Any]:
    command = [
        gcc,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-c",
        str(c_path),
        "-o",
        str(object_path),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
        timeout=30.0,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", errors="replace"),
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
        "ok": completed.returncode == 0 and object_path.is_file(),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta156-seccomp-nonloaded-filter-artifact-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    policy_path = resolve_path(args.wsta153_seccomp_policy_json)
    gcc_path = shutil.which(args.aarch64_gcc)
    result: dict[str, Any] = {
        "scope": "WSTA156 host-only non-loaded seccomp filter artifact",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_seccomp_nonloaded_filter_artifact),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "policy_json_private": is_under(policy_path, PRIVATE_ROOT),
            "policy_json_present": policy_path.is_file(),
            "aarch64_gcc_present": bool(gcc_path),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta156-blocked-explicit-gate-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta156-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["policy_json_private"]:
        result["decision"] = "wsta156-blocked-policy-json-nonprivate"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["policy_json_present"]:
        result["decision"] = "wsta156-blocked-policy-json-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result
    if not result["checks"]["aarch64_gcc_present"]:
        result["decision"] = "wsta156-blocked-aarch64-gcc-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    policy = load_json(policy_path)
    policy_checks = wsta154.validate_policy_source(policy)
    result["policy_checks"] = policy_checks
    result["checks"].update({f"policy_{key}": value for key, value in policy_checks.items()})
    if not all(policy_checks.values()):
        result["decision"] = "wsta156-blocked-policy-not-ready-for-filter-artifact"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    table = syscall_table(args.aarch64_gcc)
    resolved = [resolve_service_syscalls(item, table) for item in services(policy)]
    syscall_checks = {
        "all_services_have_allowlists": all(item["allowlist_count"] > 0 for item in resolved),
        "all_syscalls_resolved": all(item["missing"] == [] for item in resolved),
        "service_count_four": len(resolved) == 4,
    }
    result["syscall_checks"] = syscall_checks
    result["checks"].update({f"syscall_{key}": value for key, value in syscall_checks.items()})
    if not all(syscall_checks.values()):
        result["decision"] = "wsta156-blocked-syscall-resolution-failed"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    run_dir.mkdir(parents=True, exist_ok=True)
    c_path = run_dir / C_SOURCE_NAME
    object_path = run_dir / OBJECT_NAME
    c_path.write_text(emit_c_source(policy, resolved), encoding="utf-8")
    compile_result = compile_object(args.aarch64_gcc, c_path, object_path)
    result["compile"] = compile_result
    result["checks"]["compile_object_ok"] = bool(compile_result["ok"])
    if not compile_result["ok"]:
        result["decision"] = "wsta156-blocked-compile-failed"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    file_output = subprocess.check_output(["file", str(object_path)], text=True).strip()
    manifest = build_manifest(policy_path, policy, resolved, c_path, object_path, file_output=file_output)
    manifest_checks = validate_manifest(manifest)
    result["artifact"] = {
        "manifest": rel(run_dir / MANIFEST_NAME),
        "c_source": rel(c_path),
        "object": rel(object_path),
        "service_count": manifest.get("service_count"),
        "loaded": manifest.get("loaded"),
        "enforced": manifest.get("enforced"),
        "object_file": manifest.get("object_file"),
    }
    result["manifest_checks"] = manifest_checks
    result["checks"].update({f"manifest_{key}": value for key, value in manifest_checks.items()})
    result["decision"] = PASS_DECISION if all(manifest_checks.values()) else "wsta156-blocked-manifest-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(run_dir / MANIFEST_NAME, manifest)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--aarch64-gcc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--emit-seccomp-nonloaded-filter-artifact", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta156-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
