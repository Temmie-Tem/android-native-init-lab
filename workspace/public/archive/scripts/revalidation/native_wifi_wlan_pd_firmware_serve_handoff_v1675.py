#!/usr/bin/env python3
"""V1675 one-run WLAN-PD firmware-serve gate handoff.

This flashes the V1674 read-only test boot, captures the single firmware-serve
gate result, rolls back to v725-fasttransport, and stops on the gate label. It does not run
eSoC/RC1 triggers, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_test_boot_handoff_v1395 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1675"
DEFAULT_SOURCE_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1674-wlan-pd-firmware-serve-gate-test-boot"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1675-wlan-pd-firmware-serve-gate-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1675_WLAN_PD_FIRMWARE_SERVE_GATE_HANDOFF_2026-06-02.md"
)
DEFAULT_TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1674-wlan-pd-firmware-serve-gate-test-boot"
    / "boot_linux_v1674_wlan_pd_firmware_serve_gate.img"
)
ROLLBACK_IMAGE = REPO_ROOT / "stage3" / "boot_linux_v725_fasttransport.img"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.120 (v1674-wlan-pd-firmware-serve-gate)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1674.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1674.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1674-helper.result"
DMESG_PATTERN = "A90v1674|wlan_pd|wlanmdsp|tftp|rmt_storage|pd-mapper|qrtr|service 69|wlfw|icnss|FW ready|BDF|wlan0"
VALID_LABELS = {
    "firmware-not-requested",
    "firmware-requested-but-absent-at-served-path",
    "firmware-served-pd-still-uninit",
    "tqftpserv-not-running",
}


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(evidence_dir: Path, name: str) -> str:
    path = evidence_dir / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_helper_fields(evidence_dir: Path) -> dict[str, str]:
    return base.parse_key_value_lines(read_text(evidence_dir, "test-v1393-helper-result.stdout.txt"))


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    test_version = read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = parse_helper_fields(evidence_dir)
    label = helper_fields.get("wlan_pd_firmware_serve_gate.label", "")
    helper_contract_seen = helper_fields.get("wlan_pd_firmware_serve_gate.begin") == "1"
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    label_ok = label in VALID_LABELS

    details = {
        "version_ok": version_ok,
        "rollback_ok": rollback_ok,
        "helper_contract_seen": helper_contract_seen,
        "label": label,
        "label_ok": label_ok,
        "tftp_running": helper_fields.get("wlan_pd_firmware_serve_gate.tftp_running"),
        "subsys_modem_holder_started": helper_fields.get("wlan_pd_firmware_serve_gate.subsys_modem_holder_started"),
        "subsys_modem_holder_opened": helper_fields.get("wlan_pd_firmware_serve_gate.subsys_modem_holder_opened"),
        "subsys_modem_holder_postflight_safe": helper_fields.get("wlan_pd_firmware_serve_gate.subsys_modem_holder_postflight_safe"),
        "requested_wlanmdsp": helper_fields.get("wlan_pd_firmware_serve_gate.requested_wlanmdsp"),
        "requested_modem": helper_fields.get("wlan_pd_firmware_serve_gate.requested_modem"),
        "served_wlanmdsp_nonzero": helper_fields.get("wlan_pd_firmware_serve_gate.served_wlanmdsp_nonzero"),
        "served_modem_mdt_nonzero": helper_fields.get("wlan_pd_firmware_serve_gate.served_modem_mdt_nonzero"),
        "served_modem_blob_nonzero": helper_fields.get("wlan_pd_firmware_serve_gate.served_modem_blob_nonzero"),
        "wlfw_service69_seen": helper_fields.get("wlan_pd_firmware_serve_gate.wlfw_service69_seen"),
        "wlan_pd_uninit": helper_fields.get("wlan_pd_firmware_serve_gate.wlan_pd_uninit"),
        "companion_result": helper_fields.get("wifi_companion_start.result"),
        "companion_reason": helper_fields.get("wifi_companion_start.reason"),
        "companion_order": helper_fields.get("wifi_companion_start.order"),
        "service_notifier_state": helper_fields.get("wifi_companion_service_notifier_listener.response_curr_state_name"),
        "qrtr_readback_result": helper_fields.get("wifi_companion_qrtr_readback.result"),
    }

    if not test_flash.get("ok"):
        return (
            f"{args.cycle.lower()}-test-boot-flash-or-verify-failed",
            False,
            "test boot flash/verify failed; rollback evidence must be inspected before retry",
            details,
        )
    if not version_ok:
        return (
            f"{args.cycle.lower()}-test-boot-version-missing",
            False,
            f"expected {args.cycle} test boot version marker was not collected",
            details,
        )
    if not rollback_ok:
        return (
            f"{args.cycle.lower()}-rollback-failed",
            False,
            "firmware-serve evidence may exist, but rollback to v725-fasttransport did not verify",
            details,
        )
    if not helper_contract_seen:
        return (
            f"{args.cycle.lower()}-firmware-serve-contract-missing",
            False,
            "helper result did not include the WLAN-PD firmware-serve gate contract",
            details,
        )
    if not label_ok:
        return (
            f"{args.cycle.lower()}-firmware-serve-label-missing",
            False,
            "helper result did not produce one of the fixed firmware-serve labels; trigger may be incomplete",
            details,
        )
    return (
        f"{args.cycle.lower()}-{label}-rollback-pass",
        True,
        "one read-only WLAN-PD firmware-serve gate run produced a fixed label and rollback verified",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    cycle = str(result.get("cycle", CYCLE))
    lines = [
        f"# Native Init {cycle} WLAN-PD Firmware-serve Gate Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: one-run rollbackable read-only WLAN-PD firmware-serve gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        "",
        "## Gate Label",
        "",
        f"- Label: `{gate.get('label')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- subsys_modem holder started: `{gate.get('subsys_modem_holder_started')}`",
        f"- subsys_modem holder opened: `{gate.get('subsys_modem_holder_opened')}`",
        f"- subsys_modem holder postflight safe: `{gate.get('subsys_modem_holder_postflight_safe')}`",
        f"- requested wlanmdsp: `{gate.get('requested_wlanmdsp')}`",
        f"- requested modem image: `{gate.get('requested_modem')}`",
        f"- served wlanmdsp nonzero: `{gate.get('served_wlanmdsp_nonzero')}`",
        f"- served modem.mdt nonzero: `{gate.get('served_modem_mdt_nonzero')}`",
        f"- served modem blob nonzero: `{gate.get('served_modem_blob_nonzero')}`",
        f"- WLFW service 69 seen: `{gate.get('wlfw_service69_seen')}`",
        f"- WLAN-PD uninit: `{gate.get('wlan_pd_uninit')}`",
        f"- service-notifier state: `{gate.get('service_notifier_state')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Safety Scope",
        "",
        "- eSoC/subsys_esoc0, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, and BOOT_DONE spoof were not used.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was test boot flash followed by rollback to `stage3/boot_linux_v725_fasttransport.img`.",
        "",
        "## Next",
        "",
        "- Stop here for handoff. Do not spin timing/window variants for this gate.",
        "- If label is `firmware-not-requested`, analyze why the modem never requests WLAN-PD firmware.",
        "- If label is `firmware-requested-but-absent-at-served-path`, fix served-path parity in a separate approved gate.",
        "- If label is `firmware-served-pd-still-uninit`, next work is modem-side WLAN-PD start trigger, not MSA.",
        "- If label is `tqftpserv-not-running`, fix companion startup before any lower-layer expansion.",
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
        "test_image_sha256": base.local_sha256(args.test_image) if args.test_image.exists() else "",
        "rollback_image": display_path(args.rollback_image),
        "rollback_image_exists": args.rollback_image.exists(),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--rollback-image", type=Path, default=ROLLBACK_IMAGE)
    parser.add_argument("--expect-test-version", default=TEST_EXPECT_VERSION)
    parser.add_argument("--expect-rollback-version", default=ROLLBACK_EXPECT_VERSION)
    parser.add_argument("--post-boot-hold-sec", type=float, default=90.0)
    parser.add_argument("--flash-timeout-sec", type=float, default=720.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=150.0)
    parser.add_argument("--bridge-verify-timeout-sec", type=float, default=240.0)
    parser.add_argument("--native-direct-rollback-fallback", action="store_true")
    parser.add_argument("--native-direct-rollback-remote-image", default="/cache/boot_linux_v725_fasttransport.img")
    parser.add_argument("--native-direct-rollback-boot-block", default="/dev/block/sda24")
    parser.add_argument("--native-direct-rollback-boot-major", type=int, default=259)
    parser.add_argument("--native-direct-rollback-boot-minor", type=int, default=8)
    parser.add_argument("--native-direct-rollback-timeout-sec", type=float, default=120.0)
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
    if not pre["source_manifest_pass"] or not pre["test_image_exists"] or not pre["rollback_image_exists"]:
        result = {
            "cycle": args.cycle,
            "decision": f"{args.cycle.lower()}-preflight-blocked",
            "pass": False,
            "reason": "source manifest pass, test image, or rollback image missing",
            "preflight": pre,
            "steps": steps,
            "out_dir": display_path(args.out_dir),
        }
        store.write_json("manifest.json", result)
        write_private_text(args.report_path, render_report(result))
        print(json.dumps({"decision": result["decision"], "pass": False}, indent=2))
        return 1

    test_flash = base.run_command(
        base.flash_command(args.test_image, args.expect_test_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    base.write_step(store, steps, "test-flash-from-native", test_flash)

    evidence: dict[str, Any] = {}
    if test_flash["ok"]:
        if args.post_boot_hold_sec > 0:
            hold = base.run_command(
                ["python3", "-c", f"import time; time.sleep({args.post_boot_hold_sec!r})"],
                timeout=args.post_boot_hold_sec + 5.0,
            )
            base.write_step(store, steps, "post-boot-hold", hold)
        evidence = base.collect_test_boot_evidence(args, store, steps)

    rollback_result = base.rollback(args, store, steps)
    decision, pass_ok, reason, gate = classify_gate(args, test_flash, rollback_result, args.out_dir)
    result = {
        "cycle": args.cycle,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "preflight": pre,
        "test_flash_ok": bool(test_flash.get("ok")),
        "evidence": evidence,
        "rollback": rollback_result,
        "gate": gate,
        "steps": steps,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({"decision": decision, "pass": pass_ok, "gate": gate, "rollback": rollback_result}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
