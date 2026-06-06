#!/usr/bin/env python3
"""V787 live arm-only clean-DSP proof on stock v724.

V786 proved stock v724 already contains the V641 firmware-backed sibling SSCTL
one-shot hook, but V782 never armed it.  V787 arms only
/cache/native-init-sibling-fwssctl-v641, reboots, collects proof/timeline/dmesg
evidence, then unmounts the read-only firmware mountpoints left by the proof.

It does not arm the v724 QRTR flag, start CNSS/HAL/service-manager, write
boot_wlan/qcwlanstate, scan/connect, use credentials, change routes, ping, flash,
or write boot partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, strip_cmdv1_text
from a90ctl import bridge_exchange, run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v787-clean-dsp-arm-only")
LATEST_POINTER = Path("tmp/wifi/latest-v787-clean-dsp-arm-only.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_V786_MANIFEST = Path("tmp/wifi/v786-clean-dsp-v724-gap/manifest.json")

V641_FLAG = "/cache/native-init-sibling-fwssctl-v641"
V641_LOG = "/cache/native-init-sibling-fwssctl-v641.log"
V724_QRTR_FLAG = "/cache/native-init-qrtr-servloc-boot-v724"
FW_MOUNTS = ("/vendor/firmware-modem", "/vendor/firmware_mnt")

MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "proof_armed": re.compile(r"sibling fwssctl proof armed|armed one-shot", re.IGNORECASE),
    "firmware_mounts_ready": re.compile(r"firmware mounts ready", re.IGNORECASE),
    "adsp_write_ok": re.compile(r"node adsp write rc=0|adsp status=0x0", re.IGNORECASE),
    "cdsp_write_ok": re.compile(r"node cdsp write rc=0|cdsp status=0x0", re.IGNORECASE),
    "slpi_write_ok": re.compile(r"node slpi write rc=0|slpi status=0x0", re.IGNORECASE),
    "proof_complete_clean": re.compile(r"complete failures=0 timeouts=0", re.IGNORECASE),
    "adsp_pil": re.compile(r"\badsp: (?:loading|Brought out of reset|Power/Clock ready)", re.IGNORECASE),
    "cdsp_pil": re.compile(r"\bcdsp: (?:loading|Brought out of reset|Power/Clock ready)", re.IGNORECASE),
    "slpi_pil": re.compile(r"\bslpi: (?:loading|Brought out of reset|Power/Clock ready)", re.IGNORECASE),
    "sibling_sysmon": re.compile(r"sysmon-qmi:.*(?:slpi|adsp|cdsp)'s SSCTL service", re.IGNORECASE),
    "service_notifier": re.compile(r"service-notifier:.*(?:180|74) service", re.IGNORECASE),
    "wlan_pd": re.compile(r"wlan_pd", re.IGNORECASE),
    "wlfw": re.compile(r"wlfw|QMI Server Connected|WLAN FW is ready", re.IGNORECASE),
    "bdf": re.compile(r"BDF file|bdwlan\.bin|regdb\.bin", re.IGNORECASE),
    "wlan0": re.compile(r"\bwlan0\b", re.IGNORECASE),
    "pm_qos_warning": re.compile(r"pm_qos_add_request|Reference count mismatch|subsystem_put: esoc0", re.IGNORECASE),
}


@dataclass(frozen=True)
class Capture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    payload: str
    error: str
    file: str


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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--v786-manifest", type=Path, default=DEFAULT_V786_MANIFEST)
    parser.add_argument("--wait-timeout", type=float, default=120.0)
    parser.add_argument("--wait-interval", type=float, default=3.0)
    parser.add_argument("--allow-arm-clean-dsp", action="store_true")
    parser.add_argument("--allow-reboot", action="store_true")
    parser.add_argument("--allow-cleanup-umount", action="store_true")
    parser.add_argument("--no-hide-on-busy", action="store_false", dest="hide_on_busy")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def redact(text: str) -> str:
    return re.sub(r"made by [^\r\n]+", "made by [redacted]", text)


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def capture_command(args: argparse.Namespace,
                    store: EvidenceStore,
                    captures: list[Capture],
                    name: str,
                    command: list[str],
                    timeout: float | None = None,
                    expect_disconnect: bool = False) -> Capture:
    started = time.monotonic()
    command_text = " ".join(command)
    try:
        result = run_cmdv1_command(
            args.host,
            args.port,
            timeout if timeout is not None else args.timeout,
            command,
            retry_unsafe=False,
        )
        if result.status == "busy" and args.hide_on_busy:
            send_hide(args)
            result = run_cmdv1_command(
                args.host,
                args.port,
                timeout if timeout is not None else args.timeout,
                command,
                retry_unsafe=False,
            )
        duration = time.monotonic() - started
        payload = redact(strip_cmdv1_text(result.text) if result.text else "")
        capture = Capture(
            name=name,
            command=command_text,
            ok=result.rc == 0 and result.status == "ok",
            rc=result.rc,
            status=result.status,
            duration_sec=duration,
            payload=payload,
            error="",
            file=f"native/{safe_name(name)}.txt",
        )
    except Exception as exc:  # noqa: BLE001 - reboot naturally drops the protocol
        duration = time.monotonic() - started
        error = redact(str(exc))
        capture = Capture(
            name=name,
            command=command_text,
            ok=expect_disconnect,
            rc=None,
            status="expected-disconnect" if expect_disconnect else "missing",
            duration_sec=duration,
            payload="",
            error=error,
            file=f"native/{safe_name(name)}.txt",
        )
    store.write_text(capture.file, (capture.payload or capture.error or "").rstrip() + "\n")
    captures.append(capture)
    return capture


def payload(captures: list[Capture], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.payload or capture.error
    return ""


def ok(captures: list[Capture], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def shell_command(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def send_hide(args: argparse.Namespace) -> None:
    bridge_exchange(
        args.host,
        args.port,
        "hide",
        min(args.timeout, 8.0),
        markers=(b"[busy]", b"[done]", b"[err]"),
    )


def require_live_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.assume_yes:
        missing.append("--assume-yes")
    if not args.allow_arm_clean_dsp:
        missing.append("--allow-arm-clean-dsp")
    if not args.allow_reboot:
        missing.append("--allow-reboot")
    if not args.allow_cleanup_umount:
        missing.append("--allow-cleanup-umount")
    return missing


def wait_for_version(args: argparse.Namespace, store: EvidenceStore, captures: list[Capture]) -> dict[str, Any]:
    deadline = time.monotonic() + args.wait_timeout
    attempts = 0
    last_error = ""
    while time.monotonic() < deadline:
        attempts += 1
        capture = capture_command(args, store, captures, f"wait-version-{attempts:02d}", ["version"], 12.0)
        text = capture.payload
        if capture.ok and args.expect_version in text:
            return {"ok": True, "attempts": attempts, "text": text, "last_error": ""}
        last_error = capture.error or text[-300:]
        time.sleep(args.wait_interval)
    return {"ok": False, "attempts": attempts, "text": "", "last_error": last_error}


def marker_counts(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in MARKER_PATTERNS.items()}


def flag_probe_script() -> str:
    bb = DEFAULT_BUSYBOX
    return (
        f"for f in {V641_FLAG} {V724_QRTR_FLAG} {V641_LOG}; do "
        'if [ -e "$f" ]; then echo "exists $f"; '
        f"{bb} wc -c \"$f\" 2>/dev/null || true; "
        'else echo "missing $f"; fi; done'
    )


def arm_script() -> str:
    bb = DEFAULT_BUSYBOX
    return (
        f"if [ -e {V724_QRTR_FLAG} ]; then echo v787.blocked=qrtr_flag_present; exit 42; fi; "
        f"umask 077; printf run > {V641_FLAG}; sync; "
        f"if [ -e {V641_FLAG} ]; then echo v787.arm=ok; "
        f"{bb} wc -c {V641_FLAG} 2>/dev/null || true; else echo v787.arm=missing; exit 43; fi"
    )


def dmesg_filter_script() -> str:
    bb = DEFAULT_BUSYBOX
    return (
        f"{bb} dmesg | "
        f"{bb} grep -Ei 'A90v641|wifi-v641|adsp:|cdsp:|slpi:|sysmon-qmi|service-notifier|"
        "wlan_pd|icnss|wlfw|BDF|bdwlan|regdb|wlan0|pm_qos|Reference count|subsystem_put|WARNING' | "
        f"{bb} tail -n 260"
    )


def rpmsg_script() -> str:
    bb = DEFAULT_BUSYBOX
    return (
        "echo --rpmsg--; "
        f"{bb} find /sys/bus/rpmsg/devices -maxdepth 1 2>/dev/null | {bb} sort | {bb} sed -n '1,120p'; "
        "echo --mounts--; "
        f"{bb} grep -E 'firmware_mnt|firmware-modem' /proc/mounts || true"
    )


def cleanup_script() -> str:
    bb = DEFAULT_BUSYBOX
    return (
        f"for m in {' '.join(FW_MOUNTS)}; do "
        f'if {bb} grep -q " $m " /proc/mounts; then '
        f"{bb} umount \"$m\" && echo cleanup.umount.$m=ok || echo cleanup.umount.$m=failed; "
        'else echo cleanup.umount.$m=not-mounted; fi; done; '
        f"if [ -e {V724_QRTR_FLAG} ]; then echo cleanup.qrtr_flag=present; else echo cleanup.qrtr_flag=absent; fi; "
        f"if [ -e {V641_FLAG} ]; then echo cleanup.v641_flag=present; else echo cleanup.v641_flag=absent; fi"
    )


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[Capture], dict[str, Any]]:
    captures: list[Capture] = []
    pre_version = capture_command(args, store, captures, "pre-version", ["version"], 12.0)
    capture_command(args, store, captures, "pre-status", ["status"], 30.0)
    capture_command(args, store, captures, "pre-flags", shell_command(args, flag_probe_script()), 20.0)

    if args.expect_version not in pre_version.payload:
        return captures, {"blocked": "unexpected-version", "wait": {}, "markers": {}}
    if f"exists {V724_QRTR_FLAG}" in payload(captures, "pre-flags"):
        return captures, {"blocked": "qrtr-flag-present", "wait": {}, "markers": {}}

    capture_command(args, store, captures, "arm-v641-clean-dsp", shell_command(args, arm_script()), 20.0)
    if not ok(captures, "arm-v641-clean-dsp") or "v787.arm=ok" not in payload(captures, "arm-v641-clean-dsp"):
        return captures, {"blocked": "arm-failed", "wait": {}, "markers": {}}

    capture_command(args, store, captures, "reboot-after-arm", ["reboot"], 10.0, expect_disconnect=True)
    wait_result = wait_for_version(args, store, captures)
    if not wait_result["ok"]:
        return captures, {"blocked": "post-reboot-version-timeout", "wait": wait_result, "markers": {}}

    capture_command(args, store, captures, "post-status", ["status"], 30.0)
    capture_command(args, store, captures, "post-bootstatus", ["bootstatus"], 30.0)
    capture_command(args, store, captures, "post-timeline", ["timeline"], 30.0)
    capture_command(args, store, captures, "post-proof-log-tail", shell_command(args, f"{args.busybox} tail -n 120 {V641_LOG}"), 20.0)
    capture_command(args, store, captures, "post-dmesg-markers", shell_command(args, dmesg_filter_script()), 30.0)
    capture_command(args, store, captures, "post-rpmsg-mounts", shell_command(args, rpmsg_script()), 25.0)
    capture_command(args, store, captures, "cleanup-firmware-mounts", shell_command(args, cleanup_script()), 25.0)
    capture_command(args, store, captures, "post-cleanup-mounts", shell_command(args, rpmsg_script()), 25.0)
    capture_command(args, store, captures, "post-cleanup-status", ["status"], 30.0)

    marker_text = "\n".join(
        payload(captures, name)
        for name in ("post-timeline", "post-dmesg-markers", "post-rpmsg-mounts")
    )
    return captures, {"blocked": "", "wait": wait_result, "markers": marker_counts(marker_text)}


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str],
              next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def build_checks(args: argparse.Namespace,
                 command: str,
                 v786: dict[str, Any],
                 captures: list[Capture],
                 live: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    flags_missing = require_live_flags(args)
    markers = live.get("markers") or {}
    proof_clean = all(markers.get(marker, 0) > 0 for marker in (
        "proof_armed",
        "firmware_mounts_ready",
        "adsp_write_ok",
        "cdsp_write_ok",
        "slpi_write_ok",
        "proof_complete_clean",
    ))
    pil_clean = all(markers.get(marker, 0) > 0 for marker in ("adsp_pil", "cdsp_pil", "slpi_pil"))
    warning_free = markers.get("pm_qos_warning", 0) == 0
    cleanup_text = payload(captures, "cleanup-firmware-mounts") + payload(captures, "post-cleanup-mounts")
    cleanup_ok = (
        "cleanup.qrtr_flag=absent" in cleanup_text
        and "cleanup.v641_flag=absent" in cleanup_text
        and "/vendor/firmware-modem" not in payload(captures, "post-cleanup-mounts")
        and "/vendor/firmware_mnt" not in payload(captures, "post-cleanup-mounts")
    )

    add_check(
        checks,
        "v786-prerequisite",
        "pass" if v786.get("decision") == "v786-v724-clean-dsp-hook-available-but-unarmed" and v786.get("pass") is True else "blocked",
        "blocker",
        f"decision={v786.get('decision')} pass={v786.get('pass')}",
        [str(repo_path(args.v786_manifest))],
        "run V786 before V787",
    )
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no live action", [], "run V787 with explicit live flags")
        return checks

    add_check(
        checks,
        "explicit-live-flags",
        "pass" if not flags_missing else "blocked",
        "blocker",
        "missing=" + ",".join(flags_missing),
        [],
        "pass --assume-yes --allow-arm-clean-dsp --allow-reboot --allow-cleanup-umount",
    )
    add_check(
        checks,
        "preflight-version",
        "pass" if args.expect_version in payload(captures, "pre-version") else "blocked",
        "blocker",
        f"expect={args.expect_version}",
        ["native/pre-version.txt"],
        "restore stock v724 before arming clean-DSP proof",
    )
    add_check(
        checks,
        "qrtr-flag-absent",
        "pass" if f"missing {V724_QRTR_FLAG}" in payload(captures, "pre-flags") else "blocked",
        "blocker",
        f"blocked={live.get('blocked')}",
        ["native/pre-flags.txt"],
        "do not run V787 while the v724 QRTR flag is armed",
    )
    add_check(
        checks,
        "arm-and-reboot",
        "pass" if ok(captures, "arm-v641-clean-dsp") and (live.get("wait") or {}).get("ok") else "blocked",
        "blocker",
        f"arm={ok(captures, 'arm-v641-clean-dsp')} wait={(live.get('wait') or {}).get('ok')}",
        ["native/arm-v641-clean-dsp.txt"],
        "inspect bridge/reboot health before retrying",
    )
    add_check(
        checks,
        "proof-log-clean",
        "pass" if proof_clean else "blocked",
        "blocker",
        f"markers={markers}",
        ["native/post-proof-log-tail.txt", "native/post-timeline.txt"],
        "do not continue to CNSS/boot_wlan until V641 proof is clean",
    )
    add_check(
        checks,
        "dsp-pil-markers",
        "pass" if pil_clean else "review",
        "warn",
        f"adsp={markers.get('adsp_pil', 0)} cdsp={markers.get('cdsp_pil', 0)} slpi={markers.get('slpi_pil', 0)}",
        ["native/post-dmesg-markers.txt"],
        "if absent, compare proof log with dmesg filter and consider a read-only recapture",
    )
    add_check(
        checks,
        "warning-boundary",
        "pass" if warning_free else "blocked",
        "blocker",
        f"pm_qos_warning={markers.get('pm_qos_warning', 0)}",
        ["native/post-dmesg-markers.txt"],
        "stop if pm_qos/reference warning recurs",
    )
    add_check(
        checks,
        "cleanup",
        "pass" if cleanup_ok else "blocked",
        "blocker",
        f"cleanup_ok={cleanup_ok}",
        ["native/cleanup-firmware-mounts.txt", "native/post-cleanup-mounts.txt"],
        "ensure read-only firmware mounts and one-shot flags are cleaned before next gate",
    )
    add_check(
        checks,
        "post-health",
        "pass" if "BOOT OK" in payload(captures, "post-cleanup-status") and "selftest: pass=11" in payload(captures, "post-cleanup-status") else "blocked",
        "blocker",
        "post-cleanup status healthy",
        ["native/post-cleanup-status.txt"],
        "recover stock v724 health before next gate",
    )
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v787-clean-dsp-arm-only-plan-ready",
            True,
            "plan-only; live arm/reboot/cleanup requires explicit flags",
            "run V787 arm-only proof on stock v724",
        )
    blocking = blockers(checks)
    if blocking:
        return (
            "v787-clean-dsp-arm-only-blocked",
            False,
            "blocked by " + ", ".join(blocking),
            "inspect V787 evidence and recover stock v724 health before retrying",
        )
    markers = live.get("markers") or {}
    if markers.get("sibling_sysmon", 0) > 0 or markers.get("service_notifier", 0) > 0:
        return (
            "v787-clean-dsp-arm-only-lower-markers-advanced",
            True,
            "V641 arm-only proof completed cleanly and lower markers advanced without CNSS/HAL/connect",
            "classify lower-marker delta before any CNSS or boot_wlan retry",
        )
    return (
        "v787-clean-dsp-arm-only-proof-pass",
        True,
        "V641 arm-only proof completed on stock v724 with clean ADSP/CDSP/SLPI writes, no warning boundary, and cleanup complete",
        "V788 may run a separate clean-DSP plus lower companion readback; still no Wi-Fi HAL, scan/connect, credentials, DHCP, external ping, or custom-kernel flash",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    marker_rows = [[key, value] for key, value in sorted((manifest["live"].get("markers") or {}).items())]
    return "\n".join([
        "# V787 Clean-DSP Arm-Only Live Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- evidence: `{manifest['evidence_dir']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], ", ".join(check["evidence"]), check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Markers",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [
            ["device_commands_executed", manifest["device_commands_executed"]],
            ["arm_clean_dsp_executed", manifest["arm_clean_dsp_executed"]],
            ["reboot_executed", manifest["reboot_executed"]],
            ["cleanup_umount_executed", manifest["cleanup_umount_executed"]],
            ["qrtr_flag_armed", manifest["qrtr_flag_armed"]],
            ["wifi_trigger_executed", manifest["wifi_trigger_executed"]],
            ["wifi_hal_start_executed", manifest["wifi_hal_start_executed"]],
            ["scan_connect_executed", manifest["scan_connect_executed"]],
            ["credential_use_executed", manifest["credential_use_executed"]],
            ["external_ping_executed", manifest["external_ping_executed"]],
            ["boot_image_write_executed", manifest["boot_image_write_executed"]],
        ]),
        "",
        "## Interpretation",
        "",
        "- V787 is intentionally not a Wi-Fi bring-up gate.",
        "- Its only live mutation is the V641 clean-DSP one-shot flag, followed by reboot and firmware-mount cleanup.",
        "- If clean-DSP passes, the next useful gate is a separate clean-DSP plus lower companion readback, not scan/connect.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v786 = load_json(args.v786_manifest)
    captures: list[Capture] = []
    live: dict[str, Any] = {"blocked": "", "wait": {}, "markers": {}}
    if args.command == "run" and not require_live_flags(args):
        captures, live = collect_live(args, store)
    checks = build_checks(args, args.command, v786, captures, live)
    decision, passed, reason, next_step = decide(args.command, checks, live)
    manifest: dict[str, Any] = {
        "cycle": "v787",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "evidence_dir": str(store.run_dir.relative_to(repo_path("."))),
        "v786_decision": v786.get("decision", ""),
        "captures": [asdict(capture) for capture in captures],
        "live": live,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command == "run" and not require_live_flags(args),
        "device_mutations": args.command == "run" and not require_live_flags(args),
        "arm_clean_dsp_executed": ok(captures, "arm-v641-clean-dsp"),
        "reboot_executed": ok(captures, "reboot-after-arm"),
        "cleanup_umount_executed": ok(captures, "cleanup-firmware-mounts"),
        "qrtr_flag_armed": False,
        "wifi_trigger_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
