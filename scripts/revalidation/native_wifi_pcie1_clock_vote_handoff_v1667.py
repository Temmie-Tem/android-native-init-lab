#!/usr/bin/env python3
"""V1667 rollbackable live retry for the V1666 pcie1 clock vote harness repair."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_test_boot_handoff_v1395 as base
from a90harness.evidence import write_private_json, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1667-pcie1-clock-vote-retry-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1667_PCIE1_CLOCK_VOTE_RETRY_HANDOFF_2026-06-02.md"
)
DEFAULT_V1666_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1666-pcie1-clock-vote-repair-test-boot"
    / "manifest.json"
)
DEFAULT_TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1666-pcie1-clock-vote-repair-test-boot"
    / "boot_linux_v1666_pcie1_clock_vote.img"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.117 (v1666-pcie1-clock-vote)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1666.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1666.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1666-helper.result"
DEFAULT_TEST_WATCHER_PATH = "/cache/native-init-wifi-test-boot-v1666-natural-watcher.result"
DEFAULT_TEST_WINDOW_PATH = "/cache/native-init-wifi-test-boot-v1666-clock-vote-window.result"
DEFAULT_TEST_CLOCK_VOTE_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1666-pcie1-clock-vote.result"
DEFAULT_DMESG_PATTERN = (
    "A90v1666|pcie1 clock vote|subsystem_get|mdm_subsys_powerup|"
    "sdx50m_toggle_soft_reset|pil_notif|fw=esoc0|gpio_value|gpio_direction|"
    "GPIO142|mdm status|mdm errfatal|PCIe RC1|LTSSM|mhi|MHI|wlfw|WLFW|BDF|FW ready|wlan0|ks"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def int_field(fields: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(str(fields.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


def inline_int(text: str, prefix: str, key: str, default: int = -1) -> int:
    pattern = re.compile(rf"^{re.escape(prefix)}=.*\b{re.escape(key)}=(-?\d+)\b", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def line_value_int(text: str, key: str, default: int = -1) -> int:
    pattern = re.compile(rf"^{re.escape(key)}=(-?\d+)\b", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def max_regulator_use(text: str, name: str) -> int:
    max_use = 0
    pattern = re.compile(rf"^\s*{re.escape(name)}\s+(-?\d+)\s+", re.MULTILINE)
    for match in pattern.finditer(text):
        try:
            max_use = max(max_use, int(match.group(1)))
        except ValueError:
            pass
    return max_use


def matching_lines(text: str, pattern: str, limit: int = 28) -> list[str]:
    matcher = re.compile(pattern)
    rows: list[str] = []
    for line in text.splitlines():
        if matcher.search(line):
            rows.append(line[:260])
            if len(rows) >= limit:
                break
    return rows


def classify_clock_vote(out_dir: Path, handoff: dict[str, Any]) -> dict[str, Any]:
    window = read_text(out_dir / "test-rc1-window-result.stdout.txt")
    vote_result = read_text(out_dir / "test-extra-pcie1-clock-vote.stdout.txt")
    vote_source = vote_result if vote_result.strip() else window
    dmesg = read_text(out_dir / "test-v1393-dmesg.stdout.txt")
    summary = read_text(out_dir / "test-v1393-summary.stdout.txt")
    combined = vote_source + "\n" + window + "\n" + dmesg + "\n" + summary
    fields = parse_key_values(vote_source)
    safety_keys = {
        key: int_field(fields, key, -1)
        for key in (
            "pcie1_clock_vote.safety_regulator_write",
            "pcie1_clock_vote.safety_gdsc_write",
            "pcie1_clock_vote.safety_pci_case_write",
            "pcie1_clock_vote.safety_forced_rc1",
            "pcie1_clock_vote.safety_pmic_write",
            "pcie1_clock_vote.safety_gpio_write",
            "pcie1_clock_vote.safety_esoc_notify",
            "pcie1_clock_vote.safety_boot_done_spoof",
            "pcie1_clock_vote.safety_pci_rescan",
            "pcie1_clock_vote.safety_platform_bind",
            "pcie1_clock_vote.safety_wifi_hal_start",
            "pcie1_clock_vote.safety_scan_connect",
            "pcie1_clock_vote.safety_credentials",
            "pcie1_clock_vote.safety_dhcp_route",
            "pcie1_clock_vote.safety_external_ping",
        )
    }
    success_count = int_field(fields, "pcie1_clock_vote.success_count", 0)
    failure_count = int_field(fields, "pcie1_clock_vote.failure_count", 0)
    rate_success_count = int_field(fields, "pcie1_clock_vote.rate_success_count", 0)
    cleanup_success_count = int_field(fields, "pcie1_clock_vote.cleanup_success_count", 0)
    cleanup_failure_count = int_field(fields, "pcie1_clock_vote.cleanup_failure_count", -1)
    wait_ready_count = inline_int(vote_source, "pcie1_clock_vote.wait_end", "ready_count")
    wait_sample_count = inline_int(vote_source, "pcie1_clock_vote.wait_end", "sample_count")
    wait_elapsed_ms = inline_int(vote_source, "pcie1_clock_vote.wait_end", "elapsed_ms")
    async_begin_rc = line_value_int(vote_source, "pcie1_clock_vote.async_begin_rc")
    pcie1_gdsc_max_use = max_regulator_use(combined, "pcie_1_gdsc")
    mdm2ap_delta = int_field(fields, "mdm2ap_timing.gpio142_irq_delta", 0)
    errfatal_delta = int_field(fields, "mdm2ap_timing.errfatal_irq_delta", 0)
    progress = handoff.get("wifi_progress", {})
    rc1_progress = bool(progress.get("rc1_progress"))
    mhi_progress = bool(progress.get("mhi_progress"))
    wlfw_progress = bool(progress.get("wlfw_progress"))
    wlan0_present = bool(progress.get("wlan0_present"))
    handoff_pass = bool(handoff.get("handoff_pass") and handoff.get("rollback", {}).get("ok"))
    safety_zero = all(value == 0 for value in safety_keys.values())
    forbidden_seen = any(
        token in combined
        for token in (
            "scan/connect",
            "wpa_supplicant",
            "dhcpcd",
            "udhcpc",
            "external ping",
            "BOOT_DONE spoof",
            "/sys/kernel/debug/pci-msm/case",
        )
    )
    evidence_ok = bool(
        handoff_pass
        and fields.get("pcie1_clock_vote.begin") == "1"
        and fields.get("pcie1_clock_vote.cleanup_end") == "1"
        and success_count > 0
        and cleanup_failure_count == 0
        and safety_zero
        and not forbidden_seen
    )
    moved = bool(pcie1_gdsc_max_use > 0 or mdm2ap_delta > 0 or rc1_progress or mhi_progress or wlfw_progress or wlan0_present)
    if not evidence_ok:
        label = "clock-vote-surface-failed"
        if handoff_pass and fields.get("pcie1_clock_vote.cleanup_end") == "1" and success_count == 0:
            reason = (
                "rollback and cleanup succeeded, but no clock enable write succeeded; "
                f"target enable leaves were not observed before the bounded wait expired "
                f"(ready_count={wait_ready_count}, wait_elapsed_ms={wait_elapsed_ms}, async_begin_rc={async_begin_rc})"
            )
        else:
            reason = "clock vote evidence, cleanup, safety, or rollback was incomplete"
    elif moved:
        label = "clock-vote-surface-pass-gdsc-moved"
        reason = "targeted clock votes succeeded and pcie1/MDM2AP/downstream observables moved"
    else:
        label = "clock-vote-surface-pass-no-gdsc"
        reason = "targeted clock votes succeeded and cleaned up, but pcie1 GDSC/MDM2AP/RC1 did not move"
    return {
        "label": label,
        "pass": evidence_ok,
        "reason": reason,
        "begin": fields.get("pcie1_clock_vote.begin") == "1",
        "wait_begin": fields.get("pcie1_clock_vote.wait_begin") is not None,
        "wait_ready_count": wait_ready_count,
        "wait_sample_count": wait_sample_count,
        "wait_elapsed_ms": wait_elapsed_ms,
        "async_begin_rc": async_begin_rc,
        "cleanup_end": fields.get("pcie1_clock_vote.cleanup_end") == "1",
        "success_count": success_count,
        "failure_count": failure_count,
        "rate_success_count": rate_success_count,
        "cleanup_success_count": cleanup_success_count,
        "cleanup_failure_count": cleanup_failure_count,
        "safety_values": safety_keys,
        "safety_zero": safety_zero,
        "forbidden_seen": forbidden_seen,
        "pcie1_gdsc_max_use": pcie1_gdsc_max_use,
        "mdm2ap_gpio142_irq_delta": mdm2ap_delta,
        "errfatal_irq_delta": errfatal_delta,
        "rc1_progress": rc1_progress,
        "mhi_progress": mhi_progress,
        "wlfw_progress": wlfw_progress,
        "wlan0_present": wlan0_present,
        "clock_vote_excerpt": matching_lines(vote_source, r"pcie1_clock_vote\.|A90_V1666_CLOCK_VOTE_SNAPSHOT", 40),
        "power_excerpt": matching_lines(combined, r"pcie_1_gdsc|CLOCK .*gcc_pcie|mdm2ap_timing\.", 36),
    }


def render_report(result: dict[str, Any]) -> str:
    vote = result["clock_vote"]
    lines = [
        "# Native Init V1667 pcie1 Clock Vote Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1667`",
        "- Type: one-run rollbackable bounded live pcie1 clock-debug vote proof",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Label: `{vote['label']}`",
        f"- Reason: {vote['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Handoff/rollback pass: `{result['handoff_pass']}`",
        "",
        "## Clock Vote Classification",
        "",
        f"- `begin`: `{vote['begin']}`",
        f"- `wait_begin`: `{vote['wait_begin']}`",
        f"- `wait_ready_count`: `{vote['wait_ready_count']}`",
        f"- `wait_sample_count`: `{vote['wait_sample_count']}`",
        f"- `wait_elapsed_ms`: `{vote['wait_elapsed_ms']}`",
        f"- `async_begin_rc`: `{vote['async_begin_rc']}`",
        f"- `success_count`: `{vote['success_count']}`",
        f"- `failure_count`: `{vote['failure_count']}`",
        f"- `rate_success_count`: `{vote['rate_success_count']}`",
        f"- `cleanup_success_count`: `{vote['cleanup_success_count']}`",
        f"- `cleanup_failure_count`: `{vote['cleanup_failure_count']}`",
        f"- `safety_zero`: `{vote['safety_zero']}`",
        f"- `forbidden_seen`: `{vote['forbidden_seen']}`",
        f"- `pcie1_gdsc_max_use`: `{vote['pcie1_gdsc_max_use']}`",
        f"- `mdm2ap_gpio142_irq_delta`: `{vote['mdm2ap_gpio142_irq_delta']}`",
        f"- `errfatal_irq_delta`: `{vote['errfatal_irq_delta']}`",
        f"- `rc1_progress`: `{vote['rc1_progress']}`",
        f"- `mhi_progress`: `{vote['mhi_progress']}`",
        f"- `wlfw_progress`: `{vote['wlfw_progress']}`",
        f"- `wlan0_present`: `{vote['wlan0_present']}`",
        "",
        "## Clock Vote Excerpt",
        "",
        *[f"- `{line}`" for line in vote["clock_vote_excerpt"]],
        "",
        "## Power/Timing Excerpt",
        "",
        *[f"- `{line}`" for line in vote["power_excerpt"]],
        "",
        "## Safety Scope",
        "",
        "This run used only the V1666 bounded clock-debug vote surface inside the",
        "test boot. It did not write regulator/GDSC state, `/sys/kernel/debug/pci-msm/case`,",
        "PMIC/GPIO/PERST, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind,",
        "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "Rollback restored `stage3/boot_linux_v724.img` and the base handoff verified",
        "native selftest when `handoff_pass=True`.",
        "",
        "## Next",
        "",
    ]
    if vote["label"] == "clock-vote-surface-pass-gdsc-moved":
        lines.extend([
            "Clock-only vote changed pcie1/MDM2AP/downstream observables. The next gate",
            "should classify which enabled clock or sequence moved the endpoint before",
            "considering any broader pcie1 normal resource vote.",
        ])
    elif vote["label"] == "clock-vote-surface-pass-no-gdsc":
        lines.extend([
            "Clock-only vote is not sufficient. The next bounded plan should target the",
            "missing pcie1 GDSC/resource vote through a proven narrow surface or a normal",
            "driver PM path, still without scan/connect or credentials.",
        ])
    else:
        if vote["wait_ready_count"] == 0 and vote["cleanup_failure_count"] == 0:
            lines.extend([
                "The separate result file was collected and rollback passed, but the async",
                "vote child timed out before the target clock debugfs leaves became visible.",
                "The next source/build unit should move the vote trigger later or extend the",
                "bounded readiness window before interpreting hardware behavior.",
            ])
        else:
            lines.append("Repair the clock-vote harness before any further live mutation.")
    lines.append("")
    return "\n".join(lines)


def build_base_argv(args: argparse.Namespace) -> list[str]:
    return [
        "--cycle",
        "V1667",
        "--out-dir",
        str(args.out_dir),
        "--report-path",
        str(args.report_path),
        "--v1394-manifest",
        str(args.v1666_manifest),
        "--test-image",
        str(args.test_image),
        "--expect-test-version",
        TEST_EXPECT_VERSION,
        "--test-log-path",
        DEFAULT_TEST_LOG_PATH,
        "--test-summary-path",
        DEFAULT_TEST_SUMMARY_PATH,
        "--test-helper-result-path",
        DEFAULT_TEST_HELPER_RESULT_PATH,
        "--test-rc1-watcher-result-path",
        DEFAULT_TEST_WATCHER_PATH,
        "--test-rc1-window-result-path",
        DEFAULT_TEST_WINDOW_PATH,
        "--test-extra-result-path",
        f"pcie1-clock-vote={DEFAULT_TEST_CLOCK_VOTE_RESULT_PATH}",
        "--dmesg-grep-pattern",
        DEFAULT_DMESG_PATTERN,
        "--post-boot-hold-sec",
        str(args.post_boot_hold_sec),
        "--collect-timeout-sec",
        str(args.collect_timeout_sec),
        "--native-direct-rollback-fallback",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1666-manifest", type=Path, default=DEFAULT_V1666_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--post-boot-hold-sec", type=float, default=100.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=180.0)
    parser.add_argument("--classify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_rc = 0
    if not args.classify_only:
        base_rc = base.main(build_base_argv(args))
    manifest_path = args.out_dir / "manifest.json"
    handoff = read_json(manifest_path)
    if not handoff:
        print(json.dumps({
            "decision": "v1667-pcie1-clock-vote-retry-handoff-manifest-missing",
            "pass": False,
            "base_rc": base_rc,
        }, indent=2))
        return 1

    vote = classify_clock_vote(args.out_dir, handoff)
    pass_ok = bool(vote["pass"])
    decision = f"v1667-{vote['label']}"
    result = dict(handoff)
    result.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": vote["reason"],
        "clock_vote": vote,
        "base_handoff_decision": handoff.get("decision", ""),
        "base_handoff_pass": handoff.get("pass", False),
        "contract": {
            "source": "docs/reports/NATIVE_INIT_V1663_PCIE1_VOTE_GATE_PLAN_2026-06-02.md",
            "bounded_clock_debug_vote_only": True,
            "no_autonomous_broader_write_gate": True,
        },
    })
    write_private_json(manifest_path, result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": vote["label"],
        "base_rc": base_rc,
        "handoff_pass": result.get("handoff_pass"),
        "success_count": vote["success_count"],
        "cleanup_failure_count": vote["cleanup_failure_count"],
        "pcie1_gdsc_max_use": vote["pcie1_gdsc_max_use"],
        "rc1_progress": vote["rc1_progress"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
