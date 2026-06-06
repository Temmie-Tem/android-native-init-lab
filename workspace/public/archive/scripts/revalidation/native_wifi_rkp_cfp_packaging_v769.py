#!/usr/bin/env python3
"""V769 bounded RKP_CFP Python3 packaging repair gate.

V767 proved that the ICNSS/QCACLD instrumentation compiles to target objects,
then isolated final Image packaging at Samsung's RKP_CFP post-link Python2
script. V769 applies a minimal Python3 compatibility repair to the disposable
V766 source tree and reruns the bounded kernel packaging path. It does not write
a boot image, flash, reboot, contact the device, start daemons, scan/connect
Wi-Fi, use credentials, DHCP, routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_icnss_qcacld_full_build_v767 as v767
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v769-rkp-cfp-python3-packaging")
LATEST_POINTER = Path("tmp/wifi/latest-v769-rkp-cfp-python3-packaging.txt")
DEFAULT_SOURCE_ROOT = v767.DEFAULT_SOURCE_ROOT
DEFAULT_V766_MANIFEST = v767.DEFAULT_V766_MANIFEST
DEFAULT_V767_MANIFEST = Path("tmp/wifi/v767-icnss-qcacld-full-build/manifest.json")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v766-manifest", type=Path, default=DEFAULT_V766_MANIFEST)
    parser.add_argument("--v767-manifest", type=Path, default=DEFAULT_V767_MANIFEST)
    parser.add_argument("--llvm-dir", type=Path, default=v767.DEFAULT_LLVM_DIR)
    parser.add_argument("--gcc-dir", type=Path, default=v767.DEFAULT_GCC_DIR)
    parser.add_argument("--compat-lib-dir", type=Path, default=v767.DEFAULT_COMPAT_LIB_DIR)
    parser.add_argument("--make-bin", type=Path, default=v767.DEFAULT_MAKE_BIN)
    parser.add_argument("--openssl-sysroot", type=Path, default=v767.DEFAULT_OPENSSL_SYSROOT)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--build-timeout", type=float, default=1800.0)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = v767.resolve_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def replace_all(text: str, pairs: list[tuple[str, str]]) -> tuple[str, list[str]]:
    changed: list[str] = []
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
            changed.append(old.split("\n", 1)[0][:80])
    return text, changed


def patch_file(path: Path, pairs: list[tuple[str, str]], required: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "changed": False,
        "replacements": [],
        "required_present": {},
        "complete": False,
    }
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    text, replacements = replace_all(text, pairs)
    if text != original:
        path.write_text(text, encoding="utf-8")
    result["changed"] = text != original
    result["replacements"] = replacements
    result["required_present"] = {needle: needle in text for needle in required}
    result["complete"] = all(result["required_present"].values())
    return result


def patch_rkp_cfp_python3(source_root: Path) -> dict[str, Any]:
    rkp_dir = source_root / "scripts/rkp_cfp"
    instrument = rkp_dir / "instrument.py"
    common = rkp_dir / "common.py"
    debug = rkp_dir / "debug.py"
    instrument_pairs = [
        ("import pipes", "import shlex"),
        (
            "import multiprocessing\nimport math\n",
            "import multiprocessing\ntry:\n    multiprocessing.set_start_method(\"fork\", force=True)\nexcept RuntimeError:\n    pass\nimport math\n",
        ),
        ("pipes.quote(", "shlex.quote("),
        ("xrange(", "range("),
        (".iteritems()", ".items()"),
        ("it.next()", "next(it)"),
        ("iter(i_set).next()", "next(iter(i_set))"),
        (
            "subprocess.Popen([\"{NM} {vmlinux} | sort\".format(NM=NM, vmlinux=vmlinux)], shell=True, stdout=subprocess.PIPE)",
            "subprocess.Popen([\"{NM} {vmlinux} | sort\".format(NM=NM, vmlinux=vmlinux)], shell=True, stdout=subprocess.PIPE, universal_newlines=True)",
        ),
        (
            "subprocess.Popen([OBJDUMP, '--section-headers', vmlinux], stdout=subprocess.PIPE)",
            "subprocess.Popen([OBJDUMP, '--section-headers', vmlinux], stdout=subprocess.PIPE, universal_newlines=True)",
        ),
        (
            'print "in function common.run_from_ipython()"',
            'print("in function common.run_from_ipython()")',
        ),
    ]
    common_pairs = [
        ("xrange(", "range("),
        (".iteritems()", ".items()"),
        ("it.next()", "next(it)"),
        ("iter(i_set).next()", "next(iter(i_set))"),
        (
            'print "in function common.run_from_ipython()"',
            'print("in function common.run_from_ipython()")',
        ),
    ]
    debug_pairs = [
        ("import pipes", "import shlex"),
        ("pipes.quote(", "shlex.quote("),
        ("xrange(", "range("),
        (".iteritems()", ".items()"),
        ("it.next()", "next(it)"),
        ("iter(i_set).next()", "next(iter(i_set))"),
        (
            "subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)",
            "subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, universal_newlines=True)",
        ),
    ]
    files = {
        "instrument.py": patch_file(
            instrument,
            instrument_pairs,
            [
                "import shlex",
                'multiprocessing.set_start_method("fork", force=True)',
                "universal_newlines=True",
            ],
        ),
        "common.py": patch_file(common, common_pairs, []),
        "debug.py": patch_file(debug, debug_pairs, ["universal_newlines=True"]),
    }
    return {
        "rkp_dir": str(rkp_dir),
        "files": files,
        "all_files_exist": all(item["exists"] for item in files.values()),
        "all_required_present": all(item["complete"] for item in files.values()),
        "changed_files": [name for name, item in files.items() if item["changed"]],
        "scope": "tmp/wifi disposable source tree only",
    }


def extract_rkp_failure(output_file: str) -> dict[str, Any]:
    path = Path(output_file) if output_file else Path()
    result: dict[str, Any] = {
        "output_file": output_file,
        "first_error": "",
        "errors": [],
        "traceback": [],
    }
    if not output_file or not path.exists():
        return result
    patterns = (
        "Traceback",
        "TypeError",
        "AttributeError",
        "PicklingError",
        "SyntaxError",
        "NameError",
        "ModuleNotFoundError",
        "RKP_CFP",
        "make[",
        "Error ",
        "오류",
    )
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    errors: list[str] = []
    traceback: list[str] = []
    in_traceback = False
    for line in lines:
        stripped = line.strip()
        if "Traceback" in stripped:
            in_traceback = True
        if in_traceback and len(traceback) < 80:
            traceback.append(stripped)
        if in_traceback and stripped.startswith(("TypeError:", "AttributeError:", "SyntaxError:", "NameError:", "ModuleNotFoundError:", "_pickle.")):
            in_traceback = False
        if any(pattern in stripped for pattern in patterns):
            errors.append(stripped)
            if len(errors) >= 40:
                break
    result["errors"] = errors
    result["first_error"] = next((line for line in errors if "Traceback" not in line and "RKP_CFP" not in line), errors[0] if errors else "")
    result["traceback"] = traceback
    return result


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source_root = v767.resolve_path(args.source_root)
    v766_manifest = load_json(args.v766_manifest)
    v767_manifest = load_json(args.v767_manifest)
    analysis: dict[str, Any] = {
        "inputs": {
            "v766": {
                "path": v766_manifest.get("path"),
                "exists": v766_manifest.get("exists", False),
                "decision": v766_manifest.get("decision", ""),
                "pass": bool(v766_manifest.get("pass")),
            },
            "v767": {
                "path": v767_manifest.get("path"),
                "exists": v767_manifest.get("exists", False),
                "decision": v767_manifest.get("decision", ""),
                "pass": bool(v767_manifest.get("pass")),
            },
        },
        "paths": {
            "source_root": v767.file_info(args.source_root),
            "make_bin": v767.file_info(args.make_bin),
            "llvm_dir": v767.file_info(args.llvm_dir),
            "gcc_dir": v767.file_info(args.gcc_dir),
        },
        "rkp_python3_repair": {},
        "v767_build": {},
        "rkp_failure": {},
        "kernel_build_executed": False,
        "boot_image_write_executed": False,
        "device_commands_executed": False,
    }
    if args.command == "plan":
        return analysis
    repair = patch_rkp_cfp_python3(source_root)
    logs = store.run_dir / "logs"
    logs.mkdir(parents=True, mode=0o700, exist_ok=True)
    py_compile = v767.run_command(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(source_root / "scripts/rkp_cfp/instrument.py"),
            str(source_root / "scripts/rkp_cfp/common.py"),
            str(source_root / "scripts/rkp_cfp/debug.py"),
        ],
        source_root,
        60.0,
        logs / "rkp-cfp-py-compile.txt",
    )
    repair["py_compile"] = py_compile
    build = v767.build_analysis(args, store)
    output_file = str((build.get("build") or {}).get("output_file", ""))
    analysis.update({
        "rkp_python3_repair": repair,
        "v767_build": build,
        "rkp_failure": extract_rkp_failure(output_file),
        "kernel_build_executed": bool(build.get("kernel_build_executed")),
        "artifacts": build.get("artifacts") or {},
        "instrumented_objects": build.get("instrumented_objects") or {},
        "build": build.get("build") or {},
    })
    return analysis


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    v766_input = analysis["inputs"]["v766"]
    v767_input = analysis["inputs"]["v767"]
    repair = analysis.get("rkp_python3_repair") or {}
    build = analysis.get("build") or {}
    artifacts = analysis.get("artifacts") or {}
    objects = analysis.get("instrumented_objects") or {}
    add_check(
        checks,
        "v766-input",
        "pass" if v766_input.get("exists") and v766_input.get("pass") else "blocked",
        "blocker",
        f"decision={v766_input.get('decision')} pass={v766_input.get('pass')}",
        "rerun V766 patch apply/defconfig gate before V769",
    )
    add_check(
        checks,
        "v767-input",
        "pass" if v767_input.get("exists") and v767_input.get("pass") else "warn",
        "warn",
        f"decision={v767_input.get('decision')} pass={v767_input.get('pass')}",
        "V769 can repair from V766 source, but V767 evidence should remain available",
    )
    add_check(
        checks,
        "source-root",
        "pass" if analysis["paths"]["source_root"].get("exists") and analysis["paths"]["source_root"].get("is_dir") else "blocked",
        "blocker",
        f"path={analysis['paths']['source_root'].get('path')} exists={analysis['paths']['source_root'].get('exists')}",
        "restore V766 disposable source tree",
    )
    if manifest["command"] == "plan":
        return checks
    add_check(
        checks,
        "rkp-python3-repair",
        "pass" if repair.get("all_files_exist") and repair.get("all_required_present") else "blocked",
        "blocker",
        f"changed={repair.get('changed_files')} required={repair.get('all_required_present')}",
        "fix RKP_CFP Python3 compatibility patcher",
    )
    add_check(
        checks,
        "rkp-py-compile",
        "pass" if (repair.get("py_compile") or {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={(repair.get('py_compile') or {}).get('rc')} timeout={(repair.get('py_compile') or {}).get('timeout')}",
        "repair remaining RKP_CFP syntax/import errors",
    )
    add_check(
        checks,
        "instrumented-objects",
        "pass" if objects.get("all_exist") and objects.get("marker_total") == 19 else "blocked",
        "blocker",
        f"all_exist={objects.get('all_exist')} markers={objects.get('marker_total')}",
        "rerun V767/V769 build until ICNSS/QCACLD markers survive",
    )
    add_check(
        checks,
        "kernel-image",
        "pass" if build.get("rc") == 0 and artifacts.get("image_exists") else "warn",
        "warn",
        f"rc={build.get('rc')} timeout={build.get('timeout')} image={artifacts.get('image_exists')}",
        "inspect RKP/post-link failure before packaging a diagnostic boot image",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v769-rkp-cfp-python3-packaging-plan-ready",
            True,
            "plan-only; no source mutation, build, boot-image write, device command, or Wi-Fi action executed",
            "run V769 bounded RKP_CFP Python3 packaging repair gate",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v769-rkp-cfp-python3-packaging-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blocker before rerunning packaging",
        )
    build = analysis.get("build") or {}
    artifacts = analysis.get("artifacts") or {}
    if build.get("rc") == 0 and artifacts.get("image_exists"):
        return (
            "v769-rkp-cfp-python3-repair-image-pass",
            True,
            "RKP_CFP Python3 repair completed and final Image exists in disposable source tree",
            "document image-readiness; next gate should package a diagnostic boot image without live flash until separately approved",
        )
    failure = analysis.get("rkp_failure") or {}
    return (
        "v769-rkp-cfp-python3-repair-postlink-blocked",
        True,
        f"RKP_CFP Python3 repair applied but final Image still blocked: {failure.get('first_error', '')}",
        "classify the remaining post-link failure before any diagnostic image packaging",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    repair = analysis.get("rkp_python3_repair") or {}
    artifacts = analysis.get("artifacts") or {}
    objects = analysis.get("instrumented_objects") or {}
    checks = manifest.get("checks") or []
    return "\n".join([
        "# V769 RKP_CFP Python3 Packaging Repair",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- kernel_build_executed: `{manifest['kernel_build_executed']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- none",
        "",
        "## RKP_CFP Repair",
        "",
        markdown_table(["file", "exists", "changed", "complete"], [
            [name, item.get("exists"), item.get("changed"), item.get("complete")]
            for name, item in (repair.get("files") or {}).items()
        ]) if repair else "- not run",
        "",
        "## Artifacts",
        "",
        markdown_table(["artifact", "exists", "size"], [
            [name, value.get("exists"), value.get("size")]
            for name, value in artifacts.items()
            if isinstance(value, dict)
        ]) if artifacts else "- not run",
        "",
        "## Instrumented Objects",
        "",
        markdown_table(["relative_path", "exists", "markers"], [
            [item.get("relative_path"), item.get("exists"), item.get("a90v765_marker_count")]
            for item in objects.get("objects", [])
        ]) if objects else "- not run",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v769",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "kernel_build_executed": bool(analysis.get("kernel_build_executed")),
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "device_commands_executed": False,
        "device_mutations": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"kernel_build_executed: {manifest['kernel_build_executed']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
