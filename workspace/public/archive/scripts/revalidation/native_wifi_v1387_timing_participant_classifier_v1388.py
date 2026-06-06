#!/usr/bin/env python3
"""V1388 host-only classifier for the V1387 pre-poll corrected RC1 timing gap."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1388-v1387-timing-participant-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1388_V1387_TIMING_PARTICIPANT_CLASSIFIER_2026-06-01.md")
V1371_REPORT = Path("docs/reports/NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md")
V1379_MANIFEST = Path("tmp/wifi/v1379-android-participant-corrected-rc1-live/manifest.json")
V1383_MANIFEST = Path("tmp/wifi/v1383-android-participant-immediate-corrected-rc1-live/manifest.json")
V1384_MANIFEST = Path("tmp/wifi/v1384-v1383-timing-gap-classifier/manifest.json")
V1385_REPORT = Path("docs/reports/NATIVE_INIT_V1385_PREPOLL_CORRECTED_RC1_SUPPORT_2026-06-01.md")
V1386_REPORT = Path("docs/reports/NATIVE_INIT_V1386_EXECNS_HELPER_V285_DEPLOY_2026-06-01.md")
V1387_MANIFEST = Path("tmp/wifi/v1387-android-participant-prepoll-corrected-rc1-live/manifest.json")
V1387_OBSERVER = Path("tmp/wifi/v1387-android-participant-prepoll-corrected-rc1-live/host/pm-server-wchan-tracefs-observer.txt")

ANDROID_DELTA_RE = re.compile(r"\| android_esoc0_to_assert_sec \| ([0-9.]+) \|")
ANDROID_RELEASE_L0_RE = re.compile(r"\| android_release_to_l0_sec \| ([0-9.]+) \|")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def as_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def first_line_index(lines: list[str], *needles: str) -> int | None:
    for index, line in enumerate(lines, start=1):
        if all(needle in line for needle in needles):
            return index
    return None


def first_line(lines: list[str], *needles: str) -> str:
    for line in lines:
        if all(needle in line for needle in needles):
            return line
    return ""


def parse_android_reference() -> dict[str, float]:
    text = read(V1371_REPORT)
    delta_match = ANDROID_DELTA_RE.search(text)
    release_match = ANDROID_RELEASE_L0_RE.search(text)
    if not delta_match or not release_match:
        raise RuntimeError("missing Android timing reference in V1371 report")
    return {
        "android_esoc0_to_assert_sec": float(delta_match.group(1)),
        "android_release_to_l0_sec": float(release_match.group(1)),
    }


def no_downstream(sampler: dict[str, Any]) -> bool:
    return (
        as_int(sampler.get("timing_gpio142_irq_delta"), 0) == 0
        and as_int(sampler.get("timing_errfatal_irq_delta"), 0) == 0
        and as_int(sampler.get("timing_pci_dev_max"), 0) == 0
        and as_int(sampler.get("timing_mhi_bus_max"), 0) == 0
        and not bool(sampler.get("timing_mhi_pipe_seen"))
        and as_int(sampler.get("timing_ks_process_max"), 0) == 0
        and as_int(sampler.get("timing_wlfw_kmsg_max"), 0) == 0
        and not bool(sampler.get("timing_wlan0_seen"))
    )


def observer_order_summary() -> dict[str, Any]:
    lines = read(V1387_OBSERVER).splitlines()
    first_powerup_line = first_line_index(lines, "wchan=mdm_subsys_powerup")
    first_late_begin_line = first_line_index(lines, "pm_service_trigger_observer.late_per_proxy.begin=1")
    first_response_begin_line = first_line_index(lines, "pm_service_trigger_observer.response_sampler.begin=1")
    first_prepoll_begin_line = first_line_index(lines, "pm_service_trigger_observer.prepoll_corrected_rc1.begin=1")
    first_corrected_begin_line = first_line_index(lines, "pm_service_trigger_observer.corrected_rc1_enumerate.begin=1")
    first_corrected_end_line = first_line_index(lines, "pm_service_trigger_observer.corrected_rc1_enumerate.end=1")
    return {
        "first_powerup_thread_line": first_powerup_line,
        "first_late_per_proxy_begin_line": first_late_begin_line,
        "first_response_sampler_begin_line": first_response_begin_line,
        "first_prepoll_begin_line": first_prepoll_begin_line,
        "first_corrected_begin_line": first_corrected_begin_line,
        "first_corrected_end_line": first_corrected_end_line,
        "powerup_seen_before_late_per_proxy_begin": (
            first_powerup_line is not None
            and first_late_begin_line is not None
            and first_powerup_line < first_late_begin_line
        ),
        "powerup_seen_before_prepoll_begin": (
            first_powerup_line is not None
            and first_prepoll_begin_line is not None
            and first_powerup_line < first_prepoll_begin_line
        ),
        "first_powerup_thread_sample": first_line(lines, "wchan=mdm_subsys_powerup"),
        "late_per_proxy_begin_line_text": first_line(lines, "pm_service_trigger_observer.late_per_proxy.begin=1"),
        "prepoll_begin_line_text": first_line(lines, "pm_service_trigger_observer.prepoll_corrected_rc1.begin=1"),
        "corrected_begin_line_text": first_line(lines, "pm_service_trigger_observer.corrected_rc1_enumerate.begin=1"),
    }


def classify() -> dict[str, Any]:
    android = parse_android_reference()
    v1379 = load_json(V1379_MANIFEST)
    v1383 = load_json(V1383_MANIFEST)
    v1384 = load_json(V1384_MANIFEST)
    v1387 = load_json(V1387_MANIFEST)
    v1385_text = read(V1385_REPORT)
    v1386_text = read(V1386_REPORT)

    corrected = v1387.get("corrected_rc1_enumerate") or {}
    prepoll = v1387.get("prepoll_corrected_rc1") or {}
    sampler = v1387.get("response_sampler") or {}
    dmesg = v1387.get("dmesg_rc1") or {}
    route = v1387.get("current_route") or {}
    order = observer_order_summary()

    android_delta = android["android_esoc0_to_assert_sec"]
    v1379_delta = as_float((v1384.get("timing") or {}).get("v1379_esoc0_to_assert_sec"))
    v1383_delta = as_float((v1384.get("timing") or {}).get("v1383_esoc0_to_assert_sec"))
    v1387_delta = as_float(dmesg.get("esoc0_to_assert_sec"))
    prepoll_start_ms = as_int(prepoll.get("start_monotonic_ms"), -1)
    corrected_ms = as_int(corrected.get("monotonic_ms"), -1)
    esoc0_time = as_float(dmesg.get("esoc0_time"))

    timing = {
        "android_esoc0_to_assert_sec": android_delta,
        "android_release_to_l0_sec": android["android_release_to_l0_sec"],
        "v1379_esoc0_to_assert_sec": v1379_delta,
        "v1383_esoc0_to_assert_sec": v1383_delta,
        "v1387_esoc0_to_assert_sec": v1387_delta,
        "v1387_vs_android_ratio": None if v1387_delta is None else v1387_delta / android_delta,
        "v1387_improvement_vs_v1383_sec": None if v1383_delta is None or v1387_delta is None else v1383_delta - v1387_delta,
        "v1387_improvement_vs_v1379_sec": None if v1379_delta is None or v1387_delta is None else v1379_delta - v1387_delta,
        "v1387_prepoll_start_after_esoc0_sec": None if esoc0_time is None or prepoll_start_ms < 0 else (prepoll_start_ms / 1000.0) - esoc0_time,
        "v1387_corrected_write_after_prepoll_start_sec": None if corrected_ms < 0 or prepoll_start_ms < 0 else (corrected_ms - prepoll_start_ms) / 1000.0,
        "v1387_release_to_link_failed_sec": as_float(dmesg.get("release_to_link_failed_sec")),
    }

    checks = {
        "v1385_helper_support_passed": "v1385-helper-v285-prepoll-corrected-rc1-ready" in v1385_text,
        "v1386_deploy_passed": "execns-helper-v285-deploy-pass" in v1386_text,
        "v1387_live_passed": v1387.get("pass") is True,
        "v1387_precondition_flags_present": (
            route.get("private_flag_in_child_script") == 1
            and route.get("precondition_flag_in_child_script") == 1
            and route.get("corrected_rc1_flag_in_child_script") == 1
        ),
        "v1387_prepoll_triggered": prepoll.get("triggered") is True,
        "v1387_prepoll_poll0": as_int(prepoll.get("poll_count"), -1) == 0,
        "v1387_corrected_from_prepoll_phase": str(corrected.get("phase", "")).startswith("late_per_proxy_prepoll_"),
        "v1387_powerup_gate_positive": as_int(corrected.get("gate_pm_service_powerup_thread_count"), -1) > 0,
        "v1387_write_ok": corrected.get("rc_sel_rc") == 0 and corrected.get("case_rc") == 0,
        "v1387_rc1_transition_seen": dmesg.get("transition_seen") is True,
        "v1387_failed_before_l0": dmesg.get("l0_seen") is False and dmesg.get("link_failed_seen") is True,
        "v1387_no_downstream": no_downstream(sampler),
        "v1387_still_late_vs_android": timing["v1387_vs_android_ratio"] is not None and timing["v1387_vs_android_ratio"] > 4.0,
        "v1387_prepoll_improvement_small": timing["v1387_improvement_vs_v1383_sec"] is not None and timing["v1387_improvement_vs_v1383_sec"] < 0.25,
        "v1387_prepoll_started_after_esoc0_gap": timing["v1387_prepoll_start_after_esoc0_sec"] is not None and timing["v1387_prepoll_start_after_esoc0_sec"] > 3.0,
        "v1387_prepoll_loop_not_primary_delay": timing["v1387_corrected_write_after_prepoll_start_sec"] is not None and timing["v1387_corrected_write_after_prepoll_start_sec"] < 0.25,
        "observer_saw_powerup_before_response_sampler": order["powerup_seen_before_late_per_proxy_begin"] is True,
        "v1384_prior_classifier_passed": v1384.get("decision") == "v1384-immediate-flag-still-too-late-poll-entry-gap",
        "host_only": True,
    }
    passed = all(checks.values())
    decision = "v1388-prepoll-gate-works-but-helper-enters-it-too-late" if passed else "v1388-timing-participant-classifier-incomplete"
    reason = (
        f"V1387 proves the v285 pre-poll writer works, but it starts about "
        f"{timing['v1387_prepoll_start_after_esoc0_sec']:.3f}s after esoc0 and only "
        f"{timing['v1387_improvement_vs_v1383_sec']:.3f}s earlier than V1383. The observer already saw "
        "a pm-service mdm_subsys_powerup thread before the late_per_proxy response-sampler block, so the next fix must move corrected RC1 into that earlier observer phase."
        if passed
        else "one or more V1388 host-only checks failed"
    )
    next_step = (
        "V1389 source/build-only: add helper v286 early-observer corrected RC1 trigger that fires on the first pm_service_powerup_thread observation before response-sampler/proc-map snapshots"
        if passed
        else "repair V1387 evidence parsing before another live mutation"
    )
    return {
        "cycle": "V1388",
        "type": "host-only V1387 timing/participant classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "timing": timing,
        "observer_order": order,
        "interpretation": {
            "prepoll_code_path_works": checks["v1387_prepoll_triggered"] and checks["v1387_write_ok"],
            "prepoll_loop_is_not_primary_delay": checks["v1387_prepoll_loop_not_primary_delay"],
            "late_per_proxy_response_sampler_entry_is_too_late": checks["v1387_prepoll_started_after_esoc0_gap"],
            "earlier_powerup_thread_signal_exists": checks["observer_saw_powerup_before_response_sampler"],
            "another_same_shape_live_retry_is_low_value": passed,
            "next_change_should_be_source_build_only": passed,
        },
        "source_evidence": {
            "v1371_report": str(V1371_REPORT),
            "v1379_manifest": str(V1379_MANIFEST),
            "v1383_manifest": str(V1383_MANIFEST),
            "v1384_manifest": str(V1384_MANIFEST),
            "v1385_report": str(V1385_REPORT),
            "v1386_report": str(V1386_REPORT),
            "v1387_manifest": str(V1387_MANIFEST),
            "v1387_observer": str(V1387_OBSERVER),
        },
        "hard_exclusions": [
            "host-only; no device command",
            "no debugfs/sysfs write, rc_sel/case write, or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[key, fmt(value)] for key, value in mapping.items()])


def bool_table(mapping: dict[str, bool]) -> str:
    return markdown_table(["check", "pass"], [[key, str(value).lower()] for key, value in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    observer_lines = {
        key: value
        for key, value in manifest["observer_order"].items()
        if key.endswith("_sample") or key.endswith("_text")
    }
    return "\n".join([
        "# Native Init V1388 V1387 Timing/Participant Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1388`",
        "- Type: host-only V1387 timing/participant classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_v1387_timing_participant_classifier_v1388.py`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        bool_table(manifest["checks"]),
        "",
        "## Timing",
        "",
        table(manifest["timing"]),
        "",
        "## Observer Ordering",
        "",
        table({
            key: value
            for key, value in manifest["observer_order"].items()
            if not key.endswith("_sample") and not key.endswith("_text")
        }),
        "",
        "## Interpretation",
        "",
        table({key: str(value).lower() for key, value in manifest["interpretation"].items()}),
        "",
        "## Key Observer Lines",
        "",
        *[f"- `{key}`: {value}" for key, value in observer_lines.items() if value],
        "",
        "## Hard Exclusions",
        "",
        *[f"- {item}" for item in manifest["hard_exclusions"]],
        "",
    ])


def main() -> int:
    out = repo_path(OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    manifest = classify()
    write_private_text(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rendered = render(manifest)
    write_private_text(out / "summary.md", rendered)
    write_private_text(repo_path(REPORT_PATH), rendered)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
