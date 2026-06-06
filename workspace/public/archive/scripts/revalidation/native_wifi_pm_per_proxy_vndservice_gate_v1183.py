#!/usr/bin/env python3
"""V1183 bounded PM per_proxy vndservice gate live observer.

Helper v220 change: --pm-observer-per-proxy-after-vndservice-provider replaces
the unsafe fixed-time --pm-observer-per-proxy-pph-delta-ms approach.  The gate
polls vndservice list at 200ms intervals until vendor.qcom.PeripheralManager is
registered (bounded 5s timeout) before spawning per_proxy.

This directly fixes the V1179/V1180 race: per_mgr needs ~1000ms to build its
internal peripheral list and register with vndservicemanager before it can safely
handle pm_client_register("modem") from pm-proxy.  The gate ensures per_mgr is
fully initialized before per_proxy (and its pm-proxy child) connect.

Does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

# Capture originals BEFORE patch_defaults() to avoid circular references.
_ORIG_V1180_CHILD_COMMAND = v1180.pm_dep_early_per_proxy_child_command_v1180
_ORIG_V1180_SERIAL_REMOTE_MARKER_CHECK = v1180.serial_remote_marker_check_v1180
_ORIG_V1106_PARSE_TRACEFS_OUTPUT = (
    v1180.v1179.v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168
    .v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v1183-pm-per-proxy-vndservice-gate")
LATEST_POINTER = Path("tmp/wifi/latest-v1183-pm-per-proxy-vndservice-gate.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "985675707ee433ec0203cbd1e59b0cd439dee0bc05d315266657b889d0c384a0"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v220"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1183"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1183/pm-per-proxy-vndservice-gate-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1183/pm-per-proxy-vndservice-gate-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1183/pm-per-proxy-vndservice-gate-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1183-"

VNDSERVICE_GATE_FLAG = "--pm-observer-per-proxy-after-vndservice-provider"
PPH_DELTA_OPTION = "--pm-observer-per-proxy-pph-delta-ms"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ── Child command override ─────────────────────────────────────────────────

def pm_per_proxy_vndservice_gate_child_command(args: Any) -> list[str]:
    """Build helper command: vndservice gate replaces pph_delta timing."""
    base = _ORIG_V1180_CHILD_COMMAND(args)
    # Remove pph_delta option (mutually exclusive with vndservice gate)
    result: list[str] = []
    i = 0
    while i < len(base):
        if base[i] == PPH_DELTA_OPTION and i + 1 < len(base):
            i += 2  # skip option + value
        else:
            result.append(base[i])
            i += 1
    # Add vndservice gate flag
    if VNDSERVICE_GATE_FLAG not in result:
        result.append(VNDSERVICE_GATE_FLAG)
    return result


def serial_remote_marker_check_v1183(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    info = _ORIG_V1180_SERIAL_REMOTE_MARKER_CHECK(args, store, steps)
    step_file = info.get("file", "")
    text = ""
    if step_file:
        try:
            text = (store.run_dir / str(step_file)).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            pass
    info["vndservice_gate_flag_ok"] = VNDSERVICE_GATE_FLAG in text
    info["pph_delta_flag_absent"] = PPH_DELTA_OPTION not in text
    info["v220_marker_ok"] = "v220" in text
    return info


# ── Tracefs parse extension ────────────────────────────────────────────────

def _collect_prefix(keys: dict[str, str], prefix: str) -> dict[str, str]:
    return {
        key[len(prefix):]: value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def parse_tracefs_output_v1183(text: str) -> dict[str, Any]:
    # Delegate to the parent chain's parser (sets up pm_contract, tracefs events, etc.)
    # Use the pre-patch capture to avoid infinite recursion after patch_defaults().
    v1177 = v1180.v1179.v1177
    v1106 = v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106
    parsed = _ORIG_V1106_PARSE_TRACEFS_OUTPUT(text)
    keys = v1106.parse_keys(text)
    # Extract vndservice gate sub-keys from pm_service_trigger_observer.*
    gate = _collect_prefix(
        keys, "pm_service_trigger_observer.per_proxy_vndservice_gate."
    )
    parsed["per_proxy_vndservice_gate"] = gate
    return parsed


# ── Decision ──────────────────────────────────────────────────────────────

def _vndservice_gate(manifest: dict[str, Any]) -> dict[str, str]:
    value = (
        (manifest.get("analysis") or {})
        .get("tracefs_uprobe", {})
        .get("per_proxy_vndservice_gate") or {}
    )
    return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _pm_contract(manifest: dict[str, Any]) -> dict[str, str]:
    value = (
        (manifest.get("analysis") or {})
        .get("tracefs_uprobe", {})
        .get("pm_contract") or {}
    )
    return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _post_pm(manifest: dict[str, Any]) -> dict[str, str]:
    value = (
        (manifest.get("analysis") or {})
        .get("tracefs_uprobe", {})
        .get("post_pm_mdm_helper") or {}
    )
    return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    return value if isinstance(value, dict) else {}


def decide_v1183(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1183-pm-per-proxy-vndservice-gate-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v220, then run V1183 live gate",
        )

    gate = _vndservice_gate(manifest)
    contract = _pm_contract(manifest)
    post = _post_pm(manifest)
    tfs = _tracefs(manifest)

    # Gate must have activated — if missing, the flag was not in the command
    if gate.get("begin") != "1":
        return (
            "v1183-vndservice-gate-not-activated",
            False,
            (
                f"per_proxy_vndservice_gate.begin not found in output; "
                f"gate flag may be missing from helper command or helper is wrong version; "
                f"contract={contract}"
            ),
            "verify helper v220 is deployed and "
            f"{VNDSERVICE_GATE_FLAG} is in the command; check {PPH_DELTA_OPTION} is absent",
        )

    gate_result = gate.get("result", "")
    gate_open = gate.get("gate_open", "0")
    poll_count = gate.get("poll_count", "?")
    elapsed_ms = gate.get("elapsed_ms", "?")
    query_error = gate.get("query_error", "0")

    if query_error == "1":
        return (
            "v1183-vndservice-gate-query-error",
            False,
            (
                f"vndservice gate query error; gate_result={gate_result} "
                f"poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            "check vndservice binary availability and SELinux context",
        )

    if gate_result == "timeout" or gate_open != "1":
        per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")
        return (
            "v1183-vndservice-gate-timeout",
            True,
            (
                f"vndservice gate timed out; per_mgr did not register with vndservicemanager "
                f"within 5000ms; poll_count={poll_count} elapsed_ms={elapsed_ms}ms "
                f"per_mgr_observable={per_mgr_obs}; "
                f"gate_result={gate_result} gate_open={gate_open}"
            ),
            "investigate why per_mgr does not register with vndservicemanager; "
            "check SELinux context and vndservicemanager readiness",
        )

    # Gate opened (result=ready)
    per_proxy_obs = contract.get("child.per_proxy.post_start_observable", "?")
    per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")

    # Check if pm-proxy's modem registration returned
    pm_client_modem_count = tfs.get("pm_client_register_ret_modem_count")
    if pm_client_modem_count is None:
        # Fall back to raw count from event keys
        pm_client_modem_count = str(
            (manifest.get("analysis") or {})
            .get("tracefs_uprobe", {})
            .get("pm_contract", {})
            .get("pm_client_register_ret.count", "?")
        )

    # Check subsys fd hold from post_pm observer
    subsys_esoc0_count = post.get("fd_subsys_esoc0_count.window", "?")
    subsys_modem_count = post.get("fd_subsys_modem_count.window", "?")
    mdm_helper_result = post.get("result", "?")

    if gate_result == "ready" and gate_open == "1":
        return (
            "v1183-vndservice-gate-ready",
            True,
            (
                f"vndservice gate opened; vendor.qcom.PeripheralManager registered after "
                f"poll_count={poll_count} polls elapsed_ms={elapsed_ms}ms; "
                f"per_proxy spawned; per_proxy_obs={per_proxy_obs} "
                f"per_mgr_obs_at_gate={per_mgr_obs}; "
                f"subsys_esoc0_count={subsys_esoc0_count} "
                f"subsys_modem_count={subsys_modem_count} "
                f"mdm_helper_result={mdm_helper_result}"
            ),
            (
                "check pm_server_register_ret tracefs events for modem registration success; "
                "check subsys_esoc0/subsys_modem fd holds and mdm3 ONLINE state"
            ),
        )

    return (
        "v1183-unexpected-state",
        False,
        (
            f"unexpected gate state; gate={gate} contract={contract}"
        ),
        "inspect raw output manually",
    )


# ── Summary ───────────────────────────────────────────────────────────────

def render_summary(manifest: dict[str, Any]) -> str:
    gate = _vndservice_gate(manifest)
    contract = _pm_contract(manifest)
    post = _post_pm(manifest)

    rows = [
        ["vndservice_gate_flag", VNDSERVICE_GATE_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["gate_begin", gate.get("begin", "")],
        ["gate_result", gate.get("result", "")],
        ["gate_open", gate.get("gate_open", "")],
        ["gate_poll_count", gate.get("poll_count", "")],
        ["gate_elapsed_ms", gate.get("elapsed_ms", "")],
        ["gate_timeout_ms", gate.get("timeout_ms", "")],
        ["gate_query_error", gate.get("query_error", "")],
        ["per_mgr_obs_at_probe",
         contract.get("child.per_mgr.post_start_observable", "")],
        ["per_proxy_obs_post_start",
         contract.get("child.per_proxy.post_start_observable", "")],
        ["subsys_esoc0_count_window", post.get("fd_subsys_esoc0_count.window", "")],
        ["subsys_modem_count_window", post.get("fd_subsys_modem_count.window", "")],
        ["mdm_helper_result", post.get("result", "")],
    ]
    lines = [
        "# V1183 PM Per-Proxy Vndservice Gate Observer",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:300]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## Vndservice Gate State",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


# ── Wiring ────────────────────────────────────────────────────────────────

def patch_defaults() -> None:
    v1180.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1180.LATEST_POINTER = LATEST_POINTER
    v1180.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1180.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1180.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1180.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1180.PROOF_PREFIX = PROOF_PREFIX

    v1180.patch_defaults()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    # Override child command with V1183 version (vndservice gate)
    v1165.pm_late_per_proxy_child_command = pm_per_proxy_vndservice_gate_child_command
    v1106.pm_cnss_child_command = pm_per_proxy_vndservice_gate_child_command

    # Override marker check
    v1165.serial_remote_marker_check_v1165 = serial_remote_marker_check_v1183
    v1165.v1143.serial_remote_marker_check_v1143 = serial_remote_marker_check_v1183
    v1165.v1143.v1139.serial_remote_marker_check = serial_remote_marker_check_v1183
    v1106.remote_marker_check = serial_remote_marker_check_v1183

    # Override tracefs parser to extract vndservice gate keys
    v1106.parse_tracefs_output = parse_tracefs_output_v1183

    # Update helper sha/marker at all levels
    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1183"
    manifest["generated_at"] = _now_iso()
    manifest["vndservice_gate_flag"] = VNDSERVICE_GATE_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER

    decision, passed, reason, next_step = decide_v1183(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = _vndservice_gate(manifest)
    contract = _pm_contract(manifest)
    post = _post_pm(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["vndservice_gate_begin"] = gate.get("begin") == "1"
    manifest["vndservice_gate_result"] = gate.get("result", "")
    manifest["vndservice_gate_open"] = gate.get("gate_open") == "1"
    manifest["vndservice_gate_poll_count"] = gate.get("poll_count", "")
    manifest["vndservice_gate_elapsed_ms"] = gate.get("elapsed_ms", "")
    manifest["per_mgr_obs_at_probe"] = (
        contract.get("child.per_mgr.post_start_observable", "")
    )
    manifest["per_proxy_obs_post_start"] = (
        contract.get("child.per_proxy.post_start_observable", "")
    )
    manifest["subsys_esoc0_count_window"] = post.get("fd_subsys_esoc0_count.window", "")
    manifest["subsys_modem_count_window"] = post.get("fd_subsys_modem_count.window", "")
    manifest["mdm_helper_result"] = post.get("result", "")
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
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

    print(f"decision                   : {manifest['decision']}")
    print(f"pass                       : {manifest['pass']}")
    print(f"reason                     : {manifest['reason'][:200]}")
    print(f"next                       : {manifest['next_step']}")
    print(f"firmware_mounts_executed   : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed            : {manifest['reboot_executed']}")
    print(f"gate_begin                 : {manifest['vndservice_gate_begin']}")
    print(f"gate_result                : {manifest['vndservice_gate_result']}")
    print(f"gate_open                  : {manifest['vndservice_gate_open']}")
    print(f"gate_poll_count            : {manifest['vndservice_gate_poll_count']}")
    print(f"gate_elapsed_ms            : {manifest['vndservice_gate_elapsed_ms']}ms")
    print(f"per_mgr_obs_at_probe       : {manifest['per_mgr_obs_at_probe']}")
    print(f"per_proxy_obs_post_start   : {manifest['per_proxy_obs_post_start']}")
    print(f"subsys_esoc0_count_window  : {manifest['subsys_esoc0_count_window']}")
    print(f"subsys_modem_count_window  : {manifest['subsys_modem_count_window']}")
    print(f"mdm_helper_result          : {manifest['mdm_helper_result']}")
    print(f"wifi_hal_start_executed    : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed      : {manifest['wifi_bringup_executed']}")
    print(f"manifest                   : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
