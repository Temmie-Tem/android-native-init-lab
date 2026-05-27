#!/usr/bin/env python3
"""V1180 bounded PM dep early per-proxy observer with zero-delay per_mgr probe.

Helper v219 change: adds --pm-observer-zero-delay-per-mgr-probe which skips the
1000ms per_mgr post-start probe wait, so per_proxy pph_delta=300ms puts per_proxy
at pph+300ms — before pm-service's no-client initialization timeout (~500-800ms)
and well before modem pm-proxy connects at pph+~1254ms.

Does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_early_per_proxy_observer_v1179 as v1179
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

# Capture original functions BEFORE any patch_defaults() call.
_ORIG_V1179_CHILD_COMMAND = v1179.pm_dep_early_per_proxy_child_command
_ORIG_V1179_SERIAL_REMOTE_MARKER_CHECK = v1179.serial_remote_marker_check_v1179
_ORIG_V1179_PARSE_TRACEFS = v1179.parse_tracefs_output_v1179
_ORIG_V1179_TRACEFS_COLLECTOR = v1179.tracefs_collector_script_v1179


DEFAULT_OUT_DIR = Path("tmp/wifi/v1180-pm-dep-early-per-proxy-zero-delay-per-mgr")
LATEST_POINTER = Path("tmp/wifi/latest-v1180-pm-dep-early-per-proxy-zero-delay-per-mgr.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "b9c93cf4e87b11a33203b5cec36b01c323e99bc61d3bbc20c24d2d811ee768fc"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v219"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1180"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1180/pm-dep-early-per-proxy-zero-delay-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1180/pm-dep-early-per-proxy-zero-delay-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1180/pm-dep-early-per-proxy-zero-delay-output.txt"
PROOF_PREFIX = "/tmp/a90-v1180-"

# per_proxy pph delta: pph+300ms starts per_proxy ~123ms after per_mgr (pph+177ms),
# while pm-service init timeout is ~500-800ms after per_mgr starts.
EARLY_PER_PROXY_PPH_DELTA_MS = 300

# Flag that eliminates the 1000ms per_mgr post-start probe wait (helper v219).
ZERO_DELAY_PER_MGR_FLAG = "--pm-observer-zero-delay-per-mgr-probe"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ── Child command override ─────────────────────────────────────────────────

def pm_dep_early_per_proxy_child_command_v1180(args: Any) -> list[str]:
    """Build helper command: zero-delay per_mgr probe + pph_delta=300ms."""
    base = _ORIG_V1179_CHILD_COMMAND(args)
    # Replace the pph delta value inserted by v1179
    result: list[str] = []
    i = 0
    while i < len(base):
        if base[i] == "--pm-observer-per-proxy-pph-delta-ms" and i + 1 < len(base):
            result.extend(["--pm-observer-per-proxy-pph-delta-ms",
                            str(EARLY_PER_PROXY_PPH_DELTA_MS)])
            i += 2
        else:
            result.append(base[i])
            i += 1
    # Add zero-delay per_mgr probe flag (new in v219)
    if ZERO_DELAY_PER_MGR_FLAG not in result:
        result.append(ZERO_DELAY_PER_MGR_FLAG)
    return result


def serial_remote_marker_check_v1180(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    info = _ORIG_V1179_SERIAL_REMOTE_MARKER_CHECK(args, store, steps)
    step_file = info.get("file", "")
    text = ""
    if step_file:
        try:
            text = (store.run_dir / str(step_file)).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            pass
    info["zero_delay_per_mgr_flag_ok"] = ZERO_DELAY_PER_MGR_FLAG in text
    info["v219_marker_ok"] = "v219" in text
    return info


# ── Decision ──────────────────────────────────────────────────────────────

def decide_v1180(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1180-pm-dep-early-per-proxy-zero-delay-per-mgr-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "deploy helper v219, then run V1180 live gate",
        )

    base_decision, base_pass, base_reason, base_next = v1179.decide_v1179(args, manifest)
    dst = v1179.dep_state_transitions(manifest)

    # V1179 base may return pass=False for "pre-cnss-per-proxy-not-skipped" (normal
    # with early per_proxy) or its own diagnostic pass=True cases.  Either way
    # proceed to V1180 dep-state analysis.
    _skip_base = (
        (not base_pass and any(base_decision.endswith(s) for s in {
            "pre-cnss-per-proxy-not-skipped",
            "helper-late-per-proxy-flag-missing",
        }))
        or "v1179-per-mgr-probe-wait" in base_decision
        or "v1179-per-mgr-exited" in base_decision
        or "v1179-pm-state-machine-never-fired" in base_decision
    )

    if not base_pass and not _skip_base:
        return (
            base_decision.replace("v1179", "v1180", 1).replace("v1177", "v1180", 1),
            False,
            base_reason,
            base_next,
        )

    dep_state1_obs = dst.get("dep_state1_observed", False)
    dep_state1_time = dst.get("dep_state1_time")
    dep_before_connect = dst.get("dep_state1_before_per_proxy_connect", False)
    first_connect = dst.get("first_per_proxy_connect_time")

    # PM never fired at all — per_proxy still arrived too late or pm-service
    # exited before connecting.
    if dst.get("state_set_event_count", 0) == 0:
        pm_contract = (
            (manifest.get("analysis") or {})
            .get("tracefs_uprobe", {})
            .get("pm_contract") or {}
        )
        elapsed_ms = pm_contract.get("early_per_proxy.elapsed_since_pph_ms", "?")
        target_ms = pm_contract.get("early_per_proxy.target_delta_ms",
                                    str(EARLY_PER_PROXY_PPH_DELTA_MS))
        already_elapsed = pm_contract.get("early_per_proxy.already_elapsed") == "1"
        per_mgr_gone = pm_contract.get("child.per_mgr.post_start_observable") == "0"
        probe_wait_ms = pm_contract.get("child.per_mgr.post_start_probe_wait_ms", "?")
        return (
            "v1180-pm-state-machine-never-fired",
            True,
            (
                f"PM state machine never fired (state_set_event_count=0); "
                f"per_proxy at pph+{elapsed_ms}ms (target={target_ms}ms); "
                f"already_elapsed={already_elapsed} per_mgr_gone={per_mgr_gone} "
                f"probe_wait_ms={probe_wait_ms}; pm_contract={pm_contract}"
            ),
            (
                "check pm_proxy_helper_vndbinder_count and pm-service stdout; "
                "pm-service may need vndbinder fd before clients connect; "
                "consider even shorter pph_delta or pm-service init path fix"
            ),
        )

    if dep_state1_obs and not dep_before_connect:
        return (
            "v1180-dep-state1-after-per-proxy-connect-timing-ok",
            True,
            (
                f"dep state=1 at t={dep_state1_time}s AFTER first per_proxy connect "
                f"t={first_connect}s; zero-delay per_mgr probe + "
                f"pph_delta={EARLY_PER_PROXY_PPH_DELTA_MS}ms timing ok; dst={dst}"
            ),
            "V1181 should verify dep_flag is set to 1 (state0 path ran with dep still state=0)",
        )

    if dep_state1_obs and dep_before_connect:
        return (
            "v1180-dep-state1-before-per-proxy-connect-still-too-late",
            True,
            (
                f"dep state=1 at t={dep_state1_time}s BEFORE first per_proxy connect "
                f"t={first_connect}s; even zero-delay per_mgr + "
                f"pph_delta={EARLY_PER_PROXY_PPH_DELTA_MS}ms too late; dst={dst}"
            ),
            "investigate what drives dep state=1 before any client connects; "
            "consider simultaneous per_proxy + per_proxy_helper start",
        )

    if not dep_state1_obs and dst.get("state_set_event_count", 0) > 0:
        return (
            "v1180-dep-state1-not-observed-in-window",
            True,
            f"dep never reached state=1 in trace window; dst={dst}",
            "extend trace window or arm uprobes earlier in boot sequence",
        )

    return (
        base_decision.replace("v1179", "v1180", 1).replace("v1177", "v1180", 1),
        base_pass,
        base_reason + f" dst={dst}",
        base_next,
    )


# ── Summary ───────────────────────────────────────────────────────────────

def render_summary(manifest: dict[str, Any]) -> str:
    base = v1179.render_summary(manifest).replace(
        "# V1179 PM Dep Early Per-Proxy Observer",
        "# V1180 PM Dep Early Per-Proxy Zero-Delay Per-Mgr",
        1,
    )
    dst = v1179.dep_state_transitions(manifest)
    dep = v1179.v1177.dependency_flag(manifest)
    rows = [
        ["zero_delay_per_mgr_probe", "1"],
        ["per_proxy_pph_delta_ms", str(EARLY_PER_PROXY_PPH_DELTA_MS)],
        ["dep_state1_observed", str(dst.get("dep_state1_observed", ""))],
        ["dep_state1_time", str(dst.get("dep_state1_time", ""))],
        ["dep_state1_before_per_proxy_connect",
         str(dst.get("dep_state1_before_per_proxy_connect", ""))],
        ["first_per_proxy_connect_time",
         str(dst.get("first_per_proxy_connect_time", ""))],
        ["state_set_event_count", str(dst.get("state_set_event_count", ""))],
        ["dep_flag_set_seen", str(dep.get("state0_flag_set_seen", ""))],
        ["dep_state_history", json.dumps(dst.get("dep_state_history", []))],
    ]
    return base + "\n".join([
        "",
        "## V1180 Zero-Delay Per-Mgr Dep State Transition",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ])


# ── Wiring ────────────────────────────────────────────────────────────────

def patch_defaults() -> None:
    v1179.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1179.LATEST_POINTER = LATEST_POINTER
    v1179.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1179.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1179.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1179.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1179.PROOF_PREFIX = PROOF_PREFIX

    v1179.patch_defaults()

    # Override child command and marker check with V1180 versions
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1143 = v1165.v1143
    v1106 = v1143.v1139.v1113.v1106

    v1165.pm_late_per_proxy_child_command = pm_dep_early_per_proxy_child_command_v1180
    v1106.pm_cnss_child_command = pm_dep_early_per_proxy_child_command_v1180
    v1165.serial_remote_marker_check_v1165 = serial_remote_marker_check_v1180
    v1143.serial_remote_marker_check_v1143 = serial_remote_marker_check_v1180
    v1143.v1139.serial_remote_marker_check = serial_remote_marker_check_v1180
    v1106.remote_marker_check = serial_remote_marker_check_v1180

    # Update helper sha/marker at all levels
    for module in [
        v1177_chain,
        v1165,
        v1106,
    ]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    patch_defaults()
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1179_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1180"
    manifest["generated_at"] = _now_iso()
    manifest["early_per_proxy_pph_delta_ms"] = EARLY_PER_PROXY_PPH_DELTA_MS
    manifest["zero_delay_per_mgr_probe"] = True
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER

    decision, passed, reason, next_step = decide_v1180(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    dst = v1179.dep_state_transitions(manifest)
    dep = v1177_chain.dependency_flag(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    post = v1165.v1143.v1139.post_pm(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["dep_state1_observed"] = dst.get("dep_state1_observed", False)
    manifest["dep_state1_time"] = dst.get("dep_state1_time")
    manifest["dep_state1_before_per_proxy_connect"] = dst.get("dep_state1_before_per_proxy_connect", False)
    manifest["first_per_proxy_connect_time"] = dst.get("first_per_proxy_connect_time")
    manifest["dep_flag_armed"] = dep.get("state0_flag_value_one_seen", False)
    manifest["dep_state2_call_seen"] = dep.get("state2_dependency_call_seen", False)
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or post.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["scan_connect_executed"] = (
        values.get("scan_connect_linkup") == "1"
        or post.get("scan_connect_linkup") == "1"
        or lower.get("scan_connect_linkup") == "1"
    )
    manifest["credential_use_executed"] = lower.get("credentials") == "1"
    manifest["dhcp_route_executed"] = lower.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = (
        values.get("external_ping") == "1"
        or post.get("external_ping") == "1"
        or lower.get("external_ping") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                    : {manifest['decision']}")
    print(f"pass                        : {manifest['pass']}")
    print(f"reason                      : {manifest['reason'][:200]}")
    print(f"next                        : {manifest['next_step']}")
    print(f"firmware_mounts_executed    : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed             : {manifest['reboot_executed']}")
    print(f"dep_state1_observed         : {manifest['dep_state1_observed']}")
    print(f"dep_state1_time             : {manifest['dep_state1_time']}")
    print(f"dep_state1_before_pp_connect: {manifest['dep_state1_before_per_proxy_connect']}")
    print(f"first_pp_connect_time       : {manifest['first_per_proxy_connect_time']}")
    print(f"dep_flag_armed              : {manifest['dep_flag_armed']}")
    print(f"dep_state2_call_seen        : {manifest['dep_state2_call_seen']}")
    print(f"zero_delay_per_mgr_probe    : {manifest['zero_delay_per_mgr_probe']}")
    print(f"wifi_hal_start_executed     : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed       : {manifest['wifi_bringup_executed']}")
    print(f"manifest                    : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
