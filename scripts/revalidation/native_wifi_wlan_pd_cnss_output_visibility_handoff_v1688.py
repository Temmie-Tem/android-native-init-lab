#!/usr/bin/env python3
"""V1688 one-run WLAN-PD cnss-daemon output-visibility handoff."""

from __future__ import annotations

import argparse
import json
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_wlan_pd_firmware_serve_handoff_v1675 as fwbase
import tcpctl_host


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1688"
V1687_OUT = REPO_ROOT / "tmp" / "wifi" / "v1687-wlan-pd-cnss-output-visibility-test-boot"
DEFAULT_SOURCE_MANIFEST = V1687_OUT / "manifest.json"
DEFAULT_TEST_IMAGE = V1687_OUT / "boot_linux_v1687_wlan_pd_cnss_output_visibility.img"
LOCAL_PROPERTY_ROOT = V1687_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1687/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1688-wlan-pd-cnss-output-visibility-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1688_WLAN_PD_CNSS_OUTPUT_VISIBILITY_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.123 (v1687-wlan-pd-cnss-output-visibility)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1687.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1687.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1687-helper.result"
DMESG_PATTERN = (
    "A90v1687|wlan_pd_cnss_output_visibility|wlan_pd_firmware_serve_gate|"
    "wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|"
    "wlfw|wlfw_start|wlfw_service_request|icnss|FW ready|BDF|wlan0|"
    "cnss-daemon|4080000.qcom,mss|Brought out of reset|modem: loading"
)
VALID_LABELS = {
    "wlfw-start-reached-downstream-block",
    "cnss-output-still-invisible",
}
VALID_LABEL_RE = re.compile(r"^cnss-init-step-failed-[A-Za-z0-9-]+$")
SAFE_REMOTE_RE = re.compile(r"^[A-Za-z0-9_./:+-]+$")


def display_path(path: Path) -> str:
    return fwbase.display_path(path)


def tcp_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host=args.bridge_host,
        bridge_port=args.bridge_port,
        device_ip=args.device_ip,
        tcp_port=args.tcp_port,
        toybox=args.toybox,
        token=None,
        token_command=args.token_command,
        no_auth=False,
        connect_timeout=5.0,
        tcp_timeout=args.tcp_timeout,
        bridge_timeout=args.bridge_timeout,
        device_protocol="auto",
        busy_retries=3,
        busy_retry_sleep=2.0,
        menu_hide_sleep=1.0,
    )


def tcp_run(targs: argparse.Namespace, argv: list[str], *, timeout: float = 30.0) -> str:
    return tcpctl_host.tcpctl_install_command(
        targs,
        tcpctl_host.tcpctl_run_line(argv),
        timeout=timeout,
    )


def validate_remote_path(path: str) -> None:
    if not path.startswith(REMOTE_PROPERTY_ROOT + "/"):
        raise RuntimeError(f"remote path outside V1687 private property root: {path}")
    if ".." in path or not SAFE_REMOTE_RE.fullmatch(path):
        raise RuntimeError(f"unsafe remote path: {path}")


def local_property_files() -> list[Path]:
    if not LOCAL_PROPERTY_ROOT.exists():
        raise RuntimeError(f"missing local V1687 property root: {LOCAL_PROPERTY_ROOT}")
    return sorted(path for path in LOCAL_PROPERTY_ROOT.iterdir() if path.is_file())


def sha256_file(path: Path) -> str:
    return fwbase.base.local_sha256(path)


def write_transfer_step(store: EvidenceStore,
                        steps: list[dict[str, Any]],
                        name: str,
                        command: list[str],
                        stdout: str,
                        stderr: str,
                        ok: bool,
                        rc: int | None = 0) -> None:
    store.write_text(f"{name}.stdout.txt", stdout)
    store.write_text(f"{name}.stderr.txt", stderr)
    steps.append({
        "command": command,
        "started": "",
        "ended": "",
        "timeout": False,
        "rc": rc,
        "ok": ok,
        "stdout_file": f"{name}.stdout.txt",
        "stderr_file": f"{name}.stderr.txt",
    })


def transfer_file(targs: argparse.Namespace,
                  store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  local_path: Path,
                  remote_path: str,
                  index: int,
                  port: int) -> dict[str, Any]:
    validate_remote_path(remote_path)
    remote_dir = str(Path(remote_path).parent)
    tmp_path = f"{remote_dir}/.{Path(remote_path).name}.tmp.{int(time.time())}.{index}"
    validate_remote_path(tmp_path)
    expected_sha = sha256_file(local_path)
    transfer_output: dict[str, str] = {}
    transfer_error: dict[str, Exception] = {}

    tcp_run(targs, [targs.toybox, "mkdir", "-p", remote_dir], timeout=30.0)
    tcp_run(targs, [targs.toybox, "rm", "-f", tmp_path], timeout=30.0)
    receive_command = tcpctl_host.tcpctl_run_line([
        targs.toybox,
        "netcat",
        "-l",
        "-p",
        str(port),
        targs.toybox,
        "dd",
        f"of={tmp_path}",
        "bs=4096",
    ])

    def receiver() -> None:
        try:
            transfer_output["text"] = tcpctl_host.tcpctl_request(
                targs,
                receive_command,
                timeout=75.0,
            )
        except Exception as exc:  # noqa: BLE001 - evidence keeps failure text
            transfer_error["error"] = exc

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()
    time.sleep(0.5)
    with socket.create_connection((targs.device_ip, port), timeout=5.0) as sock:
        with local_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sock.sendall(chunk)
        sock.shutdown(socket.SHUT_WR)
    thread.join(90.0)
    if thread.is_alive():
        raise RuntimeError(f"transfer did not finish: {remote_path}")
    if transfer_error:
        raise RuntimeError(f"transfer failed for {remote_path}: {transfer_error['error']}")
    transfer_text = transfer_output.get("text", "")
    write_transfer_step(
        store,
        steps,
        f"property-transfer-{index:02d}",
        ["tcpctl", receive_command],
        transfer_text,
        "",
        "\nOK" in transfer_text or transfer_text.rstrip().endswith("OK"),
    )
    sha_text = tcp_run(targs, [targs.toybox, "sha256sum", tmp_path], timeout=30.0)
    if expected_sha not in sha_text:
        raise RuntimeError(f"sha256 mismatch for {remote_path}: expected={expected_sha} output={sha_text}")
    tcp_run(targs, [targs.toybox, "chmod", "444", tmp_path], timeout=30.0)
    tcp_run(targs, [targs.toybox, "mv", "-f", tmp_path, remote_path], timeout=30.0)
    return {
        "local": display_path(local_path),
        "remote": remote_path,
        "sha256": expected_sha,
        "bytes": local_path.stat().st_size,
        "mode": "0444",
    }


def deploy_property_root(args: argparse.Namespace,
                         store: EvidenceStore,
                         steps: list[dict[str, Any]]) -> dict[str, Any]:
    targs = tcp_args(args)
    tcpctl_host.wait_for_tcpctl(targs, args.tcp_ready_timeout)
    files = local_property_files()
    tcp_run(targs, [targs.toybox, "rm", "-rf", REMOTE_PROPERTY_ROOT], timeout=30.0)
    tcp_run(targs, [targs.toybox, "mkdir", "-p", REMOTE_PROPERTY_ROOT], timeout=30.0)
    tcp_run(targs, [targs.toybox, "chmod", "755", "/mnt/sdext/a90/private-property-v317/v1687"], timeout=30.0)
    tcp_run(targs, [targs.toybox, "chmod", "755", "/mnt/sdext/a90/private-property-v317/v1687/dev"], timeout=30.0)
    tcp_run(targs, [targs.toybox, "chmod", "755", REMOTE_PROPERTY_ROOT], timeout=30.0)

    uploaded: list[dict[str, Any]] = []
    for index, local_path in enumerate(files, start=1):
        remote_path = REMOTE_PROPERTY_ROOT + "/" + local_path.name
        uploaded.append(transfer_file(targs, store, steps, local_path, remote_path, index, args.transfer_port + index))
    sha_text = tcp_run(targs, [targs.toybox, "sha256sum", REMOTE_PROPERTY_ROOT + "/property_info"], timeout=30.0)
    vendor_text = tcp_run(targs, [targs.toybox, "sha256sum", REMOTE_PROPERTY_ROOT + "/u:object_r:vendor_default_prop:s0"], timeout=30.0)
    property_info_sha = sha256_file(LOCAL_PROPERTY_ROOT / "property_info")
    vendor_default_sha = sha256_file(LOCAL_PROPERTY_ROOT / "u:object_r:vendor_default_prop:s0")
    return {
        "remote_property_root": REMOTE_PROPERTY_ROOT,
        "file_count": len(uploaded),
        "bytes": sum(item["bytes"] for item in uploaded),
        "uploaded": uploaded,
        "property_info_sha_ok": property_info_sha in sha_text,
        "vendor_default_sha_ok": vendor_default_sha in vendor_text,
    }


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = fwbase.parse_helper_fields(evidence_dir)
    label = helper_fields.get("wlan_pd_cnss_output_visibility.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_cnss_output_visibility.begin") == "1"
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    label_ok = label in VALID_LABELS or VALID_LABEL_RE.fullmatch(label) is not None
    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "label": label,
        "label_ok": label_ok,
        "old_firmware_serve_label": helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        "wlfw_start_seen": helper_fields.get("wlan_pd_cnss_output_visibility.wlfw_start_seen"),
        "first_failure_slug": helper_fields.get("wlan_pd_cnss_output_visibility.first_failure_slug"),
        "syslog_available": helper_fields.get("wlan_pd_cnss_output_visibility.syslog_available"),
        "syslog_errno": helper_fields.get("wlan_pd_cnss_output_visibility.syslog_errno"),
        "syslog_filtered_count": helper_fields.get("wlan_pd_cnss_output_visibility.syslog_filtered_count"),
        "cnss_daemon_running": helper_fields.get("wlan_pd_cnss_output_visibility.cnss_daemon_running"),
        "tftp_running": helper_fields.get("wlan_pd_cnss_output_visibility.tftp_running"),
        "no_service_manager": helper_fields.get("wlan_pd_cnss_output_visibility.no_service_manager"),
        "no_pm_trio": helper_fields.get("wlan_pd_cnss_output_visibility.no_pm_trio"),
        "no_esoc0": helper_fields.get("wlan_pd_cnss_output_visibility.no_esoc0"),
        "no_forced_rc1": helper_fields.get("wlan_pd_cnss_output_visibility.no_forced_rc1"),
        "no_fake_online": helper_fields.get("wlan_pd_cnss_output_visibility.no_fake_online"),
        "no_wifi_hal": helper_fields.get("wlan_pd_cnss_output_visibility.no_wifi_hal"),
        "no_scan_connect": helper_fields.get("wlan_pd_cnss_output_visibility.no_scan_connect"),
        "no_credentials": helper_fields.get("wlan_pd_cnss_output_visibility.no_credentials"),
        "no_dhcp_routes": helper_fields.get("wlan_pd_cnss_output_visibility.no_dhcp_routes"),
        "no_external_ping": helper_fields.get("wlan_pd_cnss_output_visibility.no_external_ping"),
        "companion_order": helper_fields.get("wifi_companion_start.order"),
    }
    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1687 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if not helper_contract_seen:
        return f"{args.cycle.lower()}-cnss-output-contract-missing", False, "helper result did not include cnss output visibility contract", details
    if not label_ok:
        return f"{args.cycle.lower()}-cnss-output-label-missing", False, "helper result did not produce a fixed cnss output visibility label", details
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, "one cnss output visibility gate run produced a fixed label and rollback verified", details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD cnss-daemon Output Visibility Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable WLAN-PD cnss-daemon output-visibility gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- Label: `{gate.get('label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- wlfw_start seen: `{gate.get('wlfw_start_seen')}`",
        f"- first failure slug: `{gate.get('first_failure_slug')}`",
        f"- syslog available: `{gate.get('syslog_available')}`",
        f"- syslog errno: `{gate.get('syslog_errno')}`",
        f"- syslog filtered count: `{gate.get('syslog_filtered_count')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Uploaded files: `{property_deploy.get('file_count')}`",
        f"- Uploaded bytes: `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- service-manager, PM trio, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Stop after this one label.",
        "- If label is `wlfw-start-reached-downstream-block`, classify the blocker as downstream of cnss-daemon entry.",
        "- If label starts with `cnss-init-step-failed-`, classify that named init step before any WLAN-PD/firmware expansion.",
        "- If label is `cnss-output-still-invisible`, inspect property shim/kmsg visibility before adding actors.",
        "",
    ]
    return "\n".join(lines)


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    source_manifest: dict[str, Any] = {}
    if args.source_manifest.exists():
        source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    return {
        "source_manifest": display_path(args.source_manifest),
        "source_manifest_exists": args.source_manifest.exists(),
        "source_manifest_pass": bool(source_manifest.get("pass")),
        "source_decision": source_manifest.get("decision", ""),
        "test_image": display_path(args.test_image),
        "test_image_exists": args.test_image.exists(),
        "test_image_sha256": fwbase.base.local_sha256(args.test_image) if args.test_image.exists() else "",
        "rollback_image": display_path(args.rollback_image),
        "rollback_image_exists": args.rollback_image.exists(),
        "local_property_root": display_path(LOCAL_PROPERTY_ROOT),
        "local_property_root_exists": LOCAL_PROPERTY_ROOT.exists(),
        "remote_property_root": REMOTE_PROPERTY_ROOT,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--rollback-image", type=Path, default=fwbase.ROLLBACK_IMAGE)
    parser.add_argument("--expect-test-version", default=TEST_EXPECT_VERSION)
    parser.add_argument("--expect-rollback-version", default=ROLLBACK_EXPECT_VERSION)
    parser.add_argument("--post-boot-hold-sec", type=float, default=90.0)
    parser.add_argument("--flash-timeout-sec", type=float, default=720.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=150.0)
    parser.add_argument("--bridge-verify-timeout-sec", type=float, default=240.0)
    parser.add_argument("--native-direct-rollback-fallback", action="store_true", default=True)
    parser.add_argument("--native-direct-rollback-remote-image", default="/cache/boot_linux_v724.img")
    parser.add_argument("--native-direct-rollback-boot-block", default="/dev/block/sda24")
    parser.add_argument("--native-direct-rollback-boot-major", type=int, default=259)
    parser.add_argument("--native-direct-rollback-boot-minor", type=int, default=8)
    parser.add_argument("--native-direct-rollback-timeout-sec", type=float, default=120.0)
    parser.add_argument("--bridge-host", default=tcpctl_host.DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=tcpctl_host.DEFAULT_BRIDGE_PORT)
    parser.add_argument("--bridge-timeout", type=float, default=30.0)
    parser.add_argument("--device-ip", default=tcpctl_host.DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=tcpctl_host.DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=20.0)
    parser.add_argument("--tcp-ready-timeout", type=float, default=20.0)
    parser.add_argument("--toybox", default=tcpctl_host.DEFAULT_TOYBOX)
    parser.add_argument("--token-command", default=tcpctl_host.DEFAULT_TOKEN_COMMAND)
    parser.add_argument("--transfer-port", type=int, default=18168)
    args = parser.parse_args(argv)
    args.cycle = CYCLE
    args.test_log_path = TEST_LOG_PATH
    args.test_summary_path = TEST_SUMMARY_PATH
    args.test_helper_result_path = TEST_HELPER_RESULT_PATH
    args.test_rc1_watcher_result_path = ""
    args.test_rc1_window_result_path = ""
    args.test_extra_result_path = []
    args.dmesg_grep_pattern = DMESG_PATTERN
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(args.out_dir)
    steps: list[dict[str, Any]] = []
    pre = preflight(args)
    store.write_json("preflight.json", pre)
    if not pre["source_manifest_pass"] or not pre["test_image_exists"] or not pre["rollback_image_exists"] or not pre["local_property_root_exists"]:
        result = {
            "cycle": args.cycle,
            "decision": f"{args.cycle.lower()}-preflight-blocked",
            "pass": False,
            "reason": "source manifest pass, test image, rollback image, or local property root missing",
            "preflight": pre,
            "steps": steps,
            "out_dir": display_path(args.out_dir),
        }
        store.write_json("manifest.json", result)
        write_private_text(args.report_path, render_report(result))
        print(json.dumps({"decision": result["decision"], "pass": False}, indent=2))
        return 1

    property_deploy: dict[str, Any] = {}
    test_flash: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    rollback_result: dict[str, Any] = {}
    live_error = ""
    try:
        property_deploy = deploy_property_root(args, store, steps)
        store.write_json("property-deploy.json", property_deploy)
        test_flash = fwbase.base.run_command(
            fwbase.base.flash_command(args.test_image, args.expect_test_version, from_native=True),
            timeout=args.flash_timeout_sec,
        )
        fwbase.base.write_step(store, steps, "test-flash-from-native", test_flash)
        if test_flash["ok"]:
            if args.post_boot_hold_sec > 0:
                hold = fwbase.base.run_command(
                    ["python3", "-c", f"import time; time.sleep({args.post_boot_hold_sec!r})"],
                    timeout=args.post_boot_hold_sec + 5.0,
                )
                fwbase.base.write_step(store, steps, "post-boot-hold", hold)
            evidence = fwbase.base.collect_test_boot_evidence(args, store, steps)
    except Exception as exc:  # noqa: BLE001 - evidence preserves live failure
        live_error = str(exc)
    finally:
        rollback_result = fwbase.base.rollback(args, store, steps)

    decision, pass_ok, reason, gate = classify_gate(args, test_flash, rollback_result, args.out_dir)
    if live_error and not pass_ok:
        reason = f"{reason}; live_error={live_error}"
    result = {
        "cycle": args.cycle,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "preflight": pre,
        "property_deploy": property_deploy,
        "test_flash_ok": bool(test_flash.get("ok")),
        "evidence": evidence,
        "rollback": rollback_result,
        "gate": gate,
        "steps": steps,
        "live_error": live_error,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({"decision": decision, "pass": pass_ok, "gate": gate, "rollback": rollback_result, "live_error": live_error}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
