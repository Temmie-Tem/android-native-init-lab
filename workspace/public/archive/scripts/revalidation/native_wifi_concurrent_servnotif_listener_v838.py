#!/usr/bin/env python3
"""V838 concurrent service-notifier listener proof.

V837 showed that the service-notifier listener was registered after service74
had already arrived.  This runner pre-arms a listener-only helper in the same
lower modem/CNSS window, then runs the existing lower companion stack without
starting service-manager, Wi-Fi HAL, scan/connect, DHCP/routes, external ping,
esoc0, wlan module load/unload, boot image writes, or partition writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_clean_dsp_arm_only_v787 as v787
import native_wifi_clean_dsp_lower_readback_v788 as v788
import native_wifi_known_asoc_warning_cnss_wlfw_v792 as v792
import native_wifi_known_asoc_warning_servnotif_replay_v835 as v835
import native_wifi_service_notifier_early_listener_probe_v831 as v831
import native_wifi_timestamped_servnotif_hold_v837 as v837
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v838-concurrent-servnotif-listener")
LATEST_POINTER = Path("tmp/wifi/latest-v838-concurrent-servnotif-listener.txt")
DEFAULT_V837_MANIFEST = Path("tmp/wifi/v837-timestamped-servnotif-hold-live-20260525-134510/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v838-execns-helper-v130-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "5c605f4b848f7d4897091d4f0cf901350a34acb685cbc75cea81e9880be8c3df"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v130"
DEPLOY_APPROVAL = "approve v838 deploy execns helper v130 only; no daemon start and no Wi-Fi bring-up"
PROOF_PREFIX = "/tmp/a90-v838-"
LISTENER_OUT = "/cache/a90-v838-servnotif-listener.out"
LISTENER_RC = "/cache/a90-v838-servnotif-listener.rc"
LISTENER_PID = "/cache/a90-v838-servnotif-listener.pid"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v788.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v788.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v788.DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=v788.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--busybox", default=v788.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v788.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=v788.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--transfer-method", choices=("auto", "ncm", "serial"), default="auto")
    parser.add_argument("--companion-runtime-sec", type=int, default=v792.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--v786-manifest", type=Path, default=v788.DEFAULT_V786_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=v788.DEFAULT_V787_MANIFEST)
    parser.add_argument("--v791-manifest", type=Path, default=v792.DEFAULT_V791_MANIFEST)
    parser.add_argument("--v837-manifest", type=Path, default=DEFAULT_V837_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=v788.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v788.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v788.DEFAULT_V734_MANIFEST)
    parser.add_argument("--wait-timeout", type=float, default=120.0)
    parser.add_argument("--wait-interval", type=float, default=3.0)
    parser.add_argument("--allow-arm-clean-dsp", action="store_true")
    parser.add_argument("--allow-reboot", action="store_true")
    parser.add_argument("--allow-cleanup-umount", action="store_true")
    parser.add_argument("--allow-system-mount", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-policy-load", action="store_true")
    parser.add_argument("--allow-firmware-mounts", action="store_true")
    parser.add_argument("--allow-subsys-modem-holder", action="store_true")
    parser.add_argument("--allow-cnss-start-only", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--allow-known-asoc-warning", action="store_true")
    parser.add_argument("--allow-concurrent-listener", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return v837.load_json(path)


def sha256_file(path: Path) -> str:
    return v837.sha256_file(path)


def required_flags(args: argparse.Namespace) -> list[str]:
    missing = v792.required_flags(args)
    if not args.allow_concurrent_listener:
        missing.append("--allow-concurrent-listener")
    return missing


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    return v837.run_host(store, name, command, timeout)


def local_helper(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "marker": False,
        "listener_option": False,
        "listener_mode": False,
        "timing_fields": False,
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    result = subprocess.run(["strings", str(path)], cwd=repo_path("."), text=True, capture_output=True, check=False)
    strings_output = result.stdout if result.returncode == 0 else ""
    info["marker"] = args.helper_marker in strings_output
    info["listener_option"] = "--allow-service-notifier-listener-probe" in strings_output
    info["listener_mode"] = "service-notifier-listener-only" in strings_output
    info["timing_fields"] = "wifi_companion_service_notifier_listener.timing.close_ms" in strings_output
    return info


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    deploy_dir = store.path(f"deploy-v130-{command}")
    cmd = [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v130_deploy_preflight.py",
        "--out-dir",
        str(deploy_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--local-helper",
        str(args.local_helper),
        "--remote-helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--transfer-method",
        args.transfer_method,
    ]
    if command == "run":
        cmd.extend(["--approval-phrase", DEPLOY_APPROVAL, "--apply", "--assume-yes", "run"])
        timeout = 2400.0 if args.transfer_method in {"auto", "serial"} else 300.0
    else:
        cmd.append("preflight")
        timeout = 240.0
    result = run_host(store, f"v838-deploy-{command}", cmd, timeout)
    manifest_path = deploy_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result.update({
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "device_mutations": manifest.get("device_mutations", False),
        "deploy_result": manifest.get("deploy_result"),
    })
    return result


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def configure_concurrent_helper(args: argparse.Namespace) -> Any:
    v788.v735.configure_base()
    v788.v735.PROOF_PREFIX = PROOF_PREFIX
    original_helper = v788.v735.base.helper_command

    def helper_command_with_prearmed_listener(inner_args: argparse.Namespace) -> list[str]:
        lower_command = original_helper(inner_args)
        if not lower_command or lower_command[0] != "run":
            raise RuntimeError("unexpected lower helper command shape")
        listener_command = [
            inner_args.helper,
            "--system-root",
            "/mnt/system/system",
            "--vendor-block",
            "/dev/block/sda29",
            "--vendor-fstype",
            "ext4",
            "--mode",
            "service-notifier-listener-only",
            "--allow-service-notifier-listener-probe",
        ]
        script = "\n".join([
            f"rm -f {shlex.quote(LISTENER_OUT)} {shlex.quote(LISTENER_RC)} {shlex.quote(LISTENER_PID)}",
            f"({shell_join(listener_command)} > {shlex.quote(LISTENER_OUT)} 2>&1; echo $? > {shlex.quote(LISTENER_RC)}) &",
            f"echo $! > {shlex.quote(LISTENER_PID)}",
            shell_join(lower_command[1:]),
        ])
        return ["run", inner_args.busybox, "sh", "-c", script]

    v788.v735.base.helper_command = helper_command_with_prearmed_listener
    return original_helper


def restore_helper(original_helper: Any) -> None:
    v788.v735.base.helper_command = original_helper


def collect_listener_files(args: argparse.Namespace, store: EvidenceStore) -> tuple[str, list[dict[str, Any]]]:
    captures: list[v787.Capture] = []
    for name, path in (
        ("v838-listener-out-after-cleanup", LISTENER_OUT),
        ("v838-listener-rc-after-cleanup", LISTENER_RC),
        ("v838-listener-pid-after-cleanup", LISTENER_PID),
    ):
        v787.capture_command(args, store, captures, name, ["run", args.toybox, "cat", path], 30.0)
    v787.capture_command(
        args,
        store,
        captures,
        "v838-listener-cleanup-cache-files",
        ["run", args.toybox, "rm", "-f", LISTENER_OUT, LISTENER_RC, LISTENER_PID],
        20.0,
    )
    return captures[0].payload if captures else "", [asdict(capture) for capture in captures]


def analyze_timing(service_notifier: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    timing = v837.analyze_timing(service_notifier, events)
    begin_ms = v837.ms_or_none(service_notifier.get("timing_begin_ms"))
    service74_ms = timing.get("service74_ms")
    close_ms = timing.get("close_ms")
    timing["begin_ms"] = begin_ms
    timing["begin_to_service74_ms"] = None
    timing["process_open_at_service74"] = None
    if isinstance(service74_ms, (float, int)) and begin_ms is not None:
        timing["begin_to_service74_ms"] = round(float(service74_ms) - begin_ms, 3)
    if begin_ms is not None and close_ms is not None and isinstance(service74_ms, (float, int)):
        timing["process_open_at_service74"] = begin_ms <= float(service74_ms) <= float(close_ms)
    return timing


def run_lower_concurrent_listener(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    lower_args = v788.lower_args(args, str(prep["v490_manifest"]))
    original_helper = configure_concurrent_helper(args)
    try:
        manifest = v788.v735.build_manifest(lower_args, store)
    finally:
        restore_helper(original_helper)
    lower = v788.lower_summary(manifest)
    listener_payload, listener_captures = collect_listener_files(args, store)
    service_notifier = v831.summarize_service_notifier(listener_payload)
    events = v837.parse_lower_events(store)
    lower["listener_payload_present"] = bool(listener_payload)
    lower["listener_captures"] = listener_captures
    lower["service_notifier"] = service_notifier
    lower["dmesg_events"] = events
    lower["timing"] = analyze_timing(service_notifier, events)
    store.write_json("lower-concurrent-summary.json", lower)
    store.write_text("lower-concurrent-summary.md", v788.v735.render_summary(manifest))
    return lower


def add_check(checks: list[dict[str, Any]], name: str, status: str, severity: str, detail: Any, next_step: str) -> None:
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "next_step": next_step,
    })


def build_checks(args: argparse.Namespace,
                 v837_reference: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 flags_missing: list[str],
                 clean: dict[str, Any],
                 prep: dict[str, Any],
                 lower: dict[str, Any],
                 guard: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "v837-reference",
        "pass" if v837_reference.get("decision") == "v837-listener-not-open-at-service74" and v837_reference.get("pass") is True else "blocked",
        "blocker",
        {"decision": v837_reference.get("decision"), "pass": v837_reference.get("pass")},
        "complete V837 before V838",
    )
    add_check(
        checks,
        "local-helper-v130",
        "pass" if (
            local.get("exists")
            and local.get("sha256") == args.helper_sha256
            and local.get("marker")
            and local.get("listener_option")
            and local.get("listener_mode")
            and local.get("timing_fields")
        ) else "blocked",
        "blocker",
        local,
        "rebuild helper v130 before V838",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run preflight or live with explicit flags")
        return checks
    add_check(
        checks,
        "helper-v130-ready" if args.command == "preflight" else "helper-v130-deploy-run",
        "pass" if deploy and deploy.get("pass") else "blocked",
        "blocker",
        deploy or {},
        "fix helper v130 deploy before V838 live",
    )
    if args.command == "preflight":
        return checks
    add_check(
        checks,
        "explicit-live-flags",
        "pass" if not flags_missing else "blocked",
        "blocker",
        {"missing": flags_missing},
        "pass all explicit V838 allow flags",
    )
    add_check(
        checks,
        "clean-dsp-inline",
        "pass" if clean.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked",
        "blocker",
        {"decision": clean.get("decision"), "reason": clean.get("reason")},
        "do not run concurrent listener until clean-DSP passes",
    )
    add_check(
        checks,
        "current-boot-prep",
        "pass" if prep.get("ready") else "blocked",
        "blocker",
        {"v401": prep.get("v401_decision"), "v490": prep.get("v490_decision"), "policy_load": prep.get("v490_policy_load_executed")},
        "refresh current V401/V490 after clean-DSP reboot",
    )
    helper = v835.lower_helper(lower)
    add_check(
        checks,
        "cnss-start-only-contract",
        "pass" if (
            helper.get("order") == v788.v735.EXPECTED_ORDER
            and helper.get("cnss_diag") == 1
            and helper.get("cnss_daemon") == 1
            and helper.get("all_postflight_safe") == 1
        ) else "blocked",
        "blocker",
        helper,
        "inspect lower helper transcript before interpreting listener timing",
    )
    safety = v835.lower_safety(lower)
    forbidden_keys = (
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    )
    add_check(
        checks,
        "forbidden-actions",
        "pass" if all(not safety.get(key) for key in forbidden_keys) else "blocked",
        "blocker",
        {key: safety.get(key) for key in forbidden_keys},
        "discard run if V838 crossed HAL/connect/network boundary",
    )
    service_notifier = lower.get("service_notifier") or {}
    add_check(
        checks,
        "prearmed-listener-attempt",
        "pass" if v835.listener_attempt_ok(service_notifier) else "blocked",
        "blocker",
        service_notifier,
        "fix listener-only prearm before interpreting timing",
    )
    timing = lower.get("timing") or {}
    add_check(
        checks,
        "service74-observed",
        "pass" if timing.get("service74_ms") is not None else "blocked",
        "blocker",
        timing,
        "repeat only after lower window reaches service74",
    )
    markers = v835.lower_markers(lower)
    add_check(
        checks,
        "known-asoc-warning-guard",
        "pass" if not markers.get("kernel_warning") or guard.get("exact_known_asoc_warning") else "blocked",
        "blocker",
        {"kernel_warning": markers.get("kernel_warning"), "exact_known": guard.get("exact_known_asoc_warning"), "gaps_ms": guard.get("gaps_ms")},
        "only exact ASoC pm_qos warning may be tolerated",
    )
    cleanup = ((lower.get("live") or {}).get("reboot_cleanup") or {})
    add_check(
        checks,
        "cleanup-health",
        "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked",
        "blocker",
        cleanup,
        "recover stock v724 health before continuing",
    )
    add_check(
        checks,
        "concurrent-listener-window",
        "finding",
        "info",
        timing,
        "if listener was open through service74+5s and still no indication, timing is ruled out",
    )
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], lower: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v838-concurrent-servnotif-listener-plan-ready", True, "plan-only; no device command executed", "run V838 preflight then bounded live proof"
    blocked = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blocked:
        return "v838-concurrent-servnotif-listener-blocked", False, "blocked by " + ", ".join(blocked), "repair blocker before retrying V838"
    if args.command == "preflight":
        return "v838-concurrent-servnotif-listener-preflight-ready", True, "helper v130 and V837 reference are ready; live proof still requires explicit flags", "run V838 bounded live proof"
    service_notifier = lower.get("service_notifier") or {}
    timing = lower.get("timing") or {}
    if v835.state_up(service_notifier):
        return (
            "v838-native-servnotif-state-up",
            True,
            "native prearmed listener reported WLAN-PD UP",
            "observe WLFW service69/BDF/wlan0 below HAL/connect before widening",
        )
    if timing.get("process_open_at_service74") is False:
        return (
            "v838-listener-process-not-open-at-service74",
            True,
            "listener-only process did not survive until service74",
            "fix prearm launch/hold before classifying WLAN-PD trigger",
        )
    if timing.get("listener_open_at_service74") is False:
        return (
            "v838-listener-register-still-post-service74",
            True,
            "listener process was prearmed, but REGISTER_LISTENER still occurred after service74",
            "move registration earlier than endpoint publication or analyze service-notifier kernel timing",
        )
    if timing.get("held_5s_after_service74") is True:
        return (
            "v838-held-through-post74-no-indication",
            True,
            "prearmed listener stayed registered through service74+5s and still received no WLAN-PD UP indication",
            "classify the missing Android-only explicit WLAN-PD state-up trigger before HAL/connect",
        )
    return (
        "v838-concurrent-window-inconclusive",
        True,
        "listener ran, but timing was not sufficient to classify the post-service74 window",
        "inspect listener transcript and extend or reposition the prearm",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lower = manifest.get("lower_concurrent") or {}
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    service_notifier = lower.get("service_notifier") or {}
    timing = lower.get("timing") or {}
    events = lower.get("dmesg_events") or {}
    return "\n".join([
        "# V838 Concurrent Service-notifier Listener",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Timing",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted(timing.items())]),
        "",
        "## Service-notifier",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted(service_notifier.items()) if key != "packets"]),
        "",
        "## Dmesg Events",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted((events.get("counts") or {}).items())]),
        "",
        "## Markers",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted(markers.items())]) if markers else "- none",
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted((manifest.get("safety") or {}).items())]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v837_reference = load_json(args.v837_manifest)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    flags_missing = required_flags(args)
    clean: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    lower: dict[str, Any] = {}
    guard: dict[str, Any] = {}
    clean_captures: list[v787.Capture] = []
    if args.command == "preflight":
        deploy = deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = deploy_helper(args, store, "run")
        if deploy.get("pass") and not flags_missing:
            v787_args = argparse.Namespace(**vars(args))
            v787_args.v786_manifest = args.v786_manifest
            v787_args.hide_on_busy = True
            clean_captures, clean_live = v787.collect_live(v787_args, store)
            clean_checks = v787.build_checks(v787_args, "run", v787.load_json(args.v786_manifest), clean_captures, clean_live)
            clean_decision, clean_pass, clean_reason, clean_next = v787.decide("run", clean_checks, clean_live)
            clean = {
                "decision": clean_decision,
                "pass": clean_pass,
                "reason": clean_reason,
                "next_step": clean_next,
                "checks": [asdict(check) for check in clean_checks],
                "live": clean_live,
            }
            if clean_pass:
                prep = v788.run_current_boot_prep(args, store)
            if clean_pass and prep.get("ready"):
                lower = run_lower_concurrent_listener(args, store, prep)
                guard = v792.warning_guard(args, store, lower)
    checks = build_checks(args, v837_reference, local, deploy, flags_missing, clean, prep, lower, guard)
    decision, passed, reason, next_step = decide(args, checks, lower)
    safety = v835.lower_safety(lower)
    manifest = {
        "cycle": "v838",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v837_reference": {"decision": v837_reference.get("decision"), "pass": v837_reference.get("pass"), "path": str(repo_path(args.v837_manifest))},
        "local_helper": local,
        "deploy": deploy,
        "clean_dsp_inline": clean,
        "current_boot_prep": prep,
        "lower_concurrent": lower,
        "known_asoc_warning_guard": guard,
        "checks": checks,
        "safety": {
            "device_commands_executed": args.command in {"preflight", "run"} and deploy is not None,
            "device_mutations": bool((deploy or {}).get("device_mutations")) or (args.command == "run" and not flags_missing),
            "helper_deploy_executed": bool((deploy or {}).get("device_mutations")),
            "clean_dsp_arm_executed": bool(clean_captures and v787.ok(clean_captures, "arm-v641-clean-dsp")),
            "reboot_executed": bool(clean_captures and v787.ok(clean_captures, "reboot-after-arm")),
            "system_mount_executed": bool(prep.get("mountsystem_ok")),
            "selinuxfs_mount_executed": prep.get("v401_decision") == "toybox-selinuxfs-mount-live-executor-run-pass",
            "policy_load_executed": prep.get("v490_policy_load_executed") is True,
            "firmware_mounts_executed": safety.get("firmware_mounts_executed", False),
            "subsys_modem_opened": safety.get("subsys_modem_opened", False),
            "cnss_diag_start_executed": safety.get("cnss_diag_start_executed", False),
            "cnss_daemon_start_executed": safety.get("cnss_daemon_start_executed", False),
            "qmi_payload_executed": args.command == "run" and bool((lower.get("service_notifier") or {}).get("qmi_payload")),
            "service_manager_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
            "partition_write_executed": False,
            "custom_kernel_flash_executed": False,
            "esoc0_open_executed": False,
            "subsystem_write_executed": False,
            "module_load_unload_executed": False,
        },
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    store.mkdir("host")
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['safety']['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['safety']['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['safety']['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['safety']['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['safety']['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
