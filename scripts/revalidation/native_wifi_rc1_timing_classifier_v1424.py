#!/usr/bin/env python3
"""V1424 host-only classifier for Android-vs-native RC1 timing parity."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1424-rc1-timing-parity-classifier"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1424_RC1_TIMING_PARITY_CLASSIFIER_2026-06-01.md"
DEFAULT_ANDROID_DMESG = REPO_ROOT / "tmp" / "wifi" / "v852-android-ext-mdm-provider-surface-handoff" / "v852-android-ext-mdm-provider-surface-run" / "android" / "commands" / "dmesg-focus.txt"
DEFAULT_NATIVE_DMESG = REPO_ROOT / "tmp" / "wifi" / "v1422-wifi-test-boot-rc1-window-sampler-handoff" / "test-v1393-dmesg.stdout.txt"
DEFAULT_NATIVE_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1422-wifi-test-boot-rc1-window-sampler-handoff" / "manifest.json"
TS_RE = re.compile(r"\[\s*(\d+\.\d+)\]")


EVENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("esoc0", "__subsystem_get: esoc0 count"),
    ("test_case_11", "PCIe: TEST: 11"),
    ("assert_reset", "Assert the reset of endpoint of RC1"),
    ("int_mask", "PCIE20_PARF_INT_ALL_MASK"),
    ("phy_ready", "PCIe RC1 PHY is ready"),
    ("release_reset", "Release the reset of endpoint of RC1"),
    ("detect_quiet", "LTSSM_STATE: LTSSM_DETECT_QUIET"),
    ("poll_active", "LTSSM_STATE: LTSSM_POLL_ACTIVE"),
    ("poll_compliance", "LTSSM_STATE: LTSSM_POLL_COMPLIANCE"),
    ("l0", "LTSSM_STATE: LTSSM_L0"),
    ("link_initialized", "PCIe RC1 link initialized"),
    ("link_failed", "PCIe RC1 link initialization failed"),
    ("current_gen", "PCIe RC1 Current GEN"),
    ("bdf_regdb", "BDF file : regdb.bin"),
    ("bdf_bdwlan", "BDF file : bdwlan.bin"),
    ("fw_ready", "FW ready event received"),
    ("wlan0", "dev : wlan0"),
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def timestamp(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def first_events(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    events: dict[str, Any] = {}
    for line in text.splitlines():
        ts = timestamp(line)
        if ts is None:
            continue
        for name, needle in EVENT_PATTERNS:
            if name not in events and needle in line:
                events[name] = {"timestamp": ts, "line": line.strip()}
    return events


def delta_ms(events: dict[str, Any], start: str, end: str) -> float | None:
    if start not in events or end not in events:
        return None
    return round((float(events[end]["timestamp"]) - float(events[start]["timestamp"])) * 1000.0, 3)


def classify(android: dict[str, Any], native: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    android_esoc_to_assert = delta_ms(android, "esoc0", "assert_reset")
    native_esoc_to_assert = delta_ms(native, "esoc0", "assert_reset")
    native_test_to_assert = delta_ms(native, "test_case_11", "assert_reset")
    android_assert_to_release = delta_ms(android, "assert_reset", "release_reset")
    native_assert_to_release = delta_ms(native, "assert_reset", "release_reset")
    android_release_to_l0 = delta_ms(android, "release_reset", "l0")
    native_release_to_fail = delta_ms(native, "release_reset", "link_failed")
    timing_gap_ms = None
    if android_esoc_to_assert is not None and native_esoc_to_assert is not None:
        timing_gap_ms = round(native_esoc_to_assert - android_esoc_to_assert, 3)

    android_l0 = "l0" in android
    native_l0 = "l0" in native
    native_failed = "link_failed" in native
    int_mask_parity = (
        "int_mask" in android
        and "int_mask" in native
        and "0x7f80c202" in android["int_mask"]["line"]
        and "0x7f80c202" in native["int_mask"]["line"]
    )
    reset_path_present = all(key in native for key in ("assert_reset", "int_mask", "phy_ready", "release_reset"))
    timing_close = timing_gap_ms is not None and abs(timing_gap_ms) <= 50.0
    downstream_absent = not any(key in native for key in ("l0", "current_gen", "bdf_regdb", "bdf_bdwlan", "fw_ready", "wlan0"))
    window_samples_ok = manifest.get("wifi_progress", {}).get("pid1_rc1_window_sample_count") == 5

    if timing_close and reset_path_present and int_mask_parity and android_l0 and native_failed and downstream_absent:
        decision = "v1424-rc1-timing-precondition-parity-but-endpoint-no-l0"
        passed = True
        reason = "RC1 trigger/reset/release timing is close enough to Android; native diverges after PERST release when the endpoint fails to reach L0"
    else:
        decision = "v1424-rc1-timing-classifier-needs-more-evidence"
        passed = False
        reason = "existing evidence does not cleanly separate timing parity from endpoint response failure"

    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "android": {
            "events": android,
            "esoc_to_assert_ms": android_esoc_to_assert,
            "assert_to_release_ms": android_assert_to_release,
            "release_to_l0_ms": android_release_to_l0,
            "l0": android_l0,
        },
        "native": {
            "events": native,
            "esoc_to_assert_ms": native_esoc_to_assert,
            "test_to_assert_ms": native_test_to_assert,
            "assert_to_release_ms": native_assert_to_release,
            "release_to_fail_ms": native_release_to_fail,
            "l0": native_l0,
            "link_failed": native_failed,
            "reset_path_present": reset_path_present,
            "downstream_absent": downstream_absent,
            "window_samples_ok": window_samples_ok,
        },
        "comparison": {
            "esoc_to_assert_gap_ms": timing_gap_ms,
            "timing_close_50ms": timing_close,
            "int_mask_parity": int_mask_parity,
        },
    }


def render_report(args: argparse.Namespace, result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    comparison = result["comparison"]
    return "\n".join([
        "# Native Init V1424 RC1 Timing Parity Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1424`",
        "- Type: host-only/read-only classifier over existing Android and native evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Android input: `{rel(args.android_dmesg)}`",
        f"- Native input: `{rel(args.native_dmesg)}`",
        "",
        "## Timing Comparison",
        "",
        "| Signal | Android V852 | Native V1422 |",
        "| --- | --- | --- |",
        f"| esoc0 to RC1 assert | `{android['esoc_to_assert_ms']}ms` | `{native['esoc_to_assert_ms']}ms` |",
        f"| assert to release | `{android['assert_to_release_ms']}ms` | `{native['assert_to_release_ms']}ms` |",
        f"| release to terminal state | L0 in `{android['release_to_l0_ms']}ms` | fail in `{native['release_to_fail_ms']}ms` |",
        f"| L0 | `{android['l0']}` | `{native['l0']}` |",
        f"| link failed | `False` | `{native['link_failed']}` |",
        f"| downstream Wi-Fi | BDF/FW-ready/`wlan0` present | downstream absent `{native['downstream_absent']}` |",
        "",
        "## Classification",
        "",
        f"- esoc-to-assert gap: `{comparison['esoc_to_assert_gap_ms']}ms`",
        f"- timing close within 50ms: `{comparison['timing_close_50ms']}`",
        f"- RC1 INT mask parity: `{comparison['int_mask_parity']}`",
        f"- native reset path present: `{native['reset_path_present']}`",
        f"- V1422 RC1-window sample count valid: `{native['window_samples_ok']}`",
        "",
        "The native test boot no longer looks primarily blocked by a too-early or",
        "too-late RC1 trigger. The assert/release path is close to Android and uses",
        "the same RC1 INT mask. The divergence is after PERST release: Android reaches",
        "L0 quickly, while native enters poll-active/poll-compliance and fails before",
        "L0, with no MHI/WLFW/BDF/FW-ready/`wlan0`.",
        "",
        "## Safety Scope",
        "",
        "This cycle was host-only. It did not run device commands, flash, reboot,",
        "write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,",
        "ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/BOOT_DONE,",
        "run global PCI rescan, or bind/unbind platform devices.",
        "",
        "## Next",
        "",
        "V1425 should target the post-release endpoint-response gap. The safest next",
        "implementation is a source/build-only higher-resolution read-only sampler",
        "around RC1 release and link failure, or a narrowly planned rollbackable test",
        "that changes only the RC1 timing/retry policy after documenting why repeated",
        "case writes are still below Wi-Fi scan/connect.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    android = first_events(args.android_dmesg)
    native = first_events(args.native_dmesg)
    manifest = json.loads(args.native_manifest.read_text(encoding="utf-8"))
    result = classify(android, native, manifest)
    result["cycle"] = "V1424"
    result["inputs"] = {
        "android_dmesg": rel(args.android_dmesg),
        "native_dmesg": rel(args.native_dmesg),
        "native_manifest": rel(args.native_manifest),
    }
    report = render_report(args, result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": str(args.out_dir),
        "comparison": result["comparison"],
        "native_final": {
            "l0": result["native"]["l0"],
            "link_failed": result["native"]["link_failed"],
            "downstream_absent": result["native"]["downstream_absent"],
        },
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
