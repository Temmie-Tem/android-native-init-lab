#!/usr/bin/env python3
"""Run v234 Android linker crash-context comparison.

This wrapper keeps Wi-Fi daemon execution blocked.  It only runs the allowlisted
``a90_android_execns_probe`` helper in ``linker64 --list`` mode, inside the
helper's private mount namespace.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_android_exec_namespace_probe import parse_execns_helper_output


DEFAULT_OUT_DIR = Path("tmp/wifi/v234-linker-crash-context")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_REAL_LINKERCONFIG = "/cache/bin/a90_real_ld.config.txt"
DEFAULT_REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
DEFAULT_LOCAL_LINKERCONFIG = Path("tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__ld.config.txt")
DEFAULT_LOCAL_APEX_LIBRARIES = Path("tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__apex.libraries.config.txt")
SYSTEM_ROOT = "/mnt/system/system"
VENDOR_BLOCK = "/dev/block/sda29"
VENDOR_FSTYPE = "ext4"
LINKER = "/system/bin/linker64"
TARGET_PROFILES = ("system-toybox", "system-sh", "linker64-self", "cnss-daemon")
ENV_MODES = ("clean", "ld-debug-1", "ld-debug-2")


@dataclass
class MatrixResult:
    profile: str
    env_mode: str
    ok: bool
    decision: str
    reason: str
    child_exit_code: int
    child_signal: int
    timed_out: bool
    stdout_bytes: int
    stderr_bytes: int
    output_file: str
    command: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "capture"


def parse_int(value: Any, default: int = -1) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def helper_command(args: argparse.Namespace, profile: str, env_mode: str) -> list[str]:
    command = [
        "run",
        args.helper,
        "--system-root",
        SYSTEM_ROOT,
        "--vendor-block",
        VENDOR_BLOCK,
        "--vendor-fstype",
        VENDOR_FSTYPE,
        "--target-profile",
        profile,
        "--linker",
        LINKER,
        "--env-mode",
        env_mode,
        "--mode",
        "linker-list",
        "--linkerconfig-mode",
        args.linkerconfig_mode,
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]
    if args.linkerconfig_mode == "copy-real":
        command.extend(["--linkerconfig-source", args.linkerconfig_source])
        if args.apex_libraries_source:
            command.extend(["--apex-libraries-source", args.apex_libraries_source])
    return command


def capture_text(store: EvidenceStore, relative_path: str, text: str) -> str:
    path = store.write_text(relative_path, text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def device_capture(store: EvidenceStore, args: argparse.Namespace, name: str, command: list[str], timeout: float | None = None) -> dict[str, Any]:
    started = time.monotonic()
    capture = run_capture(args, name, command, timeout=timeout)
    duration = time.monotonic() - started
    text = capture.text if capture.text else f"{capture.error}\n"
    output_file = capture_text(store, f"commands/{safe_name(name)}.txt", text)
    return {
        **asdict(capture),
        "duration_sec": duration,
        "file": output_file,
    }


def classify_single(profile: str, env_mode: str, parsed: dict[str, Any]) -> tuple[bool, str, str]:
    fields = parsed.get("fields", {})
    child_signal = parse_int(fields.get("child_signal"), 0)
    child_exit = parse_int(fields.get("child_exit_code"))
    run_rc = parse_int(fields.get("probe_run_rc"))
    timed_out = fields.get("timed_out") == "1"
    helper_status = fields.get("helper_status", "missing")
    stdout_text = str(parsed.get("stdout", ""))
    stderr_text = str(parsed.get("stderr", ""))
    has_debug_text = bool(stdout_text.strip() or stderr_text.strip())

    if not parsed.get("has_end") or helper_status != "namespace-ready" or run_rc != 0:
        return False, "android-linker-crash-context-blocked", f"helper incomplete status={helper_status} run_rc={run_rc}"
    if timed_out:
        return False, "android-linker-crash-context-blocked", "linker --list timed out"
    if has_debug_text:
        return True, "android-linker-debug-output-ready", f"profile={profile} env={env_mode} produced linker output"
    if child_signal != 0:
        return True, "android-linker-profile-crashed", f"profile={profile} env={env_mode} signal={child_signal}"
    if child_exit == 0:
        return True, "android-linker-list-baseline-pass", f"profile={profile} env={env_mode} exited 0"
    return True, "android-linker-profile-nonzero", f"profile={profile} env={env_mode} exit={child_exit}"


def run_matrix(store: EvidenceStore, args: argparse.Namespace) -> list[MatrixResult]:
    results: list[MatrixResult] = []
    for env_mode in args.env_modes:
        for profile in args.target_profiles:
            command = helper_command(args, profile, env_mode)
            name = f"helper-{env_mode}-{profile}"
            capture = run_capture(args, name, command, timeout=args.helper_timeout_sec + 30)
            text = capture.text if capture.text else f"{capture.error}\n"
            output_file = capture_text(store, f"matrix/{safe_name(name)}.txt", text)
            parsed = parse_execns_helper_output(text)
            ok, decision, reason = classify_single(profile, env_mode, parsed)
            fields = parsed.get("fields", {})
            stdout_text = str(parsed.get("stdout", ""))
            stderr_text = str(parsed.get("stderr", ""))
            results.append(
                MatrixResult(
                    profile=profile,
                    env_mode=env_mode,
                    ok=ok,
                    decision=decision,
                    reason=reason,
                    child_exit_code=parse_int(fields.get("child_exit_code")),
                    child_signal=parse_int(fields.get("child_signal"), 0),
                    timed_out=fields.get("timed_out") == "1",
                    stdout_bytes=len(stdout_text.encode("utf-8")),
                    stderr_bytes=len(stderr_text.encode("utf-8")),
                    output_file=output_file,
                    command=command,
                )
            )
    store.write_json("matrix-results.json", {"results": [asdict(item) for item in results]})
    return results


def decide(results: list[MatrixResult]) -> tuple[str, str, bool]:
    if not results:
        return "android-linker-crash-context-blocked", "matrix produced no results", False
    if any(not item.ok and item.decision == "android-linker-crash-context-blocked" for item in results):
        return "android-linker-crash-context-blocked", "one or more helper runs were blocked", False
    if any(item.decision == "android-linker-debug-output-ready" for item in results):
        return "android-linker-debug-output-ready", "at least one debug/env run emitted linker output", True

    clean = [item for item in results if item.env_mode == "clean"]
    baseline = [item for item in clean if item.profile != "cnss-daemon"]
    cnss = [item for item in clean if item.profile == "cnss-daemon"]
    baseline_pass = any(item.child_signal == 0 and item.child_exit_code == 0 for item in baseline)
    cnss_crash = any(item.child_signal != 0 for item in cnss)
    all_clean_crash = bool(clean) and all(item.child_signal != 0 for item in clean)

    if baseline_pass and cnss_crash:
        return "android-linker-crash-target-specific", "baseline linker --list passed but cnss-daemon crashed", True
    if all_clean_crash:
        signals = sorted({item.child_signal for item in clean})
        return "android-linker-crash-generic", f"all clean target profiles crashed signals={signals}", True
    if baseline_pass:
        return "android-linker-list-baseline-pass", "at least one clean baseline target passed", True
    return "android-linker-crash-manual-review-required", "matrix completed but did not match target-specific or generic pattern", True


def build_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# v234 Linker Crash Context Probe",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- out_dir: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        "| env | profile | decision | signal | exit | stdout | stderr |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in manifest["matrix"]:
        lines.append(
            f"| `{item['env_mode']}` | `{item['profile']}` | `{item['decision']}` | "
            f"`{item['child_signal']}` | `{item['child_exit_code']}` | "
            f"`{item['stdout_bytes']}` | `{item['stderr_bytes']}` |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- no `cnss-daemon` entrypoint execution",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- no global bind mount or persistent Android partition write",
            "- helper is restricted to `linker64 --list` inside a private namespace",
            "",
        ]
    )
    return "\n".join(lines)


def split_csv(value: str) -> list[str]:
    items: list[str] = []
    for item in value.split(","):
        item = item.strip()
        if item:
            items.append(item)
    return items


def validate_profiles(values: list[str], allowed: tuple[str, ...], label: str) -> list[str]:
    invalid = [item for item in values if item not in allowed]
    if invalid:
        raise SystemExit(f"invalid {label}: {', '.join(invalid)}")
    return values


def run(args: argparse.Namespace) -> int:
    store = EvidenceStore(repo_path(args.out_dir))
    if args.subcommand == "plan":
        results: list[MatrixResult] = []
        bridge: dict[str, Any] | None = None
        helper_stat: dict[str, Any] | None = None
        linkerconfig_stat: dict[str, Any] | None = None
        apex_libraries_stat: dict[str, Any] | None = None
        postflight: dict[str, Any] = {}
        decision, reason, pass_ok = "android-linker-crash-context-plan-ready", "plan generated; no helper matrix executed", True
    else:
        bridge = device_capture(store, args, "bridge-version", ["version"], timeout=args.timeout)
        helper_stat = device_capture(store, args, "stat-helper", ["stat", args.helper], timeout=args.timeout)
        linkerconfig_stat = None
        apex_libraries_stat = None
        if args.linkerconfig_mode == "copy-real":
            linkerconfig_stat = device_capture(store, args, "stat-real-linkerconfig", ["stat", args.linkerconfig_source], timeout=args.timeout)
            if args.apex_libraries_source:
                apex_libraries_stat = device_capture(
                    store,
                    args,
                    "stat-real-apex-libraries",
                    ["stat", args.apex_libraries_source],
                    timeout=args.timeout,
                )

        if not bridge["ok"]:
            results = []
            decision, reason, pass_ok = "android-linker-crash-context-blocked", "bridge version check failed", False
        elif not helper_stat["ok"]:
            results = []
            decision, reason, pass_ok = "android-linker-crash-context-blocked", f"helper missing at {args.helper}", False
        elif args.linkerconfig_mode == "copy-real" and linkerconfig_stat is not None and not linkerconfig_stat["ok"]:
            results = []
            decision, reason, pass_ok = "android-linker-crash-context-blocked", f"real linkerconfig missing at {args.linkerconfig_source}", False
        elif args.linkerconfig_mode == "copy-real" and apex_libraries_stat is not None and not apex_libraries_stat["ok"]:
            results = []
            decision, reason, pass_ok = "android-linker-crash-context-blocked", f"real apex libraries config missing at {args.apex_libraries_source}", False
        else:
            results = run_matrix(store, args)
            decision, reason, pass_ok = decide(results)
        postflight = {
            "selftest": device_capture(store, args, "post-selftest", ["selftest", "verbose"], timeout=max(args.timeout, 20.0)),
            "mounts": device_capture(store, args, "post-mounts", ["cat", "/proc/mounts"], timeout=args.timeout),
        }

    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "expect_version": args.expect_version,
        "helper": args.helper,
        "linkerconfig_mode": args.linkerconfig_mode,
        "linkerconfig_source": args.linkerconfig_source,
        "apex_libraries_source": args.apex_libraries_source,
        "target_profiles": args.target_profiles,
        "env_modes": args.env_modes,
        "bridge": bridge,
        "helper_stat": helper_stat,
        "linkerconfig_stat": linkerconfig_stat,
        "apex_libraries_stat": apex_libraries_stat,
        "matrix": [asdict(item) for item in results],
        "postflight": postflight,
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"decision={decision} pass={pass_ok} out_dir={store.run_dir}")
    print(f"reason={reason}")
    return 0 if pass_ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / DEFAULT_OUT_DIR)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    parser.add_argument("--linkerconfig-mode", choices=("copy-real", "minimal-vendor", "none"), default="copy-real")
    parser.add_argument("--linkerconfig-source", default=DEFAULT_REAL_LINKERCONFIG)
    parser.add_argument("--apex-libraries-source", default=DEFAULT_REAL_APEX_LIBRARIES)
    parser.add_argument("--local-linkerconfig", type=Path, default=REPO_ROOT / DEFAULT_LOCAL_LINKERCONFIG)
    parser.add_argument("--local-apex-libraries", type=Path, default=REPO_ROOT / DEFAULT_LOCAL_APEX_LIBRARIES)
    parser.add_argument(
        "--target-profiles",
        default=",".join(TARGET_PROFILES),
        help="comma-separated allowlisted target profiles",
    )
    parser.add_argument(
        "--env-modes",
        default="clean,ld-debug-1",
        help="comma-separated env modes",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("probe")
    args = parser.parse_args()
    if not (1 <= args.helper_timeout_sec <= 30):
        parser.error("--helper-timeout-sec must be between 1 and 30")
    args.target_profiles = validate_profiles(split_csv(args.target_profiles), TARGET_PROFILES, "--target-profiles")
    args.env_modes = validate_profiles(split_csv(args.env_modes), ENV_MODES + ("auxv",), "--env-modes")
    if args.linkerconfig_mode == "copy-real" and not args.linkerconfig_source.startswith("/cache/"):
        parser.error("--linkerconfig-source must be an absolute /cache path")
    if args.linkerconfig_mode == "copy-real" and args.apex_libraries_source and not args.apex_libraries_source.startswith("/cache/"):
        parser.error("--apex-libraries-source must be an absolute /cache path")
    if args.linkerconfig_mode != "copy-real":
        args.apex_libraries_source = None
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
