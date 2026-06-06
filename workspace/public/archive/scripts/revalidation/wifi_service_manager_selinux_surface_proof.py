#!/usr/bin/env python3
"""Read-only SELinux runtime-surface proof for service-manager SIGABRT."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v397-selinux-surface-proof")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_V392_RUN_LOG = Path("tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt")
DEFAULT_V396_MANIFEST = Path("tmp/wifi/v396-frame-elf-pull-20260520-073940/manifest.json")
DEFAULT_V396_STRINGS = Path("tmp/wifi/v396-frame-elf-pull-20260520-073940/host/strings-servicemanager.txt")

SERVICE_CONTEXT_PATHS = (
    "/mnt/system/system/etc/selinux/plat_service_contexts",
    "/mnt/system/system_ext/etc/selinux/system_ext_service_contexts",
    "/mnt/system/system/system_ext/etc/selinux/system_ext_service_contexts",
    "/mnt/system/product/etc/selinux/product_service_contexts",
    "/mnt/system/system/product/etc/selinux/product_service_contexts",
    "/mnt/system/vendor/etc/selinux/vendor_service_contexts",
    "/mnt/system/system/vendor/etc/selinux/vendor_service_contexts",
    "/mnt/system/odm/etc/selinux/odm_service_contexts",
    "/mnt/system/system/odm/etc/selinux/odm_service_contexts",
)

HWSERVICE_CONTEXT_PATHS = (
    "/mnt/system/system/etc/selinux/plat_hwservice_contexts",
    "/mnt/system/system_ext/etc/selinux/system_ext_hwservice_contexts",
    "/mnt/system/system/system_ext/etc/selinux/system_ext_hwservice_contexts",
    "/mnt/system/product/etc/selinux/product_hwservice_contexts",
    "/mnt/system/system/product/etc/selinux/product_hwservice_contexts",
    "/mnt/system/vendor/etc/selinux/vendor_hwservice_contexts",
    "/mnt/system/system/vendor/etc/selinux/vendor_hwservice_contexts",
    "/mnt/system/odm/etc/selinux/odm_hwservice_contexts",
    "/mnt/system/system/odm/etc/selinux/odm_hwservice_contexts",
)

SELINUX_RUNTIME_PATHS = (
    "/sys/fs/selinux",
    "/sys/fs/selinux/status",
    "/sys/fs/selinux/enforce",
    "/sys/fs/selinux/null",
    "/sys/fs/selinux/policy",
    "/sys/fs/selinux/class/service_manager",
    "/sys/fs/selinux/class/service_manager/perms/list",
    "/sys/fs/selinux/class/service_manager/perms/add",
    "/sys/fs/selinux/class/service_manager/perms/find",
)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 20.0, True),
    ("mountsystem-ro", ["mountsystem", "ro"], 25.0, True),
    ("cat-proc-filesystems", ["cat", "/proc/filesystems"], 10.0, True),
    ("cat-proc-mounts", ["cat", "/proc/mounts"], 10.0, True),
    ("cat-selinux-enforce", ["cat", "/sys/fs/selinux/enforce"], 10.0, False),
    ("xxd-selinux-status", ["run", DEFAULT_TOYBOX, "xxd", "-l", "64", "/sys/fs/selinux/status"], 10.0, False),
    ("find-selinux-service-contexts", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "6", "-name", "*service_contexts"], 20.0, False),
    (
        "grep-service-context-focus",
        [
            "run",
            DEFAULT_TOYBOX,
            "grep",
            "-RHiE",
            "servicemanager|hwservicemanager|vndservicemanager|wificond|android\\.hardware\\.wifi|wifi",
            "/mnt/system/system/etc/selinux",
            "/mnt/system/system_ext/etc/selinux",
            "/mnt/system/product/etc/selinux",
            "/mnt/system/system/product/etc/selinux",
            "/mnt/system/vendor/etc/selinux",
            "/mnt/system/system/vendor/etc/selinux",
            "/mnt/system/odm/etc/selinux",
            "/mnt/system/system/odm/etc/selinux",
            "/mnt/system/system/system_ext/etc/selinux",
        ],
        30.0,
        False,
    ),
)

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\bsetenforce\b|\bload_policy\b", re.IGNORECASE),
    re.compile(r"\bctl\.start\b|\bclass_start\b|\bsetprop\b", re.IGNORECASE),
    re.compile(r"(^|\s)/(?:system|vendor)/bin/(?:servicemanager|hwservicemanager|vndservicemanager|wificond)(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)(?:wpa_supplicant|hostapd)(\s|$)", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/[^ ]+/(?:bind|unbind)\b", re.IGNORECASE),
)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v392-run-log", type=Path, default=DEFAULT_V392_RUN_LOG)
    parser.add_argument("--v396-manifest", type=Path, default=DEFAULT_V396_MANIFEST)
    parser.add_argument("--v396-strings", type=Path, default=DEFAULT_V396_STRINGS)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def validate_command_allowlist() -> None:
    command_text = "\n".join(" ".join(command) for _, command, _, _ in READ_ONLY_COMMANDS)
    for path in SELINUX_RUNTIME_PATHS + SERVICE_CONTEXT_PATHS + HWSERVICE_CONTEXT_PATHS:
        command_text += "\nstat " + path
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = str(resolved)
    return data


def load_text(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    data = capture_to_manifest(capture)
    data["file"] = rel
    data["required"] = False
    return data


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("native")
    for name, command, timeout, required in READ_ONLY_COMMANDS:
        item = capture_device(store, args, name, command, timeout)
        item["required"] = required
        captures.append(item)
    for path in SELINUX_RUNTIME_PATHS:
        captures.append(capture_device(store, args, "stat-" + safe_name(path), ["stat", path], 10.0))
    for path in SERVICE_CONTEXT_PATHS + HWSERVICE_CONTEXT_PATHS:
        captures.append(capture_device(store, args, "stat-" + safe_name(path), ["stat", path], 10.0))
    return captures


def capture_by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("name")): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_file_text(store: EvidenceStore, captures: dict[str, dict[str, Any]], name: str) -> str:
    rel = captures.get(name, {}).get("file")
    if not isinstance(rel, str):
        return ""
    path = store.path(rel)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def stat_name(path: str) -> str:
    return "stat-" + safe_name(path)


def focus_lines(text: str, limit: int = 12) -> list[str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("$")
    ]
    return lines[:limit]


def parse_private_context(run_log: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in run_log.splitlines():
        if not line.startswith("context."):
            continue
        key, _, value = line.partition("=")
        values[key] = value.strip()
    return values


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(store: EvidenceStore,
                 captures: list[dict[str, Any]],
                 v392_run_log: str,
                 v396_manifest: dict[str, Any],
                 v396_strings: str) -> list[Check]:
    checks: list[Check] = []
    by_name = capture_by_name(captures)
    proc_filesystems = capture_file_text(store, by_name, "cat-proc-filesystems")
    proc_mounts = capture_file_text(store, by_name, "cat-proc-mounts")
    enforce_text = capture_file_text(store, by_name, "cat-selinux-enforce").strip()
    status_hex = capture_file_text(store, by_name, "xxd-selinux-status")
    context_find = capture_file_text(store, by_name, "find-selinux-service-contexts")
    context_grep = capture_file_text(store, by_name, "grep-service-context-focus")
    private_context = parse_private_context(v392_run_log)

    selinuxfs_known = "selinuxfs" in proc_filesystems or " selinuxfs " in proc_mounts
    selinux_mount = "/sys/fs/selinux" in proc_mounts
    add_check(
        checks,
        "native-selinuxfs-mount",
        "present" if selinuxfs_known and selinux_mount else "incomplete",
        "info" if selinuxfs_known and selinux_mount else "blocker",
        f"proc_filesystems_selinuxfs={selinuxfs_known} proc_mounts_sysfs_selinux={selinux_mount}",
        focus_lines("\n".join(line for line in proc_mounts.splitlines() if "selinux" in line)),
        "native SELinux mount must exist before private namespace repair",
    )

    status_present = capture_ok(by_name, stat_name("/sys/fs/selinux/status"))
    enforce_present = capture_ok(by_name, stat_name("/sys/fs/selinux/enforce"))
    add_check(
        checks,
        "native-selinux-status-page",
        "present" if status_present else "missing",
        "info" if status_present else "blocker",
        f"status={status_present} enforce={enforce_present} enforce_value={enforce_text or 'unknown'}",
        focus_lines(status_hex, 4),
        "if native status is missing, selinux_status_open cannot map the status page",
    )

    class_present = capture_ok(by_name, stat_name("/sys/fs/selinux/class/service_manager"))
    perms = {
        "list": capture_ok(by_name, stat_name("/sys/fs/selinux/class/service_manager/perms/list")),
        "add": capture_ok(by_name, stat_name("/sys/fs/selinux/class/service_manager/perms/add")),
        "find": capture_ok(by_name, stat_name("/sys/fs/selinux/class/service_manager/perms/find")),
    }
    add_check(
        checks,
        "native-service-manager-class",
        "present" if class_present and all(perms.values()) else "partial",
        "info" if class_present else "warning",
        f"class={class_present} perms={perms}",
        [],
        "service-manager SELinux class/perms support is required for policy checks",
    )

    service_context_count = sum(1 for path in SERVICE_CONTEXT_PATHS if capture_ok(by_name, stat_name(path)))
    hw_context_count = sum(1 for path in HWSERVICE_CONTEXT_PATHS if capture_ok(by_name, stat_name(path)))
    add_check(
        checks,
        "mounted-service-context-inputs",
        "present" if service_context_count >= 1 else "missing",
        "info" if service_context_count >= 1 else "blocker",
        f"service_contexts={service_context_count}/{len(SERVICE_CONTEXT_PATHS)} hwservice_contexts={hw_context_count}/{len(HWSERVICE_CONTEXT_PATHS)}",
        focus_lines(context_find, 20),
        "servicemanager uses service_contexts while hwservicemanager uses hwservice_contexts",
    )

    grep_lines = focus_lines(context_grep, 20)
    add_check(
        checks,
        "focused-context-entries",
        "present" if grep_lines else "missing",
        "info" if grep_lines else "warning",
        f"focused_lines={len(grep_lines)}",
        grep_lines,
        "focused entries help compare service-manager vs Wi-Fi HAL service labels",
    )

    private_null = private_context.get("context.selinux_null.exists") == "1"
    private_status_mentioned = "/sys/fs/selinux/status" in v392_run_log or "context.selinux_status." in v392_run_log
    private_binder = private_context.get("context.dev_binder.exists") == "1"
    private_properties = private_context.get("context.dev_properties.exists") == "1"
    add_check(
        checks,
        "v392-private-preexec-selinux-evidence",
        "status-unproven" if private_null and not private_status_mentioned else "present",
        "warning" if private_null and not private_status_mentioned else "info",
        (
            f"selinux_null={private_null} selinux_status_mentioned={private_status_mentioned} "
            f"binder={private_binder} properties={private_properties}"
        ),
        [
            line
            for line in v392_run_log.splitlines()
            if "context.selinux" in line or "context.dev_binder" in line or "context.dev_properties" in line
        ][:24],
        "helper v22 should print status/enforce/service-context private-root paths before start",
    )

    strings = [
        "selinux_status_open",
        "gSehandle",
        "getcon(&mThisProcessContext)",
        "Access.cpp",
    ]
    present_strings = [needle for needle in strings if needle in v396_strings]
    framechain_decision = v396_manifest.get("framechain_manifest", {}).get("decision")
    add_check(
        checks,
        "v396-fatal-candidate",
        "present" if len(present_strings) >= 3 and framechain_decision == "service-manager-framechain-symbolization-pass" else "weak",
        "info" if len(present_strings) >= 3 else "warning",
        f"framechain={framechain_decision} strings={present_strings}",
        present_strings,
        "use V397 result to choose helper v22 private context expansion or native blocker fix",
    )
    return checks


def choose_decision(mode: str, captures: list[dict[str, Any]], checks: list[Check]) -> tuple[str, bool, str, list[str]]:
    if mode == "plan":
        return (
            "service-manager-selinux-surface-plan-ready",
            True,
            "plan-only; no device commands executed",
            [],
        )
    if not captures or not any(bool(item.get("ok")) for item in captures):
        return (
            "service-manager-selinux-surface-capture-failed",
            False,
            "no successful device captures",
            ["device-capture"],
        )
    by_check = {check.name: check for check in checks}
    if by_check["native-selinux-status-page"].status == "missing":
        return (
            "service-manager-selinux-status-native-missing",
            True,
            "native SELinux status page is absent or unreadable",
            ["native-selinux-status-page"],
        )
    if by_check["mounted-service-context-inputs"].status == "missing":
        return (
            "service-manager-selinux-context-inputs-missing",
            True,
            "mounted Android service_contexts inputs are absent",
            ["mounted-service-context-inputs"],
        )
    if by_check["v392-private-preexec-selinux-evidence"].status == "status-unproven":
        return (
            "service-manager-selinux-surface-native-ready-private-proof-needed",
            True,
            "native SELinux/status/context inputs are visible, but private namespace status visibility is unproven",
            ["private-selinux-status-proof"],
        )
    if all(check.severity != "blocker" for check in checks):
        return (
            "service-manager-selinux-surface-manual-review",
            True,
            "no native SELinux blocker found; private namespace evidence needs manual review",
            ["manual-review"],
        )
    blockers = [check.name for check in checks if check.severity == "blocker"]
    return (
        "service-manager-selinux-surface-manual-review",
        True,
        "mixed SELinux surface evidence",
        blockers,
    )


def render_summary(manifest: dict[str, Any], checks: list[Check]) -> str:
    rows = [[check.name, check.status, check.severity, check.detail, check.next_step] for check in checks]
    lines = [
        "# Service-Manager SELinux Surface Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- mode: `{manifest['mode']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail", "next"], rows) if rows else "- none",
        "",
        "## Guardrails",
        "",
        "- read-only native filesystem and mounted Android context inventory",
        "- `mountsystem ro` only",
        "- no helper deploy",
        "- no daemon start",
        "- no Wi-Fi HAL/start/scan/connect",
        "- no SELinux enforcement or policy writes",
        "",
    ]
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> tuple[dict[str, Any], list[Check]]:
    validate_command_allowlist()
    v396_manifest = load_json(args.v396_manifest)
    v392_present, v392_path, v392_text = load_text(args.v392_run_log)
    v396_strings_present, v396_strings_path, v396_strings_text = load_text(args.v396_strings)
    captures = collect_live(args, store) if args.command == "run" else []
    checks = build_checks(store, captures, v392_text, v396_manifest, v396_strings_text)
    decision, pass_ok, reason, blockers = choose_decision(args.command, captures, checks)
    next_step = (
        "run read-only SELinux surface proof"
        if args.command == "plan"
        else "plan helper v22 private SELinux status/context proof before any daemon or Wi-Fi start"
    )
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "remaining_blockers": blockers,
        "host": collect_host_metadata(),
        "references": [
            "https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp",
            "https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c",
            "https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/init.c",
        ],
        "inputs": {
            "v392_run_log": {"present": v392_present, "path": v392_path},
            "v396_manifest": {
                "present": bool(v396_manifest.get("present")),
                "path": str(repo_path(args.v396_manifest)),
                "decision": v396_manifest.get("decision"),
                "framechain_decision": v396_manifest.get("framechain_manifest", {}).get("decision"),
            },
            "v396_strings": {"present": v396_strings_present, "path": v396_strings_path},
        },
        "captures": captures,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "guardrails": [
            "read-only SELinux runtime inventory",
            "read-only Android service context inventory",
            "mountsystem ro only",
            "no helper deploy",
            "no daemon start",
            "no Wi-Fi HAL/start/scan/connect",
            "no SELinux enforcement or policy writes",
        ],
    }
    return manifest, checks


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest, checks = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": [asdict(check) for check in checks]})
    store.write_text("summary.md", render_summary(manifest, checks))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
