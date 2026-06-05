#!/usr/bin/env python3
"""V1557 native endpoint-signal long-hold test-boot handoff.

V1556 fixed the stable delta between Android-good and native: Android-good
eventually shows GPIO104/pcie-wake and GPIO142/mdm-status endpoint signals,
while native V1552 remains endpoint-silent after AP-side pcie1
power/refclk/PERST.  V1557 reuses the existing V1493 Wi-Fi test boot image but
holds it long enough to check whether the native test-boot path ever develops
the delayed endpoint signals seen in V1555.

The runner flashes only the declared test boot image, collects bounded
below-connect evidence, and rolls back to native v724.  It does not start Wi-Fi
HAL, scan/connect, use credentials, run DHCP/routes, external ping, directly
write PMIC/GPIO/GDSC, issue eSoC notify/BOOT_DONE, globally rescan PCI, or
bind/unbind platform devices.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table
from a90harness.evidence import EvidenceStore

import native_wifi_test_boot_handoff_v1395 as base


DEFAULT_OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1557-native-endpoint-long-hold-handoff"
DEFAULT_REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1557_NATIVE_ENDPOINT_LONG_HOLD_HANDOFF_2026-06-02.md"
)
DEFAULT_V1494_MANIFEST = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1494-wifi-auto-readiness-rc1-window-artifact-sanity"
    / "manifest.json"
)
DEFAULT_TEST_IMAGE = (
    base.REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1493-wifi-auto-readiness-rc1-window-test-boot"
    / "boot_linux_v1493_wifi_test.img"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.92 (v1493-wifitest)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1493.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1493.summary"
TEST_RC1_WATCHER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result"
TEST_RC1_WINDOW_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1493-rc1-window.result"
LATEST_POINTER = base.REPO_ROOT / "tmp" / "wifi" / "latest-v1557-native-endpoint-long-hold-handoff.txt"

DMESG_PATTERN = (
    "A90v1493|auto_readiness|rc1_window|pid1_rc1|wlfw|WLFW|icnss_qmi|"
    "BDF|bdwlan|regdb|FW ready|WLAN FW is ready|fw_ready|wlan0|"
    "subsystem_get|__subsystem_get|mdm_subsys_powerup|PCIe RC1|LTSSM|"
    "pcie|PCIe|mhi|MHI|ks|cnss|CNSS|GPIO142|GPIO 142|mdm status|"
    "msm_pcie_wake|GPIO104|GPIO 104|mdm errfatal"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1494-manifest", type=Path, default=DEFAULT_V1494_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--rollback-image", type=Path, default=base.DEFAULT_ROLLBACK_IMAGE)
    parser.add_argument("--post-boot-hold-sec", type=float, default=280.0)
    parser.add_argument("--expect-test-version", default=TEST_EXPECT_VERSION)
    parser.add_argument("--expect-rollback-version", default=base.ROLLBACK_EXPECT_VERSION)
    parser.add_argument("--flash-timeout-sec", type=float, default=720.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=120.0)
    parser.add_argument("--bridge-verify-timeout-sec", type=float, default=240.0)
    parser.add_argument("--native-direct-rollback-fallback", action="store_true", default=True)
    parser.add_argument("--native-direct-rollback-remote-image", default="/cache/boot_linux_v725_fasttransport.img")
    parser.add_argument("--native-direct-rollback-boot-block", default="/dev/block/sda24")
    parser.add_argument("--native-direct-rollback-boot-major", type=int, default=259)
    parser.add_argument("--native-direct-rollback-boot-minor", type=int, default=8)
    parser.add_argument("--native-direct-rollback-timeout-sec", type=float, default=120.0)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("command", choices=("plan", "run", "reclassify"), nargs="?", default="run")
    return parser.parse_args()


def display_path(path: Path) -> str:
    return base.display_path(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    artifact = load_json(args.v1494_manifest) if args.v1494_manifest.exists() else {}
    return {
        "artifact_manifest": display_path(args.v1494_manifest),
        "artifact_decision": artifact.get("decision", ""),
        "artifact_pass": bool(artifact.get("pass")),
        "test_image": display_path(args.test_image),
        "test_image_exists": args.test_image.exists(),
        "rollback_image": display_path(args.rollback_image),
        "rollback_image_exists": args.rollback_image.exists(),
        "hold_sec": args.post_boot_hold_sec,
    }


def a90ctl_collect(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None) -> dict[str, Any]:
    result = base.run_a90ctl_step(
        store,
        steps,
        name,
        base.a90ctl_command_timed(command, timeout=timeout or args.collect_timeout_sec, retry_unsafe=False),
        (timeout or args.collect_timeout_sec) + 10.0,
    )
    return result


def shell_command(args: argparse.Namespace, script: str, timeout: float | None = None) -> list[object]:
    return base.a90ctl_command_timed(
        ["run", "/cache/bin/busybox", "sh", "-c", script],
        timeout=timeout or args.collect_timeout_sec,
        retry_unsafe=False,
    )


def collect_test_evidence(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    a90ctl_collect(args, store, steps, "test-version", ["version"], timeout=20.0)
    a90ctl_collect(args, store, steps, "test-status", ["status"], timeout=30.0)
    a90ctl_collect(args, store, steps, "test-selftest", ["selftest"], timeout=30.0)
    a90ctl_collect(args, store, steps, "test-bootstatus", ["bootstatus"], timeout=30.0)
    a90ctl_collect(args, store, steps, "test-log", ["run", "/cache/bin/toybox", "cat", TEST_LOG_PATH], timeout=60.0)
    a90ctl_collect(args, store, steps, "test-summary", ["run", "/cache/bin/toybox", "cat", TEST_SUMMARY_PATH], timeout=60.0)
    a90ctl_collect(args, store, steps, "test-rc1-watcher-result", ["run", "/cache/bin/toybox", "cat", TEST_RC1_WATCHER_RESULT_PATH], timeout=60.0)
    a90ctl_collect(args, store, steps, "test-rc1-window-result", ["run", "/cache/bin/toybox", "cat", TEST_RC1_WINDOW_RESULT_PATH], timeout=60.0)
    base.write_step(
        store,
        steps,
        "test-dmesg-filtered",
        base.run_command(
            shell_command(args, f"dmesg | grep -Ei {DMESG_PATTERN!r} | tail -520", timeout=90.0),
            timeout=100.0,
        ),
    )
    base.write_step(
        store,
        steps,
        "test-endpoint-snapshot",
        base.run_command(
            shell_command(
                args,
                (
                    "echo interrupts_begin; "
                    "cat /proc/interrupts 2>/dev/null | grep -Ei 'msmgpio-dc +142|msmgpio-dc +104|mdm status|mdm errfatal|msm_pcie_wake|mhi|pcie' || true; "
                    "echo interrupts_end; "
                    "echo gpio_begin; "
                    "grep -Ei 'gpio102|gpio103|gpio104|gpio135|gpio142' /sys/kernel/debug/gpio 2>/dev/null || true; "
                    "echo gpio_end; "
                    "echo pci_mhi_begin; "
                    "find /sys/bus/pci/devices -maxdepth 2 -print 2>/dev/null || true; "
                    "ls -l /sys/bus/mhi/devices /dev/mhi* /dev/*mhi* 2>/dev/null || true; "
                    "echo pci_mhi_end; "
                    "test -e /sys/class/net/wlan0 && echo wlan0=present || echo wlan0=absent"
                ),
                timeout=90.0,
            ),
            timeout=100.0,
        ),
    )


def read_step_text(evidence_dir: Path, name: str) -> str:
    stdout = evidence_dir / f"{name}.stdout.txt"
    stderr = evidence_dir / f"{name}.stderr.txt"
    parts = []
    if stdout.exists():
        parts.append(stdout.read_text(encoding="utf-8", errors="replace"))
    if stderr.exists():
        parts.append(stderr.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def count_irq_total(text: str, irq: str, label: str) -> int:
    for line in text.splitlines():
        if label.lower() not in line.lower() and not re.match(rf"\s*{re.escape(irq)}:", line):
            continue
        numbers = [int(value) for value in re.findall(r"\b\d+\b", line)]
        if len(numbers) > 1:
            return sum(numbers[1:9])
    return 0


def gpio_high_seen(text: str, gpio: str) -> bool:
    regex = re.compile(rf"gpio{gpio}\s*:\s*(?:in|out)\s+1\b", re.I)
    return any(regex.search(line) for line in text.splitlines())


def classify(evidence_dir: Path, test_flash_ok: bool, rollback_ok: bool, expect_test_version: str) -> tuple[str, bool, str, dict[str, Any]]:
    version = read_step_text(evidence_dir, "test-version")
    dmesg = read_step_text(evidence_dir, "test-dmesg-filtered")
    snapshot = read_step_text(evidence_dir, "test-endpoint-snapshot")
    rc1_window = read_step_text(evidence_dir, "test-rc1-window-result")
    summary = read_step_text(evidence_dir, "test-summary")
    all_text = "\n".join((dmesg, snapshot, rc1_window, summary))
    pcie_wake_irq = count_irq_total(snapshot, "252", "msm_pcie_wake")
    mdm_status_irq = count_irq_total(snapshot, "290", "mdm status")
    mdm_errfatal_irq = count_irq_total(snapshot, "204", "mdm errfatal")
    progress = {
        "test_version_ok": expect_test_version in version,
        "provider_trigger": "__subsystem_get: esoc0" in all_text,
        "modem_trigger": "__subsystem_get: modem" in all_text,
        "rc1_progress": bool(re.search(r"TEST: 11|PCIe RC1 PHY is ready|LTSSM_STATE|msm_pcie_enable: PCIe", all_text, re.I)),
        "rc1_l0": bool(re.search(r"LTSSM_STATE: LTSSM_L0|PCIe RC1 link initialized|PCIe RC1 Current GEN", all_text, re.I)),
        "rc1_link_failed": bool(re.search(r"PCIe RC1 link initialization failed|LTSSM_POLL_COMPLIANCE|LTSSM_STATE:0x3", all_text, re.I)),
        "mhi_progress": bool(re.search(r"\bmhi\b|/dev/mhi|mhi_0305|mhi-pci", all_text, re.I)),
        "wlfw_progress": bool(re.search(r"\bwlfw\b|WLFW|icnss_qmi", all_text, re.I)),
        "bdf_progress": bool(re.search(r"BDF|bdwlan|regdb", all_text, re.I)),
        "fw_ready_progress": bool(re.search(r"FW ready|WLAN FW is ready|fw_ready", all_text, re.I)),
        "wlan0_present": "wlan0=present" in snapshot or bool(re.search(r"\bwlan0\b", dmesg, re.I)),
        "pcie_wake_irq_total": pcie_wake_irq,
        "mdm_status_irq_total": mdm_status_irq,
        "mdm_errfatal_irq_total": mdm_errfatal_irq,
        "gpio104_high_seen": gpio_high_seen(snapshot, "104"),
        "gpio142_high_seen": gpio_high_seen(snapshot, "142"),
        "gpio135_high_seen": gpio_high_seen(snapshot, "135"),
        "rc1_window_sample_count": rc1_window.count("rc1_window_sample label="),
    }
    endpoint_positive = (
        progress["pcie_wake_irq_total"] > 0
        or progress["mdm_status_irq_total"] > 0
        or progress["gpio104_high_seen"]
        or progress["gpio142_high_seen"]
    )
    downstream = (
        progress["rc1_progress"]
        or progress["mhi_progress"]
        or progress["wlfw_progress"]
        or progress["bdf_progress"]
        or progress["fw_ready_progress"]
        or progress["wlan0_present"]
    )
    progress["endpoint_positive"] = endpoint_positive
    progress["downstream_progress"] = downstream
    if not test_flash_ok or not progress["test_version_ok"]:
        return ("v1557-test-boot-flash-or-version-failed", False, "test boot flash/verify or version evidence failed", progress)
    if not rollback_ok:
        return ("v1557-test-boot-rollback-failed", False, "test boot evidence collected but rollback did not verify", progress)
    if endpoint_positive and progress["rc1_l0"]:
        return ("v1557-native-endpoint-signals-and-l0-observed-rollback-pass", True, "native long hold observed endpoint response and RC1 L0; rollback verified", progress)
    if endpoint_positive:
        return ("v1557-native-endpoint-signals-no-l0-rollback-pass", True, "native long hold observed endpoint response but no RC1 L0; rollback verified", progress)
    if progress["rc1_progress"] and progress["rc1_link_failed"]:
        return ("v1557-native-long-hold-endpoint-still-silent-no-l0-rollback-pass", True, "native long hold still has RC1 link failure and no wake/status endpoint signal; rollback verified", progress)
    if progress["provider_trigger"]:
        return ("v1557-native-long-hold-provider-only-rollback-pass", True, "native long hold reached provider trigger but no endpoint/RC1 progress; rollback verified", progress)
    return ("v1557-native-long-hold-no-provider-review", False, "native long hold did not show provider trigger; inspect evidence before retry", progress)


def rollback_verified(evidence_dir: Path, expect_rollback_version: str) -> bool:
    text = read_step_text(evidence_dir, "rollback-from-native")
    return (
        expect_rollback_version in text
        or "cmdv1 verify passed" in text
        or bool(re.search(r"selftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", text))
    )


def render_report(manifest: dict[str, Any]) -> str:
    progress = manifest.get("progress", {})
    return "\n".join(
        [
            "# Native Init V1557 Endpoint Signal Long-Hold Handoff",
            "",
            "## Summary",
            "",
            "- Cycle: `V1557`",
            "- Type: rollbackable native Wi-Fi test-boot long hold",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            f"- Hold seconds: `{manifest['preflight']['hold_sec']}`",
            "",
            "## Progress",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["provider/modem", f"{progress.get('provider_trigger')}/{progress.get('modem_trigger')}"],
                    ["RC1 progress/L0/link_failed", f"{progress.get('rc1_progress')}/{progress.get('rc1_l0')}/{progress.get('rc1_link_failed')}"],
                    ["MHI/WLFW/BDF/FW-ready/wlan0", f"{progress.get('mhi_progress')}/{progress.get('wlfw_progress')}/{progress.get('bdf_progress')}/{progress.get('fw_ready_progress')}/{progress.get('wlan0_present')}"],
                    ["endpoint_positive", progress.get("endpoint_positive")],
                    ["IRQ wake/status/errfatal", f"{progress.get('pcie_wake_irq_total')}/{progress.get('mdm_status_irq_total')}/{progress.get('mdm_errfatal_irq_total')}"],
                    ["GPIO104/GPIO142/GPIO135 high", f"{progress.get('gpio104_high_seen')}/{progress.get('gpio142_high_seen')}/{progress.get('gpio135_high_seen')}"],
                    ["rc1_window_sample_count", progress.get("rc1_window_sample_count")],
                ],
            ),
            "",
            "## Safety",
            "",
            "The only device mutation is the declared test boot flash and rollback to native v724. The runner performs no Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, direct PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, global PCI rescan, or platform bind/unbind.",
            "",
            "## Next",
            "",
            "- If endpoint signals remain absent, compare the provider-driven native path against Android's pre-IRQ state and avoid more long-hold retries.",
            "- If endpoint signals appear, move to the earliest missing stage after wake/status: L0, PCI enumeration, MHI, WLFW/BDF, then `wlan0`.",
            "",
        ]
    )


def build_failed_preflight_manifest(args: argparse.Namespace, store: EvidenceStore, pre: dict[str, Any]) -> dict[str, Any]:
    return {
        "cycle": "V1557",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "v1557-preflight-blocked",
        "pass": False,
        "reason": "artifact manifest, test image, or rollback image missing",
        "host": collect_host_metadata(),
        "preflight": pre,
        "steps": [],
        "out_dir": display_path(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    pre = preflight(args)
    store.write_json("preflight.json", pre)
    if args.command == "plan":
        manifest = {
            "cycle": "V1557",
            "generated_at": now_iso(),
            "command": args.command,
            "decision": "v1557-native-endpoint-long-hold-plan-ready",
            "pass": bool(pre["artifact_pass"] and pre["test_image_exists"] and pre["rollback_image_exists"]),
            "reason": "plan-only; no device command executed",
            "host": collect_host_metadata(),
            "preflight": pre,
            "steps": [],
            "out_dir": display_path(store.run_dir),
            "device_commands_executed": False,
            "device_mutations": False,
        }
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_report({**manifest, "progress": {}}))
        print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
        return 0 if manifest["pass"] else 1
    if not pre["artifact_pass"] or not pre["test_image_exists"] or not pre["rollback_image_exists"]:
        manifest = build_failed_preflight_manifest(args, store, pre)
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_report({**manifest, "progress": {}}))
        if args.write_report:
            args.report_path.write_text(render_report({**manifest, "progress": {}}), encoding="utf-8")
        print(json.dumps({"decision": manifest["decision"], "pass": False}, indent=2))
        return 1
    if args.command == "reclassify":
        test_version_path = args.out_dir / "test-version.stdout.txt"
        test_flash_ok = test_version_path.exists() and args.expect_test_version in test_version_path.read_text(encoding="utf-8", errors="replace")
        rollback_ok = rollback_verified(args.out_dir, args.expect_rollback_version)
        decision, pass_ok, reason, progress = classify(args.out_dir, test_flash_ok, rollback_ok, args.expect_test_version)
        manifest = {
            "cycle": "V1557",
            "generated_at": now_iso(),
            "command": args.command,
            "decision": decision,
            "pass": pass_ok,
            "reason": reason,
            "host": collect_host_metadata(),
            "preflight": pre,
            "progress": progress,
            "steps": [],
            "out_dir": display_path(args.out_dir),
            "device_commands_executed": False,
            "device_mutations": False,
        }
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_report(manifest))
        if args.write_report:
            args.report_path.write_text(render_report(manifest), encoding="utf-8")
        print(json.dumps({"decision": decision, "pass": pass_ok, "progress": progress}, indent=2))
        return 0 if pass_ok else 1

    steps: list[dict[str, Any]] = []
    test_flash = base.run_command(
        base.flash_command(args.test_image, args.expect_test_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    base.write_step(store, steps, "test-flash-from-native", test_flash)
    if test_flash["ok"] and args.post_boot_hold_sec > 0:
        hold = base.run_command(
            ["python3", "-c", f"import time; time.sleep({args.post_boot_hold_sec!r})"],
            timeout=args.post_boot_hold_sec + 15.0,
        )
        base.write_step(store, steps, "post-boot-hold", hold)
        collect_test_evidence(args, store, steps)
    rollback_result = base.rollback(args, store, steps)
    decision, pass_ok, reason, progress = classify(
        args.out_dir,
        bool(test_flash["ok"]),
        bool(rollback_result.get("ok")),
        args.expect_test_version,
    )
    manifest = {
        "cycle": "V1557",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "preflight": pre,
        "test_flash_ok": bool(test_flash["ok"]),
        "rollback": rollback_result,
        "progress": progress,
        "steps": steps,
        "out_dir": display_path(args.out_dir),
        "device_commands_executed": True,
        "device_mutations": True,
        "flash_executed": True,
        "boot_image_write_executed": True,
        "rollback_executed": True,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_report(manifest))
    if args.write_report:
        args.report_path.write_text(render_report(manifest), encoding="utf-8")
    LATEST_POINTER.write_text(str(store.run_dir) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "pass": pass_ok, "rollback": rollback_result, "progress": progress}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
