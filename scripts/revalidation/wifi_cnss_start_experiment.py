#!/usr/bin/env python3
"""Run the v229 controlled CNSS start-only experiment harness.

The default modes are non-destructive. The `run` subcommand refuses to start the
CNSS daemon unless both --allow-daemon-start and --assume-yes are supplied.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path, run_capture
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_PLAN_DIR = Path("tmp/wifi/v228-controlled-cnss-start-plan")
DEFAULT_OUT_DIR = Path("tmp/wifi/v229-controlled-cnss-start-experiment")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
REQUIRED_DECISIONS = {
    "v221": "elf-evidence-ready",
    "v222": "vendor-root-ready",
    "v223": "reboot-recovery-accepted",
    "v224": "shim-dryrun-ready",
    "v225": "cnss-start-plan-approved",
    "v227": "system-root-ready",
    "v228": "cnss-start-plan-ready",
}
DEFAULT_MANIFESTS = {
    "v221": Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json"),
    "v222": Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json"),
    "v223": Path("tmp/wifi/v223-recovery-rollback-policy/manifest.json"),
    "v224": Path("tmp/wifi/v224-android-env-shim-materialize/manifest.json"),
    "v225": Path("tmp/wifi/v225-exposure-security-gate-v3/manifest.json"),
    "v227": Path("tmp/wifi/v227-android-core-system-library-evidence/manifest.json"),
}

CNSS_DAEMON_COMMAND = ["runandroid", "/system/bin/toybox", "timeout", "{seconds}", "/system/vendor/bin/cnss-daemon", "-n", "-l"]
DENIED_TEXT_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|hal_wifi|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bresetprop\b", re.IGNORECASE),
    re.compile(r"\bdriver_override\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
)

SAFE_STAT_PATHS = {
    "/mnt/system/vendor/bin/cnss-daemon",
    "/mnt/system/vendor/bin/cnss_diag",
    "/mnt/system/system/bin/linker64",
    "/mnt/system/system/bin/toybox",
    "/mnt/system/system/lib64/libc.so",
    "/system/bin/linker64",
    "/system/bin/toybox",
    "/system/vendor/bin/cnss-daemon",
    "/vendor/bin/cnss-daemon",
    "/sys/devices/platform/soc/18800000.qcom,icnss",
    "/sys/bus/platform/drivers/icnss",
}
SAFE_CAT_PATHS = {
    "/proc/mounts",
    "/proc/net/dev",
    "/sys/module/firmware_class/parameters/path",
    "/sys/devices/platform/soc/18800000.qcom,icnss/uevent",
}
SAFE_LS_PATHS = {
    "/sys/class/net",
    "/sys/class/rfkill",
    "/sys/class/ieee80211",
    "/mnt/system/vendor/bin",
    "/mnt/system/system/bin",
}
READ_ONLY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("version",),
    ("status",),
    ("bootstatus",),
    ("selftest", "verbose"),
    ("logpath",),
    ("netservice", "status"),
    ("longsoak", "status", "verbose"),
    ("wifiinv", "full"),
    ("kernelinv", "summary"),
    ("mounts",),
    ("mountsystem", "ro"),
    ("cat", "/proc/mounts"),
    ("cat", "/proc/net/dev"),
    ("cat", "/sys/module/firmware_class/parameters/path"),
    ("cat", "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"),
    ("ls", "/sys/class/net"),
    ("ls", "/sys/class/rfkill"),
    ("ls", "/sys/class/ieee80211"),
    ("stat", "/mnt/system/vendor/bin/cnss-daemon"),
    ("stat", "/mnt/system/vendor/bin/cnss_diag"),
    ("stat", "/mnt/system/system/bin/linker64"),
    ("stat", "/mnt/system/system/bin/toybox"),
    ("stat", "/mnt/system/system/lib64/libc.so"),
    ("stat", "/system/bin/linker64"),
    ("stat", "/system/bin/toybox"),
    ("stat", "/system/vendor/bin/cnss-daemon"),
    ("stat", "/vendor/bin/cnss-daemon"),
    ("stat", "/sys/devices/platform/soc/18800000.qcom,icnss"),
    ("stat", "/sys/bus/platform/drivers/icnss"),
)
REQUIRED_PREFLIGHT_COMMANDS = {
    "version",
    "status",
    "bootstatus",
    "mountsystem-ro",
    "stat-mnt-system-vendor-bin-cnss-daemon",
    "stat-mnt-system-system-bin-linker64",
}
RUNANDROID_REQUIRED_COMMANDS = {
    "stat-system-bin-linker64",
    "stat-system-bin-toybox",
    "stat-system-vendor-bin-cnss-daemon",
}


@dataclass
class CommandRecord:
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


def safe_name(value: str) -> str:
    replaced = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", replaced).strip("-") or "capture"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json_file(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def manifest_decision(data: dict[str, Any]) -> str:
    if data.get("missing"):
        return "missing"
    return str(data.get("decision", "unknown"))


def manifest_pass(data: dict[str, Any]) -> bool:
    return bool(data.get("pass")) and not data.get("missing")


def plan_path(plan_dir: Path, name: str) -> Path:
    return repo_path(plan_dir) / name


def load_inputs(args: argparse.Namespace) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    manifests = {key: load_json_file(path) for key, path in DEFAULT_MANIFESTS.items()}
    v228_manifest = load_json_file(plan_path(args.plan_dir, "manifest.json"))
    manifests["v228"] = v228_manifest
    plan = {
        "manifest": v228_manifest,
        "start_plan": load_json_file(plan_path(args.plan_dir, "start-plan.json")),
        "command_allowlist": load_json_file(plan_path(args.plan_dir, "command-allowlist.json")),
        "rollback_policy": load_json_file(plan_path(args.plan_dir, "rollback-policy.json")),
        "exposure_boundary": load_json_file(plan_path(args.plan_dir, "exposure-boundary.json")),
    }
    return manifests, plan


def validate_prerequisites(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for key, expected in REQUIRED_DECISIONS.items():
        manifest = manifests.get(key, {"missing": True})
        actual = manifest_decision(manifest)
        ok = manifest_pass(manifest) and actual == expected
        checks.append(
            {
                "name": key,
                "expected_decision": expected,
                "actual_decision": actual,
                "pass": ok,
                "manifest": manifest.get("_manifest_path", manifest.get("path", "")),
                "reason": manifest.get("reason", ""),
            }
        )
    return checks


def validate_v228_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    allowlist = plan.get("command_allowlist", {})
    manifest = plan.get("manifest", {})
    start_plan = plan.get("start_plan", {})
    rollback = plan.get("rollback_policy", {})
    exposure = plan.get("exposure_boundary", {})

    checks.append(
        {
            "name": "v228-decision",
            "pass": manifest_pass(manifest) and manifest_decision(manifest) == "cnss-start-plan-ready",
            "detail": manifest_decision(manifest),
        }
    )
    checks.append(
        {
            "name": "structured-allowlist-only",
            "pass": allowlist.get("mode") == "structured-allowlist-only",
            "detail": str(allowlist.get("mode", "")),
        }
    )
    checks.append(
        {
            "name": "planner-live-commands-empty",
            "pass": allowlist.get("planner_live_commands") == [],
            "detail": str(allowlist.get("planner_live_commands", "missing")),
        }
    )
    actions = {item.get("name"): item for item in allowlist.get("future_structured_actions", []) if isinstance(item, dict)}
    daemon = actions.get("spawn-cnss-daemon-start-only", {})
    checks.append(
        {
            "name": "daemon-action-approved-for-v229",
            "pass": daemon.get("allowed_in_v229_with_confirmation") is True
            and daemon.get("binary") == "/system/vendor/bin/cnss-daemon"
            and daemon.get("argv") == ["-n", "-l"],
            "detail": json.dumps(daemon, ensure_ascii=False, sort_keys=True),
        }
    )
    diag = actions.get("spawn-cnss-diag-diagnostic-only", {})
    checks.append(
        {
            "name": "cnss-diag-disabled",
            "pass": diag.get("allowed_in_v229_with_confirmation") is False,
            "detail": str(diag.get("allowed_in_v229_with_confirmation", "missing")),
        }
    )
    checks.append(
        {
            "name": "reboot-only-recovery",
            "pass": rollback.get("failure_policy") == "mark reboot-required; do not use generic ICNSS unbind/bind",
            "detail": str(rollback.get("failure_policy", "")),
        }
    )
    checks.append(
        {
            "name": "exposure-boundary-local",
            "pass": exposure.get("allowed_boundary") == "USB-local/host-local operator workflow only",
            "detail": str(exposure.get("allowed_boundary", "")),
        }
    )
    phase_names = [item.get("name") for item in start_plan.get("phases", []) if isinstance(item, dict)]
    checks.append(
        {
            "name": "start-plan-phases-present",
            "pass": all(name in phase_names for name in ["preflight", "stage-runtime", "start-cnss-daemon", "observe", "stop", "postflight"]),
            "detail": ",".join(str(name) for name in phase_names),
        }
    )
    return checks


def validate_command(command: Iterable[str], *, allow_daemon: bool = False) -> list[str]:
    argv = list(command)
    if not argv:
        return ["empty command"]
    joined = " ".join(argv)
    problems: list[str] = []
    for pattern in DENIED_TEXT_PATTERNS:
        if pattern.search(joined):
            if allow_daemon and "cnss-daemon" in joined and "runandroid /system/bin/toybox timeout" in joined:
                continue
            problems.append(f"denied pattern: {pattern.pattern}")
    name = argv[0]
    if name in {"version", "status", "bootstatus", "logpath", "mounts"}:
        if len(argv) != 1:
            problems.append("unexpected arity")
    elif name == "selftest":
        if argv != ["selftest", "verbose"]:
            problems.append("only selftest verbose allowed")
    elif name == "netservice":
        if argv != ["netservice", "status"]:
            problems.append("only netservice status allowed")
    elif name == "longsoak":
        if argv != ["longsoak", "status", "verbose"]:
            problems.append("only longsoak status verbose allowed")
    elif name == "wifiinv":
        if argv != ["wifiinv", "full"]:
            problems.append("only wifiinv full allowed")
    elif name == "kernelinv":
        if argv != ["kernelinv", "summary"]:
            problems.append("only kernelinv summary allowed")
    elif name == "mountsystem":
        if argv != ["mountsystem", "ro"]:
            problems.append("only mountsystem ro allowed")
    elif name == "stat":
        if len(argv) != 2 or argv[1] not in SAFE_STAT_PATHS:
            problems.append("stat path not allowlisted")
    elif name == "cat":
        if len(argv) != 2 or argv[1] not in SAFE_CAT_PATHS:
            problems.append("cat path not allowlisted")
    elif name == "ls":
        if len(argv) != 2 or argv[1] not in SAFE_LS_PATHS:
            problems.append("ls path not allowlisted")
    elif name == "runandroid" and allow_daemon:
        expected_prefix = ["runandroid", "/system/bin/toybox", "timeout"]
        if len(argv) != 7 or argv[:3] != expected_prefix or argv[4:] != ["/system/vendor/bin/cnss-daemon", "-n", "-l"]:
            problems.append("daemon run command does not match exact allowlist")
        else:
            try:
                seconds = int(argv[3])
                if seconds < 1 or seconds > 30:
                    problems.append("daemon timeout outside 1..30")
            except ValueError:
                problems.append("daemon timeout is not an integer")
    else:
        problems.append(f"command not allowlisted: {name}")
    return problems


def command_label(command: Iterable[str]) -> str:
    return safe_name("-".join(command))


def record_capture(store: EvidenceStore, capture: Any) -> CommandRecord:
    text = capture.text if capture.text else f"{capture.error}\n"
    rel_path = f"commands/{safe_name(capture.name)}.txt"
    path = store.write_text(rel_path, text.rstrip() + "\n")
    return CommandRecord(
        name=capture.name,
        command=capture.command.split(),
        ok=capture.ok,
        rc=capture.rc,
        status=capture.status,
        duration_sec=capture.duration_sec,
        file=str(path.relative_to(store.run_dir)),
        error=capture.error,
    )


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None,
                   allow_daemon: bool = False) -> CommandRecord:
    problems = validate_command(command, allow_daemon=allow_daemon)
    if problems:
        text = "command blocked by v229 guard:\n" + "\n".join(problems) + "\n"
        path = store.write_text(f"commands/{safe_name(name)}.txt", text)
        return CommandRecord(name, command, False, None, "blocked", 0.0, str(path.relative_to(store.run_dir)), "; ".join(problems))
    capture = run_capture(args, name, command, timeout=timeout)
    record = record_capture(store, capture)
    record.command = command
    return record


def run_exact_cmdv1(args: argparse.Namespace, command: list[str], timeout: float) -> ProtocolResult:
    return run_cmdv1_command(args.host, args.port, timeout, command, retry_unsafe=False)


def build_dry_run_plan(max_runtime_sec: int) -> dict[str, Any]:
    daemon_command = [part.format(seconds=str(max_runtime_sec)) for part in CNSS_DAEMON_COMMAND]
    return {
        "mode": "v229-controlled-cnss-start-only",
        "default_live_execution": False,
        "requires_flags": ["--allow-daemon-start", "--assume-yes"],
        "max_runtime_sec": max_runtime_sec,
        "execution_graph": [
            {"step": "validate-v221-v228-manifests", "live_device": False},
            {"step": "collect-preflight", "live_device": True, "commands": [list(item) for item in READ_ONLY_COMMANDS]},
            {"step": "exact-daemon-command", "live_device": True, "command": daemon_command},
            {"step": "postflight", "live_device": True, "commands": [list(item) for item in READ_ONLY_COMMANDS]},
        ],
        "forbidden": [
            "rfkill write",
            "wlan link up",
            "scan/connect",
            "credential access",
            "DHCP/routing/NAT/DNS",
            "ICNSS unbind/bind",
            "property mutation",
            "persistent Android partition writes",
            "cnss_diag phase2",
        ],
    }


def status_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "fail": 0}
    for check in checks:
        counts["pass" if check.get("pass") else "fail"] += 1
    return counts


def command_record_to_dict(record: CommandRecord) -> dict[str, Any]:
    return asdict(record)


def collect_preflight(store: EvidenceStore, args: argparse.Namespace) -> tuple[list[CommandRecord], dict[str, Any]]:
    records: list[CommandRecord] = []
    for command_tuple in READ_ONLY_COMMANDS:
        command = list(command_tuple)
        label = command_label(command)
        timeout = 35.0 if command[0] in {"wifiinv", "kernelinv", "selftest"} else args.timeout
        records.append(capture_device(store, args, label, command, timeout=timeout))
    by_name = {record.name: record for record in records}
    required_failures = [name for name in REQUIRED_PREFLIGHT_COMMANDS if name not in by_name or not by_name[name].ok]
    runandroid_missing = [name for name in RUNANDROID_REQUIRED_COMMANDS if name not in by_name or not by_name[name].ok]
    active_wifi_warnings: list[str] = []
    net_record = by_name.get("ls-sys-class-net")
    if net_record and net_record.ok:
        text = (store.run_dir / net_record.file).read_text(encoding="utf-8", errors="replace")
        for iface in ("wlan0", "swlan0", "p2p0", "wifi-aware0"):
            if iface in text:
                active_wifi_warnings.append(f"unexpected interface visible: {iface}")
    summary = {
        "command_count": len(records),
        "ok_count": sum(1 for record in records if record.ok),
        "required_failures": required_failures,
        "runandroid_required_missing": runandroid_missing,
        "active_wifi_warnings": active_wifi_warnings,
        "pass": not required_failures and not active_wifi_warnings,
        "runtime_gap": bool(runandroid_missing),
    }
    return records, summary


def run_daemon_start_only(store: EvidenceStore, args: argparse.Namespace) -> tuple[CommandRecord, dict[str, Any]]:
    command = [part.format(seconds=str(args.max_runtime_sec)) for part in CNSS_DAEMON_COMMAND]
    timeout = float(args.max_runtime_sec + 20)
    record = capture_device(store, args, "run-cnss-daemon-start-only", command, timeout=timeout, allow_daemon=True)
    accepted_nonzero = record.rc in {124, 125, 126, 127, 137, 143} or record.status in {"ok", "missing"}
    observation = {
        "command": command,
        "timeout_sec": args.max_runtime_sec,
        "record": command_record_to_dict(record),
        "accepted_nonzero": accepted_nonzero,
        "note": "foreground runandroid+toybox-timeout wrapper; postflight verifies no forbidden Wi-Fi state",
    }
    return record, observation


def decide(mode: str,
           prerequisite_checks: list[dict[str, Any]],
           plan_checks: list[dict[str, Any]],
           preflight_summary: dict[str, Any] | None,
           run_record: CommandRecord | None,
           postflight_summary: dict[str, Any] | None,
           args: argparse.Namespace) -> tuple[str, str, bool]:
    if any(not check.get("pass") for check in prerequisite_checks):
        return "start-only-blocked", "required v221-v228 prerequisite decision is missing or mismatched", False
    if any(not check.get("pass") for check in plan_checks):
        return "manual-review-required", "v228 start plan or allowlist changed unexpectedly", False
    if mode in {"plan", "dry-run"}:
        return "dry-run-ready", "v229 plan/dry-run graph is ready; no live daemon execution performed", True
    if preflight_summary is None or not preflight_summary.get("pass"):
        if preflight_summary and preflight_summary.get("runtime_gap"):
            return "start-only-runtime-gap", "preflight found missing Android runtime execution namespace paths", True
        return "start-only-blocked", "live preflight failed before daemon execution", False
    if mode == "preflight":
        return "dry-run-ready", "live preflight passed; daemon execution not requested", True
    if not args.allow_daemon_start or not args.assume_yes:
        return "start-only-blocked", "daemon start requires --allow-daemon-start and --assume-yes", False
    if run_record is None:
        return "start-only-blocked", "daemon run did not execute", False
    if postflight_summary is not None and not postflight_summary.get("pass"):
        return "start-only-reboot-required", "postflight found state drift after daemon attempt", False
    if run_record.ok or run_record.rc in {124, 143}:
        return "start-only-pass", "bounded cnss-daemon start-only attempt completed with clean postflight", True
    return "start-only-runtime-gap", "cnss-daemon did not start cleanly, but cleanup/postflight stayed safe", True


def build_summary(manifest: dict[str, Any]) -> str:
    prereq_rows = [
        [item["name"], item["expected_decision"], item["actual_decision"], "PASS" if item["pass"] else "FAIL"]
        for item in manifest["prerequisite_checks"]
    ]
    plan_rows = [
        [item["name"], "PASS" if item["pass"] else "FAIL", str(item.get("detail", ""))[:96]]
        for item in manifest["plan_checks"]
    ]
    lines = [
        "# v229 Controlled CNSS Start-Only Runner",
        "",
        f"- generated: `{manifest['created']}`",
        f"- mode: `{manifest['mode']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- live_daemon_start: `{manifest['live_daemon_start']}`",
        f"- out_dir: `{manifest['out_dir']}`",
        "",
        "## Prerequisites",
        "",
        markdown_table(["version", "expected", "actual", "status"], prereq_rows),
        "",
        "## Plan Checks",
        "",
        markdown_table(["check", "status", "detail"], plan_rows),
        "",
    ]
    if manifest.get("preflight_summary"):
        lines.extend([
            "## Preflight",
            "",
            f"- pass: `{manifest['preflight_summary']['pass']}`",
            f"- ok commands: `{manifest['preflight_summary']['ok_count']}/{manifest['preflight_summary']['command_count']}`",
            f"- required_failures: `{manifest['preflight_summary']['required_failures']}`",
            f"- runtime_gap: `{manifest['preflight_summary']['runtime_gap']}`",
            f"- active_wifi_warnings: `{manifest['preflight_summary']['active_wifi_warnings']}`",
            "",
        ])
    if manifest.get("daemon_observation"):
        lines.extend([
            "## Daemon Observation",
            "",
            f"- command: `{' '.join(manifest['daemon_observation']['command'])}`",
            f"- rc: `{manifest['daemon_observation']['record']['rc']}`",
            f"- status: `{manifest['daemon_observation']['record']['status']}`",
            f"- file: `{manifest['daemon_observation']['record']['file']}`",
            "",
        ])
    lines.extend([
        "## Guardrails",
        "",
        "- no Wi-Fi scan/connect/link-up operation is allowed",
        "- no credential path access is allowed",
        "- no ICNSS unbind/bind or driver_override recovery is allowed",
        "- live daemon start requires `--allow-daemon-start --assume-yes`",
        "- `cnss_diag` remains disabled in v229",
        "",
    ])
    return "\n".join(lines)


def run_mode(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifests, plan = load_inputs(args)
    prerequisite_checks = validate_prerequisites(manifests)
    plan_checks = validate_v228_plan(plan)
    dry_run_plan = build_dry_run_plan(args.max_runtime_sec)
    store.write_json("dry-run-plan.json", dry_run_plan)

    preflight_records: list[CommandRecord] = []
    preflight_summary: dict[str, Any] | None = None
    postflight_records: list[CommandRecord] = []
    postflight_summary: dict[str, Any] | None = None
    daemon_record: CommandRecord | None = None
    daemon_observation: dict[str, Any] | None = None
    mode = args.subcommand

    if mode in {"preflight", "run"}:
        preflight_records, preflight_summary = collect_preflight(store, args)
        store.write_json("preflight.json", {
            "summary": preflight_summary,
            "commands": [command_record_to_dict(record) for record in preflight_records],
        })

    if mode == "run" and preflight_summary and preflight_summary.get("pass") and args.allow_daemon_start and args.assume_yes:
        daemon_record, daemon_observation = run_daemon_start_only(store, args)
        store.write_json("process-observation.json", daemon_observation)
        postflight_records, postflight_summary = collect_preflight(store, args)
        store.write_json("postflight.json", {
            "summary": postflight_summary,
            "commands": [command_record_to_dict(record) for record in postflight_records],
        })

    decision, reason, pass_ok = decide(
        mode,
        prerequisite_checks,
        plan_checks,
        preflight_summary,
        daemon_record,
        postflight_summary,
        args,
    )
    manifest = {
        "created": now_iso(),
        "mode": mode,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "plan_dir": str(repo_path(args.plan_dir)),
        "live_daemon_start": daemon_record is not None,
        "max_runtime_sec": args.max_runtime_sec,
        "prerequisite_checks": prerequisite_checks,
        "prerequisite_counts": status_counts(prerequisite_checks),
        "plan_checks": plan_checks,
        "plan_check_counts": status_counts(plan_checks),
        "preflight_summary": preflight_summary,
        "daemon_observation": daemon_observation,
        "postflight_summary": postflight_summary,
        "host_metadata": collect_host_metadata(),
        "guardrails": [
            "no Wi-Fi scan/connect/link-up",
            "no credential access",
            "no DHCP/routing/NAT/DNS",
            "no ICNSS unbind/bind/driver_override",
            "no persistent Android partition writes",
            "cnss_diag disabled in v229",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"decision={decision} pass={pass_ok} out_dir={out_dir}")
    print(f"reason={reason}")
    return 0 if pass_ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--plan-dir", type=Path, default=REPO_ROOT / DEFAULT_PLAN_DIR)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / DEFAULT_OUT_DIR)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--max-runtime-sec", type=int, default=10)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", default=argparse.SUPPRESS)
    common.add_argument("--port", type=int, default=argparse.SUPPRESS)
    common.add_argument("--timeout", type=float, default=argparse.SUPPRESS)
    common.add_argument("--plan-dir", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--out-dir", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--expect-version", default=argparse.SUPPRESS)
    common.add_argument("--max-runtime-sec", type=int, default=argparse.SUPPRESS)
    for name in ("plan", "dry-run", "preflight"):
        subparsers.add_parser(name, parents=[common])
    run_parser = subparsers.add_parser("run", parents=[common])
    run_parser.add_argument("--allow-daemon-start", action="store_true")
    run_parser.add_argument("--assume-yes", action="store_true")
    args = parser.parse_args()
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        parser.error("--max-runtime-sec must be 1..30")
    if args.subcommand != "run":
        args.allow_daemon_start = False
        args.assume_yes = False
    return args


if __name__ == "__main__":
    raise SystemExit(run_mode(parse_args()))
