#!/usr/bin/env python3
"""V1845 host-only classifier for V1844 post-ack modem-open/no-powerup evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1845"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1845-post-ack-modem-open-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1845_POST_ACK_MODEM_OPEN_CLASSIFIER_2026-06-03.md"
)
V1844_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1844-pm-service-post-ack-branch-handoff"
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


def sample_by_key(samples: object) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    if not isinstance(samples, list):
        return result
    for sample in samples:
        if isinstance(sample, dict) and sample.get("key"):
            result[str(sample["key"])] = {str(k): str(v) for k, v in sample.items()}
    return result


def extract_path(line: str) -> str:
    match = re.search(r'path="([^"]+)"', line)
    return match.group(1) if match else ""


def extract_open_rc(line: str) -> str:
    match = re.search(r"open_rc=(0x[0-9a-fA-F]+|-?[0-9]+)", line)
    return match.group(1) if match else ""


def collect_details(v1844: dict[str, Any]) -> dict[str, Any]:
    gate = v1844.get("gate") or {}
    post = v1844.get("post_rollback_verification") or {}
    samples = sample_by_key(gate.get("post_ack_samples"))
    open_call = samples.get("pm_service_post_ack_power_on_open_call", {})
    open_ret = samples.get("pm_service_post_ack_power_on_open_ret", {})
    open_call_line = open_call.get("sample_line_0") or open_call.get("first_hit_line", "")
    open_ret_line = open_ret.get("sample_line_0") or open_ret.get("first_hit_line", "")
    pm_names = str(gate.get("pm_service_first_add_names", "")).split(",")
    pm_devnodes = str(gate.get("pm_service_first_add_devnodes", "")).split(",")
    supported_map = {
        name: devnode
        for name, devnode in zip(pm_names, pm_devnodes, strict=False)
        if name and devnode
    }

    return {
        "source": {
            "path": rel(V1844_MANIFEST),
            "decision": v1844.get("decision", ""),
            "pass": bool(v1844.get("pass")),
            "reason": v1844.get("reason", ""),
        },
        "v1844": {
            "rollback_ok": bool((v1844.get("rollback") or {}).get("ok")),
            "post_version_ok": bool(post.get("version_ok")),
            "post_selftest_fail_zero": bool(post.get("selftest_fail_zero")),
            "post_ack_label": gate.get("post_ack_label", ""),
            "post_ack_hit_count_total": intish(gate.get("post_ack_hit_count_total")),
            "post_ack_hit_keys": gate.get("post_ack_hit_keys") or [],
            "callback_ack_label": gate.get("callback_ack_label", ""),
            "callback_ack_hit_count_total": intish(gate.get("callback_ack_hit_count_total")),
            "open_call_hits": intish(open_call.get("hit_count")),
            "open_ret_hits": intish(open_ret.get("hit_count")),
            "open_path": extract_path(open_call_line),
            "open_rc": extract_open_rc(open_ret_line),
            "open_call_line": open_call_line,
            "open_ret_line": open_ret_line,
            "supported_map": supported_map,
            "pm_service_first_count": gate.get("pm_service_first_count", ""),
            "pm_service_list_commit_hits": gate.get("pm_service_add_peripheral_list_commit_hits", ""),
            "pm_service_init_fail_hits": gate.get("pm_service_add_peripheral_init_fail_hits", ""),
            "lower_continuation_label": gate.get("lower_continuation_label", ""),
            "pm_focus_change_fields": gate.get("pm_focus_change_fields") or [],
            "pm_focus_mdm_status_delta": intish(gate.get("pm_focus_mdm_status_delta")),
            "pm_focus_mhi_wlan0_progress": bool(gate.get("pm_focus_mhi_wlan0_progress")),
            "powerup_thread_counts": [
                intish(sample.get("powerup_powerup_thread_count"))
                for sample in (gate.get("pm_focus_samples") or [])
                if isinstance(sample, dict)
            ],
            "subsys_esoc0_open_inferred": [
                intish(sample.get("powerup_subsys_esoc0_open_inferred"))
                for sample in (gate.get("pm_focus_samples") or [])
                if isinstance(sample, dict)
            ],
            "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
            "lower_mhi_present": boolish(gate.get("lower_mhi_present")),
            "lower_service69_progress": boolish(gate.get("lower_service69_progress")),
            "lower_wlan0_present": boolish(gate.get("lower_wlan0_present")),
            "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
            "servnotif_label": gate.get("servnotif_label", ""),
            "qipcrtr_bound_recv_label": gate.get("qipcrtr_bound_recv_label", ""),
            "safety_ok": bool(gate.get("safety_ok")),
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    v1844 = details["v1844"]
    source = details["source"]
    rollback_clean = (
        source["pass"]
        and v1844["rollback_ok"]
        and v1844["post_version_ok"]
        and v1844["post_selftest_fail_zero"]
    )
    supported_records_ok = (
        v1844["supported_map"].get("SDX50M") == "/dev/subsys_esoc0"
        and v1844["supported_map"].get("modem") == "/dev/subsys_modem"
        and v1844["pm_service_first_count"] == "2"
        and intish(v1844["pm_service_list_commit_hits"]) >= 2
        and intish(v1844["pm_service_init_fail_hits"]) == 0
    )
    modem_open = (
        v1844["post_ack_label"] == "post-ack-open-branch-reached"
        and v1844["open_call_hits"] > 0
        and v1844["open_ret_hits"] > 0
        and v1844["open_path"] == "/dev/subsys_modem"
        and intish(v1844["open_rc"]) >= 0
    )
    lower_static = (
        v1844["lower_continuation_label"] == "lower-continuation-static-gap"
        and v1844["post_pm_lower_state_label"] == "stable-mdm3-offlining"
        and not v1844["pm_focus_change_fields"]
        and v1844["pm_focus_mdm_status_delta"] == 0
        and not v1844["pm_focus_mhi_wlan0_progress"]
        and all(value == 0 for value in v1844["powerup_thread_counts"])
        and all(value == 0 for value in v1844["subsys_esoc0_open_inferred"])
        and v1844["lower_mdm3_states"] == "OFFLINING"
        and not v1844["lower_mhi_present"]
        and not v1844["lower_service69_progress"]
        and not v1844["lower_wlan0_present"]
        and v1844["servnotif_label"] == "service-notifier-uninit"
        and v1844["qipcrtr_bound_recv_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
    )

    if not rollback_clean:
        return "rollback-review", "v1845-rollback-review", "V1844 handoff or post-rollback health is not clean", False
    if not v1844["safety_ok"]:
        return "safety-review", "v1845-safety-review", "V1844 safety flag is not clean", False
    if not supported_records_ok:
        return "pm-record-review", "v1845-pm-record-review", "PM-service supported peripheral records do not match the expected SDX50M/modem map", False
    if modem_open and lower_static:
        return (
            "post-ack-modem-open-no-ext-powerup",
            "v1845-post-ack-modem-open-no-ext-powerup-host-pass",
            "V1844 proves the current post-ack PM-service branch opens /dev/subsys_modem successfully, while the external SDX50M/eSoC lower state remains static",
            True,
        )
    return (
        "post-ack-open-evidence-review",
        "v1845-post-ack-open-evidence-review",
        "V1844 evidence does not match the fixed modem-open/static-lower classifier",
        False,
    )


def render_report(result: dict[str, Any]) -> str:
    v1844 = result["details"]["v1844"]
    source = result["details"]["source"]
    return "\n".join([
        "# Native Init V1845 Post-Ack Modem-Open Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only classifier over V1844 rollback-verified post-ack evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input",
        "",
        f"- V1844: `{source['decision']}` / pass `{source['pass']}`",
        f"- V1844 rollback/post-version/post-selftest: `{v1844['rollback_ok']}` / `{v1844['post_version_ok']}` / `{v1844['post_selftest_fail_zero']}`",
        "",
        "## V1844 Open Evidence",
        "",
        f"- post-ack label/total: `{v1844['post_ack_label']}` / `{v1844['post_ack_hit_count_total']}`",
        f"- callback/ack label/total: `{v1844['callback_ack_label']}` / `{v1844['callback_ack_hit_count_total']}`",
        f"- open call/return hits: `{v1844['open_call_hits']}` / `{v1844['open_ret_hits']}`",
        f"- open path/rc: `{v1844['open_path']}` / `{v1844['open_rc']}`",
        f"- supported PM map: `{v1844['supported_map']}`",
        f"- open call line: `{v1844['open_call_line']}`",
        f"- open return line: `{v1844['open_ret_line']}`",
        "",
        "## Static Lower State",
        "",
        f"- lower-continuation/lower-state: `{v1844['lower_continuation_label']}` / `{v1844['post_pm_lower_state_label']}`",
        f"- powerup threads / inferred esoc0 opens: `{v1844['powerup_thread_counts']}` / `{v1844['subsys_esoc0_open_inferred']}`",
        f"- PM focus changes/status-delta/MHI-wlan0-progress: `{v1844['pm_focus_change_fields']}` / `{v1844['pm_focus_mdm_status_delta']}` / `{v1844['pm_focus_mhi_wlan0_progress']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{v1844['lower_mdm3_states']}` / `{v1844['lower_mhi_present']}` / `{v1844['lower_service69_progress']}` / `{v1844['lower_wlan0_present']}`",
        f"- service-notifier / QIPCRTR bound labels: `{v1844['servnotif_label']}` / `{v1844['qipcrtr_bound_recv_label']}`",
        "",
        "## Interpretation",
        "",
        "- The current route is no longer blocked before PM-service post-ack action: ack implementation, action branch, timer/state checks, and an open call all fired.",
        "- The open target is `/dev/subsys_modem`, not `/dev/subsys_esoc0`; this can succeed without creating the external SDX50M/eSoC powerup thread or WLFW/MHI/wlan0 progress.",
        "- The next boundary is PM-service peripheral selection/state for the post-ack open path, not callback delivery, PM ack completion, QRTR, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Next unit should be source/build-only first: decode PM-service post-ack open context around `0x8cc8`/`0x8cd4` to capture peripheral name/devnode/state/fd fields.",
        "- Do not force `/dev/subsys_esoc0` or proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "",
    ])


def main() -> int:
    v1844 = load_json(V1844_MANIFEST)
    details = collect_details(v1844)
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
