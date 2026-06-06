#!/usr/bin/env python3
"""V1889 host-only inventory of retained normal-Android PM msg-id visibility."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_SCAN_ROOT = REPO_ROOT / "tmp" / "wifi"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1889-retained-android-msgid-inventory"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1889_RETAINED_ANDROID_MSGID_INVENTORY_2026-06-03.md"
)
DEFAULT_V1888_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1888-pm-msgid-capture-diff-classifier" / "manifest.json"


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
LOGCAT_TIME_RE = re.compile(r"^\d\d-\d\d\s+(?P<time>\d\d:\d\d:\d\d\.\d+)")
MSG22_RE = re.compile(
    r"QMI service peripheral restart request|QMI service peripheral restart response|"
    r"peripheral restart request|msg(?:_| |id)?0x22|msg(?:_| |id)?22|pm_msg22",
    re.IGNORECASE,
)
PM_VOTE_RE = re.compile(r"cnss-daemon voting for modem", re.IGNORECASE)
PM_REGISTER_RE = re.compile(r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, max_bytes: int) -> str:
    if not path.exists() or path.stat().st_size > max_bytes:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def count_lines(lines: list[str], regex: re.Pattern[str]) -> int:
    return sum(1 for line in lines if regex.search(line))


def first_line(lines: list[str], regex: re.Pattern[str]) -> str:
    for line in lines:
        if regex.search(line):
            return line.strip()
    return ""


def first_logcat_time(lines: list[str], regex: re.Pattern[str]) -> str:
    line = first_line(lines, regex)
    match = LOGCAT_TIME_RE.search(line)
    return match.group("time") if match else ""


def first_dmesg_time(lines: list[str], regex: re.Pattern[str]) -> float | None:
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_dmesg_before(lines: list[str], regex: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def candidate_dirs(scan_root: Path) -> list[Path]:
    dirs: set[Path] = set()
    for logcat in scan_root.rglob("logcat-filtered.txt"):
        root = logcat.parent
        if (root / "dmesg-filtered.txt").exists():
            dirs.add(root)
    return sorted(dirs)


def analyze_candidate(root: Path, max_bytes: int) -> dict[str, Any]:
    logcat_path = root / "logcat-filtered.txt"
    dmesg_path = root / "dmesg-filtered.txt"
    request_path = root / "request-lines.txt"
    too_large = [rel(path) for path in (logcat_path, dmesg_path, request_path) if path.exists() and path.stat().st_size > max_bytes]
    logcat = read_text(logcat_path, max_bytes).splitlines()
    dmesg = read_text(dmesg_path, max_bytes).splitlines()
    request = read_text(request_path, max_bytes).splitlines()
    combined = logcat + dmesg + request
    wlan0_time = first_dmesg_time(dmesg, WLAN0_RE)
    pcie_mhi_before_wlan0 = count_dmesg_before(dmesg, PCIE_MHI_RE, wlan0_time)
    esoc_boot_failed_before_wlan0 = count_dmesg_before(dmesg, ESOC_BOOT_FAILED_RE, wlan0_time)
    pm_vote_count = count_lines(logcat, PM_VOTE_RE)
    wlan_pd_count = count_lines(dmesg, WLAN_PD_RE)
    wlanmdsp_count = count_lines(logcat, WLANMDSP_RE)
    normal_stateup = (
        not too_large
        and pm_vote_count > 0
        and count_lines(logcat, WLFW_REQUEST_RE) > 0
        and wlan_pd_count > 0
        and wlanmdsp_count > 0
        and wlan0_time is not None
        and wlan0_time <= 120.0
        and pcie_mhi_before_wlan0 == 0
        and esoc_boot_failed_before_wlan0 == 0
    )
    return {
        "dir": rel(root),
        "too_large": too_large,
        "logcat_lines": len(logcat),
        "dmesg_lines": len(dmesg),
        "request_lines": len(request),
        "pm_register_count": count_lines(logcat, PM_REGISTER_RE),
        "pm_vote_count": pm_vote_count,
        "pm_vote_first_time": first_logcat_time(logcat, PM_VOTE_RE),
        "wlfw_request_count": count_lines(logcat, WLFW_REQUEST_RE),
        "wlfw_request_first_time": first_logcat_time(logcat, WLFW_REQUEST_RE),
        "wlan_pd_count": wlan_pd_count,
        "wlan_pd_time_s": first_dmesg_time(dmesg, WLAN_PD_RE),
        "wlanmdsp_count": wlanmdsp_count,
        "wlanmdsp_first_time": first_logcat_time(logcat, WLANMDSP_RE),
        "wlan0_time_s": wlan0_time,
        "pcie_mhi_before_wlan0": pcie_mhi_before_wlan0,
        "esoc_boot_failed_before_wlan0": esoc_boot_failed_before_wlan0,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "pm_msg22_hits": count_lines(combined, MSG22_RE),
        "pm_msg22_first_line": first_line(combined, MSG22_RE),
        "normal_stateup": normal_stateup,
    }


def classify(candidates: list[dict[str, Any]], v1888: dict[str, Any]) -> tuple[str, bool, str, str]:
    normal = [candidate for candidate in candidates if candidate["normal_stateup"]]
    normal_with_msg22 = [candidate for candidate in normal if candidate["pm_msg22_hits"] > 0]
    if normal_with_msg22:
        return (
            "v1889-retained-normal-msg22-observed-host-pass",
            True,
            "at least one retained normal Android capture contains pm-service msg22 visibility",
            "retained-normal-msg22-observed",
        )
    if normal:
        return (
            "v1889-retained-normal-captures-lack-pm-msgid-host-pass",
            True,
            "retained normal Android state-up captures exist, but none contain pm-service msg22 visibility",
            "retained-normal-captures-lack-pm-msgid-visibility",
        )
    if v1888.get("label") == "android-stateup-without-msg22-log-observability-gap":
        return (
            "v1889-v1888-only-normal-capture-no-msgid-host-pass",
            True,
            "only the V1888 retained normal sample qualifies, and it lacks pm-service msg22 visibility",
            "v1888-only-normal-capture-no-msgid",
        )
    return (
        "v1889-no-retained-normal-stateup-capture-host-pass",
        True,
        "no bounded retained normal Android state-up capture was found",
        "no-retained-normal-stateup-capture",
    )


def render_report(result: dict[str, Any]) -> str:
    normal = result["normal_candidates"]
    normal_msg22 = result["normal_msg22_candidates"]
    top = normal[:5]
    lines = [
        "# Native Init V1889 Retained Android Msg-id Inventory",
        "",
        "## Summary",
        "",
        "- Cycle: `V1889`",
        "- Type: host-only bounded inventory of retained normal-Android PM msg-id visibility",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inventory",
        "",
        f"- scan root: `{result['scan_root']}`",
        f"- candidate dirs: `{result['candidate_count']}`",
        f"- normal state-up candidates: `{len(normal)}`",
        f"- normal candidates with msg22: `{len(normal_msg22)}`",
        f"- V1888 label: `{result['v1888_label']}`",
        "",
        "## Normal Candidates",
        "",
    ]
    if top:
        for candidate in top:
            lines.extend(
                [
                    f"- dir: `{candidate['dir']}`",
                    f"  PM vote/WLFW/wlan_pd/wlanmdsp/wlan0: `{candidate['pm_vote_count']}` / `{candidate['wlfw_request_count']}` / `{candidate['wlan_pd_count']}` / `{candidate['wlanmdsp_count']}` / `{candidate['wlan0_time_s']}`",
                    f"  contamination/msg22: PCIe-MHI `{candidate['pcie_mhi_before_wlan0']}` / esoc-failed `{candidate['esoc_boot_failed_before_wlan0']}` / degraded257 `{candidate['degraded_257s_like']}` / msg22 `{candidate['pm_msg22_hits']}`",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The bounded retained inventory did not find a stronger existing normal-Android sample with pm-service msg `0x22` visibility.",
            "- The retained normal path still proves internal PM vote -> WLAN-PD state-up -> `wlanmdsp.mbn` -> `wlan0` with no PCIe/MHI contamination.",
            "- The next useful evidence must be a fresh normal-Android capture with explicit pm-service msg-id visibility, then V1888 can promote to `android-msg22-stateup-observed-native-absent` if msg22 appears.",
            "",
            "## Safety Scope",
            "",
            "V1889 is host-only. It scans bounded retained text files and writes local inventory artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Capture a fresh normal Android boot with pm-service msg-id visibility; reject degraded 257s or pre-wlan0 PCIe/MHI captures.",
            "- Keep native init at v724/selftest fail=0 until a bounded rollbackable internal-modem gate is justified.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-root", type=Path, default=DEFAULT_SCAN_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888_MANIFEST)
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    v1888 = read_json(args.v1888_manifest)
    candidates = [analyze_candidate(root, args.max_bytes) for root in candidate_dirs(args.scan_root)]
    normal = [candidate for candidate in candidates if candidate["normal_stateup"]]
    normal_msg22 = [candidate for candidate in normal if candidate["pm_msg22_hits"] > 0]
    decision, passed, reason, label = classify(candidates, v1888)
    result = {
        "cycle": "V1889",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "scan_root": rel(args.scan_root),
        "candidate_count": len(candidates),
        "v1888_manifest": rel(args.v1888_manifest),
        "v1888_label": v1888.get("label", ""),
        "candidates": candidates,
        "normal_candidates": normal,
        "normal_msg22_candidates": normal_msg22,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/retained-android-msgid-candidates.json", json.dumps(candidates, indent=2, sort_keys=True) + "\n")
    store.write_text("host/normal-candidates.json", json.dumps(normal, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
