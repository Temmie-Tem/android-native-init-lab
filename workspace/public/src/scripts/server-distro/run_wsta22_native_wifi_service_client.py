#!/usr/bin/env python3
"""Run WSTA22 native-owned Wi-Fi service client live gate.

WSTA22 proves the Debian-side ``a90-native-wifi-service-client`` against the
WSTA20 native-owned service boundary:

  * require or optionally flash the V3385 native-init service boundary image,
  * health-check native init and run the WSTA2 wlan0 materialization preflight,
  * mount the SD-backed Debian image as a chroot and start key-only dropbear,
  * stage the current Debian helper into the mounted chroot,
  * start native ``wifi service`` and run the helper from Debian for status/scan,
  * stop the service, clean up chroot/dropbear/loop state, and health-check.

The runner never touches userdata, never starts association/DHCP/ping/public
tunnel work, and never logs Wi-Fi credentials.
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
import a90ctl  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta20_native_wifi_service_boundary as wsta20  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
HELPER_SOURCE = SCRIPT_DIR / "a90_native_wifi_service_client.sh"
HELPER_TARGET = "/usr/local/bin/a90-native-wifi-service-client"
PASS_DECISION = "wsta22-native-wifi-service-client-pass"


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def rel(path: Path) -> str:
    return wsta2.rel(path)


def parse_kv(text: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("A90WSTA22_") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def bridge_restart_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(wsta2.BRIDGE),
        "restart",
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--discovered",
        "--allow-device-change",
        "--wait-timeout",
        str(args.bridge_restart_timeout),
    ]


def run_host_record(command: list[str], *, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "output": completed.stdout,
    }


def native_reboot_recovery(args: argparse.Namespace, reason: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "reason": reason,
        "ok": False,
        "accepted_no_end_marker": True,
        "attempts": [],
    }
    try:
        record["hide_text"] = a90ctl.bridge_exchange(
            args.bridge_host,
            args.bridge_port,
            "hide",
            min(args.warm_reboot_command_timeout, 8.0),
            markers=(b"[busy]", b"[done]", b"[err]"),
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - hide is best effort before reboot.
        record["hide_error"] = repr(exc)
    try:
        record["reboot_text"] = a90ctl.bridge_exchange(
            args.bridge_host,
            args.bridge_port,
            "reboot",
            args.warm_reboot_command_timeout,
            markers=(b"reboot: syncing", b"[busy]", b"[err]"),
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - reboot normally drops the transport.
        record["reboot_transport_error"] = repr(exc)
    if "[busy]" in str(record.get("reboot_text", "")) or "[err]" in str(record.get("reboot_text", "")):
        record["blocked"] = "reboot-rejected"
        return record

    deadline = time.monotonic() + args.warm_reboot_total_timeout
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        item: dict[str, Any] = {"attempt": attempt}
        try:
            item["bridge_restart"] = run_host_record(
                bridge_restart_command(args),
                timeout=max(5.0, args.bridge_restart_timeout + 5.0),
            )
            if item["bridge_restart"]["returncode"] == 0:
                item["version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
                item["selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
                if (
                    wsta20.native_is_v3385(item["version"].get("text", ""))
                    and wsta2.selftest_passed(item["selftest"].get("text", ""))
                ):
                    record["ok"] = True
                    record["version"] = item["version"]
                    record["selftest"] = item["selftest"]
                    record["attempts"].append(item)
                    return record
        except Exception as exc:  # noqa: BLE001 - bounded polling while USB re-enumerates.
            item["error"] = repr(exc)
        record["attempts"].append(item)
        time.sleep(args.warm_reboot_poll_sec)
    record["blocked"] = "post-reboot-health-timeout"
    return record


def helper_status_ok(payload: dict[str, str]) -> bool:
    return (
        payload.get("native_wifi_service_client_decision") == "native-wifi-service-client-pass"
        and payload.get("version") == wsta20.SERVICE_VERSION
        and payload.get("op") == "status"
        and payload.get("owner") == "native-init"
        and payload.get("decision") == "wifi-service-status-pass"
        and payload.get("dhcp_routing") == "0"
        and payload.get("public_tunnel") == "0"
        and payload.get("native_wifi_service_client_secret_values_logged") == "0"
    )


def helper_scan_ok(payload: dict[str, str]) -> bool:
    try:
        count = int(payload.get("scan_result_count", "0"))
    except ValueError:
        count = 0
    return (
        payload.get("native_wifi_service_client_decision") == "native-wifi-service-client-pass"
        and payload.get("version") == wsta20.SERVICE_VERSION
        and payload.get("op") == "scan"
        and payload.get("owner") == "native-init"
        and payload.get("decision") == "wifi-scan-pass"
        and payload.get("raw_results_redacted") == "1"
        and payload.get("credentials") == "0"
        and payload.get("connect") == "0"
        and count > 0
        and payload.get("native_wifi_service_client_secret_values_logged") == "0"
    )


def scan_window_has_bss(window: dict[str, Any]) -> bool:
    return bool(window.get("best", {}).get("scan_has_bss"))


def ssh_exec_input(args: argparse.Namespace,
                   run_dir: Path,
                   remote_command: str,
                   *,
                   input_text: str,
                   timeout: float) -> dict[str, Any]:
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
        remote_command,
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def stage_helper(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    helper_text = HELPER_SOURCE.read_text(encoding="utf-8")
    remote = shlex.quote(HELPER_TARGET)
    backup = shlex.quote(HELPER_TARGET + ".wsta22.bak")
    command = (
        "set -eu; "
        f"STATE=/tmp/a90_wsta22_helper_state; TARGET={remote}; BACKUP={backup}; "
        "rm -f \"$BACKUP\" \"$STATE\"; "
        f"/bin/mkdir -p {shlex.quote(str(Path(HELPER_TARGET).parent))} && "
        "if [ -f \"$TARGET\" ]; then /bin/cp \"$TARGET\" \"$BACKUP\"; echo present > \"$STATE\"; "
        "else echo absent > \"$STATE\"; fi; "
        f"/bin/cat > {remote} && "
        f"/bin/chmod 755 {remote} && "
        f"/bin/grep -q 'native_wifi_service_client_secret_values_logged=0' {remote} && "
        "echo A90WSTA22_HELPER_STAGED"
    )
    record = ssh_exec_input(args, run_dir, command, input_text=helper_text, timeout=args.ssh_timeout)
    record["staged"] = record["returncode"] == 0 and "A90WSTA22_HELPER_STAGED" in record.get("stdout", "")
    record["helper_target"] = HELPER_TARGET
    return record


def cleanup_helper(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    remote = shlex.quote(HELPER_TARGET)
    backup = shlex.quote(HELPER_TARGET + ".wsta22.bak")
    command = (
        "set +e; "
        f"STATE=/tmp/a90_wsta22_helper_state; TARGET={remote}; BACKUP={backup}; "
        "if [ -f \"$STATE\" ] && /bin/grep -q '^present$' \"$STATE\"; then "
        "/bin/mv \"$BACKUP\" \"$TARGET\" && /bin/chmod 755 \"$TARGET\" && echo A90WSTA22_HELPER_RESTORED; "
        "else /bin/rm -f \"$TARGET\" \"$BACKUP\" && echo A90WSTA22_HELPER_REMOVED; fi; "
        "/bin/rm -f \"$STATE\"; "
        "echo A90WSTA22_HELPER_CLEANED"
    )
    record = wsta20.ssh_exec(args, run_dir, command, timeout=args.ssh_timeout)
    stdout = record.get("stdout", "")
    record["cleaned"] = record.get("returncode") == 0 and "A90WSTA22_HELPER_CLEANED" in stdout
    record["restored"] = "A90WSTA22_HELPER_RESTORED" in stdout
    record["removed"] = "A90WSTA22_HELPER_REMOVED" in stdout
    return record


def run_helper(args: argparse.Namespace,
               run_dir: Path,
               op: str,
               *,
               timeout_sec: int) -> dict[str, Any]:
    command = (
        f"A90_NATIVE_WIFI_SERVICE_TIMEOUT_SEC={int(timeout_sec)} "
        f"A90_NATIVE_WIFI_SERVICE_SCAN_DELAY_MS={int(args.scan_delay_ms)} "
        f"{shlex.quote(HELPER_TARGET)} {shlex.quote(op)} {shlex.quote(args.service_dir)}"
    )
    record = wsta20.ssh_exec(args, run_dir, command, timeout=timeout_sec + args.ssh_connect_timeout + 20)
    record["parsed"] = parse_kv(record.get("stdout", ""))
    return record


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("native_v3385"):
        return "wsta22-blocked-v3385-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta22-blocked-native-health"
    if not checks.get("materialization_admin_up"):
        return "wsta22-blocked-materialization"
    if not checks.get("native_scan_ready"):
        return "wsta22-blocked-native-scan-precheck"
    if not checks.get("debian_ssh_marker"):
        return "wsta22-blocked-debian-chroot-ssh"
    if not checks.get("helper_staged"):
        return "wsta22-blocked-helper-stage"
    if not checks.get("service_start_pass"):
        return "wsta22-blocked-service-start"
    if not checks.get("helper_status_pass"):
        return "wsta22-blocked-helper-status"
    if not checks.get("helper_scan_pass"):
        return "wsta22-blocked-helper-scan"
    if not checks.get("service_stop_pass"):
        return "wsta22-blocked-service-stop"
    if not checks.get("helper_cleanup_ok"):
        return "wsta22-blocked-helper-cleanup"
    if not checks.get("cleanup_ok"):
        return "wsta22-blocked-cleanup"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta22-native-wifi-service-client-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta22_result.json"

    result: dict[str, Any] = {
        "scope": "WSTA22 native-owned Wi-Fi service client live gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "candidate": {
            "version": wsta20.V3385_VERSION,
            "build": wsta20.V3385_BUILD,
            "boot_image": rel(wsta20.V3385_BOOT_IMAGE),
            "sha256": wsta20.V3385_SHA256,
        },
        "helper": {
            "source": rel(HELPER_SOURCE),
            "target": HELPER_TARGET,
        },
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "service_dir": args.service_dir,
        "service_dir_native": args.mountpoint.rstrip("/") + "/" + args.service_dir.lstrip("/"),
        "safety": {
            "boot_flash": bool(args.flash_v3385),
            "flash_helper": rel(wsta2.FLASH_HELPER),
            "switch_root": False,
            "userdata_touch": False,
            "wifi_association": False,
            "dhcp": False,
            "ping": False,
            "public_tunnel": False,
            "temporary_key_only": True,
            "service_supported_ops": ["status", "scan"],
        },
    }
    write_json(out_path, result)

    if args.flash_v3385 and not wsta20.flash_v3385(args, result):
        write_json(out_path, result)
        return result
    write_json(out_path, result)

    local_sha = d1.sha256_file(args.local_image)
    result["local_image"] = rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta22-blocked-local-image-sha"
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
    if not wsta20.native_is_v3385(version.get("text", "")):
        result["decision"] = "wsta22-blocked-v3385-not-resident"
        write_json(out_path, result)
        return result

    wsta19.run_materialization_preflight(args, result, out_path)
    pre_scan = wsta19.run_scan_window_until_bss(
        args,
        result,
        out_path,
        "native_pre_service_scan_window",
        args.scan_attempts,
    )
    native_scan_ready = scan_window_has_bss(pre_scan)
    if not native_scan_ready and args.recover_iftype_probe_on_scan_fail:
        timeout = max(args.timeout, (args.probe_timeout_ms / 1000.0) + 30.0)
        result["scan_recovery_iftype_probe"] = wsta19.try_cmdv1_retry(
            args,
            ["wifi", "softap", "iftype-probe", str(args.probe_timeout_ms)],
            timeout=timeout,
            attempts=1,
        )
        write_json(out_path, result)
        recovery_scan = wsta19.run_scan_window_until_bss(
            args,
            result,
            out_path,
            "native_post_recovery_scan_window",
            args.scan_attempts,
        )
        native_scan_ready = scan_window_has_bss(recovery_scan)
    if not native_scan_ready and args.reboot_on_native_scan_fail:
        result["materialization_preflight_before_reboot"] = result.get("materialization_preflight")
        result["native_reboot_recovery"] = native_reboot_recovery(args, "native-scan-precheck-failed")
        write_json(out_path, result)
        if result["native_reboot_recovery"].get("ok"):
            version = result["native_reboot_recovery"]["version"]
            selftest = result["native_reboot_recovery"]["selftest"]
            status = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
            contract = wsta19.try_cmdv1_retry(args, ["server-distro", "hardware-contract"], timeout=args.timeout)
            result.update({
                "version": version,
                "status": status,
                "baseline_selftest": selftest,
                "hardware_contract": contract,
            })
            wsta19.run_materialization_preflight(args, result, out_path)
            reboot_scan = wsta19.run_scan_window_until_bss(
                args,
                result,
                out_path,
                "native_post_reboot_scan_window",
                args.scan_attempts,
            )
            native_scan_ready = scan_window_has_bss(reboot_scan)
            result["native_scan_ready_source"] = "post-reboot-scan" if native_scan_ready else "none"
        else:
            result["native_scan_ready_source"] = "none"
    elif native_scan_ready:
        result["native_scan_ready_source"] = "pre-service-scan"
    result["native_scan_ready"] = native_scan_ready
    write_json(out_path, result)
    if not native_scan_ready:
        result["decision"] = "wsta22-blocked-native-scan-precheck"
        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
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
        result["decision"] = "wsta22-blocked-remote-image-sha"
        write_json(out_path, result)
        return result
    write_json(out_path, result)

    keygen_record = d2.generate_ssh_key(run_dir, run_id)
    public_key = d2.read_public_key(run_dir)
    result["keygen"] = keygen_record
    write_json(out_path, result)

    service_started = False
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
            result["decision"] = "wsta22-blocked-chroot-mount"
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
            result["decision"] = "wsta22-blocked-dropbear-start"
            return result

        ssh_record = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh"] = ssh_record
        result["ssh_parse"] = ssh_record.get("marker", {})
        write_json(out_path, result)

        result["helper_stage"] = stage_helper(args, run_dir)
        write_json(out_path, result)
        if not result["helper_stage"].get("staged"):
            result["decision"] = "wsta22-blocked-helper-stage"
            return result

        native_service_dir = result["service_dir_native"]
        result["service_start"] = wsta19.try_cmdv1_retry(
            args,
            [
                "wifi",
                "service",
                "start",
                native_service_dir,
                str(args.service_lifetime_ms),
                str(args.service_poll_ms),
                str(args.scan_delay_ms),
            ],
            timeout=args.timeout,
            attempts=1,
        )
        service_started = "wifi-service-start-pass" in result["service_start"].get("text", "")
        write_json(out_path, result)
        if not service_started:
            result["decision"] = "wsta22-blocked-service-start"
            return result

        result["helper_status"] = run_helper(
            args,
            run_dir,
            "status",
            timeout_sec=args.response_timeout_sec,
        )
        write_json(out_path, result)
        result["helper_scan"] = run_helper(
            args,
            run_dir,
            "scan",
            timeout_sec=max(args.response_timeout_sec, int(args.scan_delay_ms / 1000) + 45),
        )
        write_json(out_path, result)
    finally:
        if service_started:
            result["service_stop"] = wsta19.try_cmdv1_retry(
                args,
                ["wifi", "service", "stop", result["service_dir_native"]],
                timeout=args.timeout,
                attempts=1,
            )
        else:
            result["service_stop"] = {"skipped": True, "reason": "service-not-started"}
        if result.get("helper_stage"):
            try:
                result["helper_cleanup"] = cleanup_helper(args, run_dir)
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
    helper_scan = result.get("helper_scan", {}).get("parsed", {})
    result["checks"] = {
        "native_v3385": wsta20.native_is_v3385(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest.get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(contract.get("text", "")),
        "materialization_admin_up": bool(result.get("materialization_preflight", {}).get("after_wlan0_admin_up")),
        "native_scan_ready": bool(result.get("native_scan_ready")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "helper_staged": bool(result.get("helper_stage", {}).get("staged")),
        "helper_cleanup_ok": bool(result.get("helper_cleanup", {}).get("cleaned")),
        "service_start_pass": service_started,
        "helper_status_pass": helper_status_ok(helper_status),
        "helper_scan_pass": helper_scan_ok(helper_scan),
        "service_stop_pass": "wifi-service-stop-pass" in str(result.get("service_stop", {}).get("text", "")),
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
        "final_v3385": wsta20.native_is_v3385(final_version.get("text", "")),
        "final_selftest_fail_zero": wsta2.selftest_passed(final_selftest.get("text", "")),
    }
    result["decision"] = classify(result)
    write_json(out_path, result)
    if args.rollback_on_failed_health and args.flash_v3385 and result["decision"] != PASS_DECISION:
        wsta20.rollback_v2321(args, result, result["decision"])
        write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--flash-timeout", type=float, default=300.0)
    parser.add_argument("--flash-bridge-timeout", type=float, default=180.0)
    parser.add_argument("--flash-reboot-timeout", type=float, default=180.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=90.0)
    parser.add_argument("--ssh-timeout", type=float, default=30.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--bridge-restart-timeout", type=float, default=45.0)
    parser.add_argument("--warm-reboot-command-timeout", type=float, default=15.0)
    parser.add_argument("--warm-reboot-total-timeout", type=float, default=180.0)
    parser.add_argument("--warm-reboot-poll-sec", type=float, default=5.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-service")
    parser.add_argument("--service-lifetime-ms", type=int, default=90000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--scan-delay-ms", type=int, default=5000)
    parser.add_argument("--scan-attempts", type=int, default=2)
    parser.add_argument("--scan-interval-sec", type=float, default=3.0)
    parser.add_argument("--scan-slack-sec", type=float, default=20.0)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--probe-timeout-ms", type=int, default=220000)
    parser.add_argument("--preflight-iftype-probe", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--recover-iftype-probe-on-scan-fail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-on-native-scan-fail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--flash-v3385", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--rollback-on-failed-health", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001 - preserve partial evidence for operator handoff.
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta22-native-wifi-service-client-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "scope": "WSTA22 native-owned Wi-Fi service client live gate",
            "decision": "wsta22-runner-error",
            "error": str(exc),
            "run_dir": rel(run_dir),
        }
        write_json(run_dir / "wsta22_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
