#!/usr/bin/env python3
"""V1872 host-only blocker realignment toward lower-response inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1872-lower-response-input-reconcile"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1872_LOWER_RESPONSE_INPUT_RECONCILE_2026-06-03.md"
)
REPORTS = REPO_ROOT / "docs" / "reports"
DEFAULT_V1871_REPORT = REPORTS / "NATIVE_INIT_V1871_PRIVATE_MOUNT_PM_VOTE_RECONCILE_2026-06-03.md"
DEFAULT_V1870_REPORT = REPORTS / "NATIVE_INIT_V1870_SDX50M_PRIVATE_MOUNT_SUMMARY_HANDOFF_2026-06-03.md"
DEFAULT_V1808_REPORT = REPORTS / "NATIVE_INIT_V1808_PM_CLIENT_RETURN_FETCHARGS_HANDOFF_2026-06-03.md"
DEFAULT_V1847_REPORT = REPORTS / "NATIVE_INIT_V1847_PM_SERVICE_OPEN_CONTEXT_HANDOFF_2026-06-03.md"
DEFAULT_V1849_REPORT = REPORTS / "NATIVE_INIT_V1849_SDX50M_PRIVATE_ROUTE_REUSE_CLASSIFIER_2026-06-03.md"
DEFAULT_V1239_REPORT = REPORTS / "NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "text": ""}
    return {
        "exists": True,
        "path": rel(path),
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def contains_all(report: dict[str, Any], markers: list[str]) -> bool:
    text = str(report.get("text") or "")
    return bool(report.get("exists")) and all(marker in text for marker in markers)


def first_matching_line(report: dict[str, Any], needle: str) -> str:
    for line in str(report.get("text") or "").splitlines():
        if needle in line:
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
            return stripped
    return ""


def summarize(report: dict[str, Any], needles: list[str]) -> dict[str, Any]:
    return {
        "exists": bool(report.get("exists")),
        "path": report.get("path", ""),
        "lines": {needle: first_matching_line(report, needle) for needle in needles},
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    reports = {
        "v1871": read_report(args.v1871_report),
        "v1870": read_report(args.v1870_report),
        "v1808": read_report(args.v1808_report),
        "v1847": read_report(args.v1847_report),
        "v1849": read_report(args.v1849_report),
        "v1239": read_report(args.v1239_report),
    }
    checks = {
        "v1871_identified_pm_vote_gap": contains_all(
            reports["v1871"],
            [
                "v1871-private-mount-does-not-close-pm-vote-gap-host-pass",
                "private-mount-selection-closed-pm-vote-gap-open",
            ],
        ),
        "v1870_private_retry_has_no_wifi_prereq": contains_all(
            reports["v1870"],
            [
                "v1870-private-mount-sdx50m-selected-rollback-pass",
                "lower-continuation label: `lower-continuation-static-gap`",
                "mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`",
                "PM-client register/connect/return-path rc: `0` / `0` / `0`",
            ],
        ),
        "v1808_pm_client_boundary_closed": contains_all(
            reports["v1808"],
            [
                "v1808-pm-client-return-success-still-offlining-rollback-pass",
                "register rc: `0`",
                "connect rc: `0`",
                "PM init return-path rc: `0`",
                "WLFW service69 progress: `False`",
            ],
        ),
        "v1847_post_ack_open_success_static": contains_all(
            reports["v1847"],
            [
                "v1847-open-context-modem-success-static-rollback-pass",
                "open-context label: `open-context-modem-success-static`",
                "open-context path/state/fd: `/dev/subsys_modem`",
                "lower-continuation label: `lower-continuation-static-gap`",
            ],
        ),
        "v1849_private_sdx50m_reuse_is_known_lower_gap": contains_all(
            reports["v1849"],
            [
                "v1849-private-sdx50m-route-known-lower-gap-host-pass",
                "private-sdx50m-route-known-lower-gap",
                "The known failure is below PM-service eSoC open",
            ],
        ),
        "v1239_gap_after_esoc0_before_response": contains_all(
            reports["v1239"],
            [
                "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw",
                "Binder `mdm_subsys_powerup` | present",
                "GPIO142 IRQ | `1` | not observed",
                "`ks` / MHI pipe | present | absent",
            ],
        ),
        "hard_stops_preserved": contains_all(
            reports["v1870"],
            [
                "No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
                "direct `/dev/subsys_esoc0` open",
                "forced RC1",
            ],
        ),
    }
    pass_ok = all(checks.values())
    label = "pm-vote-closed-lower-response-input-next" if pass_ok else "review"
    decision = (
        "v1872-pm-vote-closed-lower-response-input-next-host-pass"
        if pass_ok
        else "v1872-lower-response-input-reconcile-review"
    )
    return {
        "cycle": "V1872",
        "type": "host-only blocker realignment after private SDX50M retry",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": (
            "Current and historical evidence already closes PM-client register/connect and post-ack open reachability; "
            "private SDX50M reuse is a known lower-response gap, so the next unit should target the response-input contract after mdm_subsys_powerup rather than another PM vote repair."
        ),
        "checks": checks,
        "inputs": {name: report["path"] for name, report in reports.items()},
        "summaries": {
            "v1870": summarize(reports["v1870"], ["Decision:", "lower-continuation label", "mdm3/MHI/WLFW69/wlan0"]),
            "v1808": summarize(reports["v1808"], ["Decision:", "PM init return-path rc", "WLFW service69 progress"]),
            "v1847": summarize(reports["v1847"], ["Decision:", "open-context label", "open-context path/state/fd"]),
            "v1849": summarize(reports["v1849"], ["Decision:", "Label:", "The known failure is below PM-service eSoC open"]),
            "v1239": summarize(reports["v1239"], ["decision:", "Binder `mdm_subsys_powerup`", "| GPIO142 IRQ |", "`ks` / MHI pipe"]),
        },
        "selected_next_gate": {
            "cycle": "V1873",
            "label": "lower-response-input-contract-source-only",
            "type": "host/source-only first",
            "scope": (
                "Join Android-positive and native-static evidence around mdm_subsys_powerup response inputs: "
                "GPIO142 IRQ, PCIe RC1/link state, SSCTL/sysmon, MHI pipe creation, and ks lifetime/order."
            ),
            "success_criteria": [
                "select one cleanup-safe read-only live discriminator before any new mutation",
                "preserve no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "preserve no direct eSoC open, fake ONLINE, forced RC1, PMIC/GPIO/GDSC writes, or PCI rescan/platform bind-unbind",
                "only consider Wi-Fi connect after WLFW service 69 and wlan0 both exist",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    summaries = result["summaries"]
    next_gate = result["selected_next_gate"]
    return "\n".join([
        "# Native Init V1872 Lower Response Input Reconcile",
        "",
        "## Summary",
        "",
        "- Cycle: `V1872`",
        "- Type: host-only blocker realignment after private SDX50M retry",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1872-lower-response-input-reconcile`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Boundary Evidence",
        "",
        f"- V1870 decision/lower: {summaries['v1870']['lines']['Decision:']} / {summaries['v1870']['lines']['lower-continuation label']}",
        f"- V1870 lower state: {summaries['v1870']['lines']['mdm3/MHI/WLFW69/wlan0']}",
        f"- V1808 PM return: {summaries['v1808']['lines']['PM init return-path rc']}",
        f"- V1847 open context: {summaries['v1847']['lines']['open-context path/state/fd']}",
        f"- V1849 lower-gap line: {summaries['v1849']['lines']['The known failure is below PM-service eSoC open']}",
        f"- V1239 response gap: {summaries['v1239']['lines']['decision:']}",
        f"- V1239 mdm_subsys_powerup: {summaries['v1239']['lines']['Binder `mdm_subsys_powerup`']}",
        f"- V1239 GPIO142: {summaries['v1239']['lines']['| GPIO142 IRQ |']}",
        f"- V1239 ks/MHI: {summaries['v1239']['lines']['`ks` / MHI pipe']}",
        "",
        "## Interpretation",
        "",
        "V1871 correctly avoided another blind private-mount retry, but the older V1808/V1847/V1849/V1239 chain is stronger than a new PM-vote repair: PM-client register/connect/return already reached zero, PM-service post-ack open reached a supported devnode, and the private SDX50M/eSoC route is already known to stall below `mdm_subsys_powerup` before GPIO142, PCIe, MHI, WLFW, BDF, and `wlan0` response.",
        "",
        "Therefore V1872 changes the next blocker from `PM register/vote repair` to `lower response-input contract selection`. This is a host-only decision; it does not make a live mutation safe by itself.",
        "",
        "## Next",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Label: `{next_gate['label']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Scope: {next_gate['scope']}",
        *(f"- Success criterion: {item}" for item in next_gate["success_criteria"]),
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
        "",
        "## Safety Scope",
        "",
        "V1872 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1871-report", type=Path, default=DEFAULT_V1871_REPORT)
    parser.add_argument("--v1870-report", type=Path, default=DEFAULT_V1870_REPORT)
    parser.add_argument("--v1808-report", type=Path, default=DEFAULT_V1808_REPORT)
    parser.add_argument("--v1847-report", type=Path, default=DEFAULT_V1847_REPORT)
    parser.add_argument("--v1849-report", type=Path, default=DEFAULT_V1849_REPORT)
    parser.add_argument("--v1239-report", type=Path, default=DEFAULT_V1239_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
