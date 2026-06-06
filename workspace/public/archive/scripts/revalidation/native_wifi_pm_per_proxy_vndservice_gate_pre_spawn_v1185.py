#!/usr/bin/env python3
"""V1185 PM per_proxy pre-spawn vndservice gate live observer.

Helper v221 change: moves the vndservice gate BEFORE composite_spawn_child(per_proxy)
so the gate actually prevents per_proxy from spawning until per_mgr registers with
vndservicemanager.  V1183 (helper v220) had the gate after spawn (log-only), which
meant the V1181 race still occurred.

Gate timeout (per_mgr never registers): per_proxy spawn is skipped entirely and the
experiment continues to CNSS.  This distinguishes the V1181 race from a separate
per_mgr early-death blocker.

Does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

# Capture originals BEFORE patch_defaults() to avoid circular references.
_ORIG_V1183_PATCH_DEFAULTS = v1183.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1185-pm-per-proxy-vndservice-gate-pre-spawn")
LATEST_POINTER = Path("tmp/wifi/latest-v1185-pm-per-proxy-vndservice-gate-pre-spawn.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "120fad47dad2965ab8a541759bf1cd04396b9f81eb0c06986096e6f05dfdf05d"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v221"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1185"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1185/pm-per-proxy-vndservice-gate-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1185/pm-per-proxy-vndservice-gate-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1185/pm-per-proxy-vndservice-gate-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1185-"

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG
PPH_DELTA_OPTION = v1183.PPH_DELTA_OPTION


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ── Decision ──────────────────────────────────────────────────────────────

def decide_v1185(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1185-pm-per-proxy-vndservice-gate-pre-spawn-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v221, then run V1185 live gate",
        )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    post = v1183._post_pm(manifest)
    tfs = v1183._tracefs(manifest)

    if gate.get("begin") != "1":
        return (
            "v1185-vndservice-gate-not-activated",
            False,
            (
                f"per_proxy_vndservice_gate.begin not found in output; "
                f"gate flag may be missing from helper command or helper is wrong version; "
                f"contract={contract}"
            ),
            "verify helper v221 is deployed and "
            f"{VNDSERVICE_GATE_FLAG} is in the command; check {PPH_DELTA_OPTION} is absent",
        )

    gate_result = gate.get("result", "")
    gate_open = gate.get("gate_open", "0")
    poll_count = gate.get("poll_count", "?")
    elapsed_ms = gate.get("elapsed_ms", "?")
    query_error = gate.get("query_error", "0")

    if query_error == "1":
        return (
            "v1185-vndservice-gate-query-error",
            False,
            (
                f"vndservice gate query error; gate_result={gate_result} "
                f"poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            "check vndservice binary availability and SELinux context",
        )

    if gate_result == "timeout" or gate_open != "1":
        per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")
        per_proxy_skipped = contract.get("child.per_proxy.start_skipped", "?")
        return (
            "v1185-vndservice-gate-timeout",
            False,
            (
                f"vndservice gate timed out; per_mgr did not register with vndservicemanager "
                f"within 5000ms; poll_count={poll_count} elapsed_ms={elapsed_ms}ms "
                f"per_mgr_observable={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}; "
                f"gate_result={gate_result} gate_open={gate_open}"
            ),
            "per_mgr dies before registering regardless of per_proxy timing; "
            "investigate per_mgr SELinux domain and early exit path; "
            "capture per_mgr running domain before next live attempt",
        )

    per_proxy_obs = contract.get("child.per_proxy.post_start_observable", "?")
    per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")
    post_spawn_check = gate.get("post_spawn_check", "?")

    pm_client_ret = tfs.get(
        "pm_client_register_ret.count",
        (manifest.get("analysis") or {})
        .get("tracefs_uprobe", {})
        .get("pm_contract", {})
        .get("pm_client_register_ret.count", "?"),
    )
    pm_server_entry = tfs.get(
        "pm_server_register_entry.count",
        (manifest.get("analysis") or {})
        .get("tracefs_uprobe", {})
        .get("pm_contract", {})
        .get("pm_server_register_entry.count", "?"),
    )

    subsys_esoc0_count = post.get("fd_subsys_esoc0_count.window", "?")
    subsys_modem_count = post.get("fd_subsys_modem_count.window", "?")
    mdm_helper_result = post.get("result", "?")

    if gate_result == "ready" and gate_open == "1":
        return (
            "v1185-vndservice-gate-ready",
            True,
            (
                f"vndservice gate opened pre-spawn; vendor.qcom.PeripheralManager registered "
                f"after poll_count={poll_count} polls elapsed_ms={elapsed_ms}ms; "
                f"per_proxy spawned after gate; post_spawn_check={post_spawn_check}; "
                f"per_proxy_obs={per_proxy_obs} per_mgr_obs={per_mgr_obs}; "
                f"pm_client_register_ret.count={pm_client_ret} "
                f"pm_server_register_entry.count={pm_server_entry}; "
                f"subsys_esoc0_count={subsys_esoc0_count} "
                f"subsys_modem_count={subsys_modem_count} "
                f"mdm_helper_result={mdm_helper_result}"
            ),
            (
                "check pm_server_register_ret for modem registration success; "
                "check subsys_esoc0/subsys_modem fd holds and mdm3 ONLINE state"
            ),
        )

    return (
        "v1185-unexpected-state",
        False,
        f"unexpected gate state; gate={gate} contract={contract}",
        "inspect raw output manually",
    )


# ── Summary ───────────────────────────────────────────────────────────────

def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    post = v1183._post_pm(manifest)

    rows = [
        ["vndservice_gate_flag", VNDSERVICE_GATE_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["gate_begin", gate.get("begin", "")],
        ["gate_result", gate.get("result", "")],
        ["gate_open", gate.get("gate_open", "")],
        ["gate_post_spawn_check", gate.get("post_spawn_check", "")],
        ["gate_poll_count", gate.get("poll_count", "")],
        ["gate_elapsed_ms", gate.get("elapsed_ms", "")],
        ["gate_timeout_ms", gate.get("timeout_ms", "")],
        ["per_mgr_obs_at_probe",
         contract.get("child.per_mgr.post_start_observable", "")],
        ["per_proxy_skipped",
         contract.get("child.per_proxy.start_skipped", "")],
        ["per_proxy_skip_reason",
         contract.get("child.per_proxy.skip_reason", "")],
        ["per_proxy_obs_post_start",
         contract.get("child.per_proxy.post_start_observable", "")],
        ["subsys_esoc0_count_window", post.get("fd_subsys_esoc0_count.window", "")],
        ["subsys_modem_count_window", post.get("fd_subsys_modem_count.window", "")],
        ["mdm_helper_result", post.get("result", "")],
    ]
    lines = [
        "# V1185 PM Per-Proxy Pre-Spawn Vndservice Gate Observer",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
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
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180

    v1183.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1183.LATEST_POINTER = LATEST_POINTER
    v1183.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1183.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1183.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1183.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1183.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1183_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    patch_defaults()
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1185"
    manifest["generated_at"] = _now_iso()
    manifest["vndservice_gate_flag"] = VNDSERVICE_GATE_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER

    decision, passed, reason, next_step = decide_v1185(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    post = v1183._post_pm(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["vndservice_gate_begin"] = gate.get("begin") == "1"
    manifest["vndservice_gate_result"] = gate.get("result", "")
    manifest["vndservice_gate_open"] = gate.get("gate_open") == "1"
    manifest["vndservice_gate_post_spawn_check"] = gate.get("post_spawn_check", "")
    manifest["vndservice_gate_poll_count"] = gate.get("poll_count", "")
    manifest["vndservice_gate_elapsed_ms"] = gate.get("elapsed_ms", "")
    manifest["per_mgr_obs_at_probe"] = (
        contract.get("child.per_mgr.post_start_observable", "")
    )
    manifest["per_proxy_skipped"] = contract.get("child.per_proxy.start_skipped", "")
    manifest["per_proxy_skip_reason"] = contract.get("child.per_proxy.skip_reason", "")
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
    print(f"gate_post_spawn_check      : {manifest['vndservice_gate_post_spawn_check']}")
    print(f"gate_poll_count            : {manifest['vndservice_gate_poll_count']}")
    print(f"gate_elapsed_ms            : {manifest['vndservice_gate_elapsed_ms']}ms")
    print(f"per_mgr_obs_at_probe       : {manifest['per_mgr_obs_at_probe']}")
    print(f"per_proxy_skipped          : {manifest['per_proxy_skipped']}")
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
