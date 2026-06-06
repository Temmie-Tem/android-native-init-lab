#!/usr/bin/env python3
"""CNSS start-only runner planner and guarded live launcher.

Default modes are non-starting. The live `run` mode intentionally fails closed
unless all explicit dangerous flags are supplied.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture
from a90harness.evidence import EvidenceStore
from wifi_cnss_zombie_audit import parse_ps_stat_comm, summarize_cnss_processes

DEFAULT_OUT_DIR = Path("tmp/wifi/v247-cnss-start-only-runner")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b"
DEFAULT_HELPER_TIMEOUT_SEC = 10

REQUIRED_MANIFESTS = {
    "v223": (Path("tmp/wifi/v223-recovery-rollback-policy/manifest.json"), "reboot-recovery-accepted"),
    "v225": (Path("tmp/wifi/v225-exposure-security-gate-v3/manifest.json"), "cnss-start-plan-approved"),
    "v241": (Path("tmp/wifi/v241-vndk-apex-alias-live-final/manifest.json"), "android-linker-vndk-apex-alias-cnss-list-pass"),
    "v242": (Path("tmp/wifi/v242-cnss-runtime-inventory-live2/manifest.json"), "cnss-runtime-inventory-ready-for-launcher-contract-plan"),
    "v243": (Path("tmp/wifi/v243-cnss-launcher-contract-plan/manifest.json"), "cnss-launcher-contract-ready"),
    "v244": (Path("tmp/wifi/v244-cnss-identity-probe-live4/manifest.json"), "cnss-identity-probe-pass"),
}

READ_ONLY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("version",),
    ("status",),
    ("bootstatus",),
    ("selftest", "verbose"),
    ("wifiinv", "full"),
    ("kernelinv", "summary"),
    ("netservice", "status"),
    ("mountsystem", "ro"),
    ("cat", "/proc/net/dev"),
    ("cat", "/sys/module/firmware_class/parameters/path"),
    ("stat", "/cache/bin/a90_android_execns_probe"),
    ("run", "/cache/bin/toybox", "sha256sum", "/cache/bin/a90_android_execns_probe"),
    ("stat", "/mnt/system/system/bin/linker64"),
    ("stat", "/mnt/system/system/bin/toybox"),
    ("stat", "/sys/class/block/sda29/dev"),
    ("stat", "/sys/devices/platform/soc/18800000.qcom,icnss"),
    ("run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm"),
    ("ls", "/sys/class/net"),
    ("ls", "/sys/class/rfkill"),
)

REQUIRED_PREFLIGHT = {
    "version",
    "status",
    "bootstatus",
    "selftest-verbose",
    "wifiinv-full",
    "kernelinv-summary",
    "netservice-status",
    "mountsystem-ro",
    "stat-cache-bin-a90-android-execns-probe",
    "run-cache-bin-toybox-sha256sum-cache-bin-a90_android_execns_probe",
    "stat-mnt-system-system-bin-linker64",
    "stat-mnt-system-system-bin-toybox",
    "stat-sys-class-block-sda29-dev",
    "stat-sys-devices-platform-soc-18800000-qcom-icnss",
    "run-cache-bin-toybox-ps-A-o-pid-stat-comm",
}

DENIED_TEXT_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

CNSS_START_RE = re.compile(r"^cnss_start\.([A-Za-z0-9_]+)=(.*)$")
CNSS_PROCESS_COMMAND = ("run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(command: tuple[str, ...]) -> str:
    text = "-".join(command)
    text = re.sub(r"[^A-Za-z0-9_.+-]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "command"


def load_manifest(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"missing": True, "path": str(full), "decision": "missing", "pass": False}
    data = json.loads(full.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full)
    return data


def build_prerequisite_checks() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    manifests: dict[str, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for key, (path, expected) in REQUIRED_MANIFESTS.items():
        manifest = load_manifest(path)
        manifests[key] = manifest
        actual = str(manifest.get("decision", "unknown"))
        ok = bool(manifest.get("pass")) and actual == expected and not manifest.get("missing")
        checks.append(
            {
                "name": key,
                "manifest": manifest.get("_manifest_path", manifest.get("path", "")),
                "expected_decision": expected,
                "actual_decision": actual,
                "pass": ok,
                "reason": manifest.get("reason", ""),
            }
        )
    return manifests, checks


def helper_start_argv(args: argparse.Namespace) -> list[str]:
    argv = [
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "cnss-start-only",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--data-wifi-mode",
        "private-empty",
        "--timeout-sec",
        str(args.max_runtime_sec),
    ]
    if args.command == "run" and args.allow_daemon_start and args.assume_yes and args.i_understand_reboot_only_recovery:
        argv.append("--allow-cnss-start-only")
    return argv


def build_dry_run_plan(args: argparse.Namespace) -> dict[str, Any]:
    argv = helper_start_argv(args)
    joined = " ".join(argv)
    denied_matches = [pattern.pattern for pattern in DENIED_TEXT_PATTERNS if pattern.search(joined)]
    return {
        "mode": "v247-cnss-start-only",
        "daemon_start_executed": False,
        "helper": args.helper,
        "helper_expected_sha256": args.helper_sha256,
        "helper_argv": argv,
        "runtime_materialization": {
            "null_device_mode": "dev-null-selinux",
            "data_wifi_mode": "private-empty",
            "data_wifi_path": "/data/vendor/wifi",
            "data_wifi_sockets_path": "/data/vendor/wifi/sockets",
            "private_namespace_only": True,
        },
        "daemon": {
            "path_inside_namespace": "/vendor/bin/cnss-daemon",
            "argv": ["/vendor/bin/cnss-daemon", "-n", "-l"],
            "uid": 1000,
            "gid": 1000,
            "groups": [3003, 3005, 1010],
            "capability": "CAP_NET_ADMIN",
        },
        "limits": {
            "default_runtime_sec": DEFAULT_HELPER_TIMEOUT_SEC,
            "requested_runtime_sec": args.max_runtime_sec,
            "hard_max_runtime_sec": 30,
            "retry_loop": False,
            "cnss_diag": False,
        },
        "cleanup": [
            "SIGTERM process group",
            "bounded wait",
            "SIGKILL process group if needed",
            "reap child",
            "verify no cnss-daemon/cnss_diag remains",
            "capture postflight inventory",
        ],
        "guardrails": {
            "denied_pattern_matches": denied_matches,
            "scan_connect_linkup": False,
            "persistent_android_write": False,
            "icnss_bind_unbind": False,
            "auto_reboot": False,
        },
    }


def parse_cnss_start_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = CNSS_START_RE.match(line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def bool_key(keys: dict[str, str], name: str) -> bool:
    return keys.get(name) == "1"


def build_start_observation(capture: Any) -> dict[str, Any]:
    keys = parse_cnss_start_keys(capture.text)
    return {
        "capture": capture_to_manifest(capture),
        "cnss_start": keys,
        "has_begin": keys.get("begin") == "1",
        "has_end": keys.get("end") == "1",
        "helper_result": keys.get("result", "missing"),
        "helper_reason": keys.get("reason", ""),
        "exec_attempted": bool_key(keys, "exec_attempted"),
        "child_started": bool_key(keys, "child_started"),
        "postflight_safe": bool_key(keys, "postflight_safe"),
        "reaped": bool_key(keys, "reaped"),
        "timed_out": bool_key(keys, "timed_out"),
    }


def cnss_process_summary_from_text(text: str) -> dict[str, Any]:
    return summarize_cnss_processes(parse_ps_stat_comm(text))


def capture_preflight(store: EvidenceStore, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    required_failures: list[str] = []
    active_wifi_warnings: list[str] = []
    cnss_process_summary: dict[str, Any] | None = None
    helper_sha_ok = False
    for command in READ_ONLY_COMMANDS:
        name = safe_name(command)
        capture = run_capture(args, name, list(command), timeout=args.timeout)
        store.write_text(f"commands/{name}.txt", capture.text if capture.text else capture.error + "\n")
        data = capture_to_manifest(capture)
        records.append(data)
        if name in REQUIRED_PREFLIGHT and not capture.ok:
            required_failures.append(name)
        if name == "run-cache-bin-toybox-sha256sum-cache-bin-a90_android_execns_probe" and args.helper_sha256 in capture.text:
            helper_sha_ok = True
        if name == "cat-proc-net-dev" and re.search(r"^\s*wlan\S*:", capture.text, re.MULTILINE):
            active_wifi_warnings.append("wlan interface present in /proc/net/dev")
        if command == CNSS_PROCESS_COMMAND and capture.ok:
            cnss_process_summary = cnss_process_summary_from_text(capture.text)
            if cnss_process_summary["target_zombie_count"] > 0:
                required_failures.append("cnss-zombie-preflight")
            if cnss_process_summary["target_running_count"] > 0:
                required_failures.append("cnss-running-preflight")
    if not helper_sha_ok:
        required_failures.append("helper-sha256-match")
    summary = {
        "command_count": len(records),
        "ok_count": sum(1 for item in records if item.get("ok")),
        "required_failures": sorted(set(required_failures)),
        "helper_sha256_expected": args.helper_sha256,
        "helper_sha256_match": helper_sha_ok,
        "active_wifi_warnings": active_wifi_warnings,
        "cnss_process_summary": cnss_process_summary,
        "pass": not required_failures and not active_wifi_warnings,
    }
    return records, summary


def capture_postflight_processes(store: EvidenceStore,
                                 args: argparse.Namespace,
                                 start_observation: dict[str, Any]) -> dict[str, Any]:
    capture = run_capture(
        args,
        "post-cnss-processes",
        list(CNSS_PROCESS_COMMAND),
        timeout=args.timeout,
    )
    store.write_text("commands/post-cnss-processes.txt", capture.text if capture.text else capture.error + "\n")
    summary = cnss_process_summary_from_text(capture.text) if capture.ok else None
    result = {
        "capture": capture_to_manifest(capture),
        "process_summary": summary,
        "clean": bool(capture.ok and summary is not None and summary["clean"]),
    }
    if not result["clean"]:
        start_observation["postflight_safe"] = False
        start_observation["postflight_process_clean"] = False
        start_observation["postflight_process_reason"] = "cnss target process remains after helper cleanup"
    else:
        start_observation["postflight_process_clean"] = True
        start_observation["postflight_process_reason"] = "no cnss target process remains"
    return result


def decide(mode: str,
           prereq_checks: list[dict[str, Any]],
           dry_run_plan: dict[str, Any],
           preflight_summary: dict[str, Any] | None,
           start_observation: dict[str, Any] | None,
           args: argparse.Namespace) -> tuple[str, str, bool]:
    prereq_ok = all(item.get("pass") for item in prereq_checks)
    if not prereq_ok:
        return "start-only-blocked", "required prerequisite manifest is missing or mismatched", False
    if dry_run_plan["guardrails"]["denied_pattern_matches"]:
        return "manual-review-required", "dry-run argv matched denied command patterns", False
    if mode == "plan":
        return "dry-run-ready", "prerequisites are ready; no live device command executed", True
    if preflight_summary is None:
        return "dry-run-ready", "dry-run graph is ready; no live daemon execution performed", True
    if not preflight_summary.get("pass"):
        return "start-only-blocked", "read-only preflight failed before daemon execution", False
    if mode in {"preflight", "dry-run"}:
        return "preflight-ready", "read-only preflight and dry-run graph are ready; no daemon execution performed", True
    if not (args.allow_daemon_start and args.assume_yes and args.i_understand_reboot_only_recovery):
        return "start-only-blocked", "daemon start requires explicit dangerous flags", False
    if start_observation is None:
        return "manual-review-required", "approved run did not produce a start observation", False
    if not start_observation["capture"].get("ok"):
        return "manual-review-required", "helper run command failed before a trusted result was parsed", False
    if not (start_observation.get("has_begin") and start_observation.get("has_end")):
        return "manual-review-required", "helper output is missing cnss_start begin/end markers", False
    helper_result = start_observation.get("helper_result", "missing")
    postflight_safe = bool(start_observation.get("postflight_safe"))
    if helper_result == "start-only-pass":
        return helper_result, start_observation.get("helper_reason", "helper reported pass"), postflight_safe
    if helper_result == "start-only-runtime-gap":
        return helper_result, start_observation.get("helper_reason", "helper reported runtime gap"), postflight_safe
    if helper_result == "start-only-reboot-required":
        return helper_result, start_observation.get("helper_reason", "helper could not prove safe cleanup"), False
    if helper_result == "start-only-blocked":
        return helper_result, start_observation.get("helper_reason", "helper blocked start"), False
    return "manual-review-required", f"unrecognized helper result: {helper_result}", False


def render_summary(manifest: dict[str, Any]) -> str:
    prereq_rows = [
        [
            item["name"],
            "PASS" if item["pass"] else "FAIL",
            item["expected_decision"],
            item["actual_decision"],
        ]
        for item in manifest["prerequisite_checks"]
    ]
    lines = [
        "# CNSS Start-Only Runner\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Prerequisites\n\n",
        markdown_table(["input", "result", "expected", "actual"], prereq_rows),
        "\n\n## Dry-Run Plan\n\n",
        f"- helper: `{manifest['dry_run_plan']['helper']}`\n",
        f"- helper mode: `cnss-start-only`\n",
        f"- target: `/vendor/bin/cnss-daemon -n -l`\n",
        f"- denied pattern matches: `{len(manifest['dry_run_plan']['guardrails']['denied_pattern_matches'])}`\n",
        f"- requested runtime: `{manifest['dry_run_plan']['limits']['requested_runtime_sec']}s`\n\n",
    ]
    if manifest.get("preflight_summary") is not None:
        preflight = manifest["preflight_summary"]
        lines.extend(
            [
                "## Preflight\n\n",
                f"- pass: `{preflight['pass']}`\n",
                f"- ok commands: `{preflight['ok_count']}/{preflight['command_count']}`\n",
                f"- helper sha256 match: `{preflight['helper_sha256_match']}`\n",
                f"- required failures: `{preflight['required_failures']}`\n",
                f"- active Wi-Fi warnings: `{preflight['active_wifi_warnings']}`\n\n",
            ]
        )
        process_summary = preflight.get("cnss_process_summary")
        if process_summary is not None:
            lines.extend(
                [
                    "### CNSS Process Preflight\n\n",
                    f"- target_process_count: `{process_summary['target_process_count']}`\n",
                    f"- target_zombie_count: `{process_summary['target_zombie_count']}`\n",
                    f"- target_running_count: `{process_summary['target_running_count']}`\n\n",
                ]
            )
    if manifest.get("start_observation") is not None:
        observation = manifest["start_observation"]
        lines.extend(
            [
                "## Start Observation\n\n",
                f"- helper result: `{observation['helper_result']}`\n",
                f"- helper reason: `{observation['helper_reason']}`\n",
                f"- exec attempted: `{observation['exec_attempted']}`\n",
                f"- child started: `{observation['child_started']}`\n",
                f"- postflight safe: `{observation['postflight_safe']}`\n",
                f"- postflight process clean: `{observation.get('postflight_process_clean')}`\n",
                f"- reaped: `{observation['reaped']}`\n\n",
            ]
        )
    lines.extend(
        [
            "## Guardrails\n\n",
            "- `cnss-daemon` is not executed by plan/preflight/dry-run modes.\n",
            "- live `run` requires all explicit dangerous flags and helper-side allow flag.\n",
            "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.\n",
            "- `cnss_diag`, ICNSS bind/unbind, rfkill unblock, and persistent Android writes remain blocked.\n",
        ]
    )
    return "".join(lines)


def build_manifest(args: argparse.Namespace, mode: str) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifests, prereq_checks = build_prerequisite_checks()
    dry_run_plan = build_dry_run_plan(args)
    store.write_json("prerequisite-checks.json", {"checks": prereq_checks, "manifests": manifests})
    store.write_json("dry-run-plan.json", dry_run_plan)
    preflight_records: list[dict[str, Any]] = []
    preflight_summary: dict[str, Any] | None = None
    if mode in {"preflight", "dry-run", "run"}:
        preflight_records, preflight_summary = capture_preflight(store, args)
        store.write_json("preflight.json", {"summary": preflight_summary, "commands": preflight_records})
    start_observation: dict[str, Any] | None = None
    postflight_processes: dict[str, Any] | None = None
    approved_run = (
        mode == "run"
        and args.allow_daemon_start
        and args.assume_yes
        and args.i_understand_reboot_only_recovery
    )
    if (
        approved_run
        and all(item.get("pass") for item in prereq_checks)
        and preflight_summary is not None
        and preflight_summary.get("pass")
        and not dry_run_plan["guardrails"]["denied_pattern_matches"]
    ):
        helper_command = ["run", *helper_start_argv(args)]
        capture = run_capture(
            args,
            "cnss-start-only-run",
            helper_command,
            timeout=args.timeout + args.max_runtime_sec + 20.0,
        )
        store.write_text("commands/cnss-start-only-run.txt", capture.text if capture.text else capture.error + "\n")
        start_observation = build_start_observation(capture)
        postflight_processes = capture_postflight_processes(store, args, start_observation)
        store.write_json("start-observation.json", start_observation)
        store.write_json(
            "postflight.json",
            {
                "postflight_safe": start_observation["postflight_safe"],
                "helper_result": start_observation["helper_result"],
                "helper_reason": start_observation["helper_reason"],
                "processes": postflight_processes,
            },
        )
        store.write_json(
            "cleanup.json",
            {
                "reaped": start_observation["reaped"],
                "timed_out": start_observation["timed_out"],
                "postflight_safe": start_observation["postflight_safe"],
            },
        )
    decision, reason, pass_ok = decide(mode, prereq_checks, dry_run_plan, preflight_summary, start_observation, args)
    manifest = {
        "created": now_iso(),
        "mode": mode,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "daemon_start_executed": bool(start_observation and start_observation.get("exec_attempted")),
        "host_metadata": collect_host_metadata(),
        "prerequisite_checks": prereq_checks,
        "dry_run_plan": dry_run_plan,
        "preflight_summary": preflight_summary,
        "preflight_commands": preflight_records,
        "start_observation": start_observation,
        "postflight_processes": postflight_processes,
        "guardrails": [
            "no daemon execution in plan/preflight/dry-run modes",
            "run mode requires --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no cnss_diag",
            "no rfkill unblock or ICNSS bind/unbind",
            "private/no-follow host evidence output",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--max-runtime-sec", type=int, default=DEFAULT_HELPER_TIMEOUT_SEC)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preflight", "dry-run"):
        subparsers.add_parser(name)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--allow-daemon-start", action="store_true")
    run_parser.add_argument("--assume-yes", action="store_true")
    run_parser.add_argument("--i-understand-reboot-only-recovery", action="store_true")
    args = parser.parse_args()
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        raise SystemExit("--max-runtime-sec must be 1..30")
    if args.command != "run":
        args.allow_daemon_start = False
        args.assume_yes = False
        args.i_understand_reboot_only_recovery = False
    return args


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args, args.command)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
