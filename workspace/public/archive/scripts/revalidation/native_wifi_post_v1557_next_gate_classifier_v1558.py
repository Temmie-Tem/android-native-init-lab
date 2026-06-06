#!/usr/bin/env python3
"""V1558 host-only post-V1557 next-gate classifier.

V1557 proves that a longer native hold on the current V1493/V1496 test-boot
route still leaves the endpoint silent: no GPIO104/WAKE, GPIO142/MDM2AP,
IRQ252/IRQ290, RC1 L0, MHI, WLFW, BDF, FW-ready, or wlan0.  V1558 combines
that result with the earlier msm_pcie TEST:11 static classifier and the
Android-good reference to select the next bounded work item without running any
device command.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1558-post-v1557-next-gate-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1558_POST_V1557_NEXT_GATE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1558-post-v1557-next-gate-classifier.txt")

INPUTS = {
    "v1523_msm_pcie_static": Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json"),
    "v1552_native_endpoint_trace": Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json"),
    "v1555_android_good_reference": Path("tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json"),
    "v1556_endpoint_comparator": Path("tmp/wifi/v1556-v1555-vs-v1552-endpoint-signal-comparator/manifest.json"),
    "v1557_native_long_hold": Path("tmp/wifi/v1557-native-endpoint-long-hold-handoff/manifest.json"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def bool_progress(manifest: dict[str, Any], key: str) -> bool:
    progress = manifest.get("progress")
    return bool(progress.get(key)) if isinstance(progress, dict) else False


def int_progress(manifest: dict[str, Any], key: str) -> int:
    progress = manifest.get("progress")
    if not isinstance(progress, dict):
        return 0
    value = progress.get(key, 0)
    return value if isinstance(value, int) else 0


def classify() -> dict[str, Any]:
    manifests = {name: read_json(path) for name, path in INPUTS.items()}
    v1523 = manifests["v1523_msm_pcie_static"]
    v1552 = manifests["v1552_native_endpoint_trace"]
    v1555 = manifests["v1555_android_good_reference"]
    v1556 = manifests["v1556_endpoint_comparator"]
    v1557 = manifests["v1557_native_long_hold"]

    checks = [
        {
            "name": "v1523-test11-shares-common-enable",
            "pass": v1523.get("pass") is True
            and v1523.get("decision") == "v1523-test11-shares-enable-normal-trigger-readiness-gap",
            "detail": "debugfs TEST:11, sysfs/client enumerate, and endpoint-wake normal paths converge on msm_pcie_enumerate()",
        },
        {
            "name": "v1552-native-ap-side-ready-endpoint-silent",
            "pass": v1552.get("pass") is True
            and v1552.get("decision") == "v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0",
            "detail": "native has AP-side pcie1 power/refclk/PERST but no GPIO104/GPIO142/IRQ252/IRQ290/L0",
        },
        {
            "name": "v1555-android-good-has-lower-wifi",
            "pass": v1555.get("pass") is True
            and v1555.get("decision") == "v1555-android-good-minimal-trace-reference-pass",
            "detail": "Android-good reaches WLFW, BDF, FW-ready, wlan0, and endpoint-positive GPIO/IRQ signals",
        },
        {
            "name": "v1556-stable-delta-fixed",
            "pass": v1556.get("pass") is True
            and v1556.get("decision") == "v1556-stable-gap-android-endpoint-signals-native-zero",
            "detail": "host-only comparator fixes Android endpoint-positive versus native endpoint-zero as the stable delta",
        },
        {
            "name": "v1557-long-hold-rejects-delay",
            "pass": v1557.get("pass") is True
            and v1557.get("decision") == "v1557-native-long-hold-endpoint-still-silent-no-l0-rollback-pass"
            and not bool_progress(v1557, "endpoint_positive")
            and not bool_progress(v1557, "rc1_l0")
            and int_progress(v1557, "pcie_wake_irq_total") == 0
            and int_progress(v1557, "mdm_status_irq_total") == 0,
            "detail": "280s native test-boot hold still has RC1 link-failed/no-L0 and no endpoint wake/status signal",
        },
    ]
    pass_ok = all(item["pass"] for item in checks)
    decision = (
        "v1558-next-gate-android-pre-endpoint-sequence-classifier"
        if pass_ok
        else "v1558-next-gate-inputs-incomplete-review"
    )
    reason = (
        "same-path TEST:11 and long-hold retries are closed; next work is Android-good pre-endpoint/pre-IRQ sequence comparison"
        if pass_ok
        else "one or more prerequisite evidence manifests is missing or not in the expected pass state"
    )
    next_gate = {
        "recommended_cycle": "V1559",
        "type": "host-only first, then read-only reference if needed",
        "focus": "Android-good pre-endpoint/pre-IRQ sequence versus native provider-driven endpoint-silent path",
        "must_compare": [
            "first provider/esoc0 trigger and mdm_subsys_powerup timing",
            "GPIO135/AP2MDM effective level and trace timing",
            "GPIO102/PERST assert/release timing",
            "pcie1 refclk/pipe-clock/GDSC timing",
            "GPIO104/WAKE and IRQ252 first positive event",
            "GPIO142/MDM2AP and IRQ290 first positive event",
            "first RC1 L0 / PCI enumeration / MHI marker if the evidence can order it",
        ],
        "blocked_retries": [
            "same V1493/V1496 native long-hold retry",
            "blind pci-msm TEST:11 timing retry",
            "firmware/MHI/WLFW analysis before RC1 L0 or PCI enumeration",
        ],
    }
    return {
        "manifests": manifests,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    next_gate = manifest["next_gate"]
    return "\n".join(
        [
            "# Native Init V1558 Post-V1557 Next Gate Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1558`",
            "- Type: host-only evidence/classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[name, rel(path)] for name, path in INPUTS.items()]),
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "status", "detail"],
                [[item["name"], "pass" if item["pass"] else "fail", item["detail"]] for item in checks],
            ),
            "",
            "## Interpretation",
            "",
            "V1557 closes the delayed-response hypothesis for the current native provider/RC1 test-boot route. Combined with V1523, this means the next useful work is not another TEST:11 or long-hold retry: the AP-side enable path is shared enough to reach PHY/LTSSM, but native never receives the endpoint-positive signals Android gets.",
            "",
            "The active blocker remains before firmware/MHI/WLFW: Android produces GPIO104/WAKE, GPIO142/MDM2AP, IRQ252, and IRQ290 while native remains endpoint-silent after AP-side power/refclk/PERST activity.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
            f"- Type: {next_gate['type']}",
            f"- Focus: {next_gate['focus']}",
            "",
            "### Must Compare",
            "",
            *[f"- {item}" for item in next_gate["must_compare"]],
            "",
            "### Blocked Retries",
            "",
            *[f"- {item}" for item in next_gate["blocked_retries"]],
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify()
    manifest = {
        "cycle": "V1558",
        "generated_at": now_iso(),
        "decision": result["decision"],
        "pass": result["pass"],
        "reason": result["reason"],
        "host": collect_host_metadata(),
        "input_paths": {name: rel(path) for name, path in INPUTS.items()},
        "input_decisions": {
            name: {
                "decision": data.get("decision"),
                "pass": data.get("pass"),
                "reason": data.get("reason"),
            }
            for name, data in result["manifests"].items()
        },
        "checks": result["checks"],
        "next_gate": result["next_gate"],
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
