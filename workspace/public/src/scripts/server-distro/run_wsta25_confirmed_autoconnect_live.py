#!/usr/bin/env python3
"""Run the WSTA25 confirmed-autoconnect live gate.

This runner is intentionally fail-closed.  By default it does not touch the
device and does not create an autoconnect request.  A credentialed live run must
explicitly provide:

  * ``--allow-confirmed-live``
  * ``--ack-credentialed-wifi``
  * ``--confirm-token`` matching the native uplink-service token

Even then, the runner first performs a redacted status request and requires
native autoconnect readiness before it asks the Debian helper to write the
confirmed request.  DHCP/routing remain native-config-gated; public tunnel and
external ping remain out of scope.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta20_native_wifi_service_boundary as wsta20  # noqa: E402
import run_wsta24_native_wifi_uplink_client as wsta24  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
NATIVE_CONFIRM_TOKEN = "A90_NATIVE_UPLINK_AUTOCONNECT_V1"
PASS_DECISION = "wsta25-confirmed-autoconnect-live-pass"


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def rel(path: Path) -> str:
    return wsta2.rel(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.allow_confirmed_live:
        return False, "wsta25-blocked-explicit-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta25-blocked-credentialed-wifi-ack-required"
    if args.confirm_token != NATIVE_CONFIRM_TOKEN:
        return False, "wsta25-blocked-confirm-token-required"
    return True, "ok"


def status_ready_for_confirmed_autoconnect(payload: dict[str, str]) -> bool:
    return (
        wsta24.helper_status_ok(payload)
        and payload.get("config_profile_present") == "1"
        and payload.get("profile_valid") == "1"
        and payload.get("autoconnect_ready") == "1"
        and payload.get("autoconnect_enabled") == "1"
    )


def helper_confirmed_ok(payload: dict[str, str]) -> bool:
    return (
        payload.get("native_wifi_uplink_client_decision") == "native-wifi-uplink-client-pass"
        and payload.get("native_wifi_uplink_client_requested_op") == "autoconnect-confirmed"
        and payload.get("native_wifi_uplink_client_secret_values_logged") == "0"
        and payload.get("version") == wsta24.UPLINK_SERVICE_VERSION
        and payload.get("op") == "autoconnect"
        and payload.get("owner") == "native-init"
        and payload.get("credentials") == "private-config-gated"
        and payload.get("connect") == "confirm-gated"
        and payload.get("dhcp_routing") == "config-gated"
        and payload.get("external_ping_execution") == "0"
        and payload.get("public_tunnel") == "0"
        and payload.get("secret_values_logged") == "0"
        and payload.get("rc") == "0"
        and payload.get("decision") == "wifi-uplink-service-autoconnect-pass"
    )


def ssh_exec_redacted_script(args: argparse.Namespace,
                             run_dir: Path,
                             script: str,
                             *,
                             timeout: float,
                             redacted_label: str) -> dict[str, Any]:
    key_path = run_dir / "d2_ssh_key_ed25519"
    known_hosts = run_dir / "d2_known_hosts"
    command = [
        "ssh",
        "-i",
        str(key_path),
        "-p",
        str(args.ssh_port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        f"ConnectTimeout={args.ssh_connect_timeout}",
        "-o",
        "PreferredAuthentications=publickey",
        f"root@{args.device_ip}",
        "/bin/sh",
        "-s",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "input_redacted": True,
        "redacted_label": redacted_label,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_confirmed_helper(args: argparse.Namespace,
                         run_dir: Path,
                         *,
                         timeout_sec: int) -> dict[str, Any]:
    script = f"""
set -eu
A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED=1
A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN={shlex.quote(args.confirm_token)}
A90_NATIVE_WIFI_UPLINK_SERVICE_TIMEOUT_SEC={int(timeout_sec)}
export A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED
export A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN
export A90_NATIVE_WIFI_UPLINK_SERVICE_TIMEOUT_SEC
{shlex.quote(wsta24.HELPER_TARGET)} autoconnect-confirmed {shlex.quote(args.service_dir)}
""".strip()
    record = ssh_exec_redacted_script(
        args,
        run_dir,
        script,
        timeout=timeout_sec + args.ssh_connect_timeout + 40,
        redacted_label="wsta25-confirmed-autoconnect-helper",
    )
    record["parsed"] = wsta24.parse_kv(record.get("stdout", ""))
    return record


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("explicit_live_gate"):
        return result.get("gate_decision", "wsta25-blocked-explicit-live-gate")
    if not checks.get("native_v3387"):
        return "wsta25-blocked-v3387-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta25-blocked-native-health"
    if not checks.get("debian_ssh_marker"):
        return "wsta25-blocked-debian-chroot-ssh"
    if not checks.get("helper_staged"):
        return "wsta25-blocked-helper-stage"
    if not checks.get("service_start_pass"):
        return "wsta25-blocked-service-start"
    if not checks.get("helper_status_pass"):
        return "wsta25-blocked-helper-status"
    if not checks.get("autoconnect_ready"):
        return "wsta25-blocked-autoconnect-not-ready"
    if not checks.get("helper_confirmed_pass"):
        return "wsta25-blocked-helper-confirmed-autoconnect"
    if not checks.get("service_stop_pass"):
        return "wsta25-blocked-service-stop"
    if not checks.get("helper_cleanup_ok"):
        return "wsta25-blocked-helper-cleanup"
    if not checks.get("cleanup_ok"):
        return "wsta25-blocked-cleanup"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta25-confirmed-autoconnect-live-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta25_result.json"

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA25 confirmed autoconnect live gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "resident_required": {
            "version": wsta24.V3387_VERSION,
            "build": wsta24.V3387_BUILD,
        },
        "helper": {
            "source": rel(wsta24.HELPER_SOURCE),
            "target": wsta24.HELPER_TARGET,
        },
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "service_dir": args.service_dir,
        "service_dir_native": args.mountpoint.rstrip("/") + "/" + args.service_dir.lstrip("/"),
        "gate_decision": gate_decision,
        "safety": {
            "boot_flash": False,
            "switch_root": False,
            "userdata_touch": False,
            "public_tunnel": False,
            "external_ping": False,
            "confirmed_autoconnect_requires_explicit_flags": True,
            "confirm_token_value_logged": False,
            "dhcp_routing": "native-config-gated-only-after-confirmed-live",
            "temporary_key_only": True,
        },
        "checks": {
            "explicit_live_gate": gate_ok,
            "confirm_token_supplied": bool(args.confirm_token),
            "confirm_token_matches": args.confirm_token == NATIVE_CONFIRM_TOKEN,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        write_json(out_path, result)
        return result

    local_sha = d1.sha256_file(args.local_image)
    result["local_image"] = rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta25-blocked-local-image-sha"
        write_json(out_path, result)
        return result

    result["bridge_status"] = wsta2.run_host(
        [sys.executable, str(wsta2.BRIDGE), "status", "--json"],
        timeout=10.0,
    )
    version = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    status = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
    selftest = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    contract = wsta19.try_cmdv1_retry(args, ["server-distro", "hardware-contract"], timeout=args.timeout)
    result.update({
        "version": version,
        "status": status,
        "baseline_selftest": selftest,
        "hardware_contract": contract,
    })
    write_json(out_path, result)
    if not wsta24.native_is_v3387(version.get("text", "")):
        result["decision"] = "wsta25-blocked-v3387-not-resident"
        write_json(out_path, result)
        return result
    if not wsta2.selftest_passed(selftest.get("text", "")):
        result["decision"] = "wsta25-blocked-native-health"
        write_json(out_path, result)
        return result

    before_sha, before_record = wsta19.remote_sha(args, args.remote_image)
    result["remote_sha_before"] = before_record
    result["remote_sha_before_value"] = before_sha
    if before_sha != local_sha:
        result["install"] = wsta19.install_image(args, local_sha)
    after_sha, after_record = wsta19.remote_sha(args, args.remote_image)
    result["remote_sha_after"] = after_record
    result["remote_sha_after_value"] = after_sha
    if after_sha != local_sha:
        result["decision"] = "wsta25-blocked-remote-image-sha"
        write_json(out_path, result)
        return result
    write_json(out_path, result)

    keygen_record = d2.generate_ssh_key(run_dir, run_id)
    public_key = d2.read_public_key(run_dir)
    result["keygen"] = keygen_record
    write_json(out_path, result)

    service_started = False
    confirmed_attempted = False
    try:
        mount_record = wsta19.bridge_shell(
            args,
            d2.d2_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["mount_parse"].get(key) for key in ("mount_ready", "mounted")):
            result["decision"] = "wsta25-blocked-chroot-mount"
            return result

        start_record = wsta19.bridge_shell(
            args,
            d2.d2_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["dropbear_parse"].get(key) for key in ("started", "authorized_keys", "shadow_temp_key_only")):
            result["decision"] = "wsta25-blocked-dropbear-start"
            return result

        ssh_record = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh"] = ssh_record
        result["ssh_parse"] = ssh_record.get("marker", {})
        write_json(out_path, result)

        result["helper_stage"] = wsta24.stage_helper(args, run_dir)
        write_json(out_path, result)
        if not result["helper_stage"].get("staged"):
            result["decision"] = "wsta25-blocked-helper-stage"
            return result

        result["service_start"] = wsta19.try_cmdv1_retry(
            args,
            [
                "wifi",
                "uplink-service",
                "start",
                result["service_dir_native"],
                str(args.service_lifetime_ms),
                str(args.service_poll_ms),
            ],
            timeout=args.timeout,
            attempts=1,
        )
        service_started = "wifi-uplink-service-start-pass" in result["service_start"].get("text", "")
        write_json(out_path, result)

        if service_started:
            result["helper_status"] = wsta24.run_helper(
                args,
                run_dir,
                "status",
                timeout_sec=args.response_timeout_sec,
            )
            write_json(out_path, result)
            status_payload = result["helper_status"].get("parsed", {})
            if status_ready_for_confirmed_autoconnect(status_payload) or args.allow_not_ready_confirmed:
                confirmed_attempted = True
                result["helper_confirmed"] = run_confirmed_helper(
                    args,
                    run_dir,
                    timeout_sec=args.confirmed_timeout_sec,
                )
                write_json(out_path, result)
            else:
                result["helper_confirmed"] = {
                    "skipped": True,
                    "reason": "autoconnect-not-ready",
                }
                write_json(out_path, result)
    finally:
        if service_started:
            result["service_stop"] = wsta19.try_cmdv1_retry(
                args,
                ["wifi", "uplink-service", "stop", result["service_dir_native"]],
                timeout=args.timeout,
                attempts=1,
            )
        else:
            result["service_stop"] = {"skipped": True, "reason": "service-not-started"}
        if result.get("helper_stage"):
            try:
                result["helper_cleanup"] = wsta24.cleanup_helper(args, run_dir)
            except Exception as exc:  # noqa: BLE001
                result["helper_cleanup"] = {"error": str(exc)}
        else:
            result["helper_cleanup"] = {"skipped": True, "reason": "helper-not-staged"}
        try:
            result["service_dir_cleanup"] = wsta20.cleanup_service_dir(args, run_dir)
        except Exception as exc:  # noqa: BLE001
            result["service_dir_cleanup"] = {"error": str(exc)}
        write_json(out_path, result)

        cleanup_record = wsta19.bridge_shell(
            args,
            d2.d2_cleanup_script(args.mountpoint),
            timeout=args.cleanup_timeout,
            allow_error=True,
        )
        result["cleanup"] = cleanup_record
        result["cleanup_parse"] = d2.parse_cleanup(str(cleanup_record.get("text") or ""))
        write_json(out_path, result)

        postcheck_record = wsta19.bridge_shell(
            args,
            d2.d2_postcheck_script(args.mountpoint),
            timeout=args.cleanup_timeout,
            allow_error=True,
        )
        result["postcheck"] = postcheck_record
        result["postcheck_parse"] = d2.parse_postcheck(str(postcheck_record.get("text") or ""))
        write_json(out_path, result)

    final_version = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    final_selftest = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    result["final_version"] = final_version
    result["final_selftest"] = final_selftest

    cleanup = result.get("cleanup_parse", {})
    postcheck = result.get("postcheck_parse", {})
    helper_status = result.get("helper_status", {}).get("parsed", {})
    helper_confirmed = result.get("helper_confirmed", {}).get("parsed", {})
    result["checks"] = {
        **result.get("checks", {}),
        "native_v3387": wsta24.native_is_v3387(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest.get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(contract.get("text", "")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "helper_staged": bool(result.get("helper_stage", {}).get("staged")),
        "helper_cleanup_ok": bool(result.get("helper_cleanup", {}).get("cleaned")),
        "service_start_pass": service_started,
        "helper_status_pass": wsta24.helper_status_ok(helper_status),
        "autoconnect_ready": status_ready_for_confirmed_autoconnect(helper_status),
        "helper_confirmed_attempted": confirmed_attempted,
        "helper_confirmed_pass": helper_confirmed_ok(helper_confirmed),
        "service_stop_pass": "wifi-uplink-service-stop-pass" in str(result.get("service_stop", {}).get("text", "")),
        "service_dir_cleanup_ok": "A90WSTA20_SERVICE_DIR_REMOVED" in str(result.get("service_dir_cleanup", {}).get("stdout", "")),
        "cleanup_ok": bool(
            cleanup.get("done")
            and cleanup.get("shadow_restored")
            and cleanup.get("mount_cleanup_ok")
            and cleanup.get("loop_cleanup_ok")
            and postcheck.get("mount_absent")
            and postcheck.get("loop_node_absent")
            and postcheck.get("dropbear_absent")
        ),
        "final_v3387": wsta24.native_is_v3387(final_version.get("text", "")),
        "final_selftest_fail_zero": wsta2.selftest_passed(final_selftest.get("text", "")),
    }
    result["decision"] = classify(result)
    write_json(out_path, result)
    return result


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
    parser.add_argument("--cleanup-timeout", type=float, default=90.0)
    parser.add_argument("--ssh-timeout", type=float, default=30.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-uplink-service")
    parser.add_argument("--service-lifetime-ms", type=int, default=120000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--confirmed-timeout-sec", type=int, default=90)
    parser.add_argument("--allow-confirmed-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--confirm-token", default="")
    parser.add_argument("--allow-not-ready-confirmed", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta25-confirmed-autoconnect-live-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "scope": "WSTA25 confirmed autoconnect live gate",
            "decision": "wsta25-runner-error",
            "error": str(exc),
            "run_dir": rel(run_dir),
        }
        write_json(run_dir / "wsta25_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
