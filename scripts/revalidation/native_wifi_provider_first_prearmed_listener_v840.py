#!/usr/bin/env python3
"""V840 provider-first CNSS retry with prearmed WLAN-PD listener.

V839 selected the smallest combined gate after V838 ruled out lower-only
service-notifier timing.  This runner reuses helper v130, starts a listener-only
helper in the background, then runs the V700 provider-first CNSS retry path in
the same lower window.

The live path intentionally stays below Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, esoc0, module load/unload, boot image writes, and
partition writes.  It does start the bounded service-manager/vndservice and
PeripheralManager provider-first stack already exercised by V700.
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
import native_wifi_concurrent_servnotif_listener_v838 as v838
import native_wifi_known_asoc_warning_cnss_wlfw_v792 as v792
import native_wifi_known_asoc_warning_servnotif_replay_v835 as v835
import native_wifi_provider_first_cnss_v700 as v700
import native_wifi_service_notifier_early_listener_probe_v831 as v831
import native_wifi_timestamped_servnotif_hold_v837 as v837
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v840-provider-first-prearmed-listener")
LATEST_POINTER = Path("tmp/wifi/latest-v840-provider-first-prearmed-listener.txt")
DEFAULT_V839_MANIFEST = Path("tmp/wifi/v839-post-v838-trigger-classifier/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v838-execns-helper-v130-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "5c605f4b848f7d4897091d4f0cf901350a34acb685cbc75cea81e9880be8c3df"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v130"
DEFAULT_PROVIDER_RUNTIME_SEC = 30

LISTENER_OUT = "/cache/a90-v840-servnotif-listener.out"
LISTENER_RC = "/cache/a90-v840-servnotif-listener.rc"
LISTENER_PID = "/cache/a90-v840-servnotif-listener.pid"

PROVIDER_MODE = v700.V700_MODE
PROVIDER_EXPECTED_ORDER = v700.EXPECTED_ORDER
PROOF_PREFIX = "/tmp/a90-v840-"
DEPLOY_APPROVAL = "approve v840 deploy execns helper v130 only; no daemon start and no Wi-Fi bring-up"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


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
    parser.add_argument("--transfer-method", choices=("auto", "serial", "tcp"), default="auto")
    parser.add_argument("--provider-runtime-sec", type=int, default=DEFAULT_PROVIDER_RUNTIME_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_PROVIDER_RUNTIME_SEC)
    parser.add_argument("--v786-manifest", type=Path, default=v788.DEFAULT_V786_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=v788.DEFAULT_V787_MANIFEST)
    parser.add_argument("--v839-manifest", type=Path, default=DEFAULT_V839_MANIFEST)
    parser.add_argument("--v525-manifest", type=Path, default=v700.base.DEFAULT_V525_MANIFEST)
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
    parser.add_argument("--allow-known-asoc-warning", action="store_true")
    parser.add_argument("--allow-provider-first-service-manager-start-only", action="store_true")
    parser.add_argument("--allow-provider-first-cnss-retry", action="store_true")
    parser.add_argument("--allow-service-notifier-prearm", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def required_flags(args: argparse.Namespace) -> list[str]:
    checks = {
        "--assume-yes": args.assume_yes,
        "--allow-arm-clean-dsp": args.allow_arm_clean_dsp,
        "--allow-reboot": args.allow_reboot,
        "--allow-cleanup-umount": args.allow_cleanup_umount,
        "--allow-system-mount": args.allow_system_mount,
        "--allow-selinuxfs-mount": args.allow_selinuxfs_mount,
        "--allow-policy-load": args.allow_policy_load,
        "--allow-firmware-mounts": args.allow_firmware_mounts,
        "--allow-subsys-modem-holder": args.allow_subsys_modem_holder,
        "--allow-known-asoc-warning": args.allow_known_asoc_warning,
        "--allow-provider-first-service-manager-start-only": args.allow_provider_first_service_manager_start_only,
        "--allow-provider-first-cnss-retry": args.allow_provider_first_cnss_retry,
        "--allow-service-notifier-prearm": args.allow_service_notifier_prearm,
        "--allow-cleanup-reboot": args.allow_cleanup_reboot,
    }
    return [name for name, present in checks.items() if not present]


def local_helper(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "marker": False,
        "listener_option": False,
        "listener_mode": False,
        "listener_timing_fields": False,
        "provider_mode": False,
        "provider_suppression_field": False,
        "service_manager_option": False,
        "qrtr_readback_option": False,
    }
    if not path.exists():
        return info
    info["sha256"] = v838.sha256_file(path)
    result = subprocess.run(["strings", str(path)], cwd=repo_path("."), text=True, capture_output=True, check=False)
    strings_output = result.stdout if result.returncode == 0 else ""
    info["marker"] = args.helper_marker in strings_output
    info["listener_option"] = "--allow-service-notifier-listener-probe" in strings_output
    info["listener_mode"] = "service-notifier-listener-only" in strings_output
    info["listener_timing_fields"] = "wifi_companion_service_notifier_listener.timing.close_ms" in strings_output
    info["provider_mode"] = PROVIDER_MODE in strings_output
    info["provider_suppression_field"] = "wifi_companion_start.initial_cnss_daemon.suppressed" in strings_output
    info["service_manager_option"] = "--allow-service-manager-start-only" in strings_output
    info["qrtr_readback_option"] = "--allow-qrtr-ns-readback" in strings_output
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
    result = v838.run_host(store, f"v840-deploy-{command}", cmd, timeout)
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


def configure_provider_first_prearmed(args: argparse.Namespace) -> dict[str, Any]:
    v700.base.DEFAULT_HELPER_SHA256 = args.helper_sha256
    v700.base.DEFAULT_HELPER_MARKER = args.helper_marker
    original_tokens = v700.V700_USAGE_TOKENS
    v700.V700_USAGE_TOKENS = tuple(
        args.helper_marker if token == "a90_android_execns_probe v119" else token
        for token in original_tokens
    )
    original_companion = v700.base.companion_command
    v700.base.PROOF_PREFIX = PROOF_PREFIX

    def companion_command_with_prearmed_listener(inner_args: argparse.Namespace) -> list[str]:
        provider_command = original_companion(inner_args)
        if not provider_command or provider_command[0] != "run":
            raise RuntimeError("unexpected V700 provider command shape")
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
            f"{shlex.quote(inner_args.toybox)} rm -f {shlex.quote(LISTENER_OUT)} {shlex.quote(LISTENER_RC)} {shlex.quote(LISTENER_PID)}",
            f"({shell_join(listener_command)} > {shlex.quote(LISTENER_OUT)} 2>&1; echo $? > {shlex.quote(LISTENER_RC)}) &",
            f"echo $! > {shlex.quote(LISTENER_PID)}",
            shell_join(provider_command[1:]),
        ])
        return ["run", inner_args.busybox, "sh", "-c", script]

    v700.base.companion_command = companion_command_with_prearmed_listener
    return {"original_companion": original_companion, "original_tokens": original_tokens}


def restore_provider_first_prearmed(state: dict[str, Any]) -> None:
    v700.base.companion_command = state["original_companion"]
    v700.V700_USAGE_TOKENS = state["original_tokens"]


def provider_args(args: argparse.Namespace, v490_manifest: str) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=args.out_dir,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        toybox=args.toybox,
        busybox=args.busybox,
        helper=args.helper,
        helper_sha256=args.helper_sha256,
        helper_marker=args.helper_marker,
        expect_version=args.expect_version,
        v490_manifest=Path(v490_manifest),
        v525_manifest=args.v525_manifest,
        holder_sec=90,
        companion_runtime_sec=args.provider_runtime_sec,
        qrtr_rx_timeout_sec=35.0,
        qrtr_rx_poll_sec=2.0,
        approval_phrase=v700.base.APPROVAL_PHRASE,
        apply=True,
        assume_yes=True,
        command="run",
    )


def collect_listener_files(args: argparse.Namespace, store: EvidenceStore) -> tuple[str, list[dict[str, Any]]]:
    captures: list[v787.Capture] = []
    for name, path in (
        ("v840-listener-out-after-cleanup", LISTENER_OUT),
        ("v840-listener-rc-after-cleanup", LISTENER_RC),
        ("v840-listener-pid-after-cleanup", LISTENER_PID),
    ):
        v787.capture_command(args, store, captures, name, ["run", args.toybox, "cat", path], 30.0)
    v787.capture_command(
        args,
        store,
        captures,
        "v840-listener-cleanup-cache-files",
        ["run", args.toybox, "rm", "-f", LISTENER_OUT, LISTENER_RC, LISTENER_PID],
        20.0,
    )
    return captures[0].payload if captures else "", [asdict(capture) for capture in captures]


def analyze_timing(service_notifier: dict[str, Any], store: EvidenceStore) -> dict[str, Any]:
    events = v837.parse_lower_events(store)
    timing = v838.analyze_timing(service_notifier, events)
    return {
        **timing,
        "events": {
            "counts": events.get("counts", {}),
            "first_ts": events.get("first_ts", {}),
        },
    }


def run_provider_first_prearmed(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    configured = configure_provider_first_prearmed(args)
    try:
        manifest = v700.base.build_manifest(provider_args(args, str(prep["v490_manifest"])), store)
    finally:
        restore_provider_first_prearmed(configured)
    listener_payload, listener_captures = collect_listener_files(args, store)
    service_notifier = v831.summarize_service_notifier(listener_payload)
    timing = analyze_timing(service_notifier, store)
    summary = {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason"),
        "next_step": manifest.get("next_step"),
        "provider_manifest": manifest,
        "listener_payload_present": bool(listener_payload),
        "listener_captures": listener_captures,
        "service_notifier": service_notifier,
        "timing": timing,
    }
    store.write_json("provider-first-prearmed-summary.json", summary)
    store.write_text("provider-first-prearmed-summary.md", v700.base.render_summary(manifest))
    return summary


def add_check(checks: list[dict[str, Any]], name: str, status: str, severity: str, detail: Any, next_step: str) -> None:
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "next_step": next_step,
    })


def provider_live(provider: dict[str, Any]) -> dict[str, Any]:
    manifest = provider.get("provider_manifest") or {}
    live = manifest.get("live")
    return live if isinstance(live, dict) else {}


def provider_surface(provider: dict[str, Any]) -> dict[str, Any]:
    live = provider_live(provider)
    surface = live.get("v700_peripheral_manager_surface")
    return surface if isinstance(surface, dict) else {}


def provider_counts(provider: dict[str, Any]) -> dict[str, int]:
    live = provider_live(provider)
    counts = live.get("v655_counts")
    if not isinstance(counts, dict):
        counts = {}
    return {key: int(value or 0) for key, value in counts.items() if isinstance(value, int)}


def provider_markers(provider: dict[str, Any]) -> dict[str, int]:
    live = provider_live(provider)
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {key: int(value or 0) for key, value in counts.items() if isinstance(value, int)}


def wifi_advanced(counts: dict[str, int], markers: dict[str, int]) -> bool:
    return any(counts.get(key, 0) > 0 for key in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def build_checks(args: argparse.Namespace,
                 v839_reference: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 flags_missing: list[str],
                 clean: dict[str, Any],
                 prep: dict[str, Any],
                 provider: dict[str, Any],
                 guard: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "v839-reference",
        "pass" if v839_reference.get("decision") == "v839-provider-first-prearmed-listener-selected" and v839_reference.get("pass") is True else "blocked",
        "blocker",
        {"decision": v839_reference.get("decision"), "pass": v839_reference.get("pass")},
        "complete V839 before V840",
    )
    add_check(
        checks,
        "local-helper-v130-provider-and-listener",
        "pass" if (
            local.get("exists")
            and local.get("sha256") == args.helper_sha256
            and local.get("marker")
            and local.get("listener_option")
            and local.get("listener_mode")
            and local.get("listener_timing_fields")
            and local.get("provider_mode")
            and local.get("provider_suppression_field")
            and local.get("service_manager_option")
            and local.get("qrtr_readback_option")
        ) else "blocked",
        "blocker",
        local,
        "rebuild helper v130 before V840",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run V840 preflight or live with explicit flags")
        return checks
    add_check(
        checks,
        "helper-v130-ready" if args.command == "preflight" else "helper-v130-deploy-run",
        "pass" if deploy and deploy.get("pass") else "blocked",
        "blocker",
        deploy or {},
        "fix helper v130 deploy before V840 live",
    )
    if args.command == "preflight":
        return checks
    add_check(checks, "explicit-live-flags", "pass" if not flags_missing else "blocked", "blocker", {"missing": flags_missing}, "pass all explicit V840 allow flags")
    add_check(checks, "clean-dsp-inline", "pass" if clean.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked", "blocker", {"decision": clean.get("decision"), "reason": clean.get("reason")}, "do not run provider-first prearm until clean-DSP passes")
    add_check(checks, "current-boot-prep", "pass" if prep.get("ready") else "blocked", "blocker", {"v401": prep.get("v401_decision"), "v490": prep.get("v490_decision"), "policy_load": prep.get("v490_policy_load_executed")}, "refresh current V401/V490 after clean-DSP reboot")
    add_check(checks, "provider-first-run", "pass" if provider.get("pass") is True else "blocked", "blocker", {"decision": provider.get("decision"), "reason": provider.get("reason")}, "inspect provider-first transcript before interpreting listener")
    surface = provider_surface(provider)
    add_check(
        checks,
        "provider-first-contract",
        "pass" if (
            surface.get("order") == PROVIDER_EXPECTED_ORDER
            and surface.get("peripheral_manager_enabled") == "1"
            and (surface.get("initial_cnss_daemon") or {}).get("suppressed") == "1"
            and bool((surface.get("cnss_retry") or {}).get("retry_start_order"))
        ) else "blocked",
        "blocker",
        surface,
        "fix provider-first order, suppression, or retry placement before interpreting listener",
    )
    service_notifier = provider.get("service_notifier") or {}
    add_check(
        checks,
        "prearmed-listener-attempt",
        "pass" if v835.listener_attempt_ok(service_notifier) else "blocked",
        "blocker",
        service_notifier,
        "fix listener-only prearm before interpreting provider-first result",
    )
    timing = provider.get("timing") or {}
    add_check(
        checks,
        "service74-observed",
        "pass" if timing.get("service74_ms") is not None else "blocked",
        "blocker",
        timing,
        "repeat only after provider-first lower window reaches service74",
    )
    cleanup = (provider_live(provider).get("reboot_cleanup") or {})
    add_check(checks, "cleanup-health", "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked", "blocker", cleanup, "recover stock v724 health before continuing")
    markers = provider_markers(provider)
    add_check(
        checks,
        "known-asoc-warning-guard",
        "pass" if not markers.get("kernel_warning") or guard.get("exact_known_asoc_warning") else "blocked",
        "blocker",
        {"kernel_warning": markers.get("kernel_warning"), "exact_known": guard.get("exact_known_asoc_warning"), "gaps_ms": guard.get("gaps_ms")},
        "only exact known ASoC pm_qos warning may be tolerated",
    )
    forbidden = {
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
    }
    add_check(checks, "forbidden-actions", "pass", "blocker", forbidden, "discard run if any forbidden action is introduced")
    add_check(checks, "prearmed-provider-window", "finding", "info", timing, "if listener stayed open through service74 and still no indication, provider-first did not supply the missing trigger")
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], provider: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v840-provider-first-prearmed-listener-plan-ready", True, "plan-only; no device command executed", "run V840 preflight then bounded live proof"
    blocked = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blocked:
        return "v840-provider-first-prearmed-listener-blocked", False, "blocked by " + ", ".join(blocked), "repair blocker before retrying V840"
    if args.command == "preflight":
        return "v840-provider-first-prearmed-listener-preflight-ready", True, "helper v130 and V839 reference are ready; live proof still requires explicit flags", "run V840 bounded provider-first prearmed listener proof"
    service_notifier = provider.get("service_notifier") or {}
    timing = provider.get("timing") or {}
    counts = provider_counts(provider)
    markers = provider_markers(provider)
    if v835.state_up(service_notifier):
        return (
            "v840-provider-first-servnotif-state-up",
            True,
            "provider-first prearmed listener reported WLAN-PD UP",
            "observe WLFW/BDF/wlan0 below HAL/connect before any scan/connect",
        )
    if wifi_advanced(counts, markers):
        return (
            "v840-provider-first-wifi-surface-advanced-without-listener-up",
            True,
            f"provider-first path produced WLFW/BDF/wlan0 markers while listener state was {service_notifier.get('response_curr_state_name')}",
            "classify listener state mismatch and capture WLFW/BDF/interface state before scan/connect",
        )
    if timing.get("process_open_at_service74") is False:
        return (
            "v840-listener-process-not-open-at-service74",
            True,
            "listener-only process did not survive until provider-first service74",
            "fix prearm launch/hold before interpreting provider-first trigger",
        )
    if timing.get("listener_open_at_service74") is False:
        return (
            "v840-listener-register-still-post-service74",
            True,
            "listener process was started, but REGISTER_LISTENER still occurred after service74",
            "move registration earlier or prearm before lower provider gate",
        )
    if timing.get("held_5s_after_service74") is True:
        return (
            "v840-provider-first-prearmed-no-indication",
            True,
            "provider-first CNSS retry plus prearmed listener still received no WLAN-PD UP indication",
            "classify the missing lower native WLAN-PD state-up trigger below HAL/connect",
        )
    return (
        "v840-provider-first-prearmed-window-inconclusive",
        True,
        "provider-first and listener ran, but timing was insufficient to classify the window",
        "inspect listener transcript and extend/reposition prearm",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    provider = manifest.get("provider_first_prearmed") or {}
    live = provider_live(provider)
    service_notifier = provider.get("service_notifier") or {}
    timing = provider.get("timing") or {}
    counts = provider_counts(provider)
    markers = provider_markers(provider)
    surface = provider_surface(provider)
    return "\n".join([
        "# V840 Provider-first Prearmed Listener",
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
        "## Provider-first Contract",
        "",
        markdown_table(["key", "value"], [
            ["decision", provider.get("decision")],
            ["order", surface.get("order")],
            ["initial_cnss_suppressed", (surface.get("initial_cnss_daemon") or {}).get("suppressed")],
            ["cnss_retry_start_order", (surface.get("cnss_retry") or {}).get("retry_start_order")],
            ["service_manager_start_executed", manifest["safety"]["service_manager_start_executed"]],
            ["peripheral_manager_start_executed", manifest["safety"]["peripheral_manager_start_executed"]],
        ]),
        "",
        "## Listener Timing",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted(timing.items())]),
        "",
        "## Service-notifier",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted(service_notifier.items()) if key != "packets"]),
        "",
        "## Markers",
        "",
        markdown_table(["source", "key", "value"], [["v655", key, value] for key, value in sorted(counts.items())] + [["marker", key, value] for key, value in sorted(markers.items())]),
        "",
        "## Cleanup",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted((live.get("reboot_cleanup") or {}).items())]),
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted((manifest.get("safety") or {}).items())]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v839_reference = load_json(args.v839_manifest)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    flags_missing = required_flags(args)
    clean: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    provider: dict[str, Any] = {}
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
                provider = run_provider_first_prearmed(args, store, prep)
                guard = v792.warning_guard(args, store, {"live": provider_live(provider), "safety": {}})
    checks = build_checks(args, v839_reference, local, deploy, flags_missing, clean, prep, provider, guard)
    decision, passed, reason, next_step = decide(args, checks, provider)
    live = provider_live(provider)
    provider_surface_value = provider_surface(provider)
    manifest = {
        "cycle": "v840",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v839_reference": {"decision": v839_reference.get("decision"), "pass": v839_reference.get("pass"), "path": str(repo_path(args.v839_manifest))},
        "local_helper": local,
        "deploy": deploy,
        "clean_dsp_inline": clean,
        "current_boot_prep": prep,
        "provider_first_prearmed": provider,
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
            "firmware_mounts_executed": bool(live.get("mounted_hits")),
            "subsys_modem_opened": bool(live.get("holder_started")),
            "cnss_diag_start_executed": True if provider else False,
            "cnss_daemon_retry_executed": bool((provider_surface_value.get("cnss_retry") or {}).get("retry_start_order")),
            "service_manager_start_executed": True if provider else False,
            "peripheral_manager_start_executed": bool(provider_surface_value.get("peripheral_manager_enabled") == "1"),
            "service_notifier_listener_executed": bool((provider.get("service_notifier") or {}).get("send_attempted")),
            "qmi_payload_executed": args.command == "run" and bool((provider.get("service_notifier") or {}).get("qmi_payload")),
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
    print(f"service_manager_start_executed: {manifest['safety']['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['safety']['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['safety']['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['safety']['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
