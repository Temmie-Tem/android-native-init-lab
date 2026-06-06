#!/usr/bin/env python3
"""V1632 one-run natural-path MDM2AP observation handoff.

This wraps the V1395 test-boot handoff runner with the V1630/V1631
natural-path artifact and then reclassifies the collected evidence against the
2026-06-02 MDM2AP observation contract.

Allowed live mutation is limited to flashing the V1630 test boot image and
rolling back to v724. The test boot must observe the natural
``__subsystem_get(esoc0) -> mdm_subsys_powerup`` path only; it must not force
RC1 enumerate, spoof ONLINE state, issue eSoC notify/BOOT_DONE, or perform
Wi-Fi scan/connect.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_test_boot_handoff_v1395 as base
from a90harness.evidence import write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1632-natural-path-mdm2ap-observation-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1632_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md"
)
DEFAULT_V1631_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1631-natural-path-mdm2ap-observation-artifact-sanity"
    / "manifest.json"
)
DEFAULT_TEST_IMAGE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1630-natural-path-mdm2ap-observation-test-boot"
    / "boot_linux_v1630_natural_mdm2ap.img"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.112 (v1630-natural-mdm2ap)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1630.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1630.summary"
DEFAULT_TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1393-helper.result"
DEFAULT_TEST_WATCHER_PATH = "/cache/native-init-wifi-test-boot-v1630-natural-watcher.result"
DEFAULT_TEST_WINDOW_PATH = "/cache/native-init-wifi-test-boot-v1630-natural-window.result"
DEFAULT_DMESG_PATTERN = (
    "A90v1630|subsystem_get|mdm_subsys_powerup|sdx50m_toggle_soft_reset|"
    "pil_notif|fw=esoc0|gpio_value|gpio_direction|GPIO142|mdm status|"
    "mdm errfatal|PCIe RC1|LTSSM|mhi|MHI|wlfw|WLFW|BDF|FW ready|wlan0|ks"
)

FORBIDDEN_TEXT_MARKERS = (
    "TEST: 11",
    "rc1_micro_writer_summary",
    "micro_writer rc=",
    "writer_wait_rc=",
    "case_aligned_micro_after_case_",
    "post_case_aligned_micro_200ms",
    "ap2mdm_hold attempt",
    "fake-mdm3-online",
    "fake_online",
)
SAFETY_ZERO_KEYS = (
    "mdm2ap_timing.safety_wifi_hal_start",
    "mdm2ap_timing.safety_pmic_write",
    "mdm2ap_timing.safety_gpio_write",
    "mdm2ap_timing.safety_gdsc_write",
    "mdm2ap_timing.safety_direct_esoc_ioctl",
    "mdm2ap_timing.safety_boot_done_spoof",
    "mdm2ap_timing.safety_pci_rescan",
    "mdm2ap_timing.safety_platform_bind",
)


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_key_values(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or line.startswith("A90P1 "):
            continue
        match = re.match(r"^([A-Za-z0-9_.:-]+)=(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def int_field(fields: dict[str, str], key: str, default: int = -1) -> int:
    try:
        return int(str(fields.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


def bool_text(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def count_lines_matching(text: str, pattern: str) -> int:
    matcher = re.compile(pattern)
    return sum(1 for line in text.splitlines() if matcher.search(line))


def classify_natural_path(out_dir: Path, handoff: dict[str, Any]) -> dict[str, Any]:
    dmesg = read_text(out_dir / "test-v1393-dmesg.stdout.txt")
    summary = read_text(out_dir / "test-v1393-summary.stdout.txt")
    helper = read_text(out_dir / "test-v1393-helper-result.stdout.txt")
    watcher = read_text(out_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    window = read_text(out_dir / "test-rc1-window-result.stdout.txt")
    all_text = "\n".join([dmesg, summary, helper, watcher, window])
    fields = parse_key_values(helper)
    window_fields = parse_key_values(window)
    fields.update({key: value for key, value in window_fields.items() if key.startswith("mdm2ap_timing.")})
    summary_fields = parse_key_values(summary)
    handoff_pass = bool(handoff.get("handoff_pass"))
    rollback_ok = bool((handoff.get("rollback") or {}).get("ok"))
    test_flash_ok = bool(handoff.get("test_flash_ok"))

    gpio142_irq_delta = int_field(fields, "mdm2ap_timing.gpio142_irq_delta")
    errfatal_irq_delta = int_field(fields, "mdm2ap_timing.errfatal_irq_delta")
    gpio142_irq_initial_parsed = int_field(fields, "mdm2ap_timing.gpio142_irq_initial_parsed", 0) == 1
    errfatal_irq_initial_parsed = int_field(fields, "mdm2ap_timing.errfatal_irq_initial_parsed", 0) == 1
    sample_count = int_field(fields, "mdm2ap_timing.sample_count", 0)
    timing_begin = fields.get("mdm2ap_timing.begin", "")
    timing_end = fields.get("mdm2ap_timing.end", "")
    timing_powerup_seen = fields.get("mdm2ap_timing.pm_service_powerup_seen") == "1"
    timing_complete = bool(
        timing_begin
        and timing_end
        and sample_count >= 120
        and gpio142_irq_initial_parsed
        and errfatal_irq_initial_parsed
    )
    safety_values = {key: int_field(fields, key, 0) for key in SAFETY_ZERO_KEYS if key in fields}
    safety_zero = all(value == 0 for value in safety_values.values())

    pil_esoc_seen = bool_text(window, "fw=esoc0") or bool_text(dmesg, "fw=esoc0")
    provider_trigger_seen = (
        bool_text(all_text, "__subsystem_get: esoc0", "mdm_subsys_powerup")
        or pil_esoc_seen
        or timing_powerup_seen
    )
    pon_low_seen = bool_text(window, "gpio_value: 1270 set 0")
    pon_high_seen = bool_text(window, "gpio_value: 1270 set 1")
    ap2mdm_seen = bool_text(window, "gpio_value: 135 set 1", "gpio_direction: 135 out")
    gpio142_trace_seen = bool(re.search(r"gpio_value:\s*142\s+(?:set|get)\s+1", window))
    gpio142_trace_seen = gpio142_trace_seen or bool(re.search(r"gpio142\s+:\s+in\s+1\b", window))
    mdm_status_zero_sample_count = count_lines_matching(
        window,
        r"mdm status$",
    )
    errfatal_zero_sample_count = count_lines_matching(
        window,
        r"mdm errfatal$",
    )
    gpio142_low_sample_count = count_lines_matching(window, r"gpio142\s+:\s+in\s+0\b")
    limited_silent_window_evidence = (
        mdm_status_zero_sample_count > 0
        and gpio142_low_sample_count > 0
        and not gpio142_trace_seen
    )
    forbidden_markers_seen = [marker for marker in FORBIDDEN_TEXT_MARKERS if marker in all_text]

    if not test_flash_ok or not rollback_ok:
        label = "transport-or-rollback-fail"
        pass_ok = False
        reason = "test boot flash/verify or rollback did not complete; this is not a natural-path classification result"
    elif forbidden_markers_seen:
        label = "contract-violation-forced-or-spoofed-action"
        pass_ok = False
        reason = "forbidden forced RC1, fake state, hold, or writer marker appeared in collected evidence"
    elif not provider_trigger_seen:
        label = "provider-did-not-trigger"
        pass_ok = True
        reason = "rollback verified, but the natural esoc0 provider trigger was not observed"
    elif gpio142_irq_delta > 0 or gpio142_trace_seen:
        label = "mdm2ap-responds"
        pass_ok = True
        reason = "rollback verified and natural-path MDM2AP/GPIO142 response evidence was observed"
    elif (
        pil_esoc_seen
        and pon_low_seen
        and pon_high_seen
        and ap2mdm_seen
        and gpio142_irq_delta == 0
        and errfatal_irq_delta == 0
        and timing_complete
        and safety_zero
    ):
        label = "mdm2ap-silent-natural-path"
        pass_ok = True
        reason = "rollback verified, provider/PON/AP2MDM natural path was observed, and GPIO142/errfatal stayed silent"
    elif (
        pil_esoc_seen
        and pon_low_seen
        and pon_high_seen
        and ap2mdm_seen
        and limited_silent_window_evidence
        and not timing_complete
    ):
        label = "natural-path-observation-incomplete"
        pass_ok = False
        reason = "natural provider/PON/AP2MDM path was observed and short-window samples stayed low, but the required mdm2ap_timing IRQ-delta contract evidence was not collected"
    else:
        label = "natural-path-observation-incomplete"
        pass_ok = False
        reason = "rollback verified but required provider/PON/AP2MDM/timing evidence was incomplete"

    return {
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "handoff_pass": handoff_pass,
        "test_flash_ok": test_flash_ok,
        "rollback_ok": rollback_ok,
        "provider_trigger_seen": provider_trigger_seen,
        "pil_esoc_seen": pil_esoc_seen,
        "pon_low_seen": pon_low_seen,
        "pon_high_seen": pon_high_seen,
        "ap2mdm_seen": ap2mdm_seen,
        "gpio142_trace_seen": gpio142_trace_seen,
        "gpio142_irq_delta": gpio142_irq_delta,
        "errfatal_irq_delta": errfatal_irq_delta,
        "gpio142_irq_initial_parsed": gpio142_irq_initial_parsed,
        "errfatal_irq_initial_parsed": errfatal_irq_initial_parsed,
        "mdm_status_zero_sample_count": mdm_status_zero_sample_count,
        "errfatal_zero_sample_count": errfatal_zero_sample_count,
        "gpio142_low_sample_count": gpio142_low_sample_count,
        "limited_silent_window_evidence": limited_silent_window_evidence,
        "timing_powerup_seen": timing_powerup_seen,
        "timing_complete": timing_complete,
        "sample_count": sample_count,
        "safety_zero": safety_zero,
        "safety_values": safety_values,
        "forbidden_markers_seen": forbidden_markers_seen,
        "helper_timed_out": summary_fields.get("helper_timed_out", ""),
        "helper_result_size": summary_fields.get("helper_result_size", ""),
        "mdm2ap_timing_mode": fields.get("mdm2ap_timing.mode", ""),
        "mdm2ap_timing_begin": timing_begin,
        "mdm2ap_timing_end": timing_end,
        "pcie_rc1_transition_seen": fields.get("mdm2ap_timing.pcie_rc1_transition_seen", ""),
        "mhi_bus_max": fields.get("mdm2ap_timing.mhi_bus_max", ""),
        "wlfw_kmsg_max": fields.get("mdm2ap_timing.wlfw_kmsg_max", ""),
        "wlan0_seen": fields.get("mdm2ap_timing.wlan0_seen", ""),
    }


def render_report(result: dict[str, Any]) -> str:
    observation = result["natural_path_observation"]
    lines = [
        "# Native Init V1632 Natural-path MDM2AP Observation Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1632`",
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
            "STOP. The natural provider/PON/AP2MDM path ran but MDM2AP stayed silent. "
            "Any bounded modem-rail/PMIC write gate requires a separate approval."
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
        "V1632",
        "--out-dir",
        str(args.out_dir),
        "--report-path",
        str(args.report_path),
        "--v1394-manifest",
        str(args.v1631_manifest),
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
    parser.add_argument("--v1631-manifest", type=Path, default=DEFAULT_V1631_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--post-boot-hold-sec", type=float, default=80.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=160.0)
    parser.add_argument("--classify-only", action="store_true", help="Reclassify existing V1632 evidence without flashing.")
    parser.add_argument("--assume-yes", action="store_true", help="Compatibility flag; this runner is non-interactive.")
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
            "decision": "v1632-natural-path-handoff-manifest-missing",
            "pass": False,
            "base_rc": base_rc,
        }, indent=2))
        return 1

    observation = classify_natural_path(args.out_dir, handoff)
    result = dict(handoff)
    result.update({
        "decision": f"v1632-{observation['label']}",
        "pass": bool(observation["pass"]),
        "reason": observation["reason"],
        "natural_path_observation": observation,
        "base_handoff_decision": handoff.get("base_handoff_decision", handoff.get("decision", "")),
        "base_handoff_pass": handoff.get("base_handoff_pass", handoff.get("pass", False)),
        "contract": {
            "source": "docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md",
            "one_run_only": True,
            "natural_path_only": True,
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
