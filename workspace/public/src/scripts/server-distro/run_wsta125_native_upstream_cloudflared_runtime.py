#!/usr/bin/env python3
"""Run WSTA125: WSTA124 cloudflared runtime with native STA upstream held live.

WSTA124 proved the cloudflared runtime gate fails closed when the current device
network has no usable upstream egress.  WSTA125 is the next bounded integration
gate: bring up the existing native-owned STA uplink service, keep that service
alive, and run the WSTA124 cloudflared runtime proof in the same chroot/Dropbear
session before cleaning everything up.

The runner is inert by default.  It does not flash boot, touch userdata, switch
root, or start public exposure without explicit operator gates.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta20_native_wifi_service_boundary as wsta20  # noqa: E402
import run_wsta24_native_wifi_uplink_client as wsta24  # noqa: E402
import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402
import run_wsta28_reboot_materialization_gate as wsta28  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402
import run_wsta124_cloudflared_runtime_live_gate as wsta124  # noqa: E402


REPO_ROOT = wsta42.REPO_ROOT
DEFAULT_RUN_BASE = wsta42.DEFAULT_RUN_BASE
PASS_DECISION = "wsta125-native-upstream-cloudflared-runtime-pass"
RESULT_NAME = "wsta125_result.json"


def rel(path: Path) -> str:
    return wsta42.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    wsta42.write_json(path, payload)


def finish_result(out_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def sha256_file(path: Path) -> str:
    return wsta42.sha256_file(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_native_upstream_runtime_live:
        return False, "wsta125-blocked-native-upstream-runtime-live-required"
    if not args.allow_credentialed_wifi:
        return False, "wsta125-blocked-credentialed-wifi-allow-required"
    if not args.allow_cloudflared_runtime_live:
        return False, "wsta125-blocked-cloudflared-runtime-live-allow-required"
    if args.run_wsta28_precondition and not args.allow_native_reboot:
        return False, "wsta125-blocked-native-reboot-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta125-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta125-blocked-public-exposure-ack-required"
    if not args.ack_private_url_artifact:
        return False, "wsta125-blocked-private-url-artifact-ack-required"
    if not args.ack_runtime_cleanup:
        return False, "wsta125-blocked-runtime-cleanup-ack-required"
    if args.native_confirm_token != wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta125-blocked-native-confirm-token-required"
    return True, "ok"


def safety(gate_ok: bool, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "device_action": gate_ok,
        "boot_flash": False,
        "native_reboot": bool(gate_ok and args.run_wsta28_precondition and args.allow_native_reboot),
        "wifi_connect": "explicit-native-confirm-gated" if gate_ok else False,
        "dhcp": "explicit-native-confirm-gated" if gate_ok else False,
        "public_tunnel": "explicit-live-gated-short-lived" if gate_ok else False,
        "packet_filter_mutation": "explicit-live-gated-temporary" if gate_ok else False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only" if gate_ok else False,
        "syscall_trace_capture": "explicit-live-gated-private-artifact" if gate_ok else False,
        "public_url_artifact": "workspace-private-only" if gate_ok else False,
        "native_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA125 native STA upstream plus WSTA124 cloudflared runtime",
        "default_mode": "inert-until-explicit-live-ack",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--execute-native-upstream-runtime-live",
            "--allow-credentialed-wifi",
            "--allow-cloudflared-runtime-live",
            "--run-wsta28-precondition",
            "--allow-native-reboot",
            "--use-native-uplink-profile",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--ack-private-url-artifact",
            "--ack-runtime-cleanup",
            "--native-confirm-token",
            "<native-confirm-token>",
        ],
        "device_action": "explicit-live-gated",
        "boot_flash": False,
        "native_reboot": "optional-explicit-wsta28-precondition",
        "public_tunnel": "explicit-live-gated-short-lived",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def wsta28_args(args: argparse.Namespace, run_dir: Path) -> Namespace:
    return Namespace(
        allow_native_reboot=True,
        run_id=None,
        run_dir=run_dir / "wsta28-reboot-materialization",
        host=args.bridge_host,
        port=args.bridge_port,
        timeout=args.timeout,
        warm_reboot_command_timeout=args.warm_reboot_command_timeout,
        warm_reboot_total_timeout=args.warm_reboot_total_timeout,
        warm_reboot_poll_sec=args.warm_reboot_poll_sec,
        bridge_restart_timeout=args.bridge_restart_timeout,
        health_retries=args.health_retries,
        health_timeout=args.health_timeout,
        post_reboot_settle_sec=args.post_reboot_settle_sec,
        wsta27_attempts=args.wsta27_attempts,
        wsta27_retry_delay_sec=args.wsta27_retry_delay_sec,
        probe_timeout_ms=args.probe_timeout_ms,
        scan_delay_ms=args.scan_delay_ms,
        scan_slack_sec=args.scan_slack_sec,
        scan_interval_sec=args.scan_interval_sec,
        scan_attempts=args.scan_attempts,
        print_full_json=False,
    )


def uplink_service_native_dir(args: argparse.Namespace) -> str:
    return args.mountpoint.rstrip("/") + "/" + args.service_dir.lstrip("/")


def resolver_ready(record: dict[str, Any]) -> bool:
    return wsta124.resolver_ready(record)


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    return wsta94.chroot_cleanup_ok(result)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta125-blocked-explicit-live-gate"),
        ("wsta28_precondition_pass", "wsta125-blocked-wsta28-precondition"),
        ("local_image_present", "wsta125-blocked-local-image-missing"),
        ("cloudflared_binary_present", "wsta125-blocked-cloudflared-binary-missing"),
        ("dpublic_helpers_built", "wsta125-blocked-dpublic-helper-build"),
        ("baseline_selftest_fail_zero", "wsta125-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta125-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta125-blocked-remote-image"),
        ("chroot_mount_ready", "wsta125-blocked-chroot-mount"),
        ("dropbear_started", "wsta125-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta125-blocked-debian-ssh"),
        ("service_hardening_assets_staged", "wsta125-blocked-service-hardening-stage"),
        ("dpublic_binaries_staged", "wsta125-blocked-dpublic-binary-stage"),
        ("native_uplink_helper_staged", "wsta125-blocked-native-uplink-helper-stage"),
        ("native_uplink_profile_staged", "wsta125-blocked-native-uplink-profile-stage"),
        ("uplink_service_started", "wsta125-blocked-uplink-service-start"),
        ("native_uplink_helper_ready", "wsta125-blocked-native-uplink-helper-ready"),
        ("native_uplink_confirmed", "wsta125-blocked-native-uplink-confirmed"),
        ("default_route_wlan0", "wsta125-blocked-default-route-not-wlan0"),
        ("resolver_ready", "wsta125-blocked-resolver-sync"),
        ("egress_route_ready", "wsta125-blocked-egress-route"),
        ("packet_filter_preflight_pass", "wsta125-blocked-packet-filter-preflight"),
        ("packet_filter_apply_pass", "wsta125-blocked-packet-filter-apply"),
        ("runtime_probe_completed", "wsta125-blocked-runtime-probe"),
        ("cloudflared_launched", "wsta125-blocked-cloudflared-launch"),
        ("cloudflared_uid_gid_pass", "wsta125-blocked-cloudflared-uid-gid"),
        ("cloudflared_no_new_privs_pass", "wsta125-blocked-cloudflared-no-new-privs"),
        ("cloudflared_cap_eff_zero_pass", "wsta125-blocked-cloudflared-cap-eff"),
        ("cloudflared_command_shape_pass", "wsta125-blocked-cloudflared-command-shape"),
        ("cloudflared_outbound_only_pass", "wsta125-blocked-cloudflared-outbound-only"),
        ("private_url_artifact_saved", "wsta125-blocked-private-url-artifact"),
        ("trace_file_nonempty", "wsta125-blocked-trace-empty"),
        ("syscall_profile_nonempty", "wsta125-blocked-syscall-profile-empty"),
        ("syscall_core_observed", "wsta125-blocked-core-syscalls-missing"),
        ("trace_artifact_saved", "wsta125-blocked-trace-artifact-save"),
        ("runtime_cleanup_ok", "wsta125-blocked-runtime-cleanup"),
        ("packet_filter_restore_pass", "wsta125-blocked-packet-filter-restore"),
        ("uplink_service_stop_pass", "wsta125-blocked-uplink-service-stop"),
        ("native_uplink_helper_cleanup_ok", "wsta125-blocked-native-uplink-helper-cleanup"),
        ("native_uplink_profile_cleanup_ok", "wsta125-blocked-native-uplink-profile-cleanup"),
        ("chroot_cleanup_ok", "wsta125-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta125-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta125-native-upstream-cloudflared-runtime-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    service_dir_native = uplink_service_native_dir(args)
    result: dict[str, Any] = {
        "scope": "WSTA125 native STA upstream plus WSTA124 cloudflared runtime",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "remote_image": args.remote_image,
        "remote_clean_image": args.remote_clean_image if wsta42.remote_clean_image_enabled(args) else None,
        "mountpoint": args.mountpoint,
        "service_dir": args.service_dir,
        "service_dir_native": service_dir_native,
        "use_native_uplink_profile": bool(args.use_native_uplink_profile),
        "run_wsta28_precondition": bool(args.run_wsta28_precondition),
        "safety": safety(gate_ok, args),
        "checks": {
            "explicit_live_gate": gate_ok,
            "wsta28_precondition_pass": not args.run_wsta28_precondition,
            "native_confirm_token_supplied": bool(args.native_confirm_token),
            "native_confirm_token_matches": args.native_confirm_token == wsta25.NATIVE_CONFIRM_TOKEN,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        return finish_result(out_path, result)
    args.confirm_token = args.native_confirm_token

    if args.run_wsta28_precondition:
        result["wsta28"] = wsta28.run(wsta28_args(args, run_dir))
        result["checks"]["wsta28_precondition_pass"] = (
            result["wsta28"].get("decision") == "wsta28-reboot-materialization-scan-gate-pass"
        )
        write_json(out_path, result)
        if not result["checks"]["wsta28_precondition_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

    local_image = args.local_image
    if not local_image.is_file():
        result["checks"]["local_image_present"] = False
        result["decision"] = classify(result)
        return finish_result(out_path, result)
    local_sha = sha256_file(local_image)
    result["local_image"] = rel(local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = args.local_image_sha256
    result["checks"]["local_image_present"] = True
    if args.local_image_sha256 and args.local_image_sha256 != local_sha:
        result["checks"]["remote_image_ready"] = False
        result["decision"] = "wsta125-blocked-local-image-sha"
        return finish_result(out_path, result)

    result["cloudflared_binary"] = {
        "path": rel(args.cloudflared),
        "present": args.cloudflared.is_file(),
        "sha256": sha256_file(args.cloudflared) if args.cloudflared.is_file() else None,
    }
    result["checks"]["cloudflared_binary_present"] = bool(args.cloudflared.is_file())
    result["dpublic_helper_build"] = wsta42.build_dpublic_helpers(run_dir)
    result["checks"]["dpublic_helpers_built"] = bool(result["dpublic_helper_build"].get("ok"))
    write_json(out_path, result)
    if not (result["checks"]["cloudflared_binary_present"] and result["checks"]["dpublic_helpers_built"]):
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    mounted = False
    dropbear_started = False
    helper_staged = False
    profile_staged = False
    service_started = False
    packet_filter_applied = False
    runtime_probe_started = False
    try:
        result["bridge_status"] = wsta42.run_host([sys.executable, str(wsta42.wsta2.BRIDGE), "status", "--json"], timeout=10.0)
        result["version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["status"] = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
        result["baseline_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["baseline_selftest_fail_zero"] = wsta42.wsta2.selftest_passed(
            result["baseline_selftest"].get("text", "")
        )
        result["native_stale_cleanup"] = wsta94.native_stale_cleanup(args)
        result["checks"]["native_stale_cleanup_ok"] = bool(result["native_stale_cleanup"].get("cleaned"))
        write_json(out_path, result)
        if not result["checks"]["native_stale_cleanup_ok"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        image_ready = wsta42.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)
        result["checks"]["remote_image_ready"] = bool(image_ready)
        write_json(out_path, result)
        if not image_ready:
            result["decision"] = result.get("decision") or classify(result)
            return finish_result(out_path, result)

        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        public_key = d2.read_public_key(run_dir)
        write_json(out_path, result)

        mount_record = wsta19.bridge_shell(
            args,
            wsta94.wsta94_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        result["checks"]["chroot_mount_ready"] = bool(
            result["mount_parse"].get("mount_ready") and result["mount_parse"].get("mounted")
        )
        write_json(out_path, result)
        if not result["checks"]["chroot_mount_ready"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        start_record = wsta19.bridge_shell(
            args,
            wsta94.wsta94_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        result["checks"]["dropbear_started"] = bool(
            result["dropbear_parse"].get("started")
            and result["dropbear_parse"].get("authorized_keys")
            and result["dropbear_parse"].get("shadow_temp_key_only")
        )
        dropbear_started = result["checks"]["dropbear_started"]
        write_json(out_path, result)
        if not dropbear_started:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        result["checks"]["debian_ssh_marker"] = bool(result["ssh_parse"].get("marker"))
        write_json(out_path, result)
        if not result["checks"]["debian_ssh_marker"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["service_hardening_stage"] = wsta110.stage_service_hardening_assets(args, run_dir)
        result["checks"]["service_hardening_assets_staged"] = wsta110.stage_ok(result["service_hardening_stage"])
        result["dpublic_binary_stage"] = wsta42.stage_dpublic_binaries(args, run_dir)
        result["checks"]["dpublic_binaries_staged"] = wsta42.stage_binaries_ok(result["dpublic_binary_stage"])
        result["native_uplink_helper_stage"] = wsta24.stage_helper(args, run_dir)
        helper_staged = bool(result["native_uplink_helper_stage"].get("staged"))
        result["checks"]["native_uplink_helper_staged"] = helper_staged
        if args.use_native_uplink_profile:
            result["native_uplink_profile_stage"] = wsta42.stage_native_uplink_profile(args, run_dir)
            profile_staged = bool(result["native_uplink_profile_stage"].get("staged"))
        else:
            result["native_uplink_profile_stage"] = {"skipped": True, "reason": "not-requested"}
            profile_staged = False
        result["checks"]["native_uplink_profile_staged"] = bool(profile_staged or not args.use_native_uplink_profile)
        write_json(out_path, result)
        if not (
            result["checks"]["service_hardening_assets_staged"]
            and result["checks"]["dpublic_binaries_staged"]
            and result["checks"]["native_uplink_helper_staged"]
            and result["checks"]["native_uplink_profile_staged"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["service_start"] = wsta19.try_cmdv1_retry(
            args,
            [
                "wifi",
                "uplink-service",
                "start",
                service_dir_native,
                str(args.service_lifetime_ms),
                str(args.service_poll_ms),
            ],
            timeout=args.timeout,
            attempts=1,
        )
        service_started = "wifi-uplink-service-start-pass" in result["service_start"].get("text", "")
        result["checks"]["uplink_service_started"] = service_started
        write_json(out_path, result)
        if not service_started:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["helper_status"] = wsta24.run_helper(args, run_dir, "status", timeout_sec=args.response_timeout_sec)
        result["checks"]["native_uplink_helper_ready"] = wsta25.status_ready_for_confirmed_autoconnect(
            result["helper_status"].get("parsed", {})
        )
        write_json(out_path, result)
        if not result["checks"]["native_uplink_helper_ready"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        if args.use_native_uplink_profile:
            result["helper_confirmed"] = wsta42.run_profile_confirmed_helper(
                args,
                run_dir,
                timeout_sec=args.confirmed_timeout_sec,
            )
            confirmed_ok = wsta42.profile_confirmed_ok(result["helper_confirmed"])
        else:
            result["helper_confirmed"] = wsta25.run_confirmed_helper(
                args,
                run_dir,
                timeout_sec=args.confirmed_timeout_sec,
            )
            confirmed_ok = wsta42.helper_confirmed_ok(result["helper_confirmed"])
        result["checks"]["native_uplink_confirmed"] = confirmed_ok
        write_json(out_path, result)
        if not confirmed_ok:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        if args.sync_time:
            result["time_sync"] = wsta42.sync_time(args)
            write_json(out_path, result)

        result["native_default_route"] = wsta42.native_default_route(args)
        result["checks"]["default_route_wlan0"] = result["native_default_route"].get("default_route_dev") == "wlan0"
        result["resolver_sync"] = wsta124.ensure_runtime_resolver(args, run_dir)
        result["checks"]["resolver_ready"] = resolver_ready(result["resolver_sync"])
        result["egress_route_preflight"] = (
            wsta124.egress_route_preflight(args, run_dir)
            if result["checks"]["resolver_ready"]
            else {"skipped": True, "reason": "resolver-not-ready"}
        )
        result["checks"]["egress_route_ready"] = bool(result["egress_route_preflight"].get("ready"))
        write_json(out_path, result)
        if not (
            result["checks"]["default_route_wlan0"]
            and result["checks"]["resolver_ready"]
            and result["checks"]["egress_route_ready"]
        ):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["packet_filter_preflight"] = wsta42.run_packet_filter(args, run_dir, "preflight")
        result["checks"]["packet_filter_preflight_pass"] = wsta42.packet_filter_preflight_ok(
            result["packet_filter_preflight"]
        )
        write_json(out_path, result)
        if not result["checks"]["packet_filter_preflight_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["packet_filter_apply"] = wsta42.run_packet_filter(args, run_dir, "apply-loopback-default-drop")
        packet_filter_applied = True
        result["checks"]["packet_filter_apply_pass"] = wsta42.packet_filter_apply_ok(result["packet_filter_apply"])
        write_json(out_path, result)
        if not result["checks"]["packet_filter_apply_pass"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        runtime_probe_started = True
        result["runtime_probe"] = wsta124.run_runtime_probe(args, run_dir)
        parsed = result["runtime_probe"].get("parsed", {})
        result["checks"].update({
            "runtime_probe_completed": bool(
                result["runtime_probe"].get("returncode") == 0
                and not result["runtime_probe"].get("timed_out")
                and parsed.get("runtime_done")
            ),
            "cloudflared_launched": bool(parsed.get("cloudflared_launch_started") and parsed.get("cloudflared_pid_found")),
            "cloudflared_uid_gid_pass": bool(parsed.get("uid_3902") and parsed.get("gid_3902")),
            "cloudflared_no_new_privs_pass": bool(parsed.get("no_new_privs")),
            "cloudflared_cap_eff_zero_pass": bool(parsed.get("cap_eff_zero")),
            "cloudflared_command_shape_pass": bool(
                parsed.get("command_has_tunnel")
                and parsed.get("command_no_autoupdate")
                and parsed.get("command_origin")
                and parsed.get("command_metrics")
            ),
            "cloudflared_outbound_only_pass": bool(parsed.get("outbound_only") and parsed.get("established_outbound")),
            "trace_file_nonempty": bool(parsed.get("trace_file_nonempty")),
            "syscall_profile_nonempty": bool(parsed.get("syscall_profile_nonempty")),
            "syscall_core_observed": bool(parsed.get("core_syscalls_observed")),
        })
        result["private_url_artifact"] = (
            wsta124.fetch_private_url(args, run_dir)
            if parsed.get("url_artifact_private")
            else {"url_artifact_saved": False, "skipped": True, "reason": "url-not-observed"}
        )
        result["checks"]["private_url_artifact_saved"] = bool(result["private_url_artifact"].get("url_artifact_saved"))
        result["trace_artifacts"] = (
            wsta124.fetch_trace_artifacts(args, run_dir)
            if parsed.get("trace_file_nonempty") and parsed.get("syscall_profile_nonempty")
            else {"all_saved": False, "skipped": True, "reason": "trace-not-complete"}
        )
        result["checks"]["trace_artifact_saved"] = bool(result["trace_artifacts"].get("all_saved"))
        result["cloudflared_runtime_profile"] = wsta124.runtime_profile(
            parsed,
            result.get("trace_artifacts"),
            result.get("private_url_artifact"),
        )
        write_json(out_path, result)
    finally:
        if mounted and runtime_probe_started:
            result["runtime_cleanup"] = wsta124.cleanup_cloudflared_runtime(args, run_dir)
            result["checks"]["runtime_cleanup_ok"] = bool(result["runtime_cleanup"].get("cleaned"))
        else:
            result["runtime_cleanup"] = {"skipped": True, "reason": "runtime-probe-not-started"}
            result["checks"]["runtime_cleanup_ok"] = not runtime_probe_started
        if mounted and packet_filter_applied:
            result["packet_filter_restore"] = wsta42.run_packet_filter(args, run_dir, "restore")
            result["checks"]["packet_filter_restore_pass"] = wsta42.packet_filter_restore_ok(
                result["packet_filter_restore"]
            )
        else:
            result["packet_filter_restore"] = {"skipped": True, "reason": "packet-filter-not-applied"}
            result["checks"]["packet_filter_restore_pass"] = not packet_filter_applied
        if service_started:
            result["service_stop"] = wsta19.try_cmdv1_retry(
                args,
                ["wifi", "uplink-service", "stop", service_dir_native],
                timeout=args.timeout,
                attempts=1,
            )
            result["checks"]["uplink_service_stop_pass"] = (
                "wifi-uplink-service-stop-pass" in str(result["service_stop"].get("text", ""))
            )
        else:
            result["service_stop"] = {"skipped": True, "reason": "service-not-started"}
            result["checks"]["uplink_service_stop_pass"] = not service_started
        if helper_staged:
            result["native_uplink_helper_cleanup"] = wsta24.cleanup_helper(args, run_dir)
            result["checks"]["native_uplink_helper_cleanup_ok"] = bool(
                result["native_uplink_helper_cleanup"].get("cleaned")
            )
        else:
            result["native_uplink_helper_cleanup"] = {"skipped": True, "reason": "helper-not-staged"}
            result["checks"]["native_uplink_helper_cleanup_ok"] = not helper_staged
        if profile_staged:
            result["native_uplink_profile_cleanup"] = wsta42.cleanup_native_uplink_profile(args, run_dir)
            result["checks"]["native_uplink_profile_cleanup_ok"] = bool(
                result["native_uplink_profile_cleanup"].get("cleaned")
            )
        else:
            result["native_uplink_profile_cleanup"] = {"skipped": True, "reason": "profile-not-staged"}
            result["checks"]["native_uplink_profile_cleanup_ok"] = not args.use_native_uplink_profile
        if dropbear_started:
            result["service_dir_cleanup"] = wsta20.cleanup_service_dir(args, run_dir)
        else:
            result["service_dir_cleanup"] = {"skipped": True, "reason": "dropbear-not-started"}
        if mounted:
            result["service_probe_cleanup"] = wsta19.bridge_shell(
                args,
                wsta110.service_probe_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
        else:
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}
        result["wifi_cleanup"] = wsta19.try_cmdv1_retry(args, ["wifi", "cleanup"], timeout=args.timeout, attempts=1)
        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["chroot_cleanup_ok"] = bool(not mounted or chroot_cleanup_ok(result))
        result["checks"]["final_selftest_fail_zero"] = wsta42.wsta2.selftest_passed(
            result["final_selftest"].get("text", "")
        )
        write_json(out_path, result)

    result["decision"] = classify(result)
    return finish_result(out_path, result)


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "run_wsta28_precondition": result.get("run_wsta28_precondition"),
        "use_native_uplink_profile": result.get("use_native_uplink_profile"),
        "checks": result.get("checks", {}),
        "native_default_route": {
            "default_route_dev": result.get("native_default_route", {}).get("default_route_dev"),
            "default_route_is_wlan0": result.get("native_default_route", {}).get("default_route_is_wlan0"),
        },
        "resolver_sync": {
            key: result.get("resolver_sync", {}).get(key)
            for key in (
                "ready",
                "copied",
                "source",
                "nameserver_count",
                "host_fallback_attempted",
                "host_fallback_checked_count",
                "host_fallback_source_nameserver_count",
            )
        },
        "egress_route_preflight": {
            key: result.get("egress_route_preflight", {}).get(key)
            for key in ("target_present", "route_ok", "target_redacted", "ready")
        },
        "cloudflared_runtime_profile": result.get("cloudflared_runtime_profile", {}),
        "postcheck_parse": result.get("postcheck_parse", {}),
        "safety": result.get("safety", {}),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default=wsta24.DEFAULT_DEVICE_IP)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--runtime-timeout", type=float, default=150.0)
    parser.add_argument("--runtime-wait-sec", type=int, default=75)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--cloudflared-stage-timeout", type=float, default=180.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=wsta42.d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=wsta42.DEFAULT_LOCAL_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=wsta42.d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=wsta42.d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--cloudflared", type=Path, default=wsta42.dpublic.DEFAULT_CLOUDFLARED)
    parser.add_argument("--host-resolver-conf", type=Path, action="append", default=[])
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-uplink-service")
    parser.add_argument("--service-lifetime-ms", type=int, default=360000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--confirmed-timeout-sec", type=int, default=300)
    parser.add_argument("--use-native-uplink-profile", action="store_true")
    parser.add_argument("--no-sync-time", dest="sync_time", action="store_false", default=True)
    parser.add_argument("--run-wsta28-precondition", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--warm-reboot-command-timeout", type=float, default=8.0)
    parser.add_argument("--warm-reboot-total-timeout", type=float, default=120.0)
    parser.add_argument("--warm-reboot-poll-sec", type=float, default=2.0)
    parser.add_argument("--bridge-restart-timeout", type=float, default=12.0)
    parser.add_argument("--health-retries", type=int, default=3)
    parser.add_argument("--health-timeout", type=float, default=12.0)
    parser.add_argument("--post-reboot-settle-sec", type=float, default=5.0)
    parser.add_argument("--wsta27-attempts", type=int, default=2)
    parser.add_argument("--wsta27-retry-delay-sec", type=float, default=3.0)
    parser.add_argument("--probe-timeout-ms", type=int, default=220000)
    parser.add_argument("--scan-delay-ms", type=int, default=5000)
    parser.add_argument("--scan-slack-sec", type=float, default=20.0)
    parser.add_argument("--scan-interval-sec", type=float, default=8.0)
    parser.add_argument("--scan-attempts", type=int, default=4)
    parser.add_argument("--execute-native-upstream-runtime-live", action="store_true")
    parser.add_argument("--allow-credentialed-wifi", action="store_true")
    parser.add_argument("--allow-cloudflared-runtime-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--ack-private-url-artifact", action="store_true")
    parser.add_argument("--ack-runtime-cleanup", action="store_true")
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta125-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
