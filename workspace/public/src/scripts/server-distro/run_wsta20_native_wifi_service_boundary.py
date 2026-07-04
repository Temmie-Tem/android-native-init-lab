#!/usr/bin/env python3
"""Run WSTA20 native-owned Wi-Fi service-boundary live gate.

WSTA20 keeps native init as the WLAN owner and gives the Debian chroot a small
file request/response boundary:

  * flash the V3385 native-init candidate through the checked helper,
  * health-check V3385 and run the WSTA2 wlan0 materialization preflight,
  * mount the SD-backed Debian image as a chroot and start key-only dropbear,
  * write status/scan requests from Debian into a shared chroot-visible dir,
  * start the native ``wifi service`` worker and verify it writes redacted
    response files as the WLAN owner,
  * stop the service, clean up the chroot/dropbear/loop state, and health-check.

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
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
V3385_BOOT_IMAGE = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v3385_wifi_service_boundary.img"
)
V3385_SHA256 = "33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710"
V3385_VERSION = "0.11.141"
V3385_BUILD = "v3385-wifi-service-boundary"
ROLLBACK_VERSION = "0.9.285"
SERVICE_VERSION = "a90-native-wifi-service-v1"
PASS_DECISION = "wsta20-native-wifi-service-boundary-pass"


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def native_is_v3385(text: str) -> bool:
    return V3385_VERSION in text and V3385_BUILD in text


def rel(path: Path) -> str:
    return wsta2.rel(path)


def flash_command(args: argparse.Namespace,
                  image: Path,
                  sha256: str,
                  version: str,
                  *,
                  from_native: bool) -> list[str]:
    command = [
        sys.executable,
        str(wsta2.FLASH_HELPER),
        str(image),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--expect-version",
        version,
        "--expect-sha256",
        sha256,
        "--verify-protocol",
        "cmdv1",
        "--reboot-timeout",
        str(args.flash_reboot_timeout),
        "--bridge-timeout",
        str(args.flash_bridge_timeout),
    ]
    if from_native:
        command.append("--from-native")
    return command


def flash_v3385(args: argparse.Namespace, result: dict[str, Any]) -> bool:
    rollback = wsta2.verify_rollback_images()
    result["rollback_images"] = rollback
    if not rollback["ok"]:
        result["decision"] = "wsta20-blocked-rollback-image-precondition"
        return False

    image_state = {"path": rel(V3385_BOOT_IMAGE), "exists": V3385_BOOT_IMAGE.is_file()}
    if V3385_BOOT_IMAGE.is_file():
        image_state["sha256"] = wsta2.sha256_file(V3385_BOOT_IMAGE)
        image_state["sha256_ok"] = image_state["sha256"] == V3385_SHA256
    result["v3385_image"] = image_state
    if not image_state.get("sha256_ok"):
        result["decision"] = "wsta20-blocked-v3385-image-precondition"
        return False

    recovery = wsta2.adb_recovery_available(args.adb)
    native = wsta2.try_cmdv1(args, ["version"], timeout=args.timeout)
    result["preflash_recovery_adb_available"] = recovery
    result["preflash_native_version_probe"] = native
    if not recovery and not native.get("transport_ok"):
        result["decision"] = "wsta20-blocked-no-native-cmdv1-or-recovery-adb"
        return False

    record = wsta2.run_host(
        flash_command(args, V3385_BOOT_IMAGE, V3385_SHA256, V3385_VERSION, from_native=not recovery),
        timeout=args.flash_timeout,
    )
    result["candidate_flash"] = record
    if record["rc"] != 0:
        result["decision"] = "wsta20-blocked-v3385-flash-failed"
        return False
    return True


def rollback_v2321(args: argparse.Namespace, result: dict[str, Any], reason: str) -> None:
    rollback_image, rollback_sha = wsta2.ROLLBACK_IMAGES["v2321"]
    result["rollback_attempt_reason"] = reason
    result["rollback_attempted"] = True
    recovery = wsta2.adb_recovery_available(args.adb)
    native = wsta2.try_cmdv1(args, ["version"], timeout=args.timeout)
    result["rollback_recovery_adb_available"] = recovery
    result["rollback_native_version_probe"] = native
    if not recovery and not native.get("transport_ok"):
        result["rollback_blocked"] = "no-native-cmdv1-or-recovery-adb"
        return
    rollback = wsta2.run_host(
        flash_command(args, rollback_image, rollback_sha or "", ROLLBACK_VERSION, from_native=not recovery),
        timeout=args.flash_timeout,
    )
    result["rollback_flash"] = rollback
    if rollback["rc"] == 0:
        result["rollback_version"] = wsta2.try_cmdv1(args, ["version"], timeout=args.timeout)
        result["rollback_selftest"] = wsta2.try_cmdv1(args, ["selftest"], timeout=args.timeout)
        result["rollback_selftest_fail_zero"] = wsta2.selftest_passed(
            result["rollback_selftest"].get("text", "")
        )


def ssh_exec(args: argparse.Namespace,
             run_dir: Path,
             remote_command: str,
             *,
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


def parse_response(text: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("A90WSTA20_") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def write_request(args: argparse.Namespace,
                  run_dir: Path,
                  *,
                  seq: int,
                  op: str) -> dict[str, Any]:
    service_dir = shlex.quote(args.service_dir)
    script = f"""
set -eu
DIR={service_dir}
/bin/mkdir -p "$DIR"
/bin/rm -f "$DIR/response" "$DIR/response.tmp"
/usr/bin/printf 'seq=%s\\nop=%s\\nscan_delay_ms=%s\\n' {seq} {shlex.quote(op)} {args.scan_delay_ms} > "$DIR/request.tmp"
/bin/mv "$DIR/request.tmp" "$DIR/request"
echo A90WSTA20_REQUEST_WRITTEN
/bin/cat "$DIR/request"
""".strip()
    return ssh_exec(args, run_dir, script, timeout=args.ssh_timeout)


def wait_response(args: argparse.Namespace,
                  run_dir: Path,
                  *,
                  seq: int,
                  timeout_sec: int) -> dict[str, Any]:
    service_dir = shlex.quote(args.service_dir)
    script = f"""
set +e
DIR={service_dir}
RESP="$DIR/response"
i=0
while [ "$i" -lt {timeout_sec} ]; do
  if [ -f "$RESP" ] && /bin/grep -q '^seq={seq}$' "$RESP"; then
    echo A90WSTA20_RESPONSE_READY
    /bin/cat "$RESP"
    exit 0
  fi
  i=$((i + 1))
  /bin/sleep 1
done
echo A90WSTA20_RESPONSE_TIMEOUT
if [ -f "$RESP" ]; then /bin/cat "$RESP"; fi
exit 23
""".strip()
    record = ssh_exec(args, run_dir, script, timeout=timeout_sec + args.ssh_connect_timeout + 10)
    record["response"] = parse_response(record.get("stdout", ""))
    return record


def cleanup_service_dir(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    return ssh_exec(
        args,
        run_dir,
        f"/bin/rm -rf {shlex.quote(args.service_dir)}; echo A90WSTA20_SERVICE_DIR_REMOVED",
        timeout=args.ssh_timeout,
    )


def response_status_ok(response: dict[str, str], seq: int, op: str) -> bool:
    return (
        response.get("version") == SERVICE_VERSION
        and response.get("seq") == str(seq)
        and response.get("op") == op
        and response.get("owner") == "native-init"
        and response.get("decision") == "wifi-service-status-pass"
        and response.get("dhcp_routing") == "0"
        and response.get("public_tunnel") == "0"
    )


def response_scan_ok(response: dict[str, str], seq: int) -> bool:
    try:
        count = int(response.get("scan_result_count", "0"))
    except ValueError:
        count = 0
    return (
        response.get("version") == SERVICE_VERSION
        and response.get("seq") == str(seq)
        and response.get("op") == "scan"
        and response.get("owner") == "native-init"
        and response.get("raw_results_redacted") == "1"
        and response.get("decision") == "wifi-scan-pass"
        and count > 0
    )


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("native_v3385"):
        return "wsta20-blocked-v3385-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta20-blocked-native-health"
    if not checks.get("materialization_admin_up"):
        return "wsta20-blocked-materialization"
    if not checks.get("debian_ssh_marker"):
        return "wsta20-blocked-debian-chroot-ssh"
    if not checks.get("service_start_pass"):
        return "wsta20-blocked-service-start"
    if not checks.get("status_response_pass"):
        return "wsta20-blocked-status-response"
    if not checks.get("scan_response_pass"):
        return "wsta20-blocked-scan-response"
    if not checks.get("service_stop_pass"):
        return "wsta20-blocked-service-stop"
    if not checks.get("cleanup_ok"):
        return "wsta20-blocked-cleanup"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta20-native-wifi-service-boundary-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta20_result.json"

    result: dict[str, Any] = {
        "scope": "WSTA20 native-owned Wi-Fi service boundary",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "candidate": {
            "version": V3385_VERSION,
            "build": V3385_BUILD,
            "boot_image": rel(V3385_BOOT_IMAGE),
            "sha256": V3385_SHA256,
        },
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "service_dir": args.service_dir,
        "service_dir_native": args.mountpoint.rstrip("/") + "/" + args.service_dir.lstrip("/"),
        "safety": {
            "boot_flash": True,
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

    if args.flash_v3385 and not flash_v3385(args, result):
        write_json(out_path, result)
        return result
    write_json(out_path, result)

    local_sha = d1.sha256_file(args.local_image)
    result["local_image"] = rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta20-blocked-local-image-sha"
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
    if not native_is_v3385(version.get("text", "")):
        result["decision"] = "wsta20-blocked-v3385-not-resident"
        write_json(out_path, result)
        return result

    wsta19.run_materialization_preflight(args, result, out_path)

    before_sha, before_record = wsta19.remote_sha(args, args.remote_image)
    result["remote_sha_before"] = before_record
    result["remote_sha_before_value"] = before_sha
    if before_sha != local_sha:
        result["install"] = wsta19.install_image(args, local_sha)
    after_sha, after_record = wsta19.remote_sha(args, args.remote_image)
    result["remote_sha_after"] = after_record
    result["remote_sha_after_value"] = after_sha
    if after_sha != local_sha:
        result["decision"] = "wsta20-blocked-remote-image-sha"
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
            result["decision"] = "wsta20-blocked-chroot-mount"
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
            result["decision"] = "wsta20-blocked-dropbear-start"
            return result

        ssh_record = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh"] = ssh_record
        result["ssh_parse"] = ssh_record.get("marker", {})
        write_json(out_path, result)

        native_service_dir = result["service_dir_native"]
        result["status_request"] = write_request(args, run_dir, seq=1, op="status")
        write_json(out_path, result)

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

        result["status_response"] = wait_response(args, run_dir, seq=1, timeout_sec=args.response_timeout_sec)
        write_json(out_path, result)

        result["scan_request"] = write_request(args, run_dir, seq=2, op="scan")
        write_json(out_path, result)
        result["scan_response"] = wait_response(
            args,
            run_dir,
            seq=2,
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
        try:
            result["service_dir_cleanup"] = cleanup_service_dir(args, run_dir)
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
    status_response = result.get("status_response", {}).get("response", {})
    scan_response = result.get("scan_response", {}).get("response", {})
    result["checks"] = {
        "native_v3385": native_is_v3385(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest.get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(contract.get("text", "")),
        "materialization_admin_up": bool(result.get("materialization_preflight", {}).get("after_wlan0_admin_up")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "service_start_pass": service_started,
        "status_response_pass": response_status_ok(status_response, 1, "status"),
        "scan_response_pass": response_scan_ok(scan_response, 2),
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
        "final_v3385": native_is_v3385(final_version.get("text", "")),
        "final_selftest_fail_zero": wsta2.selftest_passed(final_selftest.get("text", "")),
    }
    result["decision"] = classify(result)
    write_json(out_path, result)
    if args.rollback_on_failed_health and result["decision"] != PASS_DECISION:
        rollback_v2321(args, result, result["decision"])
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
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--probe-timeout-ms", type=int, default=220000)
    parser.add_argument("--preflight-iftype-probe", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--flash-v3385", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--rollback-on-failed-health", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001 - preserve partial evidence for operator handoff.
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta20-native-wifi-service-boundary-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "scope": "WSTA20 native-owned Wi-Fi service boundary",
            "decision": "wsta20-runner-error",
            "error": str(exc),
            "run_dir": rel(run_dir),
        }
        write_json(run_dir / "wsta20_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
