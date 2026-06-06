#!/usr/bin/env python3
"""V775 host-only custom-kernel boot incompatibility postmortem classifier.

V774 proved that adding the stock DTB tail to the OSRC-built diagnostic kernel
did not make the image live-boot compatible. This classifier keeps the next
step host-only: compare the known-good v724 boot artifacts against the V773
stock-DTB-tail diagnostic artifacts and classify the remaining observability
route without flashing, rebooting, or touching the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, parse_kernel_config, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v775-boot-incompat-postmortem")
LATEST_POINTER = Path("tmp/wifi/latest-v775-boot-incompat-postmortem.txt")
DEFAULT_BASE_BOOT = Path("stage3/boot_linux_v724.img")
DEFAULT_BASE_KERNEL = Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel")
DEFAULT_DIAG_BOOT = Path("tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img")
DEFAULT_DIAG_KERNEL = Path("tmp/wifi/v773-stock-dtb-tail-repack/instrumented-image-with-stock-dtb-tail.bin")
DEFAULT_BASE_CONFIG = Path("tmp/wifi/v772-boot-incompat-classifier/logs/base-ikconfig.txt")
DEFAULT_DIAG_CONFIG = Path("tmp/wifi/v772-boot-incompat-classifier/logs/diag-ikconfig.txt")
DEFAULT_V774_REPORT = Path("docs/reports/NATIVE_INIT_V774_STOCK_DTB_TAIL_LIVE_BOOT_FAIL_2026-05-25.md")
DEFAULT_V755_MANIFEST = Path("tmp/wifi/v755-tracefs-mount-filter-proof/manifest.json")

FDT_MAGIC = b"\xd0\r\xfe\xed"
PATCH_MARKER = b"A90V765"
LINUX_VERSION_RE = re.compile(rb"Linux version [^\x00]+")
PRODUCTION_MARKERS = ("RKP", "CFP", "RTIC", "DEFEX", "KNOX", "PROCA", "FIVE")
OBSERVABILITY_CONFIGS = (
    "CONFIG_KPROBES",
    "CONFIG_DYNAMIC_DEBUG",
    "CONFIG_FTRACE",
    "CONFIG_FUNCTION_TRACER",
    "CONFIG_TRACEPOINTS",
    "CONFIG_BPF_SYSCALL",
    "CONFIG_BPF_EVENTS",
    "CONFIG_BPF",
)


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
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--base-kernel", type=Path, default=DEFAULT_BASE_KERNEL)
    parser.add_argument("--diag-boot", type=Path, default=DEFAULT_DIAG_BOOT)
    parser.add_argument("--diag-kernel", type=Path, default=DEFAULT_DIAG_KERNEL)
    parser.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--diag-config", type=Path, default=DEFAULT_DIAG_CONFIG)
    parser.add_argument("--v774-report", type=Path, default=DEFAULT_V774_REPORT)
    parser.add_argument("--v755-manifest", type=Path, default=DEFAULT_V755_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def find_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    index = data.find(needle)
    while index >= 0:
        offsets.append(index)
        index = data.find(needle, index + 1)
    return offsets


def linux_versions(data: bytes) -> list[str]:
    versions: list[str] = []
    for match in LINUX_VERSION_RE.finditer(data):
        text = match.group(0).decode("utf-8", errors="replace")
        if text not in versions:
            versions.append(text)
        if len(versions) >= 5:
            break
    return versions


def marker_counts(data: bytes) -> dict[str, int]:
    return {marker: data.count(marker.encode("ascii")) for marker in PRODUCTION_MARKERS}


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    try:
        loaded = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(resolved), "exists": True, "error": str(exc)}
    if isinstance(loaded, dict):
        loaded["path"] = str(resolved)
        loaded["exists"] = True
        return loaded
    return {"path": str(resolved), "exists": True, "error": "json-root-not-object"}


def load_config(path: Path) -> dict[str, str]:
    resolved = resolve(path)
    if not resolved.exists():
        return {}
    return parse_kernel_config(resolved.read_text(encoding="utf-8", errors="replace"))


def run_command(command: list[str], output_file: Path, timeout: float = 120.0) -> dict[str, Any]:
    started = now_iso()
    try:
        result = subprocess.run(
            [str(part) for part in command],
            cwd=repo_path(Path(".")),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {
            "command": [str(part) for part in command],
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
            "started_at": started,
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {
            "command": [str(part) for part in command],
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
            "started_at": started,
        }


def unpack_boot(boot: Path, out_dir: Path, output_file: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    return run_command(
        [
            sys.executable,
            repo_path("mkbootimg/unpack_bootimg.py"),
            "--boot_img",
            resolve(boot),
            "--out",
            out_dir,
            "--format=mkbootimg",
        ],
        output_file,
    )


def parse_mkboot_args(output_file: str) -> dict[str, str]:
    if not output_file:
        return {}
    path = Path(output_file)
    if not path.exists():
        return {}
    try:
        tokens = shlex.split(path.read_text(encoding="utf-8", errors="replace"))
    except ValueError:
        return {}
    parsed: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
            key = token.removeprefix("--")
            value = tokens[index + 1]
            if key in {"kernel", "ramdisk"}:
                value = "<artifact-path>"
            parsed[key] = value
            index += 2
        else:
            index += 1
    return parsed


def diff_dict(left: dict[str, str], right: dict[str, str]) -> dict[str, dict[str, str]]:
    keys = sorted(set(left) | set(right))
    return {
        key: {"base": left.get(key, ""), "diag": right.get(key, "")}
        for key in keys
        if left.get(key, "") != right.get(key, "")
    }


def config_surface(config: dict[str, str]) -> dict[str, str]:
    return {name: config.get(name, "unset") for name in OBSERVABILITY_CONFIGS}


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("logs")
    base_boot = resolve(args.base_boot)
    diag_boot = resolve(args.diag_boot)
    base_kernel = resolve(args.base_kernel)
    diag_kernel = resolve(args.diag_kernel)
    base_data = read_bytes(base_kernel)
    diag_data = read_bytes(diag_kernel)
    base_fdt_offsets = find_offsets(base_data, FDT_MAGIC)
    diag_fdt_offsets = find_offsets(diag_data, FDT_MAGIC)
    base_config = load_config(args.base_config)
    diag_config = load_config(args.diag_config)
    base_boot_unpack = unpack_boot(args.base_boot, store.run_dir / "base-unpack", logs / "unpack-base-boot.txt") if args.command == "run" else {}
    diag_boot_unpack = unpack_boot(args.diag_boot, store.run_dir / "diag-unpack", logs / "unpack-diag-boot.txt") if args.command == "run" else {}
    base_mkboot = parse_mkboot_args(base_boot_unpack.get("output_file", ""))
    diag_mkboot = parse_mkboot_args(diag_boot_unpack.get("output_file", ""))
    v755 = load_json(args.v755_manifest)

    base_first_fdt = base_fdt_offsets[0] if base_fdt_offsets else None
    diag_first_fdt = diag_fdt_offsets[0] if diag_fdt_offsets else None
    v755_proof = v755.get("analysis", {}).get("proof", {}) if isinstance(v755.get("analysis"), dict) else {}
    if not v755_proof:
        v755_proof = v755.get("proof", {}) if isinstance(v755.get("proof"), dict) else {}

    return {
        "paths": {
            "base_boot": file_info(base_boot),
            "base_kernel": file_info(base_kernel),
            "diag_boot": file_info(diag_boot),
            "diag_kernel": file_info(diag_kernel),
            "base_config": file_info(args.base_config),
            "diag_config": file_info(args.diag_config),
            "v774_report": file_info(args.v774_report),
            "v755_manifest": file_info(args.v755_manifest),
        },
        "hashes": {
            "base_boot_sha256": sha256(base_boot) if base_boot.exists() else "",
            "diag_boot_sha256": sha256(diag_boot) if diag_boot.exists() else "",
            "base_kernel_sha256": sha256(base_kernel) if base_kernel.exists() else "",
            "diag_kernel_sha256": sha256(diag_kernel) if diag_kernel.exists() else "",
        },
        "payload": {
            "base_kernel_size": len(base_data),
            "diag_kernel_size": len(diag_data),
            "kernel_size_delta_diag_minus_base": len(diag_data) - len(base_data) if base_data and diag_data else None,
            "base_fdt_count": len(base_fdt_offsets),
            "diag_fdt_count": len(diag_fdt_offsets),
            "base_fdt_offsets": base_fdt_offsets,
            "diag_fdt_offsets": diag_fdt_offsets,
            "base_first_fdt_offset": base_first_fdt,
            "diag_first_fdt_offset": diag_first_fdt,
            "pre_dtb_size_delta_diag_minus_base": (
                diag_first_fdt - base_first_fdt
                if diag_first_fdt is not None and base_first_fdt is not None
                else None
            ),
            "base_patch_marker_count": base_data.count(PATCH_MARKER),
            "diag_patch_marker_count": diag_data.count(PATCH_MARKER),
            "production_marker_counts": {
                "base": marker_counts(base_data),
                "diag": marker_counts(diag_data),
            },
        },
        "version_strings": {
            "base": linux_versions(base_data),
            "diag": linux_versions(diag_data),
            "match": linux_versions(base_data) == linux_versions(diag_data),
        },
        "boot_header": {
            "base_unpack": base_boot_unpack,
            "diag_unpack": diag_boot_unpack,
            "base_mkboot_args": base_mkboot,
            "diag_mkboot_args": diag_mkboot,
            "normalized_diff": diff_dict(base_mkboot, diag_mkboot),
            "normalized_match": not diff_dict(base_mkboot, diag_mkboot) and bool(base_mkboot) and bool(diag_mkboot),
        },
        "ikconfig": {
            "base_surface": config_surface(base_config),
            "diag_surface": config_surface(diag_config),
            "observability": classify_observability(base_config),
            "surface_match": config_surface(base_config) == config_surface(diag_config),
        },
        "previous_tracefs": {
            "v755_exists": bool(v755.get("exists")),
            "v755_decision": v755.get("decision", ""),
            "available_events_readable": v755_proof.get("available_events_readable"),
            "available_filter_functions_readable": v755_proof.get("available_filter_functions_readable"),
            "set_ftrace_filter_readable": v755_proof.get("set_ftrace_filter_readable"),
            "target_hits": v755_proof.get("target_hits", {}),
        },
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }


def classify_observability(config: dict[str, str]) -> dict[str, str]:
    return {
        "kprobes": "unavailable" if config.get("CONFIG_KPROBES", "n") in {"n", "unset"} else "available",
        "dynamic_debug": "unavailable" if config.get("CONFIG_DYNAMIC_DEBUG", "n") in {"n", "unset"} else "available",
        "function_tracer": "unavailable" if config.get("CONFIG_FUNCTION_TRACER", "n") in {"n", "unset"} else "available",
        "tracepoints": "candidate" if config.get("CONFIG_TRACEPOINTS") == "y" else "unavailable",
        "bpf_tracepoint": (
            "candidate-needs-live-proof"
            if config.get("CONFIG_TRACEPOINTS") == "y" and config.get("CONFIG_BPF_SYSCALL") == "y"
            else "unavailable"
        ),
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    paths = analysis["paths"]
    payload = analysis["payload"]
    checks: list[Check] = []
    add_check(
        checks,
        "v774-report",
        "pass" if paths["v774_report"].get("exists") else "blocked",
        "blocker",
        f"exists={paths['v774_report'].get('exists')}",
        "document V774 failure and rollback before postmortem classification",
    )
    add_check(
        checks,
        "required-artifacts",
        "pass"
        if all(paths[name].get("exists") for name in ("base_boot", "base_kernel", "diag_boot", "diag_kernel"))
        else "blocked",
        "blocker",
        " ".join(f"{name}={paths[name].get('exists')}" for name in ("base_boot", "base_kernel", "diag_boot", "diag_kernel")),
        "restore v724 and V773 artifacts before classifying",
    )
    add_check(
        checks,
        "dtb-tail-present",
        "pass" if payload.get("base_fdt_count", 0) > 0 and payload.get("diag_fdt_count", 0) > 0 else "blocked",
        "blocker",
        f"base={payload.get('base_fdt_count')} diag={payload.get('diag_fdt_count')}",
        "do not continue custom-kernel analysis until both payloads contain appended DTBs",
    )
    add_check(
        checks,
        "pre-dtb-size-parity",
        "pass" if payload.get("pre_dtb_size_delta_diag_minus_base") == 0 else "review",
        "warn",
        f"delta={payload.get('pre_dtb_size_delta_diag_minus_base')}",
        "treat non-zero pre-DTB size delta as a remaining boot-compatibility suspect",
    )
    add_check(
        checks,
        "kernel-version-provenance",
        "pass" if analysis["version_strings"].get("match") else "review",
        "warn",
        f"match={analysis['version_strings'].get('match')}",
        "treat toolchain/build-host/date/provenance delta as a remaining boot-compatibility suspect",
    )
    add_check(
        checks,
        "boot-header-parity",
        "pass" if analysis["boot_header"].get("normalized_match") else "review",
        "warn",
        f"normalized_diff_keys={sorted(analysis['boot_header'].get('normalized_diff', {}).keys())}",
        "inspect boot header differences before any future live handoff",
    )
    add_check(
        checks,
        "ikconfig-observability-surface",
        "pass" if analysis["ikconfig"].get("surface_match") else "review",
        "warn",
        f"surface_match={analysis['ikconfig'].get('surface_match')} base={analysis['ikconfig'].get('base_surface')}",
        "inspect config delta before selecting tracing or BPF observers",
    )
    add_check(
        checks,
        "custom-kernel-flash-route",
        "review",
        "warn",
        "V774 failed after DTB-tail repair",
        "pause OSRC custom-kernel flashing until a new host-only compatibility gate exists",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v775-boot-incompat-postmortem-plan-ready",
            True,
            "plan-only; no device command, flash, partition write, reboot, or Wi-Fi action executed",
            "run V775 host-only postmortem classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v775-boot-incompat-postmortem-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "restore required host artifacts before further classification",
        )
    return (
        "v775-non-dtb-custom-kernel-incompat-classified",
        True,
        "V773/V774 eliminated missing DTB tail as the sole cause; remaining suspects are custom kernel provenance, pre-DTB payload delta, and Samsung production metadata/transform differences",
        "keep custom-kernel flash paused; next use stock-kernel observability, starting with read-only tracepoint availability and optional BPF tracepoint feasibility",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    payload = analysis.get("payload") or {}
    observability = analysis.get("ikconfig", {}).get("observability", {})
    return "\n".join([
        "# V775 Boot Incompatibility Postmortem",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- partition_write_executed: `{manifest['partition_write_executed']}`",
        f"- flash_executed: `{manifest['flash_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Payload Delta",
        "",
        markdown_table(["signal", "value"], [
            ["base_kernel_size", payload.get("base_kernel_size")],
            ["diag_kernel_size", payload.get("diag_kernel_size")],
            ["kernel_size_delta_diag_minus_base", payload.get("kernel_size_delta_diag_minus_base")],
            ["base_fdt_offsets", payload.get("base_fdt_offsets")],
            ["diag_fdt_offsets", payload.get("diag_fdt_offsets")],
            ["pre_dtb_size_delta_diag_minus_base", payload.get("pre_dtb_size_delta_diag_minus_base")],
            ["diag_patch_marker_count", payload.get("diag_patch_marker_count")],
        ]),
        "",
        "## Observability",
        "",
        markdown_table(["surface", "classification"], [[key, value] for key, value in observability.items()]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = analyze(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v775",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"partition_write_executed: {manifest['partition_write_executed']}")
    print(f"flash_executed: {manifest['flash_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
