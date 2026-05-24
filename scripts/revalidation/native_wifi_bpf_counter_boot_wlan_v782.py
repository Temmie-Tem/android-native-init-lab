#!/usr/bin/env python3
"""V782 BPF-counted lower-window boot_wlan observer.

This gate adds a count-capable BPF tracepoint helper and uses it around the
previously tested lower-window boot_wlan transition.  The goal is observability:
count PIL notification tracepoint hits while preserving the no-scan/no-connect
Wi-Fi boundary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_lower_window_boot_wlan_v750 as v750
import native_wifi_holder_lower_companion_v733 as base
import native_wifi_bpf_loader_deploy_checkonly_v780 as deploy_v780
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v782-bpf-counter-boot-wlan")
LATEST_POINTER = Path("tmp/wifi/latest-v782-bpf-counter-boot-wlan.txt")
DEFAULT_SOURCE = Path("stage3/linux_init/helpers/a90_bpf_trace_counter.c")
DEFAULT_BUILD_DIR = Path("tmp/wifi/v782-bpf-counter-build")
DEFAULT_LOCAL_COUNTER_NAME = "a90_bpf_trace_counter-aarch64-static"
DEFAULT_REMOTE_COUNTER = "/cache/bin/a90_bpf_trace_counter"
DEFAULT_COUNTER_MARKER = "a90_bpf_trace_counter v782"
DEFAULT_COUNTER_DURATION_SEC = 75
DEFAULT_BOOT_OBSERVE_SEC = 10
DEFAULT_TRACEFS_TARGET = "/sys/kernel/tracing"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
PROOF_PREFIX = "/tmp/a90-v782-"

FORBIDDEN_TERMS = (
    "subsys_esoc0",
    "/sys/class/subsys/subsys_esoc0",
    "/dev/subsys_esoc0",
    "echo online",
    "driver_override",
    "/bind",
    "/unbind",
    "insmod",
    "rmmod",
    "modprobe",
    "qcwlanstate on",
    "cnss-daemon",
    "cnss_diag",
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
    "android.hardware.wifi",
    "IWifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    "iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v750.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v750.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v750.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v750.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v750.DEFAULT_BUSYBOX)
    parser.add_argument("--helper", default=v750.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v750.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v750.DEFAULT_HELPER_MARKER)
    parser.add_argument("--wlanbootctl", default=v750.DEFAULT_WLANBOOTCTL)
    parser.add_argument("--wlanbootctl-sha256", default=v750.DEFAULT_WLANBOOTCTL_SHA256)
    parser.add_argument("--wlanbootctl-marker", default=v750.DEFAULT_WLANBOOTCTL_MARKER)
    parser.add_argument("--bpf-source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--bpf-build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--bpf-counter", default=DEFAULT_REMOTE_COUNTER)
    parser.add_argument("--counter-duration-sec", type=int, default=DEFAULT_COUNTER_DURATION_SEC)
    parser.add_argument("--boot-observe-sec", type=int, default=DEFAULT_BOOT_OBSERVE_SEC)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v750.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=v750.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v750.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v750.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=v750.DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("--allow-bpf-counter-deploy", action="store_true")
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--allow-bpf-attach", action="store_true")
    parser.add_argument("--allow-lower-window-boot-wlan", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return v750.safe_name(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], output_file: Path, timeout: float = 120.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=repo_path("."),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {"command": [str(item) for item in command], "rc": result.returncode, "timeout": False, "file": str(output_file)}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {"command": [str(item) for item in command], "rc": None, "timeout": True, "file": str(output_file)}


def build_counter(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("host")
    source = repo_path(args.bpf_source)
    build_dir = repo_path(args.bpf_build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    output = build_dir / DEFAULT_LOCAL_COUNTER_NAME
    compile_result = run_host(
        [
            "aarch64-linux-gnu-gcc",
            "-static",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(output),
            str(source),
        ],
        logs / "bpf-counter-compile.txt",
    )
    strip_result = {"rc": None, "timeout": False, "file": ""}
    if compile_result["rc"] == 0 and output.exists():
        strip_result = run_host(["aarch64-linux-gnu-strip", str(output)], logs / "bpf-counter-strip.txt")
        output.chmod(0o600)
    readelf = run_host(["aarch64-linux-gnu-readelf", "-l", str(output)], logs / "bpf-counter-readelf-program.txt") if output.exists() else {}
    strings = run_host(["strings", str(output)], logs / "bpf-counter-strings.txt") if output.exists() else {}
    readelf_text = Path(readelf.get("file", "")).read_text(encoding="utf-8", errors="replace") if readelf.get("file") else ""
    strings_text = Path(strings.get("file", "")).read_text(encoding="utf-8", errors="replace") if strings.get("file") else ""
    return {
        "source": str(source),
        "source_exists": source.exists(),
        "output": str(output),
        "output_exists": output.exists(),
        "output_size": output.stat().st_size if output.exists() else 0,
        "output_sha256": sha256_file(output) if output.exists() else "",
        "compile": compile_result,
        "strip": strip_result,
        "readelf": readelf,
        "strings": strings,
        "static_no_interp": output.exists() and "INTERP" not in readelf_text,
        "marker_present": DEFAULT_COUNTER_MARKER in strings_text,
        "counter_present": "event_count=%llu" in strings_text and "attach-count-pass" in strings_text,
    }


def deploy_counter(args: argparse.Namespace, store: EvidenceStore, build: dict[str, Any]) -> dict[str, Any]:
    expected_sha = str(build.get("output_sha256") or "")
    probe = run_capture(args, "bpf-counter-sha-before-deploy", ["run", args.toybox, "sha256sum", args.bpf_counter], timeout=20.0)
    probe_text = strip_cmdv1_text(probe.text) if probe.text else probe.error + "\n"
    store.write_text("native/bpf-counter-sha-before-deploy.txt", probe_text.rstrip() + "\n")
    if expected_sha and expected_sha in probe_text:
        return {
            "method": "existing",
            "ok": True,
            "rc": 0,
            "file": "native/bpf-counter-sha-before-deploy.txt",
            "chunks": 0,
            "chunks_written": 0,
            "remote_sha256": expected_sha,
        }
    deploy_args = argparse.Namespace(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        local_helper=Path(build.get("output", "")),
        remote_helper=args.bpf_counter,
        expect_sha256=expected_sha,
        toybox=args.toybox,
        serial_staging_dir="/cache/a90-runtime/bin",
        serial_chunk_size=1800,
    )
    return deploy_v780.run_serial_install(deploy_args, store)


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return base.step_payload(steps, name)


def tracefs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEFAULT_TRACEFS_TARGET)}\s+tracefs\s", text) is not None


def validate_device_command(args: argparse.Namespace, command: list[str], proof_base: str | None = None) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise RuntimeError(f"forbidden V782 command term {term!r}: {joined}")
    if command == ["run", args.bpf_counter, "--check-only"]:
        return
    if command == ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", DEFAULT_TRACEFS_TARGET]:
        return
    if command == ["run", args.busybox, "umount", DEFAULT_TRACEFS_TARGET]:
        return
    if command[:2] == ["run", args.busybox] and len(command) >= 4 and command[2] == "sh":
        script = command[-1]
        if proof_base and proof_base not in script:
            raise RuntimeError(f"V782 proof script missing proof path: {joined}")
        allowed_tokens = (
            args.bpf_counter,
            "--allow-attach",
            "--duration-sec",
            args.wlanbootctl,
            "boot-observe",
            "mount -t tracefs",
            "umount",
        )
        if any(token in script for token in allowed_tokens):
            return
    try:
        v750.validate_device_command(args, command, proof_base)
    except RuntimeError as exc:
        raise RuntimeError(f"unexpected V782 command: {joined}") from exc


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None) -> dict[str, Any]:
    validate_device_command(args, command, proof_base)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    steps.append(item)
    return item


def bpf_start_script(args: argparse.Namespace, proof_base: str) -> str:
    bpf_out = f"{proof_base}/bpf-counter.txt"
    pid_file = f"{proof_base}/bpf-counter.pid"
    return (
        f"BB={args.busybox}; P={proof_base}; OUT={bpf_out}; PID={pid_file}; "
        "$BB mkdir -p \"$P\" 2>/dev/null || true; "
        "$BB rm -f \"$OUT\" \"$PID\"; "
        f"{args.bpf_counter} --allow-attach --verbose --duration-sec {args.counter_duration_sec} >\"$OUT\" 2>&1 & "
        "BPF_PID=$!; printf '%s\\n' \"$BPF_PID\" >\"$PID\"; "
        "printf 'v782.bpf_started=1\\n'; printf 'v782.bpf_pid=%s\\n' \"$BPF_PID\"; "
        f"printf 'v782.bpf_duration_sec={args.counter_duration_sec}\\n'"
    )


def bpf_collect_script(args: argparse.Namespace, proof_base: str) -> str:
    bpf_out = f"{proof_base}/bpf-counter.txt"
    pid_file = f"{proof_base}/bpf-counter.pid"
    wait_limit = max(5, min(args.counter_duration_sec + 8, 130))
    return (
        f"BB={args.busybox}; OUT={bpf_out}; PIDF={pid_file}; LIMIT={wait_limit}; "
        "PID=$($BB cat \"$PIDF\" 2>/dev/null || true); "
        "i=0; while [ -n \"$PID\" ] && $BB kill -0 \"$PID\" 2>/dev/null && [ \"$i\" -lt \"$LIMIT\" ]; do $BB sleep 1; i=$((i+1)); done; "
        "if [ -n \"$PID\" ] && $BB kill -0 \"$PID\" 2>/dev/null; then $BB kill \"$PID\" 2>/dev/null || true; printf 'v782.bpf_killed=1\\n'; else printf 'v782.bpf_killed=0\\n'; fi; "
        "printf 'v782.bpf_wait_sec=%s\\n' \"$i\"; "
        "printf '--- bpf-counter-output-begin ---\\n'; $BB cat \"$OUT\" 2>&1 || true; printf '--- bpf-counter-output-end ---\\n'"
    )


def capture_preflight(args: argparse.Namespace,
                      store: EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = v750.capture_preflight(args, store, steps)
    run_step(args, store, steps, "bpf-counter-sha", ["run", args.toybox, "sha256sum", args.bpf_counter], 20.0)
    run_step(args, store, steps, "bpf-counter-check-only", ["run", args.bpf_counter, "--check-only"], 20.0)
    return preflight


def bpf_ready(args: argparse.Namespace, build: dict[str, Any], deploy: dict[str, Any], steps: list[dict[str, Any]]) -> bool:
    sha = step_payload(steps, "bpf-counter-sha")
    check = step_payload(steps, "bpf-counter-check-only")
    return (
        build.get("output_sha256") in sha
        and DEFAULT_COUNTER_MARKER in check
        and "result=check-only" in check
        and "attach_attempted=0" in check
        and bool(deploy.get("ok"))
    )


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0, proof_base)
    helper_item: dict[str, Any] | None = None
    boot_item: dict[str, Any] | None = None
    bpf_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    reboot: dict[str, Any] = {}
    mounted_before = False
    try:
        run_step(args, store, steps, "proc-mounts-before-tracefs", ["cat", "/proc/mounts"], 15.0, proof_base)
        mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before-tracefs"))
        if not mounted_before:
            run_step(args, store, steps, "tracefs-mount", ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", DEFAULT_TRACEFS_TARGET], 20.0, proof_base)
        run_step(args, store, steps, "bpf-counter-start", ["run", args.busybox, "sh", "-c", bpf_start_script(args, proof_base)], 20.0, proof_base)

        for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
            run_step(args, store, steps, f"v782-{name}", command, timeout, proof_base)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof_base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", base.FIRMWARE_CLASS_PATH], 10.0, proof_base)
        for path in base.GLOBAL_MODEM_BLOB_PATHS + base.WLAN_FIRMWARE_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0, proof_base)

        dev = base.parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        holder = base.holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        write_capture(store, "holder-script-redacted", holder.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF"))
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", holder], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-holder", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mss-crash-after-holder", ["cat", base.MSS_CRASH_COUNT], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", base.MDM3_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", base.MDM3_CRASH_COUNT], 10.0, proof_base)
        qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)
        if qrtr_wait.get("seen"):
            helper_item = run_step(args, store, steps, "lower-companion-start-only", v750.helper_command(args), args.companion_runtime_sec + 75.0, proof_base)
        run_step(args, store, steps, "wlanbootctl-status-before-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        boot_item = run_step(
            args,
            store,
            steps,
            "boot-wlan-observe",
            ["run", args.wlanbootctl, "boot-observe", str(args.boot_observe_sec)],
            args.boot_observe_sec + 35.0,
            proof_base,
        )
        run_step(args, store, steps, "wlanbootctl-status-after-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-boot", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-boot", ["cat", base.MDM3_STATE], 10.0, proof_base)
        for path in v750.POST_BOOT_PATHS:
            v750.read_path_capture(args, store, steps, path, proof_base)
        bpf_item = run_step(args, store, steps, "bpf-counter-collect", ["run", args.busybox, "sh", "-c", bpf_collect_script(args, proof_base)], args.counter_duration_sec + 25.0, proof_base)
        if not mounted_before:
            run_step(args, store, steps, "tracefs-umount", ["run", args.busybox, "umount", DEFAULT_TRACEFS_TARGET], 20.0, proof_base)
        run_step(args, store, steps, "proc-mounts-after-tracefs", ["cat", "/proc/mounts"], 15.0, proof_base)
        after = run_step(args, store, steps, "dmesg-after-boot", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = base.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = v750.extended_marker_summary(delta)
    finally:
        reboot = base.reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    helper = v750.helper_surface(str((helper_item or {}).get("payload") or ""))
    after_status = step_payload(steps, "wlanbootctl-status-after-boot")
    proc_net_dev = step_payload(steps, "post-boot-cat-proc-net-dev")
    ieee80211 = step_payload(steps, "post-boot-ls-sys-class-ieee80211")
    sys_class_net = step_payload(steps, "post-boot-ls-sys-class-net")
    bpf_payload = str((bpf_item or {}).get("payload") or "")
    event_count_match = re.search(r"^event_count=(\d+)$", bpf_payload, re.MULTILINE)
    return {
        "base": proof_base,
        "mounted_before_tracefs": mounted_before,
        "mounted_after_tracefs": tracefs_mounted(step_payload(steps, "proc-mounts-after-tracefs")),
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: base.path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in base.GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: base.path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in base.WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_boot": step_payload(steps, "mss-state-after-boot").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_boot": step_payload(steps, "mdm3-state-after-boot").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": bool(qrtr_wait.get("seen")),
        "helper_result": helper,
        "boot_wlan_write_executed": bool(boot_item),
        "boot_wlan_ok": bool((boot_item or {}).get("ok")),
        "boot_wlan_status": (boot_item or {}).get("status"),
        "qcwlanstate_after": "wlanboot.status.qcwlanstate.value=ON" in after_status,
        "dev_wlan_after": "wlanboot.status.dev_wlan.exists=1" in after_status,
        "wlan0_after": "wlan0" in proc_net_dev or "wlan0" in sys_class_net,
        "wiphy_after": "phy" in ieee80211 or "wlan" in ieee80211.lower(),
        "qrtr_services_after_boot": base.qrtr_service_counts(step_payload(steps, "post-boot-cat-proc-net-qrtr")),
        "bpf_counter_payload_file": (bpf_item or {}).get("file"),
        "bpf_counter_result": base.parse_keys(bpf_payload),
        "bpf_event_count": int(event_count_match.group(1)) if event_count_match else None,
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def preflight_blockers(args: argparse.Namespace,
                       build: dict[str, Any],
                       deploy: dict[str, Any],
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any],
                       v732: dict[str, Any],
                       v490: dict[str, Any]) -> list[str]:
    blockers = v750.preflight_blockers(args, steps, preflight, v731, v732, v490)
    if build.get("compile", {}).get("rc") != 0 or not build.get("static_no_interp") or not build.get("marker_present") or not build.get("counter_present"):
        blockers.append("bpf-counter-build-not-ready")
    if not deploy.get("ok"):
        blockers.append("bpf-counter-deploy-failed")
    if not bpf_ready(args, build, deploy, steps):
        blockers.append("bpf-counter-runtime-not-ready")
    if args.command == "run" and not (args.allow_bpf_counter_deploy and args.allow_tracefs_mount and args.allow_bpf_attach and args.allow_lower_window_boot_wlan and args.assume_yes):
        blockers.append("live-v782-not-approved")
    if not (20 <= args.counter_duration_sec <= 120):
        blockers.append("counter-duration-out-of-range")
    if not (5 <= args.boot_observe_sec <= 30):
        blockers.append("boot-observe-window-out-of-range")
    return sorted(set(blockers))


def build_checks(args: argparse.Namespace,
                 build: dict[str, Any],
                 deploy: dict[str, Any],
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        {
            "name": "bpf-counter-build",
            "status": "pass" if build.get("compile", {}).get("rc") == 0 and build.get("static_no_interp") and build.get("marker_present") and build.get("counter_present") else "blocked",
            "detail": {key: build.get(key) for key in ("output", "output_size", "output_sha256", "static_no_interp", "marker_present", "counter_present")},
            "next_step": "fix counter helper build before live",
        },
        {
            "name": "bpf-counter-deploy",
            "status": "pass" if deploy.get("ok") else "blocked",
            "detail": {key: deploy.get(key) for key in ("method", "chunks_written", "chunks", "error")},
            "next_step": "redeploy counter helper",
        },
        {
            "name": "bpf-counter-runtime",
            "status": "pass" if bpf_ready(args, build, deploy, steps) else "blocked",
            "detail": {"sha_seen": build.get("output_sha256") in step_payload(steps, "bpf-counter-sha"), "check_only": step_payload(steps, "bpf-counter-check-only").splitlines()[:8]},
            "next_step": "verify remote counter helper before transition",
        },
        {
            "name": "v750-preflight",
            "status": "pass" if not [item for item in blockers if item not in {"live-v782-not-approved"}] else "blocked",
            "detail": {"blockers": blockers, "preflight": preflight},
            "next_step": "clear inherited lower-window blockers",
        },
    ]
    if live:
        helper = live.get("helper_result") or {}
        counts = ((live.get("markers") or {}).get("counts") or {})
        checks.extend([
            {
                "name": "bpf-count-observer",
                "status": "pass" if live.get("bpf_event_count") is not None and (live.get("bpf_counter_result") or {}).get("result") == "attach-count-pass" else "blocked",
                "detail": {"event_count": live.get("bpf_event_count"), "result": (live.get("bpf_counter_result") or {}).get("result"), "file": live.get("bpf_counter_payload_file")},
                "next_step": "if missing, inspect BPF counter transcript",
            },
            {
                "name": "lower-window-transition",
                "status": "pass" if live.get("holder_opened") and (live.get("qrtr_rx_wait") or {}).get("seen") and helper.get("order") == v750.EXPECTED_ORDER and live.get("boot_wlan_write_executed") else "blocked",
                "detail": {"holder": live.get("holder_opened"), "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen"), "helper_order": helper.get("order"), "boot_wlan": live.get("boot_wlan_write_executed")},
                "next_step": "re-run only after lower-window preconditions are restored",
            },
            {
                "name": "wifi-readiness",
                "status": "finding",
                "detail": {"wlan0": live.get("wlan0_after"), "wiphy": live.get("wiphy_after"), "service69": (live.get("qrtr_services_after_boot") or {}).get("69", 0), "markers": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlfw", "bdf", "wlan0", "qcwlanstate")}},
                "next_step": "only proceed to scan/connect if wlan0/wiphy appears",
            },
            {
                "name": "cleanup",
                "status": "pass" if not live.get("mounted_after_tracefs") and (live.get("reboot_cleanup") or {}).get("status_healthy") else "blocked",
                "detail": {"tracefs_after": live.get("mounted_after_tracefs"), "reboot": live.get("reboot_cleanup")},
                "next_step": "verify native health before any next gate",
            },
        ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return ("v782-bpf-counter-boot-wlan-plan-ready", True, "plan-only; no device command executed", "run gated V782 proof")
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return ("v782-bpf-counter-boot-wlan-blocked", False, "blocked by " + ", ".join(blocked), "fix blockers before retry")
    if not live:
        return ("v782-bpf-counter-boot-wlan-preflight-ready", True, "build/deploy/preflight ready", "run gated V782 proof")
    if live.get("wlan0_after") or live.get("wiphy_after"):
        return ("v782-bpf-counter-boot-wlan-netdev-appeared", True, "BPF-counted transition produced wlan0/wiphy evidence", "plan scan-only readiness gate")
    if (live.get("qrtr_services_after_boot") or {}).get("69", 0):
        return ("v782-bpf-counter-boot-wlan-service69-appeared", True, "BPF-counted transition produced WLFW service 69 evidence", "classify service69-to-netdev gap")
    return ("v782-bpf-counter-boot-wlan-counted-control-surface-only", True, "BPF-counted lower-window transition completed but still did not produce WLFW/netdev readiness", "use counted PIL evidence to choose the next lower trigger")


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    checks = manifest.get("checks") or []
    counts = ((live.get("markers") or {}).get("counts") or {})
    return "\n".join([
        "# V782 BPF Counter Boot WLAN Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], [
            [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
            for check in checks
        ]),
        "",
        "## Live",
        "",
        markdown_table(["signal", "value"], [
            ["bpf_event_count", live.get("bpf_event_count", "")],
            ["bpf_result", (live.get("bpf_counter_result") or {}).get("result", "")],
            ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_boot', '')}"],
            ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_boot', '')}"],
            ["qrtr_services", json.dumps(live.get("qrtr_services_after_boot", {}), sort_keys=True)],
            ["wlan0_after", live.get("wlan0_after", "")],
            ["wiphy_after", live.get("wiphy_after", "")],
            ["marker_counts", json.dumps({key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlfw", "bdf", "wlan0", "qcwlanstate")}, sort_keys=True)],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    v731 = base.load_json_if_exists(args.v731_manifest)
    v732 = base.load_json_if_exists(args.v732_manifest)
    v490 = base.load_json_if_exists(args.v490_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    build = {"output_sha256": ""}
    deploy: dict[str, Any] = {}
    blockers: list[str] = []
    if args.command != "plan":
        build = build_counter(args, store)
        if args.allow_bpf_counter_deploy and args.assume_yes and build.get("output_exists"):
            deploy = deploy_counter(args, store, build)
        else:
            deploy = {"ok": False, "error": "deploy requires --allow-bpf-counter-deploy --assume-yes"}
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, build, deploy, steps, preflight, v731, v732, v490)
        if args.command == "run" and not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, build, deploy, steps, preflight, live, blockers)
    decision, ok, reason, next_step = decide(args, checks, live)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v782",
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "build": build,
        "deploy": deploy,
        "preflight": preflight,
        "steps": steps,
        "checks": checks,
        "live": live or {},
        "device_commands_executed": args.command != "plan",
        "device_mutations": bool(live),
        "bpf_counter_deploy_executed": bool(deploy.get("ok")),
        "bpf_attach_executed": bool(live),
        "firmware_mounts_executed": bool(live),
        "subsys_modem_open_attempted": bool(live),
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
        "boot_wlan_write_executed": bool((live or {}).get("boot_wlan_write_executed")),
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "reboot_cleanup_executed": bool(live),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"bpf_attach_executed: {manifest['bpf_attach_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
