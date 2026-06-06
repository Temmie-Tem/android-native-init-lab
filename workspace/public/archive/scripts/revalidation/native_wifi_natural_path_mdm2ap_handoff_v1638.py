#!/usr/bin/env python3
"""V1638 one-run natural-path MDM2AP IRQ-summary handoff.

This flashes the V1636 test boot artifact, collects the PID1 window-level
``mdm2ap_timing.*`` IRQ summary, rolls back to v724, and classifies with the
strict V1632 natural-path rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import native_wifi_natural_path_mdm2ap_handoff_v1632 as v1632
import native_wifi_test_boot_handoff_v1395 as base
from a90harness.evidence import write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1638-natural-path-mdm2ap-irq-summary-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1638_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_HANDOFF_2026-06-02.md"
)
DEFAULT_V1637_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1637-natural-path-mdm2ap-irq-summary-artifact-sanity"
    / "manifest.json"
)
DEFAULT_TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1636-natural-path-mdm2ap-irq-summary-test-boot"
    / "boot_linux_v1636_natural_mdm2ap_irq_summary.img"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.114 (v1636-natural-mdm2ap-irq-summary)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1636.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1636.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1636-helper.result"
DEFAULT_TEST_WATCHER_PATH = "/cache/native-init-wifi-test-boot-v1636-natural-watcher.result"
DEFAULT_TEST_WINDOW_PATH = "/cache/native-init-wifi-test-boot-v1636-natural-window.result"
DEFAULT_DMESG_PATTERN = (
    "A90v1636|subsystem_get|mdm_subsys_powerup|sdx50m_toggle_soft_reset|"
    "pil_notif|fw=esoc0|gpio_value|gpio_direction|GPIO142|mdm status|"
    "mdm errfatal|PCIe RC1|LTSSM|mhi|MHI|wlfw|WLFW|BDF|FW ready|wlan0|ks"
)


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_report(result: dict) -> str:
    observation = result["natural_path_observation"]
    lines = [
        "# Native Init V1638 Natural-path MDM2AP IRQ Summary Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1638`",
        "- Type: one-run rollbackable natural-path live observation",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Contract label: `{observation['label']}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Test boot image: `{result['preflight']['test_image']}`",
        f"- Rollback image: `{result['preflight']['rollback_image']}`",
        f"- Rollback ok: `{observation['rollback_ok']}`",
        "",
        "## Contract Checks",
        "",
        f"- `provider_trigger_seen`: `{observation['provider_trigger_seen']}`",
        f"- `pil_esoc_seen`: `{observation['pil_esoc_seen']}`",
        f"- `pon_low_seen`: `{observation['pon_low_seen']}`",
        f"- `pon_high_seen`: `{observation['pon_high_seen']}`",
        f"- `ap2mdm_seen`: `{observation['ap2mdm_seen']}`",
        f"- `gpio142_trace_seen`: `{observation['gpio142_trace_seen']}`",
        f"- `gpio142_irq_delta`: `{observation['gpio142_irq_delta']}`",
        f"- `errfatal_irq_delta`: `{observation['errfatal_irq_delta']}`",
        f"- `gpio142_irq_initial_parsed`: `{observation['gpio142_irq_initial_parsed']}`",
        f"- `errfatal_irq_initial_parsed`: `{observation['errfatal_irq_initial_parsed']}`",
        f"- `mdm_status_zero_sample_count`: `{observation['mdm_status_zero_sample_count']}`",
        f"- `errfatal_zero_sample_count`: `{observation['errfatal_zero_sample_count']}`",
        f"- `gpio142_low_sample_count`: `{observation['gpio142_low_sample_count']}`",
        f"- `limited_silent_window_evidence`: `{observation['limited_silent_window_evidence']}`",
        f"- `timing_powerup_seen`: `{observation['timing_powerup_seen']}`",
        f"- `timing_complete`: `{observation['timing_complete']}`",
        f"- `sample_count`: `{observation['sample_count']}`",
        f"- `safety_zero`: `{observation['safety_zero']}`",
        f"- `forbidden_markers_seen`: `{observation['forbidden_markers_seen']}`",
        "",
        "## Downstream Context",
        "",
        f"- `pcie_rc1_transition_seen`: `{observation['pcie_rc1_transition_seen']}`",
        f"- `mhi_bus_max`: `{observation['mhi_bus_max']}`",
        f"- `wlfw_kmsg_max`: `{observation['wlfw_kmsg_max']}`",
        f"- `wlan0_seen`: `{observation['wlan0_seen']}`",
        "",
        "## Safety Scope",
        "",
        "This run observes the natural `__subsystem_get(esoc0)` provider path only.",
        "It does not force RC1 enumerate, write pci-msm debugfs case values, spoof",
        "ONLINE/system-info, write PMIC/GPIO/GDSC/regulator state, issue eSoC",
        "notify/`BOOT_DONE`, rescan PCI, bind/unbind platforms, start Wi-Fi HAL,",
        "scan/connect, use credentials, run DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
    ]
    if observation["label"] == "mdm2ap-silent-natural-path":
        lines.append(
            "STOP before modem-rail/PMIC writes.  The natural provider/PON/AP2MDM "
            "path ran and MDM2AP stayed silent with complete IRQ-delta evidence."
        )
    elif observation["label"] == "mdm2ap-responds":
        lines.append(
            "Treat this as lower-layer progress and design the next bounded gate around "
            "RC1/MHI/WLFW after the confirmed MDM2AP response."
        )
    elif observation["label"] == "provider-did-not-trigger":
        lines.append(
            "Treat this as route regression; inspect why the natural pm-service/per-proxy "
            "path did not reach `subsys_esoc0` before changing hardware assumptions."
        )
    else:
        lines.append("Inspect evidence before any further live mutation.")
    lines.append("")
    return "\n".join(lines)


def build_base_argv(args: argparse.Namespace) -> list[str]:
    return [
        "--cycle",
        "V1638",
        "--out-dir",
        str(args.out_dir),
        "--report-path",
        str(args.report_path),
        "--v1394-manifest",
        str(args.v1637_manifest),
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
    parser.add_argument("--v1637-manifest", type=Path, default=DEFAULT_V1637_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--post-boot-hold-sec", type=float, default=100.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=180.0)
    parser.add_argument("--classify-only", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
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
            "decision": "v1638-natural-path-handoff-manifest-missing",
            "pass": False,
            "base_rc": base_rc,
        }, indent=2))
        return 1

    observation = v1632.classify_natural_path(args.out_dir, handoff)
    result = dict(handoff)
    result.update({
        "decision": f"v1638-{observation['label']}",
        "pass": bool(observation["pass"]),
        "reason": observation["reason"],
        "natural_path_observation": observation,
        "base_handoff_decision": handoff.get("base_handoff_decision", handoff.get("decision", "")),
        "base_handoff_pass": handoff.get("base_handoff_pass", handoff.get("pass", False)),
        "contract": {
            "source": "docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md",
            "one_run_only": True,
            "natural_path_only": True,
            "pid1_irq_summary": True,
            "stop_on_mdm2ap_silent": observation["label"] == "mdm2ap-silent-natural-path",
        },
    })
    write_json(manifest_path, result)
    write_private_text(args.out_dir / "summary.md", render_report(result))
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": observation["label"],
        "base_rc": base_rc,
        "rollback_ok": observation["rollback_ok"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
