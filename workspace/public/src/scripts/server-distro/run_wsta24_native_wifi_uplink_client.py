#!/usr/bin/env python3
"""Run WSTA24 native-owned Wi-Fi uplink client live gate.

WSTA24 proves the Debian-side ``a90-native-wifi-uplink-client`` against the
V3387 native-owned uplink-service boundary:

  * require resident V3387 and clean selftest,
  * mount the SD-backed Debian image as a chroot and start key-only dropbear,
  * stage the current Debian helper into the mounted chroot,
  * start native ``wifi uplink-service`` in the chroot-visible service dir,
  * run helper ``status`` and ``autoconnect-no-confirm`` from Debian,
  * stop the service, clean up chroot/dropbear/loop state, and health-check.

The runner never flashes, never touches userdata, never supplies the uplink
confirm token, and never starts association/DHCP/ping/public tunnel work.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
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
import run_wsta22_native_wifi_service_client as wsta22  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
HELPER_SOURCE = SCRIPT_DIR / "a90_native_wifi_uplink_client.sh"
HELPER_TARGET = "/usr/local/bin/a90-native-wifi-uplink-client"
UPLINK_SERVICE_VERSION = "a90-native-wifi-uplink-service-v1"
V3387_VERSION = "0.11.143"
V3387_BUILD = "v3387-wifi-uplink-service-redacted"
V3388_VERSION = "0.11.144"
V3388_BUILD = "v3388-wifi-autoconnect-scan-recovery"
V3389_VERSION = "0.11.145"
V3389_BUILD = "v3389-wifi-connect-carrier-diagnostics"
V3390_VERSION = "0.11.146"
V3390_BUILD = "v3390-wifi-cache-enospc-fallback"
V3391_VERSION = "0.11.147"
V3391_BUILD = "v3391-wifi-wpa-handshake-diagnostics"
V3392_VERSION = "0.11.148"
V3392_BUILD = "v3392-wifi-tmp-ctrl-dir"
V3393_VERSION = "0.11.149"
V3393_BUILD = "v3393-wifi-ctrl-socket-unique"
V3394_VERSION = "0.11.150"
V3394_BUILD = "v3394-wifi-wpa-failure-detail"
SUPPORTED_UPLINK_NATIVE_BUILDS = (
    {"version": V3387_VERSION, "build": V3387_BUILD},
    {"version": V3388_VERSION, "build": V3388_BUILD},
    {"version": V3389_VERSION, "build": V3389_BUILD},
    {"version": V3390_VERSION, "build": V3390_BUILD},
    {"version": V3391_VERSION, "build": V3391_BUILD},
    {"version": V3392_VERSION, "build": V3392_BUILD},
    {"version": V3393_VERSION, "build": V3393_BUILD},
    {"version": V3394_VERSION, "build": V3394_BUILD},
)
PASS_DECISION = "wsta24-native-wifi-uplink-client-pass"
DEFAULT_DEVICE_IP = os.environ.get("A90_DEVICE_IP") or ".".join(("192", "168", "7", "2"))


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def rel(path: Path) -> str:
    return wsta2.rel(path)


def native_is_v3387(text: str) -> bool:
    return any(item["version"] in text and item["build"] in text for item in SUPPORTED_UPLINK_NATIVE_BUILDS)


def parse_kv(text: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("A90WSTA24_") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def ssh_exec_input(args: argparse.Namespace,
                   run_dir: Path,
                   remote_command: str,
                   *,
                   input_text: str,
                   timeout: float) -> dict[str, Any]:
    return wsta22.ssh_exec_input(args, run_dir, remote_command, input_text=input_text, timeout=timeout)


def stage_helper(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    helper_text = HELPER_SOURCE.read_text(encoding="utf-8")
    remote = shlex.quote(HELPER_TARGET)
    backup = shlex.quote(HELPER_TARGET + ".wsta24.bak")
    command = (
        "set -eu; "
        f"STATE=/tmp/a90_wsta24_helper_state; TARGET={remote}; BACKUP={backup}; "
        "rm -f \"$BACKUP\" \"$STATE\"; "
        f"/bin/mkdir -p {shlex.quote(str(Path(HELPER_TARGET).parent))} && "
        "if [ -f \"$TARGET\" ]; then /bin/cp \"$TARGET\" \"$BACKUP\"; echo present > \"$STATE\"; "
        "else echo absent > \"$STATE\"; fi; "
        f"/bin/cat > {remote} && "
        f"/bin/chmod 755 {remote} && "
        f"/bin/grep -q 'native_wifi_uplink_client_secret_values_logged=0' {remote} && "
        "echo A90WSTA24_HELPER_STAGED"
    )
    record = ssh_exec_input(args, run_dir, command, input_text=helper_text, timeout=args.ssh_timeout)
    record["staged"] = record["returncode"] == 0 and "A90WSTA24_HELPER_STAGED" in record.get("stdout", "")
    record["helper_target"] = HELPER_TARGET
    return record


def cleanup_helper(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    remote = shlex.quote(HELPER_TARGET)
    backup = shlex.quote(HELPER_TARGET + ".wsta24.bak")
    command = (
        "set +e; "
        f"STATE=/tmp/a90_wsta24_helper_state; TARGET={remote}; BACKUP={backup}; "
        "if [ -f \"$STATE\" ] && /bin/grep -q '^present$' \"$STATE\"; then "
        "/bin/mv \"$BACKUP\" \"$TARGET\" && /bin/chmod 755 \"$TARGET\" && echo A90WSTA24_HELPER_RESTORED; "
        "else /bin/rm -f \"$TARGET\" \"$BACKUP\" && echo A90WSTA24_HELPER_REMOVED; fi; "
        "/bin/rm -f \"$STATE\"; "
        "echo A90WSTA24_HELPER_CLEANED"
    )
    record = wsta20.ssh_exec(args, run_dir, command, timeout=args.ssh_timeout)
    stdout = record.get("stdout", "")
    record["cleaned"] = record.get("returncode") == 0 and "A90WSTA24_HELPER_CLEANED" in stdout
    record["restored"] = "A90WSTA24_HELPER_RESTORED" in stdout
    record["removed"] = "A90WSTA24_HELPER_REMOVED" in stdout
    return record


def run_helper(args: argparse.Namespace,
               run_dir: Path,
               op: str,
               *,
               timeout_sec: int) -> dict[str, Any]:
    command = (
        f"A90_NATIVE_WIFI_UPLINK_SERVICE_TIMEOUT_SEC={int(timeout_sec)} "
        f"{shlex.quote(HELPER_TARGET)} {shlex.quote(op)} {shlex.quote(args.service_dir)}"
    )
    record = wsta20.ssh_exec(args, run_dir, command, timeout=timeout_sec + args.ssh_connect_timeout + 20)
    record["parsed"] = parse_kv(record.get("stdout", ""))
    return record


def helper_status_ok(payload: dict[str, str]) -> bool:
    return (
        payload.get("native_wifi_uplink_client_decision") == "native-wifi-uplink-client-pass"
        and payload.get("native_wifi_uplink_client_secret_values_logged") == "0"
        and payload.get("version") == UPLINK_SERVICE_VERSION
        and payload.get("op") == "status"
        and payload.get("owner") == "native-init"
        and payload.get("decision") == "wifi-uplink-service-status-pass"
        and payload.get("credentials") == "0"
        and payload.get("connect") == "0"
        and payload.get("dhcp_routing") == "observed-only"
        and payload.get("public_tunnel") == "0"
        and payload.get("secret_values_logged") == "0"
        and "profile" not in payload
    )


def helper_no_confirm_ok(payload: dict[str, str]) -> bool:
    return (
        payload.get("native_wifi_uplink_client_decision") == "native-wifi-uplink-client-pass"
        and payload.get("native_wifi_uplink_client_requested_op") == "autoconnect-no-confirm"
        and payload.get("native_wifi_uplink_client_secret_values_logged") == "0"
        and payload.get("version") == UPLINK_SERVICE_VERSION
        and payload.get("op") == "autoconnect"
        and payload.get("owner") == "native-init"
        and payload.get("credentials") == "private-config-gated"
        and payload.get("connect") == "confirm-gated"
        and payload.get("dhcp_routing") == "config-gated"
        and payload.get("external_ping_execution") == "0"
        and payload.get("public_tunnel") == "0"
        and payload.get("secret_values_logged") == "0"
        and payload.get("rc") == "-13"
        and payload.get("decision") == "wifi-uplink-service-confirm-required"
    )


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("native_v3387"):
        return "wsta24-blocked-v3387-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta24-blocked-native-health"
    if not checks.get("debian_ssh_marker"):
        return "wsta24-blocked-debian-chroot-ssh"
    if not checks.get("helper_staged"):
        return "wsta24-blocked-helper-stage"
    if not checks.get("service_start_pass"):
        return "wsta24-blocked-service-start"
    if not checks.get("helper_status_pass"):
        return "wsta24-blocked-helper-status"
    if not checks.get("helper_no_confirm_pass"):
        return "wsta24-blocked-helper-no-confirm"
    if not checks.get("service_stop_pass"):
        return "wsta24-blocked-service-stop"
    if not checks.get("helper_cleanup_ok"):
        return "wsta24-blocked-helper-cleanup"
    if not checks.get("cleanup_ok"):
        return "wsta24-blocked-cleanup"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta24-native-wifi-uplink-client-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta24_result.json"

    result: dict[str, Any] = {
        "scope": "WSTA24 native-owned Wi-Fi uplink client live gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "resident_required": {
            "version": V3387_VERSION,
            "build": V3387_BUILD,
            "supported": SUPPORTED_UPLINK_NATIVE_BUILDS,
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
            "boot_flash": False,
            "switch_root": False,
            "userdata_touch": False,
            "wifi_association": False,
            "confirm_token_supplied": False,
            "dhcp": False,
            "ping": False,
            "public_tunnel": False,
            "temporary_key_only": True,
            "helper_supported_ops": ["status", "autoconnect-no-confirm"],
        },
    }
    write_json(out_path, result)

    local_sha = d1.sha256_file(args.local_image)
    result["local_image"] = rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta24-blocked-local-image-sha"
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
    if not native_is_v3387(version.get("text", "")):
        result["decision"] = "wsta24-blocked-v3387-not-resident"
        write_json(out_path, result)
        return result
    if not wsta2.selftest_passed(selftest.get("text", "")):
        result["decision"] = "wsta24-blocked-native-health"
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
        result["decision"] = "wsta24-blocked-remote-image-sha"
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
            result["decision"] = "wsta24-blocked-chroot-mount"
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
            result["decision"] = "wsta24-blocked-dropbear-start"
            return result

        ssh_record = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh"] = ssh_record
        result["ssh_parse"] = ssh_record.get("marker", {})
        write_json(out_path, result)

        result["helper_stage"] = stage_helper(args, run_dir)
        write_json(out_path, result)
        if not result["helper_stage"].get("staged"):
            result["decision"] = "wsta24-blocked-helper-stage"
            return result

        native_service_dir = result["service_dir_native"]
        result["service_start"] = wsta19.try_cmdv1_retry(
            args,
            [
                "wifi",
                "uplink-service",
                "start",
                native_service_dir,
                str(args.service_lifetime_ms),
                str(args.service_poll_ms),
            ],
            timeout=args.timeout,
            attempts=1,
        )
        service_started = "wifi-uplink-service-start-pass" in result["service_start"].get("text", "")
        write_json(out_path, result)
        if not service_started:
            result["decision"] = "wsta24-blocked-service-start"
            return result

        result["helper_status"] = run_helper(
            args,
            run_dir,
            "status",
            timeout_sec=args.response_timeout_sec,
        )
        write_json(out_path, result)
        result["helper_no_confirm"] = run_helper(
            args,
            run_dir,
            "autoconnect-no-confirm",
            timeout_sec=args.response_timeout_sec,
        )
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
    helper_no_confirm = result.get("helper_no_confirm", {}).get("parsed", {})
    result["checks"] = {
        "native_v3387": native_is_v3387(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest.get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(contract.get("text", "")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "helper_staged": bool(result.get("helper_stage", {}).get("staged")),
        "helper_cleanup_ok": bool(result.get("helper_cleanup", {}).get("cleaned")),
        "service_start_pass": service_started,
        "helper_status_pass": helper_status_ok(helper_status),
        "helper_no_confirm_pass": helper_no_confirm_ok(helper_no_confirm),
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
        "final_v3387": native_is_v3387(final_version.get("text", "")),
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
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
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
    parser.add_argument("--service-lifetime-ms", type=int, default=90000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001 - preserve partial evidence for operator handoff.
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta24-native-wifi-uplink-client-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "scope": "WSTA24 native-owned Wi-Fi uplink client live gate",
            "decision": "wsta24-runner-error",
            "error": str(exc),
            "run_dir": rel(run_dir),
        }
        write_json(run_dir / "wsta24_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
