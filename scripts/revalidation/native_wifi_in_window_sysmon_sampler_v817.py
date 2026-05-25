#!/usr/bin/env python3
"""V817 bounded in-window subsystem/sysmon/service-locator sampler.

The runner refreshes current-boot SELinux prep, then replays the established
V735 lower window while collecting V815-style read-only snapshots before the
modem holder, after the holder/QRTR readiness wait, and after the lower
companion/CNSS diagnostic stack.  It remains below service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, esoc0 open, bind/unbind,
module load/unload, and custom-kernel flash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_current_cnss_only_observer_v735 as v735
import native_wifi_holder_lower_companion_v733 as base
import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text
from native_wifi_firmware_mounted_modem_holder_v731 import (
    FIRMWARE_CLASS_PATH,
    GLOBAL_MODEM_BLOB_PATHS,
    MDM3_CRASH_COUNT,
    MDM3_STATE,
    MSS_CRASH_COUNT,
    MSS_STATE,
    dmesg_delta,
    holder_script,
    marker_summary,
    parse_dev,
    path_exists,
    reboot_and_wait,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v817-in-window-sysmon-sampler")
LATEST_POINTER = Path("tmp/wifi/latest-v817-in-window-sysmon-sampler.txt")
DEFAULT_V816_MANIFEST = Path("tmp/wifi/v816-idle-trigger-delta-classifier/manifest.json")
DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
DEFAULT_COMPANION_RUNTIME_SEC = 30
PROOF_PREFIX = "/tmp/a90-v817-"
V401_APPROVAL = "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"
V490_APPROVAL = "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up"
EXPECTED_V816_DECISION = "v816-trigger-advances-mss-sysmon-not-mdm3-service"

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

FORBIDDEN_SNAPSHOT_TERMS = (
    " mount ",
    " umount ",
    " echo ",
    " tee ",
    " dd ",
    " mknod ",
    " mkdir ",
    " rm ",
    " rmdir ",
    " chmod ",
    " chown ",
    " cp ",
    " mv ",
    "boot_wlan",
    "qcwlanstate on",
    "qcwlanstate off",
    "/bind",
    "/unbind",
    "driver_override",
    "drivers_probe",
    "insmod",
    "rmmod",
    "modprobe",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)

FORBIDDEN_ACTIONS = (
    "custom kernel flash, boot image write, or partition write",
    "service-manager start, Wi-Fi HAL start, scan/connect/link-up, or credential use",
    "DHCP, route change, or external ping",
    "boot_wlan, qcwlanstate write, esoc0 open, bind/unbind, driver override, or module load/unload",
    "sysfs/debugfs/control write outside established firmware mount/holder/cleanup path",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v735.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v816-manifest", type=Path, default=DEFAULT_V816_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def configure_base() -> None:
    v735.configure_base()
    base.PROOF_PREFIX = PROOF_PREFIX


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", ANSI_RE.sub("", text))


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
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


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def run_host_step(store: EvidenceStore,
                  name: str,
                  command: list[str],
                  timeout: float) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        timed_out = False
        rc = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
    ended = dt.datetime.now(dt.timezone.utc)
    transcript = "\n".join([
        "$ " + " ".join(command),
        f"[rc] {rc}",
        f"[timed_out] {timed_out}",
        "[stdout]",
        stdout.rstrip(),
        "[stderr]",
        stderr.rstrip(),
        "",
    ])
    rel = f"host/{name}.txt"
    store.write_text(rel, transcript)
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "timed_out": timed_out,
        "ok": rc == 0 and not timed_out,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_sec": (ended - started).total_seconds(),
        "file": rel,
        "stdout_tail": stdout.splitlines()[-12:],
        "stderr_tail": stderr.splitlines()[-12:],
    }


def hide_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--hide-on-busy",
        "hide",
    ]


def mountsystem_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--hide-on-busy",
        "mountsystem",
        "ro",
    ]


def prep_commands(args: argparse.Namespace, root: Path) -> tuple[list[str], list[str]]:
    v401_dir = root / "prep" / "v401"
    v490_dir = root / "prep" / "v490"
    return (
        [
            "python3",
            "scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py",
            "--out-dir",
            str(v401_dir),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--approval-phrase",
            V401_APPROVAL,
            "--apply",
            "--assume-yes",
            "run",
        ],
        [
            "python3",
            "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
            "--out-dir",
            str(v490_dir),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--timeout",
            str(args.timeout),
            "--expect-version",
            "A90 Linux init 0.9.68 (v724)",
            "--helper-sha256",
            args.helper_sha256,
            "--approval-phrase",
            V490_APPROVAL,
            "--apply",
            "--assume-yes",
            "run",
        ],
    )


def validate_snapshot_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_SNAPSHOT_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V817 snapshot term {term!r}: {' '.join(command)}")


def run_snapshot_step(args: argparse.Namespace,
                      store: EvidenceStore,
                      steps: list[dict[str, Any]],
                      phase: str,
                      name: str,
                      command: list[str],
                      timeout: float | None = None) -> dict[str, Any]:
    validate_snapshot_command(command)
    capture = run_capture(args, f"{phase}-{name}", command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    text = redact(text)
    item = capture_to_manifest(capture)
    item["file"] = f"native/{safe_name(phase)}-{safe_name(name)}.txt"
    item["payload"] = text
    item["phase"] = phase
    item["ok"] = capture.ok
    store.write_text(item["file"], text.rstrip() + "\n")
    steps.append(item)
    return item


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def snapshot_scripts(args: argparse.Namespace) -> list[tuple[str, list[str], float]]:
    bb = args.busybox
    subsys_script = (
        f"BB={bb}; "
        "printf '== msm_subsys_devices ==\\n'; $BB ls -la /sys/bus/msm_subsys/devices 2>&1 || true; "
        "for d in /sys/bus/msm_subsys/devices/*; do [ -e \"$d\" ] || continue; "
        "printf '== SUBSYS %s ==\\n' \"$d\"; $BB readlink \"$d\" 2>&1 || true; "
        "for f in name state crash_count restart_level firmware_name; do "
        "printf '%s=' \"$f\"; if [ -r \"$d/$f\" ]; then $BB cat \"$d/$f\" 2>&1 | $BB head -c 400; else printf 'unreadable'; fi; printf '\\n'; "
        "done; done; true"
    )
    esoc_script = (
        f"BB={bb}; "
        "for p in /sys/bus/esoc/devices /sys/bus/esoc/devices/* /sys/class/subsys /sys/class/subsys/* /dev/subsys* /dev/esoc*; do "
        "printf '== %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -80; fi; "
        "for f in uevent power/runtime_status power/control; do "
        "if [ -r \"$p/$f\" ]; then printf 'FILE %s/%s\\n' \"$p\" \"$f\"; $BB cat \"$p/$f\" 2>&1 | $BB head -c 500; printf '\\n'; fi; "
        "done; done; true"
    )
    proc_script = (
        f"BB={bb}; "
        "printf '== proc_net_qrtr ==\\n'; $BB cat /proc/net/qrtr 2>&1 || true; "
        "printf '\\n== proc_net_netlink_focus ==\\n'; $BB cat /proc/net/netlink 2>&1 | $BB head -120; "
        "printf '\\n== ps_focus ==\\n'; $BB ps 2>&1 | $BB grep -Ei 'qrtr|rmt|tftp|pd-mapper|cnss|mdm|qmi|diag|wifi' || true; "
        "true"
    )
    icnss_script = (
        f"BB={bb}; "
        "for p in /sys/bus/platform/drivers/icnss /sys/bus/platform/devices/18800000.qcom,icnss /sys/module/wlan /sys/module/wlan/parameters /sys/class/net/wlan0 /dev/wlan /dev/qcwlanstate; do "
        "printf '== %s ==\\n' \"$p\"; $BB ls -ld \"$p\" 2>&1 || true; "
        "if [ -d \"$p\" ]; then $BB ls -la \"$p\" 2>&1 | $BB head -80; fi; "
        "done; true"
    )
    dmesg_script = (
        f"BB={bb}; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'sysmon-qmi|sysmon|service-notifier|servreg|service.loc|servloc|qrtr: Modem QMI Readiness|subsys|ssr|pil|modem|mdm3|esoc|wlan_pd|icnss_qmi|WLAN FW|BDF file|wlan0|icnss: Modules not initialized|wlan: Loading driver|qcwlanstate' | $BB tail -n 260 || true; "
        "true"
    )
    return [
        ("subsys", shell_cmd(args, subsys_script), 45.0),
        ("esoc", shell_cmd(args, esoc_script), 45.0),
        ("proc", shell_cmd(args, proc_script), 45.0),
        ("icnss", shell_cmd(args, icnss_script), 45.0),
        ("dmesg", shell_cmd(args, dmesg_script), 60.0),
    ]


def collect_snapshot(args: argparse.Namespace,
                     store: EvidenceStore,
                     steps: list[dict[str, Any]],
                     phase: str) -> None:
    for name, command, timeout in snapshot_scripts(args):
        run_snapshot_step(args, store, steps, phase, name, command, timeout)


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def phase_payload(steps: list[dict[str, Any]], phase: str, name: str) -> str:
    target_name = f"{phase}-{name}"
    for step in steps:
        if step.get("name") == target_name:
            return str(step.get("payload") or "")
    return ""


def parse_subsys_blocks(text: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("== SUBSYS ") and line.endswith(" =="):
            current = line[len("== SUBSYS "):-len(" ==")]
            blocks[current] = {"_label": current}
            continue
        if current and "=" in line:
            key, value = line.split("=", 1)
            blocks[current][key.strip()] = value.strip()
    return blocks


def find_state(blocks: dict[str, dict[str, str]], wanted: tuple[str, ...]) -> str:
    for attrs in blocks.values():
        haystack = " ".join([attrs.get("_label", ""), *attrs.values()]).lower()
        if any(item in haystack for item in wanted):
            return attrs.get("state", "")
    return ""


def count_patterns(text: str) -> dict[str, int]:
    lower = text.lower()
    return {
        "sysmon_qmi": lower.count("sysmon-qmi"),
        "sysmon_any": lower.count("sysmon"),
        "service_notifier": lower.count("service-notifier"),
        "service_notifier_180": len(re.findall(r"service-notifier.*\\b180\\b", lower)),
        "service_notifier_74": len(re.findall(r"service-notifier.*\\b74\\b", lower)),
        "service_locator": lower.count("service.loc") + lower.count("servloc"),
        "qrtr_modem_readiness": lower.count("qrtr: modem qmi readiness"),
        "wlan_pd": lower.count("wlan_pd"),
        "wlfw": lower.count("wlfw"),
        "bdf": lower.count("bdf"),
        "wlan0": lower.count("wlan0"),
        "kernel_warning": lower.count("warning:") + lower.count("kernel panic"),
    }


def snapshot_summary(steps: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    subsys = phase_payload(steps, phase, "subsys")
    esoc = phase_payload(steps, phase, "esoc")
    proc = phase_payload(steps, phase, "proc")
    icnss = phase_payload(steps, phase, "icnss")
    dmesg = phase_payload(steps, phase, "dmesg")
    blocks = parse_subsys_blocks(subsys)
    runtime_counts = count_patterns("\n".join([proc, dmesg]))
    surface_counts = count_patterns("\n".join([subsys, esoc, icnss]))
    return {
        "phase": phase,
        "all_steps_ok": all(
            bool(step.get("ok"))
            for step in steps
            if step.get("phase") == phase
        ),
        "subsys_count": len(blocks),
        "mss_or_modem_state": find_state(blocks, ("mss", "modem")),
        "mdm3_state": find_state(blocks, ("mdm3", "esoc0")),
        "esoc_surface_present": "== /sys/bus/esoc/devices ==" in esoc and "esoc0" in esoc,
        "icnss_platform_present": "18800000.qcom,icnss" in icnss,
        "wlan0_present": "/sys/class/net/wlan0" in icnss and "No such file" not in icnss,
        "dev_qcwlanstate_present": "/dev/qcwlanstate" in icnss and "No such file" not in icnss,
        "runtime_counts": runtime_counts,
        "surface_counts": surface_counts,
    }


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             preflight: dict[str, Any]) -> dict[str, Any]:
    label = safe_name(args.proof_id) if args.proof_id else dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    proof_base = PROOF_PREFIX + label
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    before = base.run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    reboot: dict[str, Any] = {}
    helper_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
            item = base.run_step(args, store, steps, f"v817-{name}", command, timeout, proof_base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        base.run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof_base)
        base.run_step(args, store, steps, "mounted-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0, proof_base)
        for path in GLOBAL_MODEM_BLOB_PATHS + base.WLAN_FIRMWARE_PATHS:
            base.run_step(args, store, steps, f"mounted-stat-{base.safe_name(path)}", ["stat", path], 10.0, proof_base)

        collect_snapshot(args, store, steps, "before-holder")

        dev = parse_dev(base.step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        safe_script = script.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF")
        base.write_capture(store, "holder-script-redacted", safe_script)
        base.run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, proof_base)
        base.run_step(args, store, steps, "mss-state-after-holder", ["cat", MSS_STATE], 10.0, proof_base)
        base.run_step(args, store, steps, "mss-crash-after-holder", ["cat", MSS_CRASH_COUNT], 10.0, proof_base)
        base.run_step(args, store, steps, "mdm3-state-after-holder", ["cat", MDM3_STATE], 10.0, proof_base)
        base.run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", MDM3_CRASH_COUNT], 10.0, proof_base)
        qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)

        collect_snapshot(args, store, steps, "after-holder")

        if qrtr_wait.get("seen"):
            helper_item = base.run_step(args, store, steps, "lower-companion-start-only", v735.helper_command(args), args.companion_runtime_sec + 75.0, proof_base)
        else:
            helper_item = {
                "name": "lower-companion-start-only",
                "ok": True,
                "rc": 0,
                "status": "skipped",
                "command": " ".join(v735.helper_command(args)),
                "duration_sec": 0,
                "payload": "skipped: QRTR RX marker was not observed\n",
                "file": base.write_capture(store, "lower-companion-start-only-skipped", "skipped: QRTR RX marker was not observed\n"),
            }
            steps.append(helper_item)
        base.run_step(args, store, steps, "mss-state-after-companion", ["cat", MSS_STATE], 10.0, proof_base)
        base.run_step(args, store, steps, "mdm3-state-after-companion", ["cat", MDM3_STATE], 10.0, proof_base)
        base.run_step(args, store, steps, "proc-net-qrtr-after-companion", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, proof_base)

        collect_snapshot(args, store, steps, "after-companion")

        base.run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0, proof_base)
        after = base.run_step(args, store, steps, "dmesg-after-companion", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        base.write_capture(store, "dmesg-delta", delta)
        markers = marker_summary(delta)
    finally:
        reboot = reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(base.step_payload(steps, "mounted-proc-mounts"))
    helper = v735.normalize_helper(base.helper_surface(str((helper_item or {}).get("payload") or "")))
    helper_keys = helper.get("keys") if isinstance(helper.get("keys"), dict) else {}
    return {
        "base": proof_base,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": base.step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: path_exists(base.step_payload(steps, f"mounted-stat-{base.safe_name(path)}"))
            for path in GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: path_exists(base.step_payload(steps, f"mounted-stat-{base.safe_name(path)}"))
            for path in base.WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in base.step_payload(steps, "start-modem-holder"),
        "mss_before": base.step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": base.step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_companion": base.step_payload(steps, "mss-state-after-companion").strip(),
        "mdm3_before": base.step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": base.step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_companion": base.step_payload(steps, "mdm3-state-after-companion").strip(),
        "mss_crash_before": base.step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": base.step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": base.step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": base.step_payload(steps, "mdm3-crash-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": bool(qrtr_wait.get("seen")),
        "helper_result": helper,
        "helper_ok": bool((helper_item or {}).get("ok")),
        "helper_status": (helper_item or {}).get("status"),
        "qrtr_readback": v735.readback_summary(helper_keys),
        "qrtr_services_after_companion": base.qrtr_service_counts(base.step_payload(steps, "proc-net-qrtr-after-companion")),
        "snapshots": {
            phase: snapshot_summary(steps, phase)
            for phase in ("before-holder", "after-holder", "after-companion")
        },
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def build_checks(args: argparse.Namespace,
                 v816: dict[str, Any],
                 prep: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "bounded in-window sampler plan; no device command executed",
            "next_step": "run V817 after current-boot V401/V490 refresh",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "v816-route-ready",
            "status": "pass"
            if v816.get("pass") is True and v816.get("decision") == EXPECTED_V816_DECISION
            else "blocked",
            "detail": {"decision": v816.get("decision"), "pass": v816.get("pass")},
            "next_step": "complete V816 before in-window sampling",
        },
        {
            "name": "current-boot-prep",
            "status": "pass" if prep.get("v401", {}).get("pass") and prep.get("v490", {}).get("pass") else "blocked",
            "detail": prep,
            "next_step": "refresh V401/V490 before lower-window sampling",
        },
        {
            "name": "preflight-blockers",
            "status": "pass" if not blockers else "blocked",
            "detail": {"blockers": blockers},
            "next_step": "clear inherited lower-window blockers",
        },
    ]
    if not live:
        return checks
    helper = live.get("helper_result") or {}
    helper_forbidden = {
        key: helper.get(key)
        for key in ("service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")
    }
    readback = live.get("qrtr_readback") or {}
    snapshots = live.get("snapshots") or {}
    after_holder = snapshots.get("after-holder") or {}
    after_companion = snapshots.get("after-companion") or {}
    trigger_counts = ((live.get("markers") or {}).get("counts") or {})
    snapshots_ok = all((snapshots.get(phase) or {}).get("all_steps_ok") for phase in ("before-holder", "after-holder", "after-companion"))
    holder_progress = live.get("holder_opened") and live.get("mss_after_holder") == "ONLINE" and (live.get("qrtr_rx_wait") or {}).get("seen")
    service_absent = (
        int_value((after_companion.get("runtime_counts") or {}).get("service_notifier_74")) == 0
        and int_value((after_companion.get("runtime_counts") or {}).get("wlan_pd")) == 0
        and int_value((after_companion.get("runtime_counts") or {}).get("wlfw")) == 0
        and int_value(readback.get("service_events")) == 0
        and int_value(readback.get("timeouts")) == 0
    )
    checks.extend([
        {
            "name": "firmware-holder-window",
            "status": "pass" if all((live.get("mounted_hits") or {}).values()) and holder_progress else "blocked",
            "detail": {
                "mounted_hits": live.get("mounted_hits"),
                "holder_opened": live.get("holder_opened"),
                "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")],
                "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_companion")],
                "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen"),
            },
            "next_step": "if missing, fix holder/mount parity before interpreting snapshots",
        },
        {
            "name": "snapshot-completeness",
            "status": "pass" if snapshots_ok else "blocked",
            "detail": {phase: (snapshots.get(phase) or {}).get("all_steps_ok") for phase in ("before-holder", "after-holder", "after-companion")},
            "next_step": "rerun read-only sampler if any snapshot failed",
        },
        {
            "name": "below-hal-contract",
            "status": "pass"
            if all(int_value(value) == 0 for value in helper_forbidden.values()) and int_value(readback.get("qmi_attempted")) == 0
            else "blocked",
            "detail": {"helper": helper_forbidden, "readback": readback},
            "next_step": "discard if helper crossed HAL/connect or sent QMI payloads",
        },
        {
            "name": "in-window-delta",
            "status": "finding",
            "detail": {
                "before_holder": snapshots.get("before-holder"),
                "after_holder": after_holder,
                "after_companion": after_companion,
                "trigger_markers": trigger_counts,
                "readback": readback,
            },
            "next_step": "use phase deltas to select next lower blocker",
        },
        {
            "name": "service-publication-result",
            "status": "pass" if service_absent else "review",
            "detail": {
                "after_holder_runtime": after_holder.get("runtime_counts"),
                "after_companion_runtime": after_companion.get("runtime_counts"),
                "readback": readback,
            },
            "next_step": "if publication appears, route to WLFW/BDF readiness; otherwise isolate mdm3/service-locator/sysmon state",
        },
        {
            "name": "kernel-warning-review",
            "status": "blocked" if int_value(trigger_counts.get("kernel_warning")) else "pass",
            "detail": {"kernel_warning": trigger_counts.get("kernel_warning")},
            "next_step": "do not repeat or widen if warning appears",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if (live.get("reboot_cleanup") or {}).get("status_healthy") else "blocked",
            "detail": live.get("reboot_cleanup") or {},
            "next_step": "manually verify native if cleanup did not prove health",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v817-in-window-sysmon-sampler-plan-ready",
            True,
            "plan-only; no device command executed",
            "run bounded in-window sampler",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v817-in-window-sysmon-sampler-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    snapshots = (live or {}).get("snapshots") or {}
    after_companion = snapshots.get("after-companion") or {}
    runtime = after_companion.get("runtime_counts") or {}
    readback = (live or {}).get("qrtr_readback") or {}
    if any(int_value(runtime.get(key)) for key in ("service_notifier_74", "wlan_pd", "wlfw", "bdf", "wlan0")) or int_value(readback.get("service_events")):
        return (
            "v817-in-window-service-publication-advanced",
            True,
            "in-window sampler saw service publication or WLFW/BDF/wlan0 progress",
            "capture FW_READY/BDF/netdev readiness before Wi-Fi HAL or connect",
        )
    return (
        "v817-in-window-mdm3-service-gap-confirmed",
        True,
        "in-window snapshots confirm holder/companion advance mss/QRTR/sysmon but mdm3 remains OFFLINING and service74/WLAN-PD/WLFW stay absent",
        "V818 should isolate mdm3/esoc0 service-locator/sysmon registration state without esoc0 open or HAL/connect",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v816 = load_json(args.v816_manifest)
    host_steps: list[dict[str, Any]] = []
    prep: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        v401_cmd, v490_cmd = prep_commands(args, store.run_dir)
        host_steps.append(run_host_step(store, "v817-hide-before-prep", hide_command(args), 60.0))
        host_steps.append(run_host_step(store, "v817-v401", v401_cmd, 180.0))
        v401_manifest = load_json(store.run_dir / "prep" / "v401" / "manifest.json")
        host_steps.append(run_host_step(store, "v817-mountsystem-ro", mountsystem_command(args), 120.0))
        host_steps.append(run_host_step(store, "v817-v490", v490_cmd, 300.0))
        v490_manifest = load_json(store.run_dir / "prep" / "v490" / "manifest.json")
        prep = {
            "v401": {"ok": host_steps[-3]["ok"], "decision": v401_manifest.get("decision"), "pass": v401_manifest.get("pass")},
            "mountsystem": {"ok": host_steps[-2]["ok"], "rc": host_steps[-2]["rc"], "file": host_steps[-2]["file"]},
            "v490": {"ok": host_steps[-1]["ok"], "decision": v490_manifest.get("decision"), "pass": v490_manifest.get("pass")},
        }
        if prep["v401"]["pass"] and prep["v490"]["pass"]:
            args.v490_manifest = store.run_dir / "prep" / "v490" / "manifest.json"
            preflight = v735.capture_preflight(args, store, steps)
            v731 = base.load_json_if_exists(args.v731_manifest)
            v732 = base.load_json_if_exists(args.v732_manifest)
            v734 = base.load_json_if_exists(args.v734_manifest)
            blockers = v735.preflight_blockers(args, steps, preflight, v731, v732, v734, v490_manifest)
            if not blockers:
                live = run_live(args, store, steps, preflight)
    checks = build_checks(args, v816, prep, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    helper = (live or {}).get("helper_result") or {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v817",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "host_steps": host_steps,
        "prep": prep,
        "v816": {"decision": v816.get("decision"), "pass": v816.get("pass"), "path": v816.get("path")},
        "preflight": preflight,
        "steps": steps,
        "live": live or {},
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": bool(live),
        "firmware_mounts_executed": bool(live),
        "subsys_modem_opened": bool((live or {}).get("holder_opened")),
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
        "cnss_diag_start_executed": bool(int_value(helper.get("cnss_diag"))),
        "cnss_daemon_start_executed": bool(int_value(helper.get("cnss_daemon"))),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "esoc0_open_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_cleanup_executed": bool(live),
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    snapshots = live.get("snapshots") or {}
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    phase_rows = []
    for phase in ("before-holder", "after-holder", "after-companion"):
        snap = snapshots.get(phase) or {}
        phase_rows.append([
            phase,
            str(snap.get("mss_or_modem_state")),
            str(snap.get("mdm3_state")),
            json.dumps(snap.get("runtime_counts", {}), sort_keys=True),
            json.dumps({"esoc": snap.get("esoc_surface_present"), "icnss": snap.get("icnss_platform_present"), "wlan0": snap.get("wlan0_present")}, sort_keys=True),
        ])
    return "\n".join([
        "# V817 In-Window Sysmon Sampler",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- subsys_modem_opened: `{manifest['subsys_modem_opened']}`",
        f"- lower_companion_start_executed: `{manifest['lower_companion_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Phase Snapshots",
        "",
        markdown_table(["phase", "mss/modem", "mdm3/esoc0", "runtime_counts", "surface"], phase_rows),
        "",
    ])


def main() -> int:
    configure_base()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    store.mkdir("host")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"lower_companion_start_executed: {manifest['lower_companion_start_executed']}")
    print(f"cnss_diag_start_executed: {manifest['cnss_diag_start_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
