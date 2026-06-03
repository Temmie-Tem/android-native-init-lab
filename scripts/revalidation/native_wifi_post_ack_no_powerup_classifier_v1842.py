#!/usr/bin/env python3
"""V1842 host-only classifier for the current-route post-ack/no-powerup gap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1842"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1842-post-ack-no-powerup-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1842_POST_ACK_NO_POWERUP_CLASSIFIER_2026-06-03.md"
)

V1841_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1841-pm-callback-ack-current-route-handoff"
    / "manifest.json"
)
V1839_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1839-lower-continuation-gap-classifier"
    / "manifest.json"
)
V1173_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1173_PM_ACK_PATH_LIVE_2026-05-27.md"

EXPECTED_CALLBACK_ACK_KEYS = [
    "periph_pm_callback_stub_entry",
    "periph_pm_callback_write_state",
    "periph_pm_callback_remote_binder",
    "periph_pm_callback_transact_call",
    "periph_pm_callback_transact_return",
    "periph_pm_client_ack_entry",
    "periph_pm_client_ack_match",
    "periph_pm_client_ack_virtual_call",
    "periph_pm_server_ontransact_entry",
    "periph_pm_server_ack_read_state",
    "periph_pm_server_ack_impl_call",
    "periph_pm_server_ack_write_ret",
]


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return path.read_text(encoding="utf-8")


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value) in {"1", "True", "true", "yes"}


def sample_map(samples: object) -> dict[str, dict[str, Any]]:
    if not isinstance(samples, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for sample in samples:
        if isinstance(sample, dict) and sample.get("key"):
            result[str(sample["key"])] = sample
    return result


def source_summary(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "label": manifest.get("label", ""),
        "reason": manifest.get("reason", ""),
    }


def collect_details(v1841: dict[str, Any], v1839: dict[str, Any], v1173_text: str) -> dict[str, Any]:
    gate = v1841.get("gate") or {}
    post = v1841.get("post_rollback_verification") or {}
    samples = sample_map(gate.get("callback_ack_samples"))
    missing_keys = [key for key in EXPECTED_CALLBACK_ACK_KEYS if key not in samples]
    zero_hit_keys = [
        key for key in EXPECTED_CALLBACK_ACK_KEYS if intish((samples.get(key) or {}).get("hit_count")) <= 0
    ]
    hit_counts = {
        key: intish((samples.get(key) or {}).get("hit_count")) for key in EXPECTED_CALLBACK_ACK_KEYS
    }

    return {
        "sources": {
            "v1841": source_summary(v1841, V1841_MANIFEST),
            "v1839": source_summary(v1839, V1839_MANIFEST),
            "v1173_report": rel(V1173_REPORT),
        },
        "v1841": {
            "handoff_pass": bool(v1841.get("pass")),
            "rollback_ok": bool((v1841.get("rollback") or {}).get("ok")),
            "post_version_ok": bool(post.get("version_ok")),
            "post_selftest_fail_zero": bool(post.get("selftest_fail_zero")),
            "callback_ack_label": gate.get("callback_ack_label", ""),
            "callback_ack_contract_ok": bool(gate.get("callback_ack_contract_ok")),
            "callback_ack_registered_ok": bool(gate.get("callback_ack_registered_ok")),
            "callback_ack_enabled_ok": bool(gate.get("callback_ack_enabled_ok")),
            "callback_ack_hit_count_total": intish(gate.get("callback_ack_hit_count_total")),
            "callback_ack_hit_keys": gate.get("callback_ack_hit_keys") or [],
            "missing_callback_ack_keys": missing_keys,
            "zero_callback_ack_keys": zero_hit_keys,
            "callback_ack_hit_counts": hit_counts,
            "pm_client_register_rc": gate.get("pm_client_register_rc", ""),
            "pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
            "pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
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
            "servnotif_label": gate.get("servnotif_label", ""),
            "qipcrtr_bound_recv_label": gate.get("qipcrtr_bound_recv_label", ""),
            "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
            "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
            "lower_mhi_present": boolish(gate.get("lower_mhi_present")),
            "lower_service69_progress": boolish(gate.get("lower_service69_progress")),
            "lower_wlan0_present": boolish(gate.get("lower_wlan0_present")),
            "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
            "safety_ok": bool(gate.get("safety_ok")),
        },
        "v1839": {
            "pass": bool(v1839.get("pass")),
            "decision": v1839.get("decision", ""),
            "label": v1839.get("label", ""),
            "reason": v1839.get("reason", ""),
        },
        "v1173": {
            "decision_seen": "v1173-state2-ack-client-server-success-no-esoc0" in v1173_text,
            "ack_completion_closed": (
                "not CNSS callback delivery and not PM ack completion" in v1173_text
            ),
            "server_impl_target_seen": "server implementation target | `pm-service+0x63f4`" in v1173_text,
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    v1841 = details["v1841"]
    v1839 = details["v1839"]
    v1173 = details["v1173"]

    rollback_clean = (
        v1841["handoff_pass"]
        and v1841["rollback_ok"]
        and v1841["post_version_ok"]
        and v1841["post_selftest_fail_zero"]
    )
    callback_ack_present = (
        v1841["callback_ack_label"] == "callback-ack-present-no-powerup"
        and v1841["callback_ack_contract_ok"]
        and v1841["callback_ack_registered_ok"]
        and v1841["callback_ack_enabled_ok"]
        and v1841["callback_ack_hit_count_total"] > 0
        and not v1841["missing_callback_ack_keys"]
        and not v1841["zero_callback_ack_keys"]
    )
    current_route_clean = (
        v1841["pm_client_register_rc"] == "0"
        and v1841["pm_client_connect_rc"] == "0"
        and v1841["pm_init_return_path_rc"] == "0"
    )
    no_powerup = (
        v1841["lower_continuation_label"] == "lower-continuation-static-gap"
        and v1841["post_pm_lower_state_label"] == "stable-mdm3-offlining"
        and v1841["lower_mdm3_states"] == "OFFLINING"
        and not v1841["pm_focus_change_fields"]
        and v1841["pm_focus_mdm_status_delta"] == 0
        and not v1841["pm_focus_mhi_wlan0_progress"]
        and all(count == 0 for count in v1841["powerup_thread_counts"])
        and all(count == 0 for count in v1841["subsys_esoc0_open_inferred"])
        and v1841["servnotif_label"] == "service-notifier-uninit"
        and v1841["qipcrtr_bound_recv_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
        and not v1841["lower_mhi_present"]
        and not v1841["lower_service69_progress"]
        and not v1841["lower_wlan0_present"]
        and v1841["requested_wlanmdsp"] == "0"
    )
    prior_boundary_ok = (
        v1839["pass"]
        and v1839["label"] == "pm-connect-return-without-powerup-trigger"
        and v1173["decision_seen"]
        and v1173["ack_completion_closed"]
        and v1173["server_impl_target_seen"]
    )

    if not rollback_clean:
        return "rollback-review", "v1842-rollback-review", "V1841 rollback or post-rollback health is not clean", False
    if not v1841["safety_ok"]:
        return "safety-review", "v1842-safety-review", "V1841 safety flag is not clean", False
    if not current_route_clean:
        return "current-route-review", "v1842-current-route-review", "PM register/connect/return path is not clean", False
    if not callback_ack_present:
        return "callback-ack-evidence-review", "v1842-callback-ack-evidence-review", "callback/ack hit evidence is missing or incomplete", False
    if not no_powerup:
        return "lower-progress-review", "v1842-lower-progress-review", "lower state progressed or did not match the static-gap contract", False
    if not prior_boundary_ok:
        return "prior-boundary-review", "v1842-prior-boundary-review", "prior V1839/V1173 boundary evidence is unavailable or inconsistent", False

    return (
        "post-ack-no-powerup-gap",
        "v1842-post-ack-no-powerup-gap-host-pass",
        "V1841 proves current-route callback/transact/ack branch reachability, while lower powerup, service69, MHI, and wlan0 remain absent",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    v1841 = details["v1841"]
    v1839 = details["v1839"]
    v1173 = details["v1173"]
    sources = details["sources"]

    return "\n".join([
        "# Native Init V1842 Post-Ack No-Powerup Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only classifier over V1841 current-route callback/ack evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- V1841: `{sources['v1841']['decision']}` / pass `{sources['v1841']['pass']}`",
        f"- V1839: `{v1839['decision']}` / label `{v1839['label']}` / pass `{v1839['pass']}`",
        f"- V1173 report: `{sources['v1173_report']}`",
        "",
        "## V1841 Callback/Ack Evidence",
        "",
        f"- rollback/post-version/post-selftest: `{v1841['rollback_ok']}` / `{v1841['post_version_ok']}` / `{v1841['post_selftest_fail_zero']}`",
        f"- PM register/connect/return rc: `{v1841['pm_client_register_rc']}` / `{v1841['pm_client_connect_rc']}` / `{v1841['pm_init_return_path_rc']}`",
        f"- callback/ack contract/registered/enabled: `{v1841['callback_ack_contract_ok']}` / `{v1841['callback_ack_registered_ok']}` / `{v1841['callback_ack_enabled_ok']}`",
        f"- callback/ack label/total: `{v1841['callback_ack_label']}` / `{v1841['callback_ack_hit_count_total']}`",
        f"- missing/zero-hit callback keys: `{v1841['missing_callback_ack_keys']}` / `{v1841['zero_callback_ack_keys']}`",
        f"- callback hit counts: `{v1841['callback_ack_hit_counts']}`",
        "",
        "## Static Lower State",
        "",
        f"- lower-continuation/lower-state: `{v1841['lower_continuation_label']}` / `{v1841['post_pm_lower_state_label']}`",
        f"- PM focus changes/status-delta/MHI-wlan0-progress: `{v1841['pm_focus_change_fields']}` / `{v1841['pm_focus_mdm_status_delta']}` / `{v1841['pm_focus_mhi_wlan0_progress']}`",
        f"- powerup threads / inferred esoc0 opens: `{v1841['powerup_thread_counts']}` / `{v1841['subsys_esoc0_open_inferred']}`",
        f"- mdm3/MHI/WLFW69/wlan0/requested-wlanmdsp: `{v1841['lower_mdm3_states']}` / `{v1841['lower_mhi_present']}` / `{v1841['lower_service69_progress']}` / `{v1841['lower_wlan0_present']}` / `{v1841['requested_wlanmdsp']}`",
        f"- service-notifier / QIPCRTR bound labels: `{v1841['servnotif_label']}` / `{v1841['qipcrtr_bound_recv_label']}`",
        f"- safety ok: `{v1841['safety_ok']}`",
        "",
        "## Boundary Interpretation",
        "",
        "- V1841 rules out total absence of the current-route callback/transact/ack branch: all expected read-only hit-count labels fired.",
        "- V1841 does not decode callback state or return values; its evidence is branch reachability plus lower-state absence.",
        f"- V1173 decoded-state reference present/ack-closed/server-target: `{v1173['decision_seen']}` / `{v1173['ack_completion_closed']}` / `{v1173['server_impl_target_seen']}`.",
        "- The active boundary is therefore after callback/ack reachability and before any PM-service powerup thread, inferred `/dev/subsys_esoc0` open, WLFW service69, MHI, or `wlan0` publication.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Next unit should be source/build-only first: map the current PM-service ack implementation body or adjacent post-ack action path and choose read-only offsets.",
        "- Do not add actors, direct eSoC opens, restart-PD, PMIC/GPIO/GDSC writes, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until WLFW service69 and `wlan0` exist.",
        "",
    ])


def main() -> int:
    v1841 = load_json(V1841_MANIFEST)
    v1839 = load_json(V1839_MANIFEST)
    v1173_text = load_text(V1173_REPORT)
    details = collect_details(v1841, v1839, v1173_text)
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
