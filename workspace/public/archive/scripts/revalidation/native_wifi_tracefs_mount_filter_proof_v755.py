#!/usr/bin/env python3
"""V755 bounded tracefs mount/read/cleanup proof.

V754 showed tracefs support and partial target kallsyms, but tracefs was not
mounted. This runner performs the next bounded observability gate: mount tracefs
if needed, read ftrace control surfaces and target available_filter_functions,
then unmount if this runner mounted it.

It does not write ftrace controls, boot_wlan, qcwlanstate, service-manager, Wi-Fi
HAL, scan/connect, credentials, DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v755-tracefs-mount-filter-proof")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V754_MANIFEST = Path("tmp/wifi/v754-hdd-pld-traceability-selector/manifest.json")
TRACEFS_TARGET = "/sys/kernel/tracing"

TARGET_FUNCTIONS = (
    "wlan_boot_cb",
    "wlan_hdd_state_ctrl_param_create",
    "pld_init",
    "hdd_init",
    "wlan_hdd_register_driver",
    "icnss_register_driver",
    "icnss_wlan_enable",
)

FORBIDDEN_TERMS = (
    "set_ftrace_filter",
    "set_graph_function",
    "current_tracer",
    "tracing_on",
    "trace_marker",
    "boot_wlan 1",
    "qcwlanstate on",
    "/bind",
    "/unbind",
    "driver_override",
    "insmod",
    "rmmod",
    "modprobe",
    "servicemanager",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)


@dataclass(frozen=True)
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
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--v754-manifest", type=Path, default=DEFAULT_V754_MANIFEST)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_device_command(command: list[str], allow_mount: bool = False) -> None:
    joined = " " + " ".join(command).lower() + " "
    if allow_mount:
        allowed = {"set_ftrace_filter", "set_graph_function", "current_tracer", "tracing_on"}
    else:
        allowed = set()
    for term in FORBIDDEN_TERMS:
        if term in allowed:
            continue
        if term in joined:
            raise RuntimeError(f"forbidden V755 command term {term!r}: {' '.join(command)}")
    if " mount -t " in joined and not allow_mount:
        raise RuntimeError(f"tracefs mount requires explicit V755 allow flag: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             allow_mount: bool = False) -> dict[str, Any]:
    validate_device_command(command, allow_mount=allow_mount)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def target_regex() -> str:
    return "|".join(re.escape(name) for name in TARGET_FUNCTIONS)


def mount_proof_script(args: argparse.Namespace) -> str:
    regex = target_regex()
    return (
        "set -u\n"
        f"BB={args.busybox}\n"
        f"T={TRACEFS_TARGET}\n"
        "MOUNTED_BEFORE=0\n"
        "MOUNTED_BY_US=0\n"
        "$BB grep -q \" $T tracefs \" /proc/mounts && MOUNTED_BEFORE=1 || true\n"
        "printf 'v755.mounted_before=%s\\n' \"$MOUNTED_BEFORE\"\n"
        "if [ \"$MOUNTED_BEFORE\" = 0 ]; then\n"
        "  $BB mount -t tracefs tracefs \"$T\"\n"
        "  RC=$?\n"
        "  printf 'v755.mount_rc=%s\\n' \"$RC\"\n"
        "  [ \"$RC\" = 0 ] && MOUNTED_BY_US=1\n"
        "else\n"
        "  printf 'v755.mount_rc=0\\n'\n"
        "fi\n"
        "$BB grep -q \" $T tracefs \" /proc/mounts && printf 'v755.mounted_during=1\\n' || printf 'v755.mounted_during=0\\n'\n"
        "for f in available_tracers current_tracer available_filter_functions set_ftrace_filter set_graph_function tracing_on trace; do\n"
        "  P=\"$T/$f\"\n"
        "  printf '== %s ==\\n' \"$P\"\n"
        "  if [ -r \"$P\" ]; then\n"
        "    printf 'v755.readable.%s=1\\n' \"$f\"\n"
        "    $BB head -n 30 \"$P\" 2>&1 || true\n"
        "  else\n"
        "    printf 'v755.readable.%s=0\\n' \"$f\"\n"
        "  fi\n"
        "done\n"
        "printf '== target available_filter_functions ==\\n'\n"
        f"if [ -r \"$T/available_filter_functions\" ]; then $BB grep -Ei '{regex}' \"$T/available_filter_functions\" | $BB head -n 220 || true; fi\n"
        "if [ \"$MOUNTED_BY_US\" = 1 ]; then\n"
        "  $BB umount \"$T\"\n"
        "  printf 'v755.umount_rc=%s\\n' \"$?\"\n"
        "else\n"
        "  printf 'v755.umount_rc=skipped\\n'\n"
        "fi\n"
        "$BB grep -q \" $T tracefs \" /proc/mounts && printf 'v755.mounted_after=1\\n' || printf 'v755.mounted_after=0\\n'\n"
        "printf 'v755.mounted_by_us=%s\\n' \"$MOUNTED_BY_US\"\n"
        "printf 'v755.end=1\\n'\n"
    )


def collect_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 20.0)
    run_step(args, store, steps, "tracefs-full-before", ["tracefs", "full"], 30.0)
    run_step(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], 15.0)


def collect_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    script = mount_proof_script(args)
    store.write_text("native/mount-proof-script-redacted.txt", script.replace(args.busybox, "$BUSYBOX"))
    run_step(
        args,
        store,
        steps,
        "tracefs-mount-read-cleanup",
        ["run", args.busybox, "sh", "-c", script],
        args.timeout,
        allow_mount=True,
    )
    run_step(args, store, steps, "tracefs-full-after", ["tracefs", "full"], 30.0)
    run_step(args, store, steps, "proc-mounts-after", ["cat", "/proc/mounts"], 15.0)


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def key_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def target_hits(text: str) -> dict[str, int]:
    return {name: len(re.findall(re.escape(name), text, re.IGNORECASE)) for name in TARGET_FUNCTIONS}


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v754 = load_json(args.v754_manifest)
    proof = step_payload(steps, "tracefs-mount-read-cleanup")
    after = step_payload(steps, "tracefs-full-after")
    mounts_after = step_payload(steps, "proc-mounts-after")
    hits = target_hits(proof)
    mounted_by_us = key_value(proof, "v755.mounted_by_us") == "1"
    mounted_after = key_value(proof, "v755.mounted_after") == "1" or has(mounts_after, rf"\s{re.escape(TRACEFS_TARGET)}\s+tracefs\s")
    return {
        "v754": {
            "manifest": str(repo_path(args.v754_manifest)),
            "decision": v754.get("decision", ""),
            "pass": bool(v754.get("pass")),
            "device_mutations": bool(v754.get("device_mutations")),
        },
        "approval": {
            "allow_tracefs_mount": args.allow_tracefs_mount,
            "assume_yes": args.assume_yes,
        },
        "proof": {
            "mounted_before": key_value(proof, "v755.mounted_before") == "1",
            "mount_rc": key_value(proof, "v755.mount_rc"),
            "mounted_during": key_value(proof, "v755.mounted_during") == "1",
            "mounted_by_us": mounted_by_us,
            "umount_rc": key_value(proof, "v755.umount_rc"),
            "mounted_after": mounted_after,
            "available_tracers_readable": key_value(proof, "v755.readable.available_tracers") == "1",
            "current_tracer_readable": key_value(proof, "v755.readable.current_tracer") == "1",
            "available_filter_functions_readable": key_value(proof, "v755.readable.available_filter_functions") == "1",
            "set_ftrace_filter_readable": key_value(proof, "v755.readable.set_ftrace_filter") == "1",
            "set_graph_function_readable": key_value(proof, "v755.readable.set_graph_function") == "1",
            "tracing_on_readable": key_value(proof, "v755.readable.tracing_on") == "1",
            "target_hits": hits,
            "any_target_filter_function": any(value > 0 for value in hits.values()),
            "core_target_filter_functions": all(hits.get(name, 0) > 0 for name in ("wlan_boot_cb", "pld_init", "hdd_init", "wlan_hdd_register_driver")),
            "tracefs_after_summary": after.strip().splitlines()[:12],
        },
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace, analysis: dict[str, Any] | None) -> list[Check]:
    if not analysis:
        return []
    v754 = analysis["v754"]
    proof = analysis["proof"]
    approval = analysis["approval"]
    checks: list[Check] = []
    add_check(
        checks,
        "v754-input",
        "pass" if v754["decision"] == "v754-tracefs-mount-gated-observer-needed" and v754["pass"] else "blocked",
        "blocker",
        f"decision={v754['decision']} pass={v754['pass']} mutations={v754['device_mutations']}",
        [v754["manifest"]],
        "complete V754 before V755",
    )
    add_check(
        checks,
        "live-approval",
        "pass" if args.command != "run" or (approval["allow_tracefs_mount"] and approval["assume_yes"]) else "blocked",
        "blocker",
        f"allow={approval['allow_tracefs_mount']} assume_yes={approval['assume_yes']}",
        [],
        "rerun with --allow-tracefs-mount --assume-yes",
    )
    if args.command == "preflight":
        add_check(
            checks,
            "preflight-no-mount",
            "pass",
            "finding",
            "preflight captured current tracefs state without live mount/read/cleanup proof",
            ["native/tracefs-full-before.txt", "native/proc-mounts-before.txt"],
            "run gated live proof with --allow-tracefs-mount --assume-yes",
        )
        return checks
    add_check(
        checks,
        "tracefs-mounted-during-window",
        "pass" if proof["mounted_during"] and proof["mount_rc"] in {"0", ""} else "blocked",
        "blocker",
        f"mounted_before={proof['mounted_before']} mount_rc={proof['mount_rc']} mounted_during={proof['mounted_during']}",
        ["native/tracefs-mount-read-cleanup.txt"],
        "if mount failed, inspect kernel support and mountpoint",
    )
    add_check(
        checks,
        "tracefs-cleanup",
        "pass" if (not proof["mounted_by_us"] or (proof["umount_rc"] == "0" and not proof["mounted_after"])) else "blocked",
        "blocker",
        f"mounted_by_us={proof['mounted_by_us']} umount_rc={proof['umount_rc']} mounted_after={proof['mounted_after']}",
        ["native/tracefs-mount-read-cleanup.txt", "native/proc-mounts-after.txt"],
        "cleanup tracefs before continuing",
    )
    add_check(
        checks,
        "ftrace-control-readability",
        "pass" if proof["available_tracers_readable"] and proof["current_tracer_readable"] else "review",
        "finding",
        f"available_tracers={proof['available_tracers_readable']} current_tracer={proof['current_tracer_readable']} available_filter_functions={proof['available_filter_functions_readable']} set_ftrace_filter={proof['set_ftrace_filter_readable']} set_graph_function={proof['set_graph_function_readable']} tracing_on={proof['tracing_on_readable']}",
        ["native/tracefs-mount-read-cleanup.txt"],
        "if controls are missing, use non-ftrace instrumentation",
    )
    add_check(
        checks,
        "target-filter-functions",
        "pass" if proof["any_target_filter_function"] else "review",
        "finding",
        f"core={proof['core_target_filter_functions']} hits={proof['target_hits']}",
        ["native/tracefs-mount-read-cleanup.txt"],
        "if targets are present, V756 can do a no-trigger ftrace filter dry-run",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v755-tracefs-mount-filter-proof-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight, then gated tracefs mount/read/cleanup proof",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v755-tracefs-mount-filter-proof-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before continuing",
        )
    if args.command == "preflight":
        return (
            "v755-tracefs-mount-filter-proof-preflight-ready",
            True,
            "preflight captured current tracefs state without mount",
            "run with --allow-tracefs-mount --assume-yes",
        )
    proof = (analysis or {}).get("proof") or {}
    if proof.get("any_target_filter_function"):
        return (
            "v755-tracefs-target-filter-functions-visible",
            True,
            "tracefs mounted and cleaned up; target functions are visible in available_filter_functions",
            "V756 can run no-trigger ftrace filter/tracer dry-run before pairing with boot_wlan",
        )
    return (
        "v755-tracefs-mounted-no-target-filter-functions",
        True,
        "tracefs mounted and cleaned up, but target functions were not visible in available_filter_functions",
        "route to non-ftrace instrumentation or boot-image/kernel-log planning",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    proof = ((manifest.get("analysis") or {}).get("proof") or {})
    return "\n".join([
        "# V755 Tracefs Mount/Filter Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- tracefs_mount_executed: `{manifest['tracefs_mount_executed']}`",
        f"- tracefs_cleanup_executed: `{manifest['tracefs_cleanup_executed']}`",
        f"- ftrace_write_executed: `{manifest['ftrace_write_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Proof",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in proof.items()]) if proof else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] | None = None
    if args.command != "plan":
        collect_preflight(args, store, steps)
        if args.command == "run" and args.allow_tracefs_mount and args.assume_yes:
            collect_live(args, store, steps)
        analysis = build_analysis(args, steps)
    checks = build_checks(args, analysis)
    decision, ok, reason, next_step = decide(args, checks, analysis)
    proof = (analysis or {}).get("proof") or {}
    manifest: dict[str, Any] = {
        "cycle": "v755",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "run" and args.allow_tracefs_mount and args.assume_yes,
        "tracefs_mount_executed": args.command == "run" and args.allow_tracefs_mount and args.assume_yes,
        "tracefs_cleanup_executed": bool(proof.get("umount_rc")),
        "ftrace_write_executed": False,
        "debugfs_mount_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis or {},
        "checks": [asdict(check) for check in checks],
        "steps": steps,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v755-tracefs-mount-filter-proof.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"tracefs_mount_executed: {manifest['tracefs_mount_executed']}")
    print(f"tracefs_cleanup_executed: {manifest['tracefs_cleanup_executed']}")
    print(f"ftrace_write_executed: {manifest['ftrace_write_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
