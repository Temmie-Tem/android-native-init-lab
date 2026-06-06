#!/usr/bin/env python3
"""V1372 bounded provider-held corrected-RC1 enumerate proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_pci_msm_status_case_live_v1365 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1372-provider-held-pcie1-enumerate-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1372-provider-held-pcie1-enumerate-live.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1372_PROVIDER_HELD_PCIE1_ENUMERATE_LIVE_2026-06-01.md")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEBUGFS_ROOT = base.DEBUGFS_ROOT
PCI_MSM_DEBUGFS = base.PCI_MSM_DEBUGFS
SUBSYS_ESOC0 = "/dev/subsys_esoc0"
BASE_PATH = "/tmp/a90-v1372-provider-pcie"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--provider-delay-ms", type=int, default=255)
    parser.add_argument("--post-enumerate-sec", type=int, default=4)
    parser.add_argument("--allow-subsys-esoc0-open", action="store_true")
    parser.add_argument("--allow-case11-enumerate", action="store_true")
    parser.add_argument("--allow-mknod", action="store_true")
    parser.add_argument("--allow-reboot-cleanup", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run", "reclassify"))
    return parser.parse_args()


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if args.command != "run":
        return missing
    if not args.allow_subsys_esoc0_open:
        missing.append("--allow-subsys-esoc0-open")
    if not args.allow_case11_enumerate:
        missing.append("--allow-case11-enumerate")
    if not args.allow_mknod:
        missing.append("--allow-mknod")
    if not args.allow_reboot_cleanup:
        missing.append("--allow-reboot-cleanup")
    if not args.assume_yes:
        missing.append("--assume-yes")
    return missing


def capture_native(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    command: list[str],
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = capture.text if capture.text else capture.error + "\n"
    auto_hide = False
    if capture.status == "busy" or "[busy]" in text:
        auto_hide = True
        run_capture(args, f"{name}-hide-on-busy", ["hide"], timeout=min(timeout or args.timeout, 8.0))
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if text else text
    rel = f"native/{base.safe_name(name)}.txt"
    store.write_text(rel, stripped.rstrip() + "\n")
    data = asdict(capture)
    data["auto_hide_on_busy"] = auto_hide
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    return data


def run_text(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    timeout: float = 15.0,
) -> None:
    steps.append(capture_native(args, store, name, ["run", *command], timeout=timeout))


def run_shell(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    script: str,
    timeout: float = 15.0,
) -> None:
    run_text(args, store, steps, name, [args.busybox, "sh", "-c", script], timeout=timeout)


def plan_manifest(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "cycle": "V1372",
        "type": "bounded live provider-held corrected-RC1 enumerate plan",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "v1372-provider-held-pcie1-enumerate-plan-ready",
        "pass": True,
        "reason": "plan-only; no device command executed",
        "next_step": "run V1372 with explicit allow flags",
        "candidate_actions": [
            f"mknod {SUBSYS_ESOC0} c 236 9 if absent",
            f"background open {SUBSYS_ESOC0} to enter ext-sdx50m provider path",
            f"wait {args.provider_delay_ms}ms before RC1 enumerate",
            "printf '2\\n' > /sys/kernel/debug/pci-msm/rc_sel",
            "printf '11\\n' > /sys/kernel/debug/pci-msm/case",
            "capture GPIO142, LTSSM/L0, PCI/MHI, dmesg, cleanup, reboot health",
        ],
        "forbidden": [
            "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "PERST assert/deassert debug cases",
            "PMIC/GPIO/GDSC direct writes",
            "eSoC notify or BOOT_DONE spoof",
            "flash, boot image write, partition write",
        ],
    }


def debugfs_mounted(text: str) -> bool:
    return base.debugfs_mounted(text)


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    return base.step_text(store, steps, name)


def command_ok(steps: list[dict[str, Any]], name: str) -> bool:
    return base.command_ok(steps, name)


def collect_power_snapshot(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], prefix: str) -> None:
    base.collect_power_snapshot(args, store, steps, prefix)


def provider_held_case11_script(args: argparse.Namespace) -> str:
    delay_ms = max(1, args.provider_delay_ms)
    delay_sec = f"{delay_ms // 1000}.{delay_ms % 1000:03d}" if delay_ms >= 1000 else f"0.{delay_ms:03d}"
    post_sec = max(1, args.post_enumerate_sec)
    bb = args.busybox
    toybox = args.toybox
    return f"""
BB={bb}
TB={toybox}
NODE={SUBSYS_ESOC0}
PCI={PCI_MSM_DEBUGFS}
BASE={BASE_PATH}
PIDFILE=${{BASE}}.pid
STATUS=${{BASE}}.status
LOG=${{BASE}}.log
$BB rm -f "$PIDFILE" "$STATUS" "$LOG" 2>/dev/null || true
if [ ! -e "$NODE" ]; then
  $BB mknod "$NODE" c 236 9
  echo "v1372.mknod.rc=$?"
  $BB chmod 600 "$NODE" 2>/dev/null || true
else
  echo "v1372.mknod.rc=already-present"
fi
$BB ls -l "$NODE" 2>&1 || true
(
  echo "holder.inner.pid=$$" >> "$LOG"
  exec 9<>"$NODE"
  rc=$?
  echo "holder.open.rc=$rc" >> "$STATUS"
  if [ "$rc" = 0 ]; then
    echo "holder.opened=1" >> "$STATUS"
    $BB sleep 20
  fi
) &
holder=$!
echo "$holder" > "$PIDFILE"
echo "v1372.holder.pid=$holder"
$BB sleep {delay_sec}
echo "v1372.pre_enum.wchan.begin"
$BB cat /proc/$holder/wchan 2>&1 || true
echo "v1372.pre_enum.wchan.end"
echo "v1372.pre_enum.gpio.begin"
$BB grep -iE 'gpio102|gpio-102|gpio135|gpio-135|gpio142|gpio-142|1270|pm8150' /sys/kernel/debug/gpio 2>/dev/null || true
echo "v1372.pre_enum.gpio.end"
echo "v1372.write.begin"
printf '2\\n' > "$PCI/rc_sel"
rc_sel_rc=$?
printf '11\\n' > "$PCI/case"
case_rc=$?
echo "v1372.rc_sel.rc=$rc_sel_rc"
echo "v1372.case11.rc=$case_rc"
echo "v1372.write.end"
$BB sleep {post_sec}
echo "v1372.post_enum.wchan.begin"
$BB cat /proc/$holder/wchan 2>&1 || true
echo "v1372.post_enum.wchan.end"
echo "v1372.status.begin"
$BB cat "$STATUS" 2>&1 || true
echo "v1372.status.end"
echo "v1372.pci.begin"
$TB find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true
echo "v1372.pci.end"
echo "v1372.mhi.begin"
$TB ls -l /sys/bus/mhi/devices /dev/mhi* /dev/*mhi* 2>/dev/null || true
echo "v1372.mhi.end"
echo "v1372.dmesg.begin"
$TB dmesg | $BB grep -iE 'subsystem_get|mdm_subsys_powerup|mdm3|esoc|sdx50|pcie|LTSSM|PERST|WAKE|mhi|wlfw|BDF|wlan0|fatal|panic' | $BB tail -260 || true
echo "v1372.dmesg.end"
$BB kill "$holder" 2>&1 || true
$BB sleep 1
$BB kill -9 "$holder" 2>&1 || true
$BB rm -f "$NODE" "$PIDFILE" "$STATUS" "$LOG" 2>&1 || true
true
"""


def wait_for_reboot(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    reboot_capture = run_capture(args, "reboot-cleanup", ["reboot"], timeout=5.0)
    text = strip_cmdv1_text(reboot_capture.text) if reboot_capture.text else reboot_capture.error + "\n"
    store.write_text("native/reboot-cleanup.txt", text)
    started = time.monotonic()
    version_text = ""
    bootstatus_text = ""
    selftest_text = ""
    for _ in range(90):
        try:
            result = run_cmdv1_command(args.host, args.port, 3.0, ["version"], retry_unsafe=False)
            if result.rc == 0 and result.status == "ok":
                version_text = result.text
                boot = run_cmdv1_command(args.host, args.port, 8.0, ["bootstatus"], retry_unsafe=False)
                bootstatus_text = boot.text
                selftest = run_cmdv1_command(args.host, args.port, 8.0, ["selftest", "verbose"], retry_unsafe=False)
                selftest_text = selftest.text
                break
        except Exception:
            time.sleep(2.0)
    store.write_text("native/post-reboot-version.txt", strip_cmdv1_text(version_text) if version_text else "<missing>\n")
    store.write_text("native/post-reboot-bootstatus.txt", strip_cmdv1_text(bootstatus_text) if bootstatus_text else "<missing>\n")
    store.write_text("native/post-reboot-selftest.txt", strip_cmdv1_text(selftest_text) if selftest_text else "<missing>\n")
    return {
        "reboot_command_ok": reboot_capture.ok,
        "reboot_command_status": reboot_capture.status,
        "reboot_command_error": reboot_capture.error,
        "wait_sec": round(time.monotonic() - started, 3),
        "version_seen": args.expect_version in version_text,
        "bootstatus_healthy": "BOOT OK" in bootstatus_text and "fail=0" in bootstatus_text,
        "selftest_healthy": "selftest: pass=" in selftest_text and "fail=0" in selftest_text,
    }


def collect_run(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    missing = required_flags(args)
    if missing:
        return [], {"missing_flags": missing}
    steps: list[dict[str, Any]] = [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "status", ["status"], timeout=15.0),
    ]
    run_text(args, store, steps, "mounts-before", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    mounted_before = debugfs_mounted(step_text(store, steps, "mounts-before"))
    if not mounted_before:
        run_text(args, store, steps, "debugfs-mount", [args.busybox, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT], timeout=15.0)
    run_text(args, store, steps, "mounts-during", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    collect_power_snapshot(args, store, steps, "before")
    run_shell(args, store, steps, "provider-held-case11", provider_held_case11_script(args), timeout=70.0)
    collect_power_snapshot(args, store, steps, "after")
    if not mounted_before:
        run_text(args, store, steps, "debugfs-umount", [args.busybox, "umount", DEBUGFS_ROOT], timeout=15.0)
    run_text(args, store, steps, "mounts-after", [args.toybox, "cat", "/proc/mounts"], timeout=10.0)
    reboot = wait_for_reboot(args, store) if args.allow_reboot_cleanup else {}
    return steps, {"mounted_before": mounted_before, "reboot_cleanup": reboot}


def extract_between(text: str, begin: str, end: str) -> str:
    if begin not in text:
        return ""
    tail = text.split(begin, 1)[1]
    if end in tail:
        tail = tail.split(end, 1)[0]
    return tail.strip()


def analyze(store: EvidenceStore, steps: list[dict[str, Any]], run_meta: dict[str, Any]) -> dict[str, Any]:
    if run_meta.get("missing_flags"):
        return {
            "decision": "v1372-live-flags-missing",
            "pass": False,
            "reason": "explicit live flags are required",
            "next_step": "rerun V1372 with required allow flags",
            "missing_flags": run_meta["missing_flags"],
            "safety": safety_dict(False),
        }
    provider_text = step_text(store, steps, "provider-held-case11")
    after_dmesg = step_text(store, steps, "after-dmesg-pcie-tail")
    combined = provider_text + "\n" + after_dmesg
    post_selftest_ok = bool((run_meta.get("reboot_cleanup") or {}).get("selftest_healthy"))
    bootstatus_ok = bool((run_meta.get("reboot_cleanup") or {}).get("bootstatus_healthy"))
    version_seen = bool((run_meta.get("reboot_cleanup") or {}).get("version_seen"))
    write_ok = "v1372.rc_sel.rc=0" in provider_text and "v1372.case11.rc=0" in provider_text
    holder_seen = "v1372.holder.pid=" in provider_text
    holder_block_seen = "mdm_subsys_powerup" in combined or "__subsystem_get: esoc0" in combined
    pcie_l0_seen = "LTSSM_STATE: LTSSM_L0" in combined or "PCIe RC1 link initialized" in combined
    current_gen_seen = "PCIe RC1 Current GEN" in combined
    link_failed_seen = "PCIe RC1 link initialization failed" in combined
    poll_compliance_seen = "LTSSM_POLL_COMPLIANCE" in combined
    pci_text = extract_between(provider_text, "v1372.pci.begin", "v1372.pci.end")
    mhi_text = extract_between(provider_text, "v1372.mhi.begin", "v1372.mhi.end")
    pci_device_count = base.count_find_children(pci_text, "/sys/bus/pci/devices")
    mhi_present = base.mhi_nodes_present(mhi_text)
    gpio142_seen = "gpio142 : in  1" in provider_text or "gpio-142" in provider_text and " hi" in provider_text
    wlfw_seen = "wlfw" in combined.lower()
    wlan0_seen = "wlan0" in combined.lower()
    cleanup_ok = command_ok(steps, "mounts-after") and version_seen and bootstatus_ok and post_selftest_ok

    if not write_ok:
        decision = "v1372-provider-held-case11-write-failed"
        pass_condition = False
        reason = "provider-held run did not successfully write rc_sel=2 and case=11"
        next_step = "inspect provider-held-case11 transcript before retry"
    elif not cleanup_ok:
        decision = "v1372-provider-held-cleanup-health-failed"
        pass_condition = False
        reason = "provider-held run completed but reboot cleanup or post-health verification failed"
        next_step = "restore native health before continuing"
    elif pcie_l0_seen or pci_device_count > 0 or mhi_present:
        decision = "v1372-provider-held-rc1-link-progress-clean"
        pass_condition = True
        reason = "provider-held delayed corrected RC1 enumerate produced link/PCI/MHI progress and cleanup stayed healthy"
        next_step = "classify the new PCI/MHI state before Wi-Fi HAL or network bring-up"
    elif holder_block_seen and link_failed_seen:
        decision = "v1372-provider-held-still-no-l0-clean"
        pass_condition = True
        reason = "provider-held delayed corrected RC1 enumerate still stopped before L0; cleanup stayed healthy"
        next_step = "classify provider timing/MDM2AP/PON delta or Android-only endpoint readiness prerequisite"
    else:
        decision = "v1372-provider-held-inconclusive-clean"
        pass_condition = True
        reason = "provider-held delayed corrected RC1 enumerate completed cleanly but did not expose a stronger LTSSM classification"
        next_step = "inspect V1372 transcript before selecting another live mutation"

    return {
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "mounted_before": run_meta.get("mounted_before"),
        "write_ok": write_ok,
        "holder_seen": holder_seen,
        "holder_block_seen": holder_block_seen,
        "pcie_l0_seen": pcie_l0_seen,
        "current_gen_seen": current_gen_seen,
        "link_failed_seen": link_failed_seen,
        "poll_compliance_seen": poll_compliance_seen,
        "pci_device_count": pci_device_count,
        "mhi_present": mhi_present,
        "gpio142_seen": gpio142_seen,
        "wlfw_seen": wlfw_seen,
        "wlan0_seen": wlan0_seen,
        "cleanup_ok": cleanup_ok,
        "reboot_cleanup": run_meta.get("reboot_cleanup") or {},
        "safety": safety_dict(True),
    }


def safety_dict(executed: bool) -> dict[str, bool]:
    return {
        "device_command_executed": executed,
        "subsys_esoc0_open_executed": executed,
        "mknod_executed": executed,
        "debugfs_rc_sel_case11_write_executed": executed,
        "case26_status_write_executed": False,
        "perst_assert_deassert_case_executed": False,
        "pmic_gpio_gdsc_direct_write_executed": False,
        "esoc_notify_boot_done_spoof_executed": False,
        "wifi_hal_scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_external_ping_executed": False,
        "flash_boot_partition_write_executed": False,
    }


def key_rows(analysis: dict[str, Any]) -> list[list[Any]]:
    keys = [
        "write_ok",
        "holder_seen",
        "holder_block_seen",
        "pcie_l0_seen",
        "current_gen_seen",
        "link_failed_seen",
        "poll_compliance_seen",
        "pci_device_count",
        "mhi_present",
        "gpio142_seen",
        "wlfw_seen",
        "wlan0_seen",
        "cleanup_ok",
    ]
    return [[key, analysis.get(key)] for key in keys]


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1372 Provider-held pcie1 Enumerate Live",
        "",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["field", "value"], key_rows(analysis)) if analysis else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("status"), step.get("file")]
        for step in manifest.get("steps") or []
    ]
    return "\n".join([
        "# Native Init V1372 Provider-held pcie1 Enumerate Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1372`",
        "- Type: bounded live provider-held corrected-RC1 enumerate proof",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_provider_held_pcie1_enumerate_live_v1372.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/manifest.json`",
        "  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/summary.md`",
        "  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/native/`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Interpretation",
        "",
        "- The provider holder entered the ext-sdx50m path (`mdm_subsys_powerup`) before",
        "  the corrected RC1 enumerate write.",
        "- RC1 still stopped in LTSSM poll/compliance before L0; no PCI device, MHI",
        "  node, GPIO142/MDM2AP assertion, WLFW marker, or `wlan0` appeared.",
        "- This keeps Wi-Fi HAL, scan/connect, DHCP/routes, external ping, and upper",
        "  eSoC notify/`BOOT_DONE`/MHI work parked. The next blocker is provider",
        "  timing or Android-only endpoint-readiness parity, not another blind upper",
        "  Wi-Fi retry.",
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], key_rows(analysis)) if analysis else "plan-only",
        "",
        "## Captures",
        "",
        markdown_table(["name", "ok", "rc", "status", "file"], step_rows) if step_rows else "plan-only",
        "",
        "## Safety",
        "",
        "- V1372 opens only `/dev/subsys_esoc0` via a temporary char node, then writes",
        "  corrected `rc_sel=2` and enumerate `case=11` after the Android-derived delay.",
        "- No Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
        "  PERST assert/deassert debug cases, PMIC/GPIO/GDSC direct writes, eSoC",
        "  notify/`BOOT_DONE` spoof, flash, boot image write, or partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = plan_manifest(args)
        manifest["host"] = collect_host_metadata()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
        return 0

    if args.command == "reclassify":
        manifest = json.loads((store.run_dir / "manifest.json").read_text(encoding="utf-8"))
        analysis = analyze(store, manifest.get("steps") or [], manifest.get("run_meta") or {})
        manifest["analysis"] = analysis
        manifest["decision"] = analysis["decision"]
        manifest["pass"] = analysis["pass"]
        manifest["reason"] = analysis["reason"]
        manifest["next_step"] = analysis["next_step"]
        manifest["reclassified_at"] = now_iso()
        write_outputs(store, manifest)
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
        return 0 if manifest["pass"] else 1

    steps, run_meta = collect_run(args, store)
    analysis = analyze(store, steps, run_meta)
    manifest = {
        "cycle": "V1372",
        "type": "bounded live provider-held corrected-RC1 enumerate proof",
        "generated_at": now_iso(),
        "command": "run",
        "host": collect_host_metadata(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "next_step": analysis["next_step"],
        "provider_delay_ms": args.provider_delay_ms,
        "post_enumerate_sec": args.post_enumerate_sec,
        "analysis": analysis,
        "run_meta": run_meta,
        "steps": steps,
    }
    write_outputs(store, manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(store.run_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
