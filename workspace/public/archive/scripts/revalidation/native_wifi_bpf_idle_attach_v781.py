#!/usr/bin/env python3
"""V781 bounded idle BPF tracepoint attach classifier.

V780 proved the reviewed helper can execute without attaching.  V781 performs
one tightly scoped live attach attempt against the static PIL notification
tracepoint, with no modem/WLAN trigger and no Wi-Fi action.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v781-bpf-idle-attach")
LATEST_POINTER = Path("tmp/wifi/latest-v781-bpf-idle-attach.txt")
DEFAULT_V780_MANIFEST = Path("tmp/wifi/v780-bpf-loader-deploy-checkonly/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_bpf_trace_probe"
DEFAULT_HELPER_SHA256 = "9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3"
TRACEFS_TARGET = "/sys/kernel/tracing"
TRACEPOINT_ID_PATH = f"{TRACEFS_TARGET}/events/msm_pil_event/pil_notif/id"

FORBIDDEN_TERMS = (
    " boot_wlan",
    " qcwlanstate",
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
    "reboot",
    "dd if=",
    "dd of=",
    "flash",
    "set_ftrace_filter",
    "set_graph_function",
    "trace_marker",
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
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--v780-manifest", type=Path, default=DEFAULT_V780_MANIFEST)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--allow-bpf-attach", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
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


def tracefs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(TRACEFS_TARGET)}\s+tracefs\s", text) is not None


def validate_device_command(command: list[str], *, allow_mount: bool = False, allow_attach: bool = False) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V781 command term {term!r}: {' '.join(command)}")
    if " --allow-attach " in joined:
        expected_prefix = ["run"]
        if not allow_attach or command[:1] != expected_prefix or len(command) < 3:
            raise RuntimeError(f"BPF attach requires explicit V781 attach flag: {' '.join(command)}")
        if command[1] != DEFAULT_HELPER and Path(command[1]).name != Path(DEFAULT_HELPER).name:
            raise RuntimeError(f"unexpected attach helper path: {' '.join(command)}")
    if " mount -t " in joined and not allow_mount:
        raise RuntimeError(f"tracefs mount requires explicit V781 mount flag: {' '.join(command)}")
    if " umount " in joined and not allow_mount:
        raise RuntimeError(f"tracefs cleanup requires explicit V781 mount flag: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             allow_mount: bool = False,
             allow_attach: bool = False) -> dict[str, Any]:
    validate_device_command(command, allow_mount=allow_mount, allow_attach=allow_attach)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def step_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok"))
    return False


def key_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def collect_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "proc-mounts-before", ["cat", "/proc/mounts"], 15.0)
    run_step(args, store, steps, "sha-helper", ["run", args.toybox, "sha256sum", args.helper], 20.0)

    mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before"))
    if mounted_before:
        store.write_text("native/tracefs-mount-skipped.txt", "tracefs already mounted before V781\n")
    else:
        run_step(
            args,
            store,
            steps,
            "tracefs-mount",
            ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", TRACEFS_TARGET],
            20.0,
            allow_mount=True,
        )

    run_step(args, store, steps, "tracepoint-id", ["cat", TRACEPOINT_ID_PATH], 15.0)
    if args.allow_bpf_attach and args.assume_yes:
        run_step(
            args,
            store,
            steps,
            "helper-allow-attach",
            ["run", args.helper, "--allow-attach", "--verbose"],
            30.0,
            allow_attach=True,
        )
    else:
        store.write_text("native/helper-allow-attach-skipped.txt", "missing --allow-bpf-attach --assume-yes\n")

    if not mounted_before:
        run_step(
            args,
            store,
            steps,
            "tracefs-umount",
            ["run", args.busybox, "umount", TRACEFS_TARGET],
            20.0,
            allow_mount=True,
        )
    run_step(args, store, steps, "proc-mounts-after", ["cat", "/proc/mounts"], 15.0)
    run_step(args, store, steps, "status-after", ["status"], 25.0)


def parse_attach_result(text: str) -> dict[str, Any]:
    errno_value = key_value(text, "errno")
    try:
        parsed_errno: int | None = int(errno_value)
    except ValueError:
        parsed_errno = None
    return {
        "raw_result": key_value(text, "result"),
        "attach_attempted": key_value(text, "attach_attempted"),
        "errno": parsed_errno,
        "bpf_prog_fd": key_value(text, "bpf_prog_fd"),
        "tracepoint_id": key_value(text, "tracepoint_id"),
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v780 = load_json(args.v780_manifest)
    steps: list[dict[str, Any]] = []
    if args.command == "run":
        if not args.allow_tracefs_mount or not args.allow_bpf_attach or not args.assume_yes:
            store.write_text("native/not-run.txt", "run requires --allow-tracefs-mount --allow-bpf-attach --assume-yes\n")
        else:
            collect_live(args, store, steps)
    mounts_before = step_payload(steps, "proc-mounts-before")
    mounts_after = step_payload(steps, "proc-mounts-after")
    attach_text = step_payload(steps, "helper-allow-attach")
    return {
        "v780": {
            "manifest": str(repo_path(args.v780_manifest)),
            "decision": v780.get("decision", ""),
            "pass": bool(v780.get("pass")),
        },
        "steps": steps,
        "mounted_before": tracefs_mounted(mounts_before),
        "mounted_after": tracefs_mounted(mounts_after),
        "helper_sha_expected": args.helper_sha256,
        "helper_sha_seen": args.helper_sha256 in step_payload(steps, "sha-helper"),
        "tracepoint_id_text": step_payload(steps, "tracepoint-id").strip(),
        "attach": parse_attach_result(attach_text),
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    add_check(
        checks,
        "v780-input",
        "pass" if analysis["v780"]["decision"] == "v780-bpf-loader-deploy-checkonly-pass" else "blocked",
        "blocker",
        f"decision={analysis['v780']['decision']} pass={analysis['v780']['pass']}",
        [analysis["v780"]["manifest"]],
        "complete V780 before V781",
    )
    if manifest["command"] == "plan":
        add_check(checks, "plan-only", "pass", "info", "no live BPF attach executed", [], "run V781 with explicit attach/mount flags")
        return checks
    add_check(
        checks,
        "explicit-live-flags",
        "pass" if manifest["requested_live"] else "blocked",
        "blocker",
        f"requested_live={manifest['requested_live']}",
        ["native/not-run.txt"],
        "rerun with --allow-tracefs-mount --allow-bpf-attach --assume-yes",
    )
    add_check(
        checks,
        "helper-sha",
        "pass" if analysis["helper_sha_seen"] else "blocked",
        "blocker",
        f"expected_sha_seen={analysis['helper_sha_seen']}",
        ["native/sha-helper.txt"],
        "redeploy V780 helper",
    )
    tracepoint_id = analysis["tracepoint_id_text"]
    tracepoint_id_ok = bool(re.fullmatch(r"\d+", tracepoint_id))
    add_check(
        checks,
        "tracepoint-id",
        "pass" if tracepoint_id_ok else "blocked",
        "blocker",
        f"id={tracepoint_id!r}",
        ["native/tracepoint-id.txt"],
        "ensure tracefs is mounted and target event exists",
    )
    attach = analysis["attach"]
    raw_result = attach["raw_result"]
    attach_classified = raw_result in {"attach-detach-pass", "bpf-load-failed", "attach-failed", "tracepoint-id-failed"}
    add_check(
        checks,
        "attach-classified",
        "pass" if attach_classified else "blocked",
        "blocker",
        f"result={raw_result} errno={attach['errno']} attach_attempted={attach['attach_attempted']}",
        ["native/helper-allow-attach.txt"],
        "preserve evidence before next Wi-Fi observability decision",
    )
    cleanup_ok = not analysis["mounted_after"] if not analysis["mounted_before"] else True
    add_check(
        checks,
        "tracefs-cleanup",
        "pass" if cleanup_ok else "blocked",
        "blocker",
        f"mounted_before={analysis['mounted_before']} mounted_after={analysis['mounted_after']}",
        ["native/proc-mounts-after.txt"],
        "unmount tracefs if V781 mounted it",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v781-bpf-idle-attach-plan-ready", True, "plan-only; no live attach executed", "run V781 bounded idle attach classifier")
    blockers = blocking(checks)
    if blockers:
        return ("v781-bpf-idle-attach-blocked", False, "blocked by " + ", ".join(blockers), "fix blocker before using BPF observability")
    raw_result = analysis["attach"]["raw_result"]
    if raw_result == "attach-detach-pass":
        return (
            "v781-bpf-idle-attach-detach-pass",
            True,
            "idle tracepoint BPF attach/detach succeeded without Wi-Fi trigger",
            "V782 can use this observer around a bounded modem/WLAN state transition",
        )
    return (
        "v781-bpf-idle-attach-denied-classified",
        True,
        f"idle tracepoint attach did not pass but failure was classified as {raw_result}",
        "prefer non-BPF tracepoint/eventfs or userspace QRTR observation unless a safer loader fix is justified",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis", {})
    attach = analysis.get("attach", {})
    return "\n".join([
        "# V781 BPF Idle Attach Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- bpf_attach_attempted: `{manifest['bpf_attach_attempted']}`",
        f"- wifi_action_executed: `{manifest['wifi_action_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], [
            [
                check["name"],
                check["status"],
                check["severity"],
                check["detail"],
                ", ".join(check.get("evidence") or []),
                check["next_step"],
            ]
            for check in checks
        ]),
        "",
        "## Attach",
        "",
        markdown_table(["signal", "value"], [
            ["tracepoint_id", analysis.get("tracepoint_id_text", "")],
            ["result", attach.get("raw_result", "")],
            ["errno", attach.get("errno", "")],
            ["attach_attempted", attach.get("attach_attempted", "")],
            ["mounted_before", analysis.get("mounted_before", "")],
            ["mounted_after", analysis.get("mounted_after", "")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    requested_live = args.command == "run" and args.allow_tracefs_mount and args.allow_bpf_attach and args.assume_yes
    analysis = analyze(args, store)
    attach_attempted = analysis["attach"]["raw_result"] in {"attach-detach-pass", "bpf-load-failed", "attach-failed"}
    manifest: dict[str, Any] = {
        "cycle": "v781",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "requested_live": requested_live,
        "device_commands_executed": args.command == "run",
        "bpf_attach_attempted": attach_attempted,
        "bpf_attach_succeeded": analysis["attach"]["raw_result"] == "attach-detach-pass",
        "ftrace_control_write_executed": False,
        "wifi_action_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest.update({"checks": [asdict(check) for check in checks], "decision": decision, "pass": ok, "reason": reason, "next_step": next_step})
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
    print(f"bpf_attach_attempted: {manifest['bpf_attach_attempted']}")
    print(f"wifi_action_executed: {manifest['wifi_action_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
