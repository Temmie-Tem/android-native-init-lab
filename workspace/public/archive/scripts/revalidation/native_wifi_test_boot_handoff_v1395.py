#!/usr/bin/env python3
"""V1395 bounded live handoff for the V1393 Wi-Fi test boot artifact.

This runner flashes the V1393 test boot image, collects below-connect boot
evidence, and rolls back to the v725-fasttransport native boot image. It does not run
Wi-Fi scan/connect, use credentials, run DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1395-wifi-test-boot-handoff"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1395_WIFI_TEST_BOOT_HANDOFF_2026-06-01.md"
DEFAULT_V1394_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1394-wifi-test-boot-artifact-sanity" / "manifest.json"
DEFAULT_TEST_IMAGE = REPO_ROOT / "tmp" / "wifi" / "v1393-wifi-test-boot" / "boot_linux_v1393_wifi_test.img"
DEFAULT_ROLLBACK_IMAGE = REPO_ROOT / "stage3" / "boot_linux_v725_fasttransport.img"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.69 (v1393-wifitest)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1393.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1393.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = ""
DEFAULT_DMESG_PATTERN = "A90v1393|A90v1397|subsystem_get|PCIe RC1|LTSSM|GPIO142|wlfw|FW ready|BDF|wlan0|mhi|ks"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_command(command: list[object],
                *,
                timeout: float,
                check: bool = False) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        ok = completed.returncode == 0
        if check and not ok:
            raise subprocess.CalledProcessError(
                completed.returncode,
                [str(item) for item in command],
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": ok,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: EvidenceStore, steps: list[dict[str, Any]], name: str, result: dict[str, Any]) -> None:
    clean = {
        "command": result["command"],
        "started": result["started"],
        "ended": result["ended"],
        "timeout": result["timeout"],
        "rc": result["rc"],
        "ok": result["ok"],
        "stdout_file": f"{name}.stdout.txt",
        "stderr_file": f"{name}.stderr.txt",
    }
    store.write_text(clean["stdout_file"], str(result.get("stdout") or ""))
    store.write_text(clean["stderr_file"], str(result.get("stderr") or ""))
    steps.append(clean)


def run_a90ctl_step(store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    name: str,
                    command: list[object],
                    timeout: float) -> dict[str, Any]:
    result = run_command(command, timeout=timeout)
    if "[busy]" not in str(result.get("stdout") or ""):
        write_step(store, steps, name, result)
        return result

    hide = run_command(a90ctl_command(["hide"]), timeout=min(timeout, 20.0))
    write_step(store, steps, f"{name}-hide-on-busy", hide)
    retry = run_command(command, timeout=timeout)
    write_step(store, steps, name, retry)
    return retry


def a90ctl_command(command: list[str]) -> list[object]:
    return ["python3", "scripts/revalidation/a90ctl.py", *command]


def a90ctl_command_timed(command: list[str], *, timeout: float, retry_unsafe: bool = False) -> list[object]:
    result: list[object] = [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--timeout",
        str(timeout),
    ]
    if retry_unsafe:
        result.append("--retry-unsafe")
    result.extend(command)
    return result


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    command: list[object] = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        image,
        "--expect-version",
        expect_version,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "240",
        "--recovery-timeout",
        "240",
    ]
    if from_native:
        command.append("--from-native")
    return command


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_evidence_text(evidence_dir: Path, file_name: str) -> str:
    path = evidence_dir / file_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or line.startswith("A90P1 "):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def matching_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker in text]


def has_icnss_qmi_connected(text: str) -> bool:
    return "icnss_qmi: QMI Server Connected" in text


def first_state_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("state="):
            return line
    return " ".join(text.split())[:240]


def classify_wifi_progress(evidence_dir: Path) -> dict[str, Any]:
    dmesg = read_evidence_text(evidence_dir, "test-v1393-dmesg.stdout.txt")
    summary = read_evidence_text(evidence_dir, "test-v1393-summary.stdout.txt")
    helper_result = read_evidence_text(evidence_dir, "test-v1393-helper-result.stdout.txt")
    rc1_watcher_result = read_evidence_text(evidence_dir, "test-v1393-rc1-watcher-result.stdout.txt")
    rc1_window_result = read_evidence_text(evidence_dir, "test-rc1-window-result.stdout.txt")
    wlan0_stdout = read_evidence_text(evidence_dir, "test-wlan0.stdout.txt")
    summary_fields = parse_key_value_lines(summary)
    helper_result_fields = parse_key_value_lines(helper_result)

    rc1_markers = matching_markers(
        dmesg,
        (
            "TEST: 11",
            "PCIe RC1 PHY is ready",
            "LTSSM_STATE",
            "PCIe RC1 Current",
            "msm_pcie_enable: PCIe",
        ),
    )
    rc1_l0_markers = matching_markers(
        dmesg,
        (
            "LTSSM_STATE: LTSSM_L0",
            "PCIe RC1 link initialized",
            "PCIe RC1 Current GEN",
        ),
    )
    rc1_failure_markers = matching_markers(
        dmesg,
        (
            "PCIe RC1 link initialization failed",
            "LTSSM_POLL_COMPLIANCE",
            "LTSSM_STATE:0x3",
        ),
    )
    mhi_markers = matching_markers(
        dmesg,
        (
            "mhi_arch_esoc_ops_power_on",
            "mhi_pci_probe",
            "mhi_0305",
            "/dev/mhi_",
            "MHI control",
        ),
    )
    wlfw_markers = matching_markers(dmesg, ("wlfw", "WLFW"))
    icnss_qmi_connected = has_icnss_qmi_connected(dmesg)
    if icnss_qmi_connected:
        wlfw_markers.append("icnss_qmi: QMI Server Connected")
    bdf_markers = matching_markers(dmesg, ("BDF", "bdwlan", "regdb"))
    fw_ready_markers = matching_markers(dmesg, ("FW ready", "fw_ready", "FW_READY"))

    provider_trigger = "__subsystem_get: esoc0" in dmesg
    modem_trigger = "__subsystem_get: modem" in dmesg
    wlan0_present = (
        "wlan0=present" in wlan0_stdout
        or summary_fields.get("wlan0_present") == "1"
    )
    rc1_progress = bool(rc1_markers)
    rc1_l0 = bool(rc1_l0_markers)
    rc1_link_failed = bool(rc1_failure_markers)
    mhi_progress = bool(mhi_markers)
    wlfw_progress = bool(wlfw_markers)
    bdf_progress = bool(bdf_markers)
    fw_ready_progress = bool(fw_ready_markers)
    downstream_progress = any((
        rc1_progress,
        mhi_progress,
        wlfw_progress,
        bdf_progress,
        fw_ready_progress,
        wlan0_present,
    ))

    if wlan0_present:
        final_decision = "wlan0-present"
    elif wlfw_progress or bdf_progress or fw_ready_progress:
        final_decision = "firmware-progress-no-wlan0"
    elif rc1_progress and rc1_link_failed and not rc1_l0:
        final_decision = "rc1-ltssm-link-failed-no-l0"
    elif rc1_progress or mhi_progress:
        final_decision = "rc1-or-mhi-progress-only"
    elif provider_trigger:
        final_decision = "provider-trigger-no-downstream"
    elif modem_trigger:
        final_decision = "modem-trigger-no-downstream"
    else:
        final_decision = "no-provider-no-downstream"

    return {
        "provider_trigger": provider_trigger,
        "modem_trigger": modem_trigger,
        "rc1_progress": rc1_progress,
        "rc1_markers": rc1_markers,
        "rc1_l0": rc1_l0,
        "rc1_l0_markers": rc1_l0_markers,
        "rc1_link_failed": rc1_link_failed,
        "rc1_failure_markers": rc1_failure_markers,
        "mhi_progress": mhi_progress,
        "mhi_markers": mhi_markers,
        "wlfw_progress": wlfw_progress,
        "wlfw_markers": wlfw_markers,
        "icnss_qmi_connected": icnss_qmi_connected,
        "bdf_progress": bdf_progress,
        "bdf_markers": bdf_markers,
        "fw_ready_progress": fw_ready_progress,
        "fw_ready_markers": fw_ready_markers,
        "wlan0_present": wlan0_present,
        "downstream_progress": downstream_progress,
        "wifi_progress_pass": downstream_progress,
        "connect_ready": wlan0_present,
        "final_decision": final_decision,
        "helper_supervised": summary_fields.get("supervised"),
        "helper_exit_code": summary_fields.get("helper_exit_code"),
        "helper_timed_out": summary_fields.get("helper_timed_out"),
        "helper_result_path": summary_fields.get("helper_result_path"),
        "helper_result_size": summary_fields.get("helper_result_size"),
        "helper_result_size_errno": summary_fields.get("helper_result_size_errno"),
        "helper_result_file_seen": "A90_EXECNS_RESULT_FILE_BEGIN" in helper_result,
        "helper_result_contract_seen": "android_wifi_service_window.begin=1" in helper_result,
        "helper_result_mode": helper_result_fields.get("android_wifi_service_window.mode"),
        "helper_result_late_per_proxy_only": helper_result_fields.get("android_wifi_service_window.late_per_proxy_only"),
        "helper_result_subsys_open_attempted": helper_result_fields.get("android_wifi_service_window.subsys_esoc0_open_attempted"),
        "helper_result_subsys_trigger_started": helper_result_fields.get("android_wifi_service_window.subsys_trigger_started"),
        "helper_result_subsys_trigger_gate_open": helper_result_fields.get("android_wifi_service_window.subsys_trigger_gate_open"),
        "helper_result_mdm_helper_esoc0_fd_count": helper_result_fields.get("android_wifi_service_window.mdm_helper_esoc0_fd_count"),
        "helper_result_pm_proxy_contract": helper_result_fields.get("android_wifi_service_window.pm_proxy_contract"),
        "helper_result_pm_proxy_helper_subsys_modem_fd_count": helper_result_fields.get("android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count"),
        "helper_result_per_mgr_subsys_modem_fd_count": helper_result_fields.get("android_wifi_service_window.per_mgr_subsys_modem_fd_count"),
        "helper_result_pm_full_contract_seen": helper_result_fields.get("android_wifi_service_window.pm_full_contract_seen"),
        "helper_result_child_per_mgr_exit_code": helper_result_fields.get("android_wifi_service_window.child.per_mgr.exit_code"),
        "helper_result_child_pm_proxy_exit_code": helper_result_fields.get("android_wifi_service_window.child.pm_proxy.exit_code"),
        "helper_result_final_result": helper_result_fields.get("android_wifi_service_window.result"),
        "helper_result_final_reason": helper_result_fields.get("android_wifi_service_window.reason"),
        "debugfs_mount_requested": summary_fields.get("debugfs_mount_requested"),
        "firmware_mounts_requested": summary_fields.get("firmware_mounts_requested"),
        "debugfs_mounted_by_pid1": summary_fields.get("debugfs_mounted_by_pid1"),
        "debugfs_pci_msm_case_present": summary_fields.get("debugfs_pci_msm_case_present"),
        "pid1_rc1_watcher_requested": summary_fields.get("pid1_rc1_watcher_requested"),
        "pid1_rc1_watcher_result_summary": summary_fields.get("pid1_rc1_watcher_result"),
        "pid1_rc1_watcher_result_file": first_state_line(rc1_watcher_result),
        "pid1_rc1_window_sampler_requested": summary_fields.get("rc1_window_sampler_requested"),
        "pid1_rc1_window_result_summary": summary_fields.get("rc1_window_result_head"),
        "pid1_rc1_window_result_file": first_state_line(rc1_window_result),
        "pid1_rc1_window_sample_count": rc1_window_result.count("rc1_window_sample label="),
        "pid1_rc1_window_has_post_500ms": "post_rc1_500ms" in rc1_window_result,
    }


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    v1394 = load_json(args.v1394_manifest)
    return {
        "v1394_manifest": display_path(args.v1394_manifest),
        "v1394_decision": v1394.get("decision", ""),
        "v1394_pass": bool(v1394.get("pass")),
        "test_image": display_path(args.test_image),
        "test_image_exists": args.test_image.exists(),
        "rollback_image": display_path(args.rollback_image),
        "rollback_image_exists": args.rollback_image.exists(),
    }


def collect_test_boot_evidence(args: argparse.Namespace,
                               store: EvidenceStore,
                               steps: list[dict[str, Any]]) -> dict[str, Any]:
    def cat_command(path: str) -> list[str]:
        return a90ctl_command(["run", "/cache/bin/busybox", "cat", path])

    commands = {
        "test-version": a90ctl_command(["version"]),
        "test-status": a90ctl_command(["status"]),
        "test-selftest": a90ctl_command(["selftest"]),
        "test-bootstatus": a90ctl_command(["bootstatus"]),
        "test-v1393-log": cat_command(args.test_log_path),
        "test-v1393-summary": cat_command(args.test_summary_path),
        "test-v1393-dmesg": a90ctl_command([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"dmesg | grep -Ei {args.dmesg_grep_pattern!r} | tail -240",
        ]),
        "test-wlan0": a90ctl_command([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            "test -e /sys/class/net/wlan0 && echo wlan0=present || echo wlan0=absent",
        ]),
    }
    if args.test_rc1_watcher_result_path:
        commands["test-v1393-rc1-watcher-result"] = cat_command(args.test_rc1_watcher_result_path)
    if args.test_helper_result_path:
        commands["test-v1393-helper-result"] = cat_command(args.test_helper_result_path)
    if args.test_rc1_window_result_path:
        commands["test-rc1-window-result"] = cat_command(args.test_rc1_window_result_path)
    for spec in args.test_extra_result_path:
        if "=" not in spec:
            continue
        name, path = spec.split("=", 1)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-")
        if not safe_name or not path:
            continue
        commands[f"test-extra-{safe_name}"] = cat_command(path)
    evidence: dict[str, Any] = {}
    for name, command in commands.items():
        result = run_a90ctl_step(store, steps, name, command, args.collect_timeout_sec)
        evidence[name] = {
            "ok": result["ok"],
            "rc": result["rc"],
            "timeout": result["timeout"],
            "stdout_file": f"{name}.stdout.txt",
            "stderr_file": f"{name}.stderr.txt",
        }
    return evidence


def rollback(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]]) -> dict[str, Any]:
    first = run_command(
        flash_command(args.rollback_image, args.expect_rollback_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "rollback-from-native", first)
    if first["ok"]:
        return {"attempt": "from-native", "ok": True}

    if args.native_direct_rollback_fallback:
        direct = native_direct_rollback(args, store, steps)
        if direct["ok"]:
            return direct

    second = run_command(
        flash_command(args.rollback_image, args.expect_rollback_version, from_native=False),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "rollback-from-recovery", second)
    if second["ok"]:
        return {"attempt": "from-recovery", "ok": True}

    if args.native_direct_rollback_fallback:
        retry_direct = native_direct_rollback(args, store, steps, suffix="after-recovery-failure")
        if retry_direct["ok"]:
            return retry_direct

    return {"attempt": "from-recovery", "ok": False}


def native_direct_rollback(args: argparse.Namespace,
                           store: EvidenceStore,
                           steps: list[dict[str, Any]],
                           *,
                           suffix: str = "after-native-recovery-failure") -> dict[str, Any]:
    image_hash = local_sha256(args.rollback_image)
    image_size = args.rollback_image.stat().st_size
    readback_count = (image_size + 4095) // 4096
    prefix = f"rollback-native-direct-{suffix}"
    remote = args.native_direct_rollback_remote_image
    block = args.native_direct_rollback_boot_block

    check_remote = run_a90ctl_step(
        store,
        steps,
        f"{prefix}-remote-sha256",
        a90ctl_command_timed([
            "run",
            "/cache/bin/toybox",
            "sha256sum",
            remote,
        ], timeout=args.collect_timeout_sec),
        args.collect_timeout_sec + 10.0,
    )
    if image_hash not in str(check_remote.get("stdout") or ""):
        return {
            "attempt": "native-direct",
            "ok": False,
            "stage": "remote-sha256",
            "expected_sha256": image_hash,
            "remote_image": remote,
        }

    ensure_block = run_a90ctl_step(
        store,
        steps,
        f"{prefix}-ensure-block",
        a90ctl_command_timed([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                f"test -b {block} || "
                f"mknod {block} b {args.native_direct_rollback_boot_major} "
                f"{args.native_direct_rollback_boot_minor}"
            ),
        ], timeout=args.collect_timeout_sec, retry_unsafe=True),
        args.collect_timeout_sec + 10.0,
    )
    if not ensure_block["ok"]:
        return {"attempt": "native-direct", "ok": False, "stage": "ensure-block"}

    write_boot = run_a90ctl_step(
        store,
        steps,
        f"{prefix}-write-boot",
        a90ctl_command_timed([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"dd if={remote} of={block} bs=4M conv=fsync && sync",
        ], timeout=args.native_direct_rollback_timeout_sec, retry_unsafe=True),
        args.native_direct_rollback_timeout_sec + 10.0,
    )
    if not write_boot["ok"]:
        return {"attempt": "native-direct", "ok": False, "stage": "write-boot"}

    readback = run_a90ctl_step(
        store,
        steps,
        f"{prefix}-readback-sha256",
        a90ctl_command_timed([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                f"dd if={block} bs=4096 count={readback_count} 2>/dev/null | "
                "/cache/bin/toybox sha256sum"
            ),
        ], timeout=args.native_direct_rollback_timeout_sec),
        args.native_direct_rollback_timeout_sec + 10.0,
    )
    if image_hash not in str(readback.get("stdout") or ""):
        return {
            "attempt": "native-direct",
            "ok": False,
            "stage": "readback-sha256",
            "expected_sha256": image_hash,
        }

    reboot = run_command(
        a90ctl_command_timed(["reboot"], timeout=20.0, retry_unsafe=True),
        timeout=30.0,
    )
    write_step(store, steps, f"{prefix}-reboot", reboot)

    verify = run_command(
        [
            "python3",
            "scripts/revalidation/native_init_flash.py",
            "--verify-only",
            "--expect-version",
            args.expect_rollback_version,
            "--verify-protocol",
            "selftest",
            "--bridge-timeout",
            str(args.bridge_verify_timeout_sec),
        ],
        timeout=args.bridge_verify_timeout_sec + 30.0,
    )
    write_step(store, steps, f"{prefix}-verify", verify)
    if not verify["ok"]:
        return {"attempt": "native-direct", "ok": False, "stage": "verify"}

    return {
        "attempt": "native-direct",
        "ok": True,
        "remote_image": remote,
        "boot_block": block,
        "sha256": image_hash,
        "readback_count": readback_count,
    }


def cycle_slug(cycle: str) -> str:
    return cycle.strip().lower()


def decision_label(cycle: str, suffix: str) -> str:
    return f"{cycle_slug(cycle)}-{suffix}"


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def classify(test_flash: dict[str, Any],
             evidence: dict[str, Any],
             rollback_result: dict[str, Any],
             evidence_dir: Path,
             cycle: str,
             expect_test_version: str,
             strict_wifi_progress: bool) -> tuple[str, bool, str, dict[str, Any]]:
    progress = classify_wifi_progress(evidence_dir)
    if not test_flash["ok"]:
        return (
            decision_label(cycle, "test-boot-flash-or-verify-failed"),
            False,
            "test boot flash/verify did not complete; inspect rollback evidence before retry",
            progress,
        )
    test_version = read_evidence_text(evidence_dir, "test-version.stdout.txt")
    if expect_test_version not in test_version:
        return (
            decision_label(cycle, "test-boot-version-missing"),
            False,
            "test boot returned through bridge but expected version marker was missing",
            progress,
        )
    if not rollback_result.get("ok"):
        return (
            decision_label(cycle, "test-boot-rollback-failed"),
            False,
            "test boot evidence collected but rollback did not verify",
            progress,
        )
    if progress["downstream_progress"]:
        return (
            decision_label(cycle, "test-boot-downstream-progress-rollback-pass"),
            True,
            "test boot produced downstream Wi-Fi/PCIe evidence and rollback verified",
            progress,
        )
    if progress["provider_trigger"]:
        if strict_wifi_progress:
            return (
                decision_label(cycle, "test-boot-provider-trigger-no-downstream-wifi-progress-blocked"),
                False,
                "test boot reached the esoc0 provider trigger and rollback verified, but strict Wi-Fi progress markers were absent",
                progress,
            )
        return (
            decision_label(cycle, "test-boot-provider-trigger-no-downstream-rollback-pass"),
            True,
            "test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared",
            progress,
        )
    if strict_wifi_progress:
        return (
            decision_label(cycle, "test-boot-no-downstream-wifi-progress-blocked"),
            False,
            "test boot ran and rollback verified, but strict Wi-Fi progress markers were absent",
            progress,
        )
    return (
        decision_label(cycle, "test-boot-no-downstream-progress-rollback-pass"),
        True,
        "test boot ran and rollback verified, but no MDM2AP/PCIe/MHI/WLFW/wlan0 progress marker appeared",
        progress,
    )


def render_report(result: dict[str, Any]) -> str:
    cycle = str(result["cycle"])
    classify_only = bool(result.get("classify_only"))
    title = "Wi-Fi Test Boot Strict Classifier" if classify_only else "Wi-Fi Test Boot Handoff"
    run_type = (
        "host-only strict reclassification of existing test-boot evidence"
        if classify_only
        else "bounded live test-boot handoff with rollback"
    )
    lines = [
        f"# Native Init {cycle} {title}",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        f"- Type: {run_type}",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
    ]
    if "source_out_dir" in result:
        lines.append(f"- Source evidence: `{result['source_out_dir']}`")
    if "handoff_pass" in result:
        lines.append(f"- Handoff/rollback pass: `{result['handoff_pass']}`")
    if "rollback" in result:
        rollback_info = result["rollback"]
        lines.append(f"- Rollback attempt: `{rollback_info.get('attempt')}`")
        if rollback_info.get("boot_block"):
            lines.append(f"- Rollback boot block: `{rollback_info.get('boot_block')}`")
    if "strict_wifi_progress" in result:
        lines.append(f"- Strict Wi-Fi progress mode: `{result['strict_wifi_progress']}`")
    if "wifi_progress" in result:
        progress = result["wifi_progress"]
        lines.extend([
            f"- Wi-Fi progress pass: `{progress['wifi_progress_pass']}`",
            f"- Progress decision: `{progress['final_decision']}`",
            "",
            "## Progress Classification",
            "",
            f"- `provider_trigger`: `{progress['provider_trigger']}`",
            f"- `rc1_progress`: `{progress['rc1_progress']}`",
            f"- `rc1_l0`: `{progress.get('rc1_l0')}`",
            f"- `rc1_link_failed`: `{progress.get('rc1_link_failed')}`",
            f"- `mhi_progress`: `{progress['mhi_progress']}`",
            f"- `wlfw_progress`: `{progress['wlfw_progress']}`",
            f"- `icnss_qmi_connected`: `{progress.get('icnss_qmi_connected')}`",
            f"- `bdf_progress`: `{progress['bdf_progress']}`",
            f"- `fw_ready_progress`: `{progress['fw_ready_progress']}`",
            f"- `wlan0_present`: `{progress['wlan0_present']}`",
            f"- `connect_ready`: `{progress['connect_ready']}`",
            f"- `debugfs_pci_msm_case_present`: `{progress.get('debugfs_pci_msm_case_present')}`",
            f"- `firmware_mounts_requested`: `{progress.get('firmware_mounts_requested')}`",
            f"- `helper_timed_out`: `{progress.get('helper_timed_out')}`",
            f"- `helper_result_file_seen`: `{progress.get('helper_result_file_seen')}`",
            f"- `helper_result_contract_seen`: `{progress.get('helper_result_contract_seen')}`",
            f"- `helper_result_size`: `{progress.get('helper_result_size')}`",
            f"- `helper_result_late_per_proxy_only`: `{progress.get('helper_result_late_per_proxy_only')}`",
            f"- `helper_result_subsys_open_attempted`: `{progress.get('helper_result_subsys_open_attempted')}`",
            f"- `helper_result_subsys_trigger_started`: `{progress.get('helper_result_subsys_trigger_started')}`",
            f"- `helper_result_subsys_trigger_gate_open`: `{progress.get('helper_result_subsys_trigger_gate_open')}`",
            f"- `helper_result_mdm_helper_esoc0_fd_count`: `{progress.get('helper_result_mdm_helper_esoc0_fd_count')}`",
            f"- `helper_result_pm_proxy_contract`: `{progress.get('helper_result_pm_proxy_contract')}`",
            f"- `helper_result_pm_proxy_helper_subsys_modem_fd_count`: `{progress.get('helper_result_pm_proxy_helper_subsys_modem_fd_count')}`",
            f"- `helper_result_per_mgr_subsys_modem_fd_count`: `{progress.get('helper_result_per_mgr_subsys_modem_fd_count')}`",
            f"- `helper_result_pm_full_contract_seen`: `{progress.get('helper_result_pm_full_contract_seen')}`",
            f"- `helper_result_child_per_mgr_exit_code`: `{progress.get('helper_result_child_per_mgr_exit_code')}`",
            f"- `helper_result_child_pm_proxy_exit_code`: `{progress.get('helper_result_child_pm_proxy_exit_code')}`",
            f"- `helper_result_final_result`: `{progress.get('helper_result_final_result')}`",
            f"- `helper_result_final_reason`: `{progress.get('helper_result_final_reason')}`",
            f"- `pid1_rc1_watcher_requested`: `{progress.get('pid1_rc1_watcher_requested')}`",
            f"- `pid1_rc1_watcher_result_summary`: `{progress.get('pid1_rc1_watcher_result_summary')}`",
            f"- `pid1_rc1_watcher_result_file`: `{progress.get('pid1_rc1_watcher_result_file')}`",
            f"- `pid1_rc1_window_sampler_requested`: `{progress.get('pid1_rc1_window_sampler_requested')}`",
            f"- `pid1_rc1_window_result_summary`: `{progress.get('pid1_rc1_window_result_summary')}`",
            f"- `pid1_rc1_window_result_file`: `{progress.get('pid1_rc1_window_result_file')}`",
            f"- `pid1_rc1_window_sample_count`: `{progress.get('pid1_rc1_window_sample_count')}`",
            f"- `pid1_rc1_window_has_post_500ms`: `{progress.get('pid1_rc1_window_has_post_500ms')}`",
        ])
    progress = result.get("wifi_progress", {})
    final_decision = progress.get("final_decision", "")
    if final_decision == "firmware-progress-no-wlan0":
        next_lines = [
            "Treat V1586-class evidence as firmware/PIL progress without interface bring-up.",
            "The next bounded gate should preserve firmware mount parity and add focused",
            "RC1/MHI/WLFW request markers before any scan/connect, credentials, DHCP/routes,",
            "or external ping.",
        ]
    elif final_decision == "provider-trigger-no-downstream":
        next_lines = [
            "Treat provider-trigger evidence as diagnostic progress, not Wi-Fi bring-up.",
            "The next bounded gate should isolate why RC1/MHI/WLFW/`wlan0` did not follow",
            "before any scan/connect, credentials, DHCP/routes, or external ping.",
        ]
    elif final_decision == "rc1-ltssm-link-failed-no-l0":
        next_lines = [
            "Treat RC1 LTSSM link failure as the active blocker. Compare Android-good and",
            "native-fail RC1 reset/refclk/PERST sequencing before any MHI/WLFW or",
            "scan/connect work.",
        ]
    else:
        next_lines = [
            "Treat this result as diagnostic evidence, not Wi-Fi connect readiness.",
            "Do not proceed to scan/connect, credentials, DHCP/routes, or external ping",
            "until the next required lower-layer progress marker is proven.",
        ]

    lines.extend([
        "",
        "## Safety Scope",
        "",
        "No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was",
        "performed by this runner.",
    ])
    if classify_only:
        lines.extend([
            "This run was host-only and reclassified existing test-boot evidence;",
            "it did not flash, reboot, or mutate the device.",
        ])
    else:
        lines.extend([
            "Device mutation included flashing the test boot image, any bounded",
            "in-boot actions declared by that test image's artifact contract, and",
            "rolling back to `stage3/boot_linux_v725_fasttransport.img`. If enabled, native direct",
            "rollback may restore the boot partition from a pre-staged `/cache`",
            "rollback image when recovery ADB is unavailable.",
        ])
    lines.extend([
        "",
        "## Images",
        "",
        f"- Test image: `{result['preflight']['test_image']}`",
        f"- Rollback image: `{result['preflight']['rollback_image']}`",
        "",
        "## Next",
        "",
        *next_lines,
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1394-manifest", type=Path, default=DEFAULT_V1394_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--rollback-image", type=Path, default=DEFAULT_ROLLBACK_IMAGE)
    parser.add_argument("--cycle", default="V1395")
    parser.add_argument("--post-boot-hold-sec", type=float, default=0.0)
    parser.add_argument("--expect-test-version", default=TEST_EXPECT_VERSION)
    parser.add_argument("--expect-rollback-version", default=ROLLBACK_EXPECT_VERSION)
    parser.add_argument("--test-log-path", default=DEFAULT_TEST_LOG_PATH)
    parser.add_argument("--test-summary-path", default=DEFAULT_TEST_SUMMARY_PATH)
    parser.add_argument("--test-helper-result-path", default=DEFAULT_TEST_HELPER_RESULT_PATH)
    parser.add_argument("--test-rc1-watcher-result-path", default="")
    parser.add_argument("--test-rc1-window-result-path", default="")
    parser.add_argument("--test-extra-result-path", action="append", default=[])
    parser.add_argument("--dmesg-grep-pattern", default=DEFAULT_DMESG_PATTERN)
    parser.add_argument("--flash-timeout-sec", type=float, default=720.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=120.0)
    parser.add_argument("--bridge-verify-timeout-sec", type=float, default=240.0)
    parser.add_argument("--native-direct-rollback-fallback", action="store_true")
    parser.add_argument("--native-direct-rollback-remote-image", default="/cache/boot_linux_v725_fasttransport.img")
    parser.add_argument("--native-direct-rollback-boot-block", default="/dev/block/sda24")
    parser.add_argument("--native-direct-rollback-boot-major", type=int, default=259)
    parser.add_argument("--native-direct-rollback-boot-minor", type=int, default=8)
    parser.add_argument("--native-direct-rollback-timeout-sec", type=float, default=120.0)
    parser.add_argument("--classify-only", action="store_true")
    parser.add_argument("--classify-input-dir", type=Path)
    parser.add_argument("--strict-wifi-progress", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(args.out_dir)
    steps: list[dict[str, Any]] = []
    pre = preflight(args)
    store.write_json("preflight.json", pre)
    if not pre["v1394_pass"] or not pre["test_image_exists"] or not pre["rollback_image_exists"]:
        result = {
            "cycle": args.cycle,
            "decision": decision_label(args.cycle, "preflight-blocked"),
            "pass": False,
            "reason": "V1394 pass, test image, or rollback image missing",
            "preflight": pre,
            "steps": steps,
            "out_dir": display_path(args.out_dir),
        }
        store.write_json("manifest.json", result)
        args.report_path.write_text(render_report(result), encoding="utf-8")
        print(json.dumps({"decision": result["decision"], "pass": False}, indent=2))
        return 1

    if args.classify_only:
        source_dir = args.classify_input_dir or args.out_dir
        evidence = {
            name: {"stdout_file": f"{name}.stdout.txt"}
            for name in (
                "test-version",
                "test-status",
                "test-selftest",
                "test-bootstatus",
                "test-v1393-log",
                "test-v1393-summary",
                "test-v1393-helper-result",
                "test-v1393-dmesg",
                "test-wlan0",
            )
        }
        test_version_path = source_dir / "test-version.stdout.txt"
        rollback_stdout_path = source_dir / "rollback-from-native.stdout.txt"
        rollback_stderr_path = source_dir / "rollback-from-native.stderr.txt"
        rollback_stdout = (
            rollback_stdout_path.read_text(encoding="utf-8", errors="replace")
            if rollback_stdout_path.exists()
            else ""
        )
        rollback_stderr = (
            rollback_stderr_path.read_text(encoding="utf-8", errors="replace")
            if rollback_stderr_path.exists()
            else ""
        )
        test_flash = {
            "ok": test_version_path.exists() and args.expect_test_version in test_version_path.read_text(encoding="utf-8", errors="replace"),
        }
        rollback_result = {
            "attempt": "existing",
            "ok": (
                rollback_stdout_path.exists() and
                (
                    args.expect_rollback_version in rollback_stdout or
                    args.expect_rollback_version in rollback_stderr or
                    "cmdv1 verify passed: selftest rc=0 status=ok fail=0" in rollback_stderr
                )
            ),
        }
        label, pass_ok, reason, progress = classify(test_flash,
                                                    evidence,
                                                    rollback_result,
                                                    source_dir,
                                                    args.cycle,
                                                    args.expect_test_version,
                                                    args.strict_wifi_progress)
        handoff_pass = bool(test_flash["ok"] and rollback_result.get("ok"))
        result = {
            "cycle": args.cycle,
            "decision": label,
            "pass": pass_ok,
            "reason": reason,
            "preflight": pre,
            "test_flash_ok": bool(test_flash["ok"]),
            "evidence": evidence,
            "rollback": rollback_result,
            "handoff_pass": handoff_pass,
            "strict_wifi_progress": bool(args.strict_wifi_progress),
            "wifi_progress": progress,
            "steps": [],
            "out_dir": display_path(args.out_dir),
            "source_out_dir": display_path(source_dir),
            "classify_only": True,
        }
        store.write_json("manifest.json", result)
        store.write_text("summary.md", render_report(result))
        args.report_path.write_text(render_report(result), encoding="utf-8")
        print(json.dumps({
            "decision": label,
            "pass": pass_ok,
            "handoff_pass": handoff_pass,
            "wifi_progress": progress,
            "rollback": rollback_result,
        }, indent=2))
        return 0 if pass_ok else 1

    test_flash = run_command(
        flash_command(args.test_image, args.expect_test_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "test-flash-from-native", test_flash)

    evidence: dict[str, Any] = {}
    if test_flash["ok"]:
        if args.post_boot_hold_sec > 0:
            hold = run_command(
                [
                    "python3",
                    "-c",
                    f"import time; time.sleep({args.post_boot_hold_sec!r})",
                ],
                timeout=args.post_boot_hold_sec + 10.0,
            )
            write_step(store, steps, "post-boot-hold", hold)
        evidence = collect_test_boot_evidence(args, store, steps)

    rollback_result = rollback(args, store, steps)
    label, pass_ok, reason, progress = classify(test_flash,
                                                evidence,
                                                rollback_result,
                                                args.out_dir,
                                                args.cycle,
                                                args.expect_test_version,
                                                args.strict_wifi_progress)
    handoff_pass = bool(test_flash["ok"] and rollback_result.get("ok"))
    result = {
        "cycle": args.cycle,
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "preflight": pre,
        "test_flash_ok": bool(test_flash["ok"]),
        "evidence": evidence,
        "rollback": rollback_result,
        "handoff_pass": handoff_pass,
        "strict_wifi_progress": bool(args.strict_wifi_progress),
        "wifi_progress": progress,
        "steps": steps,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": label, "pass": pass_ok, "rollback": rollback_result}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
