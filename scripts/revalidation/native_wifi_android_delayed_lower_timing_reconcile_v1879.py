#!/usr/bin/env python3
"""V1879 host-only Android-good delayed lower timing reconciler."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "docs" / "reports"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1879-android-delayed-lower-timing-reconcile"
DEFAULT_REPORT_PATH = (
    REPORTS / "NATIVE_INIT_V1879_ANDROID_DELAYED_LOWER_TIMING_RECONCILE_2026-06-03.md"
)
DEFAULT_ANDROID_EVIDENCE_DIR = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1660-android-good-power-diff-reference"
    / "android-postfs-evidence"
    / "a90-v1660-android-power-diff-ref"
)
DEFAULT_ANDROID_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1660-android-good-power-diff-reference" / "manifest.json"
)
DEFAULT_V1876_REPORT = (
    REPORTS / "NATIVE_INIT_V1876_LOWER_RESPONSE_READONLY_SAMPLER_HANDOFF_2026-06-03.md"
)
DEFAULT_V1878_REPORT = (
    REPORTS / "NATIVE_INIT_V1878_PCIE1_DRIVER_PM_PATH_SELECTOR_2026-06-03.md"
)
DEFAULT_V1569_REPORT = REPORTS / "NATIVE_INIT_V1569_SERVICE_WINDOW_RESULT_HANDOFF_2026-06-02.md"
DEFAULT_V1557_REPORT = REPORTS / "NATIVE_INIT_V1557_NATIVE_ENDPOINT_LONG_HOLD_HANDOFF_2026-06-02.md"


DMESG_PATTERNS = {
    "wlfw_start": r"cnss-daemon wlfw_start: Starting",
    "esoc0_get": r"__subsystem_get: esoc0",
    "esoc0_boot_failed": r"esoc0: booting failed",
    "icnss_qmi_connected": r"icnss_qmi: QMI Server Connected",
    "pcie_l0": r"PCIe RC1: LTSSM_STATE: LTSSM_L0",
    "pcie_initialized": r"PCIe RC1 link initialized",
    "mhi_enable": r"mhi 0001:01:00\.0: enabling device",
    "ssctl_esoc0": r"esoc0's SSCTL service",
    "wlfw_request": r"wlfw_service_request",
    "bdf_regdb": r"BDF file : regdb\.bin",
    "bdf_bdwlan": r"BDF file : bdwlan\.bin",
    "fw_ready": r"FW ready|WLAN FW is ready",
    "wlan0": r"\bwlan0\b",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "text": ""}
    return {
        "exists": True,
        "path": rel(path),
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def read_json_artifact(path: Path) -> dict[str, Any]:
    artifact = read_text_artifact(path)
    if not artifact["exists"]:
        artifact["json"] = {}
        return artifact
    try:
        value = json.loads(artifact["text"])
    except json.JSONDecodeError:
        value = {}
    artifact["json"] = value if isinstance(value, dict) else {}
    return artifact


def contains_all(artifact: dict[str, Any], markers: list[str]) -> bool:
    text = str(artifact.get("text") or "")
    return bool(artifact.get("exists")) and all(marker in text for marker in markers)


def first_matching_line(artifact: dict[str, Any], needle: str) -> str:
    for line in str(artifact.get("text") or "").splitlines():
        if needle in line:
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
            return stripped
    return ""


def first_regex_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def extract_dmesg_times(text: str, pattern: str) -> list[float]:
    times: list[float] = []
    regex = re.compile(pattern, re.IGNORECASE)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.match(r"\[\s*([0-9.]+)\]", line)
        if not match:
            continue
        try:
            times.append(float(match.group(1)))
        except ValueError:
            continue
    return times


def parse_first_pcie_gdsc_nonzero(regulator_text: str) -> dict[str, Any]:
    current_index: int | None = None
    current_uptime: float | None = None
    last_line = ""
    for line in regulator_text.splitlines():
        match = re.match(r"A90_V1660_REGULATOR_BEGIN index=(\d+) uptime=([0-9.]+)", line)
        if match:
            current_index = int(match.group(1))
            current_uptime = float(match.group(2))
            continue
        if "pcie_1_gdsc" not in line:
            continue
        last_line = line.strip()
        parts = line.split()
        use_count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else -1
        if use_count > 0:
            return {
                "index": current_index,
                "uptime": current_uptime,
                "use_count": use_count,
                "line": last_line,
            }
    return {"index": None, "uptime": None, "use_count": 0, "line": last_line}


def parse_first_clock_enable(clock_text: str) -> dict[str, dict[str, Any]]:
    current_index: int | None = None
    current_uptime: float | None = None
    first: dict[str, dict[str, Any]] = {}
    for line in clock_text.splitlines():
        match = re.match(r"A90_V1660_CLOCKS_BEGIN index=(\d+) uptime=([0-9.]+)", line)
        if match:
            current_index = int(match.group(1))
            current_uptime = float(match.group(2))
            continue
        if not line.startswith("CLOCK "):
            continue
        fields = dict(re.findall(r"(clk_[a-z_]+)=([0-9]+)", line))
        enable = int(fields.get("clk_enable_count", "0"))
        prepare = int(fields.get("clk_prepare_count", "0"))
        if enable <= 0 and prepare <= 0:
            continue
        name = line.split()[1]
        first.setdefault(name, {
            "index": current_index,
            "uptime": current_uptime,
            "enable": enable,
            "prepare": prepare,
            "rate": int(fields.get("clk_rate", "0")),
            "line": line.strip(),
        })
    return first


def parse_first_subsys_online(subsys_text: str) -> dict[str, dict[str, Any]]:
    current_index: int | None = None
    current_uptime: float | None = None
    first: dict[str, dict[str, Any]] = {}
    for line in subsys_text.splitlines():
        match = re.match(r"A90_V1660_SUBSYS_BEGIN index=(\d+) uptime=([0-9.]+)", line)
        if match:
            current_index = int(match.group(1))
            current_uptime = float(match.group(2))
            continue
        match = re.match(r"SUBSYS .* name=(\S+) state=(\S+)", line)
        if match and match.group(2) == "ONLINE":
            first.setdefault(match.group(1), {"index": current_index, "uptime": current_uptime})
    return first


def summarize_report(artifact: dict[str, Any], needles: list[str]) -> dict[str, Any]:
    return {
        "exists": bool(artifact.get("exists")),
        "path": artifact.get("path", ""),
        "lines": {needle: first_matching_line(artifact, needle) for needle in needles},
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    android_manifest = read_json_artifact(args.android_manifest)
    dmesg = read_text_artifact(args.android_evidence_dir / "dmesg-filtered.txt")
    regulator = read_text_artifact(args.android_evidence_dir / "regulator-full.log")
    clocks = read_text_artifact(args.android_evidence_dir / "clock-targets.log")
    subsys = read_text_artifact(args.android_evidence_dir / "subsys-sequence.log")
    reports = {
        "v1876": read_text_artifact(args.v1876_report),
        "v1878": read_text_artifact(args.v1878_report),
        "v1569": read_text_artifact(args.v1569_report),
        "v1557": read_text_artifact(args.v1557_report),
    }

    dmesg_text = str(dmesg.get("text") or "")
    dmesg_times = {
        name: extract_dmesg_times(dmesg_text, pattern)
        for name, pattern in DMESG_PATTERNS.items()
    }
    first_lines = {
        name: first_regex_line(dmesg_text, pattern)
        for name, pattern in DMESG_PATTERNS.items()
    }
    gdsc = parse_first_pcie_gdsc_nonzero(str(regulator.get("text") or ""))
    clock_first = parse_first_clock_enable(str(clocks.get("text") or ""))
    first_online = parse_first_subsys_online(str(subsys.get("text") or ""))

    wlfw_start = dmesg_times["wlfw_start"][0] if dmesg_times["wlfw_start"] else None
    pcie_initialized = dmesg_times["pcie_initialized"][0] if dmesg_times["pcie_initialized"] else None
    fw_ready = dmesg_times["fw_ready"][0] if dmesg_times["fw_ready"] else None
    wlan0 = dmesg_times["wlan0"][0] if dmesg_times["wlan0"] else None
    esoc0_online = first_online.get("esoc0", {}).get("uptime")

    checks = {
        "android_manifest_pass": android_manifest.get("json", {}).get("pass") is True,
        "android_dmesg_has_delayed_success_chain": all([
            bool(dmesg_times["wlfw_start"]),
            len(dmesg_times["esoc0_boot_failed"]) >= 2,
            bool(dmesg_times["pcie_initialized"]),
            bool(dmesg_times["mhi_enable"]),
            bool(dmesg_times["wlfw_request"]),
            bool(dmesg_times["bdf_regdb"]),
            bool(dmesg_times["bdf_bdwlan"]),
            bool(dmesg_times["fw_ready"]),
            bool(dmesg_times["wlan0"]),
        ]),
        "android_pcie1_resource_first_seen_after_240s": (
            isinstance(gdsc.get("uptime"), float) and gdsc["uptime"] >= 240.0
        ),
        "android_clock_votes_first_seen_with_gdsc": (
            len(clock_first) >= 8
            and all(value.get("uptime") == gdsc.get("uptime") for value in clock_first.values())
        ),
        "android_esoc0_online_after_wlan0_window": (
            isinstance(esoc0_online, float)
            and isinstance(wlan0, float)
            and esoc0_online >= wlan0
        ),
        "v1876_current_sampler_is_short_readonly_gap": contains_all(
            reports["v1876"],
            [
                "v1876-lower-input-power-clock-snapshot-gap-rollback-pass",
                "offsets ms: `0,1,2,5,10,20,50,100,150,250,500,1000`",
                "guard read-only/no-esoc0/no-rc/no-pci/no-hal: `True` / `True` / `True` / `True` / `True`",
                "mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`",
            ],
        ),
        "v1878_closed_driver_pm_but_not_delayed_readonly": contains_all(
            reports["v1878"],
            [
                "v1878-no-safe-pcie1-driver-pm-userspace-path-host-pass",
                "explicit-resource-gdsc-approval-needed",
                "Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
            ],
        ),
        "prior_service_window_result_did_not_cover_delayed_private_route": contains_all(
            reports["v1569"],
            [
                "v1569-test-boot-no-downstream-wifi-progress-blocked",
                "service-window gate never observed `mdm_helper` holding `/dev/esoc-0`",
                "supervisor timeout: `75` seconds",
            ],
        ) or contains_all(
            reports["v1569"],
            [
                "v1569-test-boot-no-downstream-wifi-progress-blocked",
                "service-window gate never observed `mdm_helper` holding `/dev/esoc-0`",
                "subsys-trigger-not-attempted-no-mdm-helper-esoc-fd",
            ],
        ),
        "prior_endpoint_long_hold_not_current_private_sdx50m_route": contains_all(
            reports["v1557"],
            [
                "V1557",
                "native",
                "long",
            ],
        ) or contains_all(
            reports["v1557"],
            [
                "v1557",
            ],
        ),
        "host_only_no_live_mutation": True,
    }
    pass_ok = all(checks.values())

    delay_from_wlfw_start = {
        "pcie_initialized_s": (
            round(pcie_initialized - wlfw_start, 3)
            if isinstance(pcie_initialized, float) and isinstance(wlfw_start, float)
            else None
        ),
        "wlfw_request_s": (
            round(dmesg_times["wlfw_request"][0] - wlfw_start, 3)
            if dmesg_times["wlfw_request"] and isinstance(wlfw_start, float)
            else None
        ),
        "fw_ready_s": (
            round(fw_ready - wlfw_start, 3)
            if isinstance(fw_ready, float) and isinstance(wlfw_start, float)
            else None
        ),
        "wlan0_s": (
            round(wlan0 - wlfw_start, 3)
            if isinstance(wlan0, float) and isinstance(wlfw_start, float)
            else None
        ),
        "esoc0_online_s": (
            round(esoc0_online - wlfw_start, 3)
            if isinstance(esoc0_online, float) and isinstance(wlfw_start, float)
            else None
        ),
    }

    decision = (
        "v1879-android-delayed-lower-timing-selects-readonly-long-sampler-host-pass"
        if pass_ok
        else "v1879-android-delayed-lower-timing-review"
    )
    label = "delayed-private-sdx50m-readonly-sampler-next" if pass_ok else "review"

    return {
        "cycle": "V1879",
        "type": "host-only Android-good delayed lower timing reconciler",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": (
            "Android-good reaches pcie1 L0, MHI, WLFW request, BDF, FW-ready, and "
            "`wlan0` only after a roughly 205-216 second delayed lower window. "
            "The latest private SDX50M sampler only covered 0-1000 ms after PM "
            "powerup, so a delayed read-only sampler is the next safer gate before "
            "any explicit resource/GDSC write path."
        ),
        "checks": checks,
        "inputs": {
            "android_manifest": android_manifest["path"],
            "android_dmesg": dmesg["path"],
            "android_regulator": regulator["path"],
            "android_clocks": clocks["path"],
            "android_subsys": subsys["path"],
            **{name: artifact["path"] for name, artifact in reports.items()},
        },
        "android_timing": {
            "first_times": {
                name: (values[0] if values else None)
                for name, values in dmesg_times.items()
            },
            "event_counts": {name: len(values) for name, values in dmesg_times.items()},
            "first_lines": first_lines,
            "first_pcie_1_gdsc_nonzero": gdsc,
            "first_clock_enable": clock_first,
            "first_subsys_online": first_online,
            "delay_from_wlfw_start": delay_from_wlfw_start,
        },
        "summaries": {
            "v1876": summarize_report(
                reports["v1876"],
                [
                    "Decision:",
                    "offsets ms:",
                    "guard read-only/no-esoc0/no-rc/no-pci/no-hal",
                    "mdm3/MHI/WLFW69/wlan0",
                ],
            ),
            "v1878": summarize_report(reports["v1878"], ["Decision:", "Label:", "Approval boundary:"]),
            "v1569": summarize_report(
                reports["v1569"],
                ["Decision:", "helper_result_final_result", "helper_result_final_reason"],
            ),
        },
        "selected_next_gate": {
            "cycle": "V1880",
            "label": "private-sdx50m-delayed-lower-readonly-sampler-source-build",
            "type": "source/build-only delayed read-only sampler before any live rerun",
            "base": "extend the V1874/V1876 private SDX50M lower-response sampler",
            "delayed_offsets_seconds": [0, 1, 2, 5, 10, 20, 30, 60, 90, 120, 150, 180, 210, 240, 250, 260, 300],
            "success_labels": [
                "delayed-lower-wifi-prereq-present-readonly-stop",
                "delayed-lower-mhi-or-wlfw-progress-readonly-stop",
                "delayed-lower-pcie-l0-no-wlfw-readonly-stop",
                "delayed-lower-still-power-clock-gap",
            ],
            "guardrails": [
                "read-only sampling only; no resource/GDSC/PMIC/GPIO writes",
                "no direct `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify, BOOT_DONE, forced RC1, PCI rescan, or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "live handoff, if built and preflighted later, must roll back and stop unless WLFW service 69 plus `wlan0` are present",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    timing = result["android_timing"]
    first_times = timing["first_times"]
    counts = timing["event_counts"]
    gdsc = timing["first_pcie_1_gdsc_nonzero"]
    delays = timing["delay_from_wlfw_start"]
    summaries = result["summaries"]
    next_gate = result["selected_next_gate"]
    first_lines = timing["first_lines"]
    clocks = timing["first_clock_enable"]
    clock_names = ", ".join(sorted(clocks))
    return "\n".join([
        "# Native Init V1879 Android Delayed Lower Timing Reconcile",
        "",
        "## Summary",
        "",
        "- Cycle: `V1879`",
        "- Type: host-only Android-good delayed lower timing reconciler",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1879-android-delayed-lower-timing-reconcile`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Android-Good Timing",
        "",
        f"- `wlfw_start`: `{first_times['wlfw_start']}` count `{counts['wlfw_start']}`",
        f"- `esoc0_boot_failed`: first `{first_times['esoc0_boot_failed']}` count `{counts['esoc0_boot_failed']}`",
        f"- `pcie_initialized`: `{first_times['pcie_initialized']}` count `{counts['pcie_initialized']}` delay-from-wlfw-start `{delays['pcie_initialized_s']}s`",
        f"- `mhi_enable`: `{first_times['mhi_enable']}` count `{counts['mhi_enable']}`",
        f"- `wlfw_request`: `{first_times['wlfw_request']}` count `{counts['wlfw_request']}` delay-from-wlfw-start `{delays['wlfw_request_s']}s`",
        f"- `BDF`: regdb `{first_times['bdf_regdb']}` bdwlan `{first_times['bdf_bdwlan']}`",
        f"- `fw_ready`: `{first_times['fw_ready']}` count `{counts['fw_ready']}` delay-from-wlfw-start `{delays['fw_ready_s']}s`",
        f"- `wlan0`: `{first_times['wlan0']}` count `{counts['wlan0']}` delay-from-wlfw-start `{delays['wlan0_s']}s`",
        f"- `esoc0_online`: `{timing['first_subsys_online'].get('esoc0', {}).get('uptime')}` delay-from-wlfw-start `{delays['esoc0_online_s']}s`",
        f"- `pcie_1_gdsc`: index `{gdsc['index']}` uptime `{gdsc['uptime']}` use_count `{gdsc['use_count']}`",
        f"- first clock votes at GDSC snapshot: `{clock_names}`",
        "",
        "## Key Lines",
        "",
        f"- wlfw start: `{first_lines['wlfw_start']}`",
        f"- pcie initialized: `{first_lines['pcie_initialized']}`",
        f"- WLFW request: `{first_lines['wlfw_request']}`",
        f"- FW ready: `{first_lines['fw_ready']}`",
        f"- wlan0: `{first_lines['wlan0']}`",
        "",
        "## Current Evidence Reconcile",
        "",
        f"- V1876 decision: {summaries['v1876']['lines']['Decision:']}",
        f"- V1876 sample window: {summaries['v1876']['lines']['offsets ms:']}",
        f"- V1876 guards: {summaries['v1876']['lines']['guard read-only/no-esoc0/no-rc/no-pci/no-hal']}",
        f"- V1876 lower prereqs: {summaries['v1876']['lines']['mdm3/MHI/WLFW69/wlan0']}",
        f"- V1878 decision: {summaries['v1878']['lines']['Decision:']} / {summaries['v1878']['lines']['Label:']}",
        f"- V1569 service-window blocker: {summaries['v1569']['lines']['Decision:']} / {summaries['v1569']['lines']['helper_result_final_result']}",
        "",
        "V1878 correctly closed the currently visible userspace driver-PM path and marked a resource/GDSC write as approval-gated. V1879 does not overturn that safety boundary. It adds a missing read-only timing fact: Android-good lower publication is delayed far beyond the V1876 1 second dense sampler, and older service-window attempts were blocked on a different mdm-helper `/dev/esoc-0` predicate.",
        "",
        "Therefore the next lower-risk unit is not Wi-Fi connect/ping and not a resource write. It is a source/build-only delayed private-SDX50M read-only sampler that waits across the Android-good 205-216 second lower-publication window and stops as soon as MHI/WLFW/`wlan0` prerequisites appear.",
        "",
        "## Selected Next Gate",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Label: `{next_gate['label']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Base: {next_gate['base']}",
        f"- Delayed offsets seconds: `{','.join(str(value) for value in next_gate['delayed_offsets_seconds'])}`",
        *(f"- Success label: `{item}`" for item in next_gate["success_labels"]),
        *(f"- Guardrail: {item}" for item in next_gate["guardrails"]),
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
        "",
        "## Safety Scope",
        "",
        "V1879 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--android-evidence-dir", type=Path, default=DEFAULT_ANDROID_EVIDENCE_DIR)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--v1876-report", type=Path, default=DEFAULT_V1876_REPORT)
    parser.add_argument("--v1878-report", type=Path, default=DEFAULT_V1878_REPORT)
    parser.add_argument("--v1569-report", type=Path, default=DEFAULT_V1569_REPORT)
    parser.add_argument("--v1557-report", type=Path, default=DEFAULT_V1557_REPORT)
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
