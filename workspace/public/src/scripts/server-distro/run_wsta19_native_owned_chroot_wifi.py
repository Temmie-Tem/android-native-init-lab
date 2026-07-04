#!/usr/bin/env python3
"""Run WSTA19 native-owned Wi-Fi with Debian chroot proof.

WSTA18 showed full ``switch_root`` tears down the WCNSS/WMI control plane.
WSTA19 validates the low-risk ownership model instead:

  * keep native PID1 and vendor WLAN control-plane alive,
  * prove native STA-only scan visibility before Debian starts,
  * mount the SD-backed Debian image as a chroot and start key-only dropbear,
  * prove host SSH reaches Debian userspace over USB/NCM,
  * prove native ``wifi scan`` still works while Debian chroot is active,
  * clean up the chroot/dropbear/loop state and leave native selftest clean.

The runner never flashes, never touches userdata, never starts public tunnel work, and
never uses Wi-Fi credentials.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90ctl  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta15_handoff_scan_boundary as wsta15  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def try_cmdv1_retry(args: argparse.Namespace,
                    command: list[str],
                    *,
                    timeout: float | None = None,
                    attempts: int = 2) -> dict[str, Any]:
    return wsta15.try_cmdv1_retry(args, command, timeout=timeout, attempts=attempts)


def bridge_shell(args: argparse.Namespace,
                 script: str,
                 *,
                 timeout: float,
                 allow_error: bool = False) -> dict[str, Any]:
    return d1.run_shell(
        args.bridge_host,
        args.bridge_port,
        timeout,
        script,
        allow_error=allow_error,
    )


def remote_sha(args: argparse.Namespace, remote_image: str) -> tuple[str | None, dict[str, Any]]:
    return d1.remote_image_sha(args.bridge_host, args.bridge_port, args.sha_timeout, remote_image)


def install_image(args: argparse.Namespace, local_sha: str) -> dict[str, Any]:
    # d1.install_image expects the historical host/port field names.
    args.host = args.bridge_host
    args.port = args.bridge_port
    return d1.install_image(args, local_sha)


def ssh_chroot_marker(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    return d2.run_host_ssh(args, run_dir)


def parse_scan_window(result: dict[str, Any], label: str) -> dict[str, Any]:
    return result.get(label, {}).get("best", {})


def wifi_status_admin_up(record: dict[str, Any]) -> bool:
    return bool(record.get("transport_ok") and wsta2.wlan0_admin_up(record.get("text", "")))


def run_materialization_preflight(args: argparse.Namespace,
                                  result: dict[str, Any],
                                  out_path: Path) -> dict[str, Any]:
    status_before = try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
    preflight: dict[str, Any] = {
        "scope": "WSTA2 native wlan0 materialization preflight",
        "wifi_status_before": status_before,
        "before_wlan0_present": wsta2.wlan0_present(status_before.get("text", "")),
        "before_wlan0_admin_up": wifi_status_admin_up(status_before),
        "iftype_probe_requested": False,
    }
    result["materialization_preflight"] = preflight
    write_json(out_path, result)

    if args.preflight_iftype_probe and not preflight["before_wlan0_admin_up"]:
        timeout = max(args.timeout, (args.probe_timeout_ms / 1000.0) + 30.0)
        preflight["iftype_probe_requested"] = True
        preflight["iftype_probe"] = try_cmdv1_retry(
            args,
            ["wifi", "softap", "iftype-probe", str(args.probe_timeout_ms)],
            timeout=timeout,
            attempts=1,
        )
        write_json(out_path, result)

    status_after = try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
    preflight["wifi_status_after"] = status_after
    preflight["after_wlan0_present"] = wsta2.wlan0_present(status_after.get("text", ""))
    preflight["after_wlan0_admin_up"] = wifi_status_admin_up(status_after)
    preflight["decision"] = (
        "wsta19-materialization-preflight-pass"
        if preflight["after_wlan0_admin_up"]
        else "wsta19-materialization-preflight-not-admin-up"
    )
    write_json(out_path, result)
    return preflight


def run_scan_window_until_bss(args: argparse.Namespace,
                              result: dict[str, Any],
                              out_path: Path,
                              label: str,
                              attempts: int) -> dict[str, Any]:
    window: dict[str, Any] = {
        "label": label,
        "scan_delay_ms": args.scan_delay_ms,
        "attempts_requested": attempts,
        "attempt_interval_sec": args.scan_interval_sec,
        "attempts": [],
        "stop_condition": "scan_has_bss",
    }
    result[label] = window
    write_json(out_path, result)

    for attempt in range(1, attempts + 1):
        record = wsta15.run_scan_attempt(args, label, attempt)
        window["attempts"].append(record)
        window["best"] = wsta15.best_scan(window["attempts"])
        write_json(out_path, result)
        if record["scan_summary"]["scan_has_bss"]:
            break
        if attempt < attempts:
            time.sleep(args.scan_interval_sec)

    window["attempts_completed"] = len(window["attempts"])
    window["best"] = wsta15.best_scan(window["attempts"])
    write_json(out_path, result)
    return window


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("native_v3384"):
        return "wsta19-blocked-v3384-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta19-blocked-native-health"
    if not checks.get("pre_scan_has_bss"):
        return "wsta19-blocked-native-pre-scan"
    if not checks.get("debian_ssh_marker"):
        return "wsta19-blocked-debian-chroot-ssh"
    if not checks.get("during_scan_has_bss"):
        return "wsta19-blocked-native-scan-under-chroot"
    if not checks.get("cleanup_ok"):
        return "wsta19-blocked-cleanup"
    return "wsta19-native-owned-chroot-wifi-boundary-pass"


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta19-native-owned-chroot-wifi-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta19_result.json"

    result: dict[str, Any] = {
        "scope": "WSTA19 native-owned Wi-Fi plus Debian chroot boundary",
        "started_utc": ts,
        "run_dir": wsta2.rel(run_dir),
        "resident_required": {
            "version": wsta2.V3384_VERSION,
            "build": wsta2.V3384_BUILD,
        },
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "ssh_port": args.ssh_port,
        "safety": {
            "boot_flash": False,
            "switch_root": False,
            "userdata_touch": False,
            "no_wifi_association": True,
            "no_dhcp": True,
            "no_ping": True,
            "no_public_tunnel": True,
            "temporary_key_only": True,
        },
    }
    write_json(out_path, result)

    local_sha = d1.sha256_file(args.local_image)
    result["local_image"] = wsta2.rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta19-blocked-local-image-sha"
        write_json(out_path, result)
        return result

    result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
    version = try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    status = try_cmdv1_retry(args, ["status"], timeout=args.timeout)
    selftest = try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    contract = try_cmdv1_retry(args, ["server-distro", "hardware-contract"], timeout=args.timeout)
    result.update({
        "version": version,
        "status": status,
        "baseline_selftest": selftest,
        "hardware_contract": contract,
    })
    write_json(out_path, result)

    run_materialization_preflight(args, result, out_path)
    run_scan_window_until_bss(args, result, out_path, "native_pre_chroot_scan_window", args.sta_scan_attempts)

    before_sha, before_record = remote_sha(args, args.remote_image)
    result["remote_sha_before"] = before_record
    result["remote_sha_before_value"] = before_sha
    if before_sha != local_sha:
        result["install"] = install_image(args, local_sha)
    after_sha, after_record = remote_sha(args, args.remote_image)
    result["remote_sha_after"] = after_record
    result["remote_sha_after_value"] = after_sha
    if after_sha != local_sha:
        result["decision"] = "wsta19-blocked-remote-image-sha"
        write_json(out_path, result)
        return result
    write_json(out_path, result)

    keygen_record = d2.generate_ssh_key(run_dir, run_id)
    public_key = d2.read_public_key(run_dir)
    result["keygen"] = keygen_record
    write_json(out_path, result)

    cleanup_record: dict[str, Any] | None = None
    postcheck_record: dict[str, Any] | None = None
    try:
        mount_record = bridge_shell(
            args,
            d2.d2_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["mount_parse"].get(key) for key in ("mount_ready", "mounted")):
            result["decision"] = "wsta19-blocked-chroot-mount"
            return result

        start_record = bridge_shell(
            args,
            d2.d2_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["dropbear_parse"].get(key) for key in ("started", "authorized_keys", "shadow_temp_key_only")):
            result["decision"] = "wsta19-blocked-dropbear-start"
            return result

        ssh_record = ssh_chroot_marker(args, run_dir)
        result["ssh"] = ssh_record
        result["ssh_parse"] = ssh_record.get("marker", {})
        write_json(out_path, result)

        run_scan_window_until_bss(
            args,
            result,
            out_path,
            "native_during_chroot_scan_window",
            args.during_scan_attempts,
        )
    finally:
        cleanup_record = bridge_shell(
            args,
            d2.d2_cleanup_script(args.mountpoint),
            timeout=args.cleanup_timeout,
            allow_error=True,
        )
        result["cleanup"] = cleanup_record
        result["cleanup_parse"] = d2.parse_cleanup(str(cleanup_record.get("text") or ""))
        write_json(out_path, result)

        postcheck_record = bridge_shell(
            args,
            d2.d2_postcheck_script(args.mountpoint),
            timeout=args.cleanup_timeout,
            allow_error=True,
        )
        result["postcheck"] = postcheck_record
        result["postcheck_parse"] = d2.parse_postcheck(str(postcheck_record.get("text") or ""))
        write_json(out_path, result)

    final_version = try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    final_selftest = try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    result["final_version"] = final_version
    result["final_selftest"] = final_selftest

    pre_scan = parse_scan_window(result, "native_pre_chroot_scan_window")
    during_scan = parse_scan_window(result, "native_during_chroot_scan_window")
    cleanup = result.get("cleanup_parse", {})
    postcheck = result.get("postcheck_parse", {})
    result["checks"] = {
        "native_v3384": wsta2.native_is_v3384(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest.get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(contract.get("text", "")),
        "materialization_admin_up": bool(result.get("materialization_preflight", {}).get("after_wlan0_admin_up")),
        "pre_scan_engine_ok": bool(pre_scan.get("scan_engine_ok")),
        "pre_scan_has_bss": bool(pre_scan.get("scan_has_bss")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "during_scan_engine_ok": bool(during_scan.get("scan_engine_ok")),
        "during_scan_has_bss": bool(during_scan.get("scan_has_bss")),
        "cleanup_ok": bool(
            cleanup.get("done")
            and cleanup.get("shadow_restored")
            and cleanup.get("mount_cleanup_ok")
            and cleanup.get("loop_cleanup_ok")
            and postcheck.get("mount_absent")
            and postcheck.get("loop_node_absent")
            and postcheck.get("dropbear_absent")
        ),
        "final_v3384": wsta2.native_is_v3384(final_version.get("text", "")),
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
    parser.add_argument("--device-ip", default="192.168.7.2")
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
    parser.add_argument("--scan-delay-ms", type=int, default=5000)
    parser.add_argument("--scan-slack-sec", type=float, default=20.0)
    parser.add_argument("--scan-interval-sec", type=float, default=10.0)
    parser.add_argument("--sta-scan-attempts", type=int, default=12)
    parser.add_argument("--during-scan-attempts", type=int, default=3)
    parser.add_argument("--probe-timeout-ms", type=int, default=220000)
    parser.add_argument("--preflight-iftype-probe", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001 - preserve partial evidence for operator handoff.
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta19-native-owned-chroot-wifi-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "scope": "WSTA19 native-owned Wi-Fi plus Debian chroot boundary",
            "decision": "wsta19-runner-error",
            "error": str(exc),
            "run_dir": wsta2.rel(run_dir),
        }
        write_json(run_dir / "wsta19_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == "wsta19-native-owned-chroot-wifi-boundary-pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
