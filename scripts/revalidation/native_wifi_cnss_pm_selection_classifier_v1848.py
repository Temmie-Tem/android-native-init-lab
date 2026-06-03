#!/usr/bin/env python3
"""V1848 host-only classifier for CNSS PM peripheral selection evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1848"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1848-cnss-pm-selection-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1848_CNSS_PM_SELECTION_CLASSIFIER_2026-06-03.md"
)
V1847_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1847-pm-service-open-context-handoff"
    / "manifest.json"
)
V1211_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1211-cnss-daemon-peripheral-name"
    / "manifest.json"
)
V1219_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1219-cnss-mdmdetect-selection-trace"
    / "manifest.json"
)
V1220_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1220-cnss-daemon-sdx50m-patch"
    / "manifest.json"
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value) in {"1", "True", "true", "yes"}


def sample_lines(mapping: dict[str, Any], prefix: str, limit: int = 4) -> list[str]:
    lines: list[str] = []
    for index in range(limit):
        line = str(mapping.get(f"{prefix}_sample_line_{index}", ""))
        if line and line != "none":
            lines.append(line)
    first = str(mapping.get(f"{prefix}_first_hit_line", ""))
    if first and first != "none" and first not in lines:
        lines.insert(0, first)
    return lines


def parse_compare_pairs(lines: list[str]) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    for line in lines:
        match = re.search(r'candidate="([^"]+)" requested="([^"]+)"', line)
        if match:
            pairs.append({"candidate": match.group(1), "requested": match.group(2), "line": line})
    return pairs


def first_sample_by_key(samples: object, key: str) -> dict[str, str]:
    if not isinstance(samples, list):
        return {}
    for sample in samples:
        if isinstance(sample, dict) and sample.get("key") == key:
            return {str(k): str(v) for k, v in sample.items()}
    return {}


def pm_map(gate: dict[str, Any]) -> dict[str, str]:
    names = str(gate.get("pm_service_first_add_names", "")).split(",")
    devnodes = str(gate.get("pm_service_first_add_devnodes", "")).split(",")
    return {
        name: devnode
        for name, devnode in zip(names, devnodes, strict=False)
        if name and devnode
    }


def selects_modem_record(pairs: list[dict[str, str]]) -> bool:
    return (
        len(pairs) >= 2
        and pairs[0].get("candidate") == "SDX50M"
        and pairs[0].get("requested") == "modem"
        and pairs[1].get("candidate") == "modem"
        and pairs[1].get("requested") == "modem"
    )


def collect_v1847(v1847: dict[str, Any]) -> dict[str, Any]:
    gate = v1847.get("gate") or {}
    post = v1847.get("post_rollback_verification") or {}
    compare_lines = sample_lines(gate, "pm_server_register_strcmp_call")
    compare_pairs = parse_compare_pairs(compare_lines)
    register_call = gate.get("pm_init_pm_client_register_call") or {}
    register_retcheck = gate.get("pm_init_pm_client_register_retcheck") or {}
    open_context = first_sample_by_key(gate.get("open_context_samples"), "pm_service_post_ack_open_context")
    path_sample = first_sample_by_key(gate.get("open_context_samples"), "pm_service_post_ack_open_path_loaded")
    fd_sample = first_sample_by_key(gate.get("open_context_samples"), "pm_service_post_ack_open_fd_store")
    state_sample = first_sample_by_key(gate.get("open_context_samples"), "pm_service_post_ack_power_state_loaded")
    pm_focus_samples = [
        sample
        for sample in (gate.get("pm_focus_samples") or [])
        if isinstance(sample, dict)
    ]
    return {
        "path": rel(V1847_MANIFEST),
        "decision": v1847.get("decision", ""),
        "pass": bool(v1847.get("pass")),
        "reason": v1847.get("reason", ""),
        "rollback_ok": bool((v1847.get("rollback") or {}).get("ok")),
        "post_version_ok": bool(post.get("version_ok")),
        "post_selftest_fail_zero": bool(post.get("selftest_fail_zero")),
        "pm_client_register_rc": intish(gate.get("pm_client_register_rc")),
        "pm_init_register_call_hits": intish(register_call.get("hit_count")),
        "pm_init_register_retcheck_hits": intish(register_retcheck.get("hit_count")),
        "pm_init_register_retcheck_line": str(register_retcheck.get("first_hit_line", "")),
        "pm_map": pm_map(gate),
        "pm_service_first_count": str(gate.get("pm_service_first_count", "")),
        "pm_service_list_commit_hits": intish(gate.get("pm_service_add_peripheral_list_commit_hits")),
        "pm_service_init_fail_hits": intish(gate.get("pm_service_add_peripheral_init_fail_hits")),
        "pm_service_entry_lines": sample_lines(gate, "pm_service_add_peripheral_entry"),
        "pm_server_register_entry_hits": intish(gate.get("pm_server_register_entry_hits")),
        "pm_server_register_strcmp_hits": intish(gate.get("pm_server_register_strcmp_call_hits")),
        "pm_server_register_strcmp_lines": compare_lines,
        "pm_server_register_strcmp_pairs": compare_pairs,
        "pm_server_no_peripheral_hits": intish(gate.get("pm_server_no_peripheral_hits")),
        "requested_values": sorted({pair["requested"] for pair in compare_pairs}),
        "candidate_values": [pair["candidate"] for pair in compare_pairs],
        "open_context_label": gate.get("open_context_label", ""),
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "open_context_power_state": gate.get("open_context_power_state", ""),
        "open_context_hit_count_total": intish(gate.get("open_context_hit_count_total")),
        "open_context_line": open_context.get("sample_line_0", ""),
        "open_context_path_line": path_sample.get("sample_line_0", ""),
        "open_context_fd_line": fd_sample.get("sample_line_0", ""),
        "open_context_state_line": state_sample.get("sample_line_0", ""),
        "post_ack_label": gate.get("post_ack_label", ""),
        "callback_ack_label": gate.get("callback_ack_label", ""),
        "lower_continuation_label": gate.get("lower_continuation_label", ""),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "pm_focus_change_fields": gate.get("pm_focus_change_fields") or [],
        "pm_focus_mdm_status_delta": intish(gate.get("pm_focus_mdm_status_delta")),
        "pm_focus_mhi_wlan0_progress": bool(gate.get("pm_focus_mhi_wlan0_progress")),
        "powerup_thread_counts": [
            intish(sample.get("powerup_powerup_thread_count"))
            for sample in pm_focus_samples
        ],
        "subsys_esoc0_open_inferred": [
            intish(sample.get("powerup_subsys_esoc0_open_inferred"))
            for sample in pm_focus_samples
        ],
        "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "lower_mhi_present": boolish(gate.get("lower_mhi_present")),
        "lower_service69_progress": boolish(gate.get("lower_service69_progress")),
        "lower_wlan0_present": boolish(gate.get("lower_wlan0_present")),
        "servnotif_label": gate.get("servnotif_label", ""),
        "qipcrtr_bound_recv_label": gate.get("qipcrtr_bound_recv_label", ""),
        "safety_ok": bool(gate.get("safety_ok")),
    }


def collect_history(v1211: dict[str, Any], v1219: dict[str, Any], v1220: dict[str, Any]) -> dict[str, Any]:
    v1211_analysis = v1211.get("analysis") or {}
    v1219_by_comm = (((v1219.get("analysis") or {}).get("tracefs_uprobe") or {}).get("by_comm") or {})
    return {
        "v1211": {
            "path": rel(V1211_MANIFEST),
            "decision": v1211.get("decision", ""),
            "pass": bool(v1211.get("pass")),
            "cnss_daemon_binary_path": v1211_analysis.get("cnss_daemon_binary_path", ""),
            "cnss_daemon_peripheral_refs": v1211_analysis.get("cnss_daemon_peripheral_refs") or [],
            "libmdmdetect_key_strings": v1211_analysis.get("libmdmdetect_key_strings") or [],
            "esoc_sysfs_esoc_name": v1211_analysis.get("esoc_sysfs_esoc_name", ""),
            "dev_esoc_0_absent": bool(v1211_analysis.get("dev_esoc_0_absent")),
            "esoc_dev_esoc0_path": v1211_analysis.get("esoc_dev_esoc0_path", ""),
        },
        "v1219": {
            "path": rel(V1219_MANIFEST),
            "decision": v1219.get("decision", ""),
            "pass": bool(v1219.get("pass")),
            "reason": v1219.get("reason", ""),
            "cnss_daemon_counts": v1219_by_comm.get("cnss-daemon") or {},
        },
        "v1220": {
            "path": rel(V1220_MANIFEST),
            "decision": v1220.get("decision", ""),
            "pass": bool(v1220.get("pass")),
            "host_only": bool(v1220.get("host_only")),
            "cnss_daemon_executed": bool(v1220.get("cnss_daemon_executed")),
            "patch_literal_c_string": v1220.get("patch_literal_c_string", ""),
            "original_literal": str(v1220.get("original_literal", "")).replace("\x00", "\\0"),
            "patch_offset_hex": v1220.get("patch_offset_hex", ""),
            "output": v1220.get("output", ""),
            "output_sha256": v1220.get("output_sha256", ""),
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    current = details["v1847"]
    history = details["history"]
    rollback_clean = (
        current["pass"]
        and current["rollback_ok"]
        and current["post_version_ok"]
        and current["post_selftest_fail_zero"]
    )
    pm_records_ok = (
        current["pm_map"].get("SDX50M") == "/dev/subsys_esoc0"
        and current["pm_map"].get("modem") == "/dev/subsys_modem"
        and current["pm_service_first_count"] == "2"
        and current["pm_service_list_commit_hits"] >= 2
        and current["pm_service_init_fail_hits"] == 0
    )
    register_selects_modem = (
        current["pm_client_register_rc"] == 0
        and current["pm_init_register_call_hits"] >= 1
        and current["pm_init_register_retcheck_hits"] >= 1
        and current["pm_server_register_entry_hits"] >= 1
        and current["pm_server_register_strcmp_hits"] >= 2
        and selects_modem_record(current["pm_server_register_strcmp_pairs"])
    )
    open_context_modem = (
        current["open_context_label"] == "open-context-modem-success-static"
        and current["open_context_path"] == "/dev/subsys_modem"
        and intish(current["open_context_fd"]) >= 0
        and current["post_ack_label"] == "post-ack-open-branch-reached"
        and current["callback_ack_label"] == "callback-ack-present-no-powerup"
    )
    lower_static = (
        current["lower_continuation_label"] == "lower-continuation-static-gap"
        and current["post_pm_lower_state_label"] == "stable-mdm3-offlining"
        and not current["pm_focus_change_fields"]
        and current["pm_focus_mdm_status_delta"] == 0
        and not current["pm_focus_mhi_wlan0_progress"]
        and all(value == 0 for value in current["powerup_thread_counts"])
        and all(value == 0 for value in current["subsys_esoc0_open_inferred"])
        and current["lower_mdm3_states"] == "OFFLINING"
        and not current["lower_mhi_present"]
        and not current["lower_service69_progress"]
        and not current["lower_wlan0_present"]
        and current["servnotif_label"] == "service-notifier-uninit"
        and current["qipcrtr_bound_recv_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
    )
    history_consistent = (
        history["v1211"]["esoc_sysfs_esoc_name"] == "SDX50M"
        and "SDX50M" in history["v1211"]["libmdmdetect_key_strings"]
        and history["v1219"]["decision"] == "v1219-mdmdetect-entry-not-sdxprairie"
        and intish(history["v1219"]["cnss_daemon_counts"].get("cnss_nullname_register_call")) >= 1
        and intish(history["v1219"]["cnss_daemon_counts"].get("cnss_type_compare")) >= 1
        and history["v1220"]["decision"] == "v1220-private-cnss-daemon-sdx50m-patch-ready"
        and history["v1220"]["host_only"]
        and not history["v1220"]["cnss_daemon_executed"]
    )

    if not rollback_clean:
        return "rollback-review", "v1848-rollback-review", "V1847 handoff or post-rollback health is not clean", False
    if not current["safety_ok"]:
        return "safety-review", "v1848-safety-review", "V1847 safety flag is not clean", False
    if not pm_records_ok:
        return "pm-record-review", "v1848-pm-record-review", "PM-service SDX50M/modem records are not both present", False
    if not register_selects_modem:
        return "register-selection-review", "v1848-register-selection-review", "Current pm_client_register selection did not match the fixed modem-selection classifier", False
    if not open_context_modem:
        return "open-context-review", "v1848-open-context-review", "Current post-ack open context is not the fixed /dev/subsys_modem success case", False
    if not lower_static:
        return "lower-progress-review", "v1848-lower-progress-review", "Lower SDX50M/eSoC publication progressed or evidence is inconsistent", False
    if not history_consistent:
        return "historical-selection-review", "v1848-historical-selection-review", "Historical CNSS/mdmdetect selection evidence is missing or inconsistent", False
    return (
        "cnss-pm-register-selects-modem-record",
        "v1848-cnss-pm-register-selects-modem-not-sdx50m-host-pass",
        "Current CNSS pm_client_register requests modem, PM-service selects the modem record, and the SDX50M/eSoC lower state remains static despite a successful /dev/subsys_modem open",
        True,
    )


def render_compare_pairs(pairs: list[dict[str, str]]) -> list[str]:
    return [
        f"- compare `{index}`: candidate `{pair['candidate']}` requested `{pair['requested']}` line=`{pair['line']}`"
        for index, pair in enumerate(pairs)
    ]


def render_report(result: dict[str, Any]) -> str:
    current = result["details"]["v1847"]
    history = result["details"]["history"]
    lines = [
        "# Native Init V1848 CNSS PM Selection Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only classifier over V1847 current-route evidence plus bounded historical CNSS/mdmdetect context",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Current Evidence",
        "",
        f"- V1847: `{current['decision']}` / pass `{current['pass']}`",
        f"- rollback/post-version/post-selftest: `{current['rollback_ok']}` / `{current['post_version_ok']}` / `{current['post_selftest_fail_zero']}`",
        f"- PM map: `{current['pm_map']}`",
        f"- register rc/call/retcheck: `{current['pm_client_register_rc']}` / `{current['pm_init_register_call_hits']}` / `{current['pm_init_register_retcheck_hits']}`",
        f"- PM-server register/strcmp hits: `{current['pm_server_register_entry_hits']}` / `{current['pm_server_register_strcmp_hits']}`",
        f"- requested values: `{current['requested_values']}`",
        *render_compare_pairs(current["pm_server_register_strcmp_pairs"]),
        "",
        "## Post-Ack Open Context",
        "",
        f"- open-context label: `{current['open_context_label']}`",
        f"- open path/state/fd: `{current['open_context_path']}` / `{current['open_context_power_state']}` / `{current['open_context_fd']}`",
        f"- post-ack/callback labels: `{current['post_ack_label']}` / `{current['callback_ack_label']}`",
        f"- context line: `{current['open_context_line']}`",
        f"- path line: `{current['open_context_path_line']}`",
        f"- fd line: `{current['open_context_fd_line']}`",
        "",
        "## Static Lower State",
        "",
        f"- lower-continuation/lower-state: `{current['lower_continuation_label']}` / `{current['post_pm_lower_state_label']}`",
        f"- powerup threads / inferred esoc0 opens: `{current['powerup_thread_counts']}` / `{current['subsys_esoc0_open_inferred']}`",
        f"- PM focus changes/status-delta/MHI-wlan0-progress: `{current['pm_focus_change_fields']}` / `{current['pm_focus_mdm_status_delta']}` / `{current['pm_focus_mhi_wlan0_progress']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{current['lower_mdm3_states']}` / `{current['lower_mhi_present']}` / `{current['lower_service69_progress']}` / `{current['lower_wlan0_present']}`",
        f"- service-notifier / QIPCRTR bound labels: `{current['servnotif_label']}` / `{current['qipcrtr_bound_recv_label']}`",
        "",
        "## Historical Context",
        "",
        f"- V1211: `{history['v1211']['decision']}`; libmdmdetect knows `{history['v1211']['esoc_sysfs_esoc_name']}` and reported dev-node absence `{history['v1211']['dev_esoc_0_absent']}`",
        f"- V1219: `{history['v1219']['decision']}`; CNSS counts `{history['v1219']['cnss_daemon_counts']}`",
        f"- V1220: `{history['v1220']['decision']}`; host-only `{history['v1220']['host_only']}` executed `{history['v1220']['cnss_daemon_executed']}` patch `{history['v1220']['patch_literal_c_string']}` at `{history['v1220']['patch_offset_hex']}`",
        "",
        "## Interpretation",
        "",
        "- PM-service already has both records: `SDX50M -> /dev/subsys_esoc0` and `modem -> /dev/subsys_modem`.",
        "- The current CNSS registration request is `modem`; PM-service compares `SDX50M` against `modem`, then selects the `modem` record.",
        "- The successful post-ack open is therefore expected to target `/dev/subsys_modem`; it does not create SDX50M/eSoC powerup, WLFW service 69, MHI, or `wlan0` progress.",
        "- The next safe target is CNSS/mdmdetect selection source or a private patched-daemon gate that changes the registration request before PM-service selection.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next unit should be source/build-only first: decode or trace the CNSS/mdmdetect branch that supplies `modem` to `pm_client_register`, then re-evaluate the existing private SDX50M daemon patch as a separate gated step.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    details = {
        "v1847": collect_v1847(load_json(V1847_MANIFEST)),
        "history": collect_history(
            load_json(V1211_MANIFEST),
            load_json(V1219_MANIFEST),
            load_json(V1220_MANIFEST),
        ),
    }
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
