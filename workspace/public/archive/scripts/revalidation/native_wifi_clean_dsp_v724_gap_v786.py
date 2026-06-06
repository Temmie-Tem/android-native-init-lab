#!/usr/bin/env python3
"""V786 host-only clean-DSP/v724 gap classifier.

V775 paused custom OSRC kernel flashing and V785 identified the first current
stock-v724 divergence as missing sibling sysmon with mdm3 still OFFLINING.  This
classifier reconciles that with the historical V641/V642/V644 clean-DSP branch:
it checks whether current v724 still contains the V641 one-shot sibling SSCTL
hook, whether V782 actually armed/executed it, and what the next safe gate is.

No device command, boot image write, reboot, Wi-Fi HAL, scan/connect, credential
use, DHCP, route change, or external ping is executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v786-clean-dsp-v724-gap")
LATEST_POINTER = Path("tmp/wifi/latest-v786-clean-dsp-v724-gap.txt")
DEFAULT_V724_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")
DEFAULT_V641_SOURCE = Path("stage3/linux_init/v641/90_main.inc.c")
DEFAULT_V724_BUILDER = Path("scripts/revalidation/build_native_init_boot_v724.py")
DEFAULT_V724_BOOT = Path("stage3/boot_linux_v724.img")
DEFAULT_V775_MANIFEST = Path("tmp/wifi/v775-boot-incompat-postmortem/manifest.json")
DEFAULT_V782_MANIFEST = Path("tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json")
DEFAULT_V782_DMESG = Path("tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt")
DEFAULT_V782_SUMMARY = Path("tmp/wifi/v782-bpf-counter-boot-wlan/summary.md")
DEFAULT_V785_MANIFEST = Path("tmp/wifi/v785-android-native-memshare-delta/manifest.json")
DEFAULT_V641_REPORT = Path("docs/reports/NATIVE_INIT_V641_FIRMWARE_BACKED_BOOT_WINDOW_ARMED_LIVE_2026-05-23.md")
DEFAULT_V642_REPORT = Path("docs/reports/NATIVE_INIT_V642_CLEAN_DSP_LOWER_COMPANION_LIVE_2026-05-23.md")
DEFAULT_V644_REPORT = Path("docs/reports/NATIVE_INIT_V644_CLEAN_DSP_CNSS_WLFW_READBACK_LIVE_2026-05-23.md")
DEFAULT_V645_REPORT = Path("docs/reports/NATIVE_INIT_V645_V644_WARNING_ATTRIBUTION_2026-05-23.md")
DEFAULT_V768_REPORT = Path("docs/reports/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_2026-05-25.md")
READ_LIMIT_BYTES = 8 * 1024 * 1024

SIBLING_SYSMON_RE = re.compile(r"sysmon-qmi:.*(?:slpi|adsp|cdsp)'s SSCTL service", re.IGNORECASE)
V641_RUNTIME_RE = re.compile(r"A90v641|wifi-v641|native-init-sibling-fwssctl-v641|fwssctl", re.IGNORECASE)
SERVICE_NOTIFIER_RE = re.compile(r"service-notifier:.*(?:180|74) service", re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v724-source", type=Path, default=DEFAULT_V724_SOURCE)
    parser.add_argument("--v641-source", type=Path, default=DEFAULT_V641_SOURCE)
    parser.add_argument("--v724-builder", type=Path, default=DEFAULT_V724_BUILDER)
    parser.add_argument("--v724-boot", type=Path, default=DEFAULT_V724_BOOT)
    parser.add_argument("--v775-manifest", type=Path, default=DEFAULT_V775_MANIFEST)
    parser.add_argument("--v782-manifest", type=Path, default=DEFAULT_V782_MANIFEST)
    parser.add_argument("--v782-dmesg", type=Path, default=DEFAULT_V782_DMESG)
    parser.add_argument("--v782-summary", type=Path, default=DEFAULT_V782_SUMMARY)
    parser.add_argument("--v785-manifest", type=Path, default=DEFAULT_V785_MANIFEST)
    parser.add_argument("--v641-report", type=Path, default=DEFAULT_V641_REPORT)
    parser.add_argument("--v642-report", type=Path, default=DEFAULT_V642_REPORT)
    parser.add_argument("--v644-report", type=Path, default=DEFAULT_V644_REPORT)
    parser.add_argument("--v645-report", type=Path, default=DEFAULT_V645_REPORT)
    parser.add_argument("--v768-report", type=Path, default=DEFAULT_V768_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    size = resolved.stat().st_size if resolved.is_file() else None
    return {"path": str(resolved), "exists": True, "is_file": resolved.is_file(), "size": size}


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info = file_info(path)
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info["bytes_read"] = len(data)
    info["truncated"] = resolved.stat().st_size > len(data)
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, _ = safe_read(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def line_no(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def count_regex(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


def boot_contains_markers(path: Path, markers: tuple[bytes, ...]) -> dict[str, Any]:
    resolved = resolve(path)
    info = file_info(path)
    found = {marker.decode("utf-8", errors="replace"): False for marker in markers}
    if not resolved.exists() or not resolved.is_file():
        return {"file": info, "markers": found}
    tail = b""
    max_marker_len = max(len(marker) for marker in markers)
    with resolved.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            window = tail + chunk
            for marker in markers:
                if marker in window:
                    found[marker.decode("utf-8", errors="replace")] = True
            tail = window[-max_marker_len:]
    return {"file": info, "markers": found}


def source_scan(v724_source: Path, v641_source: Path, v724_builder: Path, v724_boot: Path) -> dict[str, Any]:
    v724_text, v724_info = safe_read(v724_source)
    v641_text, v641_info = safe_read(v641_source)
    builder_text, builder_info = safe_read(v724_builder)
    boot_markers = boot_contains_markers(
        v724_boot,
        (
            b"A90 Linux init 0.9.68 (v724)",
            b"native-init-sibling-fwssctl-v641",
            b"wifi-v641-fwssctl",
            b"A90v641: sibling fwssctl proof armed",
        ),
    )
    qrtr_call_line = line_no(v724_text, "v724_run_qrtr_servloc_boot_once();")
    sibling_call_line = line_no(v724_text, "v641_run_sibling_ssctl_once();")
    return {
        "inputs": {
            "v724_source": v724_info,
            "v641_source": v641_info,
            "v724_builder": builder_info,
            "v724_boot": boot_markers["file"],
        },
        "v724_contains_v641_flag": "A90_V641_SIBLING_SSCTL_FLAG" in v724_text,
        "v724_contains_v641_runner": "static void v641_run_sibling_ssctl_once(void)" in v724_text,
        "v724_contains_firmware_mounts": "v641_prepare_firmware_mounts" in v724_text,
        "v724_contains_sibling_nodes": all(
            marker in v724_text
            for marker in (
                "/sys/kernel/boot_adsp/boot",
                "/sys/kernel/boot_cdsp/boot",
                "/sys/kernel/boot_slpi/boot",
            )
        ),
        "v724_calls_qrtr_hook": qrtr_call_line is not None,
        "v724_calls_v641_hook": sibling_call_line is not None,
        "v724_qrtr_call_line": qrtr_call_line,
        "v724_v641_call_line": sibling_call_line,
        "v724_calls_qrtr_before_v641": (
            qrtr_call_line is not None and sibling_call_line is not None and qrtr_call_line < sibling_call_line
        ),
        "v724_builder_verifies_v641_markers": all(
            marker in builder_text
            for marker in (
                "native-init-sibling-fwssctl-v641",
                "wifi-v641-fwssctl",
            )
        ),
        "v724_boot_markers": boot_markers["markers"],
        "v724_boot_contains_v641_markers": all(boot_markers["markers"].values()),
        "v641_source_contains_same_runner": "static void v641_run_sibling_ssctl_once(void)" in v641_text,
        "v641_source_contains_sibling_nodes": all(
            marker in v641_text
            for marker in (
                "/sys/kernel/boot_adsp/boot",
                "/sys/kernel/boot_cdsp/boot",
                "/sys/kernel/boot_slpi/boot",
            )
        ),
    }


def report_scan(args: argparse.Namespace) -> dict[str, Any]:
    report_paths = {
        "v641": args.v641_report,
        "v642": args.v642_report,
        "v644": args.v644_report,
        "v645": args.v645_report,
        "v768": args.v768_report,
    }
    reports: dict[str, Any] = {}
    for key, path in report_paths.items():
        text, info = safe_read(path)
        reports[key] = {
            "file": info,
            "decision_lines": [
                line.strip()
                for line in text.splitlines()
                if "decision:" in line.lower() or "- decision:" in line.lower()
            ][:8],
            "has_v641_clean_decision": "v641-dsp-pil-clean-no-service74" in text,
            "has_v642_lower_decision": "v642-lower-modem-readiness-only" in text,
            "has_v644_service74_advance": "service_notifier_180=1" in text and "service_notifier_74=1" in text,
            "has_v644_warning": key == "v644" and ("kernel_warning=5" in text or "pm_qos_add_request" in text),
            "has_v645_warning_classified": "v645-service74-window-warning-risk-classified" in text,
            "has_v768_rejections": all(
                marker in text
                for marker in (
                    "repeat service180-gated `mdm_helper`",
                    "raw esoc0 open or hold",
                    "subsystem state write or bind/unbind",
                )
            ),
        }
    return reports


def runtime_scan(args: argparse.Namespace) -> dict[str, Any]:
    v775 = load_json(args.v775_manifest)
    v782 = load_json(args.v782_manifest)
    v785 = load_json(args.v785_manifest)
    v782_dmesg, v782_dmesg_info = safe_read(args.v782_dmesg)
    v782_summary, v782_summary_info = safe_read(args.v782_summary)
    v782_text = v782_dmesg + "\n" + v782_summary
    v782_live = v782.get("live") or {}
    v785_comparison = ((v785.get("analysis") or {}).get("comparison") or {})
    return {
        "inputs": {
            "v775_manifest": file_info(args.v775_manifest),
            "v782_manifest": file_info(args.v782_manifest),
            "v782_dmesg": v782_dmesg_info,
            "v782_summary": v782_summary_info,
            "v785_manifest": file_info(args.v785_manifest),
        },
        "v775_decision": v775.get("decision", ""),
        "v775_pass": v775.get("pass"),
        "v775_custom_kernel_pause": "pause" in str(v775.get("next_step", "")).lower()
        or "custom-kernel flash paused" in json.dumps(v775, ensure_ascii=False).lower(),
        "v782_decision": v782.get("decision", ""),
        "v782_pass": v782.get("pass"),
        "v782_version": (
            (((v782.get("checks") or [{}])[3] if len(v782.get("checks") or []) > 3 else {}).get("detail") or {})
            .get("preflight", {})
            .get("version_text", "")
            .splitlines()[0:1]
        ),
        "v782_boot_wlan_executed": bool(v782_live.get("boot_wlan_write_executed")),
        "v782_companion_executed": bool(v782_live.get("companion_executed")),
        "v782_mss_after_boot": v782_live.get("mss_after_boot", ""),
        "v782_mdm3_after_boot": v782_live.get("mdm3_after_boot", ""),
        "v782_v641_runtime_marker_count": count_regex(v782_text, V641_RUNTIME_RE),
        "v782_sibling_sysmon_count": count_regex(v782_dmesg, SIBLING_SYSMON_RE),
        "v782_service_notifier_count": count_regex(v782_dmesg, SERVICE_NOTIFIER_RE),
        "v785_decision": v785.get("decision", ""),
        "v785_pass": v785.get("pass"),
        "v785_first_divergence": v785_comparison.get("first_divergence", ""),
        "v785_native_sibling_sysmon_count": v785_comparison.get("native_sibling_sysmon_count"),
        "v785_android_sibling_sysmon_count": v785_comparison.get("android_sibling_sysmon_count"),
    }


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    sources = source_scan(args.v724_source, args.v641_source, args.v724_builder, args.v724_boot)
    reports = report_scan(args)
    runtime = runtime_scan(args)
    return {
        "inputs": {
            **sources["inputs"],
            **runtime["inputs"],
            "v641_report": reports["v641"]["file"],
            "v642_report": reports["v642"]["file"],
            "v644_report": reports["v644"]["file"],
            "v645_report": reports["v645"]["file"],
            "v768_report": reports["v768"]["file"],
        },
        "sources": sources,
        "reports": reports,
        "runtime": runtime,
        "derived": {
            "v724_clean_dsp_hook_available": (
                sources["v724_contains_v641_flag"]
                and sources["v724_contains_v641_runner"]
                and sources["v724_contains_firmware_mounts"]
                and sources["v724_contains_sibling_nodes"]
                and sources["v724_calls_v641_hook"]
                and sources["v724_boot_contains_v641_markers"]
            ),
            "v782_clean_dsp_unarmed_or_unobserved": (
                runtime["v782_v641_runtime_marker_count"] == 0
                and runtime["v782_sibling_sysmon_count"] == 0
                and runtime["v782_service_notifier_count"] == 0
            ),
            "historical_clean_dsp_branch_proven": (
                reports["v641"]["has_v641_clean_decision"]
                and reports["v642"]["has_v642_lower_decision"]
                and reports["v644"]["has_v644_service74_advance"]
            ),
            "historical_service74_warning_risk": (
                reports["v644"]["has_v644_warning"] and reports["v645"]["has_v645_warning_classified"]
            ),
            "unsafe_retry_branches_closed": reports["v768"]["has_v768_rejections"],
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_trigger_executed": False,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    inputs = analysis["inputs"]
    sources = analysis["sources"]
    runtime = analysis["runtime"]
    derived = analysis["derived"]
    checks: list[Check] = []
    add_check(
        checks,
        "required-inputs",
        "pass" if all(info.get("exists") for info in inputs.values()) else "blocked",
        "blocker",
        " ".join(f"{name}={info.get('exists')}" for name, info in inputs.items()),
        "restore exact V641/V642/V644/V645/V768/V775/V782/V785 evidence before classifying",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "device_commands=false reboot=false flash=false wifi_trigger=false",
        "keep V786 host-only; live arm/reboot must be a later explicit gate",
    )
    add_check(
        checks,
        "custom-kernel-paused",
        "pass" if runtime["v775_pass"] is True and runtime["v775_custom_kernel_pause"] else "review",
        "warn",
        f"v775={runtime['v775_decision']} pass={runtime['v775_pass']} pause={runtime['v775_custom_kernel_pause']}",
        "do not retry V770/V773 custom OSRC kernels until compatibility is solved",
    )
    add_check(
        checks,
        "v724-clean-dsp-hook-source",
        "pass" if derived["v724_clean_dsp_hook_available"] else "blocked",
        "blocker",
        (
            f"flag={sources['v724_contains_v641_flag']} runner={sources['v724_contains_v641_runner']} "
            f"nodes={sources['v724_contains_sibling_nodes']} call={sources['v724_calls_v641_hook']} "
            f"line={sources['v724_v641_call_line']} boot_markers={sources['v724_boot_contains_v641_markers']}"
        ),
        "if missing, reintroduce the V641 one-shot hook before live arm-only proof",
    )
    add_check(
        checks,
        "v724-hook-order",
        "pass" if sources["v724_calls_qrtr_before_v641"] else "review",
        "warn",
        f"qrtr_line={sources['v724_qrtr_call_line']} v641_line={sources['v724_v641_call_line']}",
        "future live proof must arm only the V641 flag first, not both QRTR and V641 flags together",
    )
    add_check(
        checks,
        "v782-clean-dsp-not-executed",
        "pass" if derived["v782_clean_dsp_unarmed_or_unobserved"] else "review",
        "warn",
        (
            f"v641_runtime_markers={runtime['v782_v641_runtime_marker_count']} "
            f"sibling_sysmon={runtime['v782_sibling_sysmon_count']} "
            f"service_notifier={runtime['v782_service_notifier_count']}"
        ),
        "treat V782 as lower-window boot_wlan without clean-DSP preconditioning",
    )
    add_check(
        checks,
        "v785-gap-reconciled",
        "pass" if runtime["v785_decision"] == "v785-memshare-common-nonfatal-sibling-sysmon-gap" else "blocked",
        "blocker",
        (
            f"v785={runtime['v785_decision']} first={runtime['v785_first_divergence']} "
            f"android_sibling={runtime['v785_android_sibling_sysmon_count']} "
            f"native_sibling={runtime['v785_native_sibling_sysmon_count']}"
        ),
        "rerun V785 if the Android/native gap evidence changed",
    )
    add_check(
        checks,
        "historical-clean-dsp-branch",
        "pass" if derived["historical_clean_dsp_branch_proven"] else "blocked",
        "blocker",
        (
            f"v641={analysis['reports']['v641']['has_v641_clean_decision']} "
            f"v642={analysis['reports']['v642']['has_v642_lower_decision']} "
            f"v644_service74={analysis['reports']['v644']['has_v644_service74_advance']}"
        ),
        "do not select clean-DSP rearm without historical proof",
    )
    add_check(
        checks,
        "unsafe-branches-closed",
        "pass" if derived["unsafe_retry_branches_closed"] else "review",
        "warn",
        f"v768_rejections={derived['unsafe_retry_branches_closed']}",
        "keep mdm_helper/esoc/subsystem writes rejected unless new evidence changes the contract",
    )
    add_check(
        checks,
        "service74-warning-risk",
        "pass" if derived["historical_service74_warning_risk"] else "review",
        "warn",
        f"warning_risk={derived['historical_service74_warning_risk']}",
        "separate arm-only clean-DSP proof from later CNSS/service74 readback",
    )
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device action", "run V786 host-only classifier")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v786-clean-dsp-v724-gap-plan-ready",
            True,
            "plan-only host classifier; no device command, reboot, flash, or Wi-Fi action",
            "run V786 against current v724 source and existing V641/V782/V785 evidence",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v786-clean-dsp-v724-gap-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "restore required source/evidence or rerun the prerequisite classifier",
        )
    return (
        "v786-v724-clean-dsp-hook-available-but-unarmed",
        True,
        (
            "Current v724 already contains and calls the V641 firmware-backed sibling SSCTL one-shot hook, "
            "but the V782 lower-window boot_wlan path shows no V641 runtime markers, no sibling sysmon, and "
            "no service-notifier; V785's sibling-sysmon gap therefore routes to an explicit v724 arm-only "
            "clean-DSP proof before any further boot_wlan/CNSS/HAL work."
        ),
        (
            "V787 should arm only /cache/native-init-sibling-fwssctl-v641 on stock v724, reboot, collect "
            "V641 proof/timeline/dmesg/rpmsg evidence, and stop; do not arm the v724 QRTR flag, do not start "
            "Wi-Fi HAL, scan/connect, DHCP, external ping, or custom-kernel flash."
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    sources = analysis["sources"]
    runtime = analysis["runtime"]
    derived = analysis["derived"]
    report_rows = [
        [name, data["file"].get("exists"), data["decision_lines"], data["has_v644_warning"]]
        for name, data in analysis["reports"].items()
    ]
    return "\n".join([
        "# V786 Clean-DSP/v724 Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_trigger_executed: `{manifest['wifi_trigger_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Source Surface",
        "",
        markdown_table(["signal", "value"], [
            ["v724_contains_v641_flag", sources["v724_contains_v641_flag"]],
            ["v724_contains_v641_runner", sources["v724_contains_v641_runner"]],
            ["v724_contains_firmware_mounts", sources["v724_contains_firmware_mounts"]],
            ["v724_contains_sibling_nodes", sources["v724_contains_sibling_nodes"]],
            ["v724_calls_qrtr_hook", sources["v724_calls_qrtr_hook"]],
            ["v724_calls_v641_hook", sources["v724_calls_v641_hook"]],
            ["v724_qrtr_call_line", sources["v724_qrtr_call_line"]],
            ["v724_v641_call_line", sources["v724_v641_call_line"]],
            ["v724_calls_qrtr_before_v641", sources["v724_calls_qrtr_before_v641"]],
            ["v724_builder_verifies_v641_markers", sources["v724_builder_verifies_v641_markers"]],
            ["v724_boot_contains_v641_markers", sources["v724_boot_contains_v641_markers"]],
            ["v724_boot_markers", sources["v724_boot_markers"]],
        ]),
        "",
        "## Runtime Surface",
        "",
        markdown_table(["signal", "value"], [
            ["v775_decision", runtime["v775_decision"]],
            ["v782_decision", runtime["v782_decision"]],
            ["v782_boot_wlan_executed", runtime["v782_boot_wlan_executed"]],
            ["v782_companion_executed", runtime["v782_companion_executed"]],
            ["v782_v641_runtime_marker_count", runtime["v782_v641_runtime_marker_count"]],
            ["v782_sibling_sysmon_count", runtime["v782_sibling_sysmon_count"]],
            ["v782_service_notifier_count", runtime["v782_service_notifier_count"]],
            ["v785_decision", runtime["v785_decision"]],
            ["v785_first_divergence", runtime["v785_first_divergence"]],
        ]),
        "",
        "## Historical Branch",
        "",
        markdown_table(["report", "exists", "decision_lines", "warning_marker"], report_rows),
        "",
        "## Derived Classification",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in derived.items()]),
        "",
        "## Interpretation",
        "",
        "- V775 already closed the custom OSRC kernel flash route for now; stock-v724 observability remains the active path.",
        "- V785 moved the blocker away from memshare/CMA and toward missing sibling sysmon plus `mdm3=OFFLINING`.",
        "- Current v724 source already carries the V641 clean-DSP one-shot implementation; the V782 evidence did not execute that hook.",
        "- The next live gate should be narrow: arm only the V641 flag on current v724, reboot, and collect proof/readback without QRTR flag, CNSS/HAL, scan/connect, or external networking.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v786",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_trigger_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "reboot_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
