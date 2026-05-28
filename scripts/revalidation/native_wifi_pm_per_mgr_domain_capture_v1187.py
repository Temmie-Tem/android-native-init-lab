#!/usr/bin/env python3
"""V1187 PM per_mgr domain capture live observer.

Helper v222 change: adds a pre-drain per_mgr attr/current capture immediately
after per_mgr spawn, before drain_pm_service_trigger_observer_children() runs.
V1185 (helper v221) missed the domain because drain reaped per_mgr (setting
child_done=true) before composite_capture_observable_children was called.

Objective: capture per_mgr's running SELinux domain (/proc/<pid>/attr/current)
and correlate with dmesg AVC denials around per_mgr exec time.

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

DEFAULT_OUT_DIR = Path("tmp/wifi/v1187-pm-per-mgr-domain-capture")
LATEST_POINTER = Path("tmp/wifi/latest-v1187-pm-per-mgr-domain-capture.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "52d32ff2e469b674dc7d424337176bae3f43e63b1135deecf77442d4ccf92266"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v223"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1187"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1187/pm-per-mgr-domain-capture-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1187/pm-per-mgr-domain-capture-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1187/pm-per-mgr-domain-capture-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1187-"

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG
PPH_DELTA_OPTION = v1183.PPH_DELTA_OPTION

_PRE_DRAIN_DOMAIN_KEY = "pm_service_trigger_observer.child.per_mgr.pre_drain_domain_probe"
_PRE_DRAIN_ATTR_KEY = "pm_service_trigger_observer.child.per_mgr.pre_drain_domain_value"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _per_mgr_domain(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract per_mgr pre-drain domain data from observer output step.

    v223 note: domain value is emitted as a direct pm_service_trigger_observer.*
    key=value line so it passes the child-script grep filter. v222 used
    A90_EXECNS_CNSS_PROC_* markers which were filtered out.
    Reads from the step file (not the truncated payload field).
    """
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "pre_drain_probe": "0",
        "pre_drain_attr_captured": "0",
        "domain_value": "",
        "pre_drain_pid": "",
    }
    run_dir = manifest.get("_run_dir", "")
    for step in steps:
        # Prefer the full file over the truncated payload field.
        text = ""
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            fpath = Path(run_dir) / step_file
            try:
                text = fpath.read_text(errors="replace")
            except OSError:
                pass
        if not text:
            text = step.get("payload", "") or ""
        for line in text.splitlines():
            line = line.strip()
            if line == f"{_PRE_DRAIN_DOMAIN_KEY}=1":
                result["pre_drain_probe"] = "1"
            if line.startswith("pm_service_trigger_observer.child.per_mgr.pre_drain_pid="):
                result["pre_drain_pid"] = line.split("=", 1)[1]
            if line.startswith("pm_service_trigger_observer.child.per_mgr.pre_drain_attr_current_captured="):
                result["pre_drain_attr_captured"] = line.split("=", 1)[1]
            if line.startswith(f"{_PRE_DRAIN_ATTR_KEY}="):
                result["domain_value"] = line.split("=", 1)[1].strip()
    return result


# ── Decision ──────────────────────────────────────────────────────────────

def decide_v1187(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1187-pm-per-mgr-domain-capture-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v222, then run V1187 live domain capture",
        )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = _per_mgr_domain(manifest)

    if gate.get("begin") != "1":
        return (
            "v1187-vndservice-gate-not-activated",
            False,
            (
                f"per_proxy_vndservice_gate.begin not found; "
                f"gate flag may be missing or helper is wrong version; "
                f"contract={contract}"
            ),
            f"verify helper v222 is deployed and {VNDSERVICE_GATE_FLAG} is in command",
        )

    gate_result = gate.get("result", "")
    poll_count = gate.get("poll_count", "?")
    elapsed_ms = gate.get("elapsed_ms", "?")

    pre_drain_captured = domain.get("pre_drain_attr_captured") == "1"
    domain_value = domain.get("domain_value", "")
    per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")
    per_proxy_skipped = contract.get("child.per_proxy.start_skipped", "?")

    if not pre_drain_captured:
        return (
            "v1187-per-mgr-domain-not-captured",
            False,
            (
                f"pre-drain attr/current capture failed; "
                f"pre_drain_probe={domain.get('pre_drain_probe')} "
                f"pre_drain_pid={domain.get('pre_drain_pid')} "
                f"per_mgr_obs={per_mgr_obs}; "
                f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            "per_mgr exited before pre-drain probe; "
            "check pre_drain_pid and whether per_mgr spawned at all",
        )

    return (
        "v1187-per-mgr-domain-captured",
        True,
        (
            f"per_mgr pre-drain domain captured: domain={domain_value!r}; "
            f"pre_drain_pid={domain.get('pre_drain_pid')} "
            f"per_mgr_obs={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}; "
            f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
        ),
        (
            "correlate domain_value with vendor_per_mgr.te SELinux policy; "
            "if domain=kernel, verify V490 policy allows transition to vendor_per_mgr; "
            "check dmesg for AVC denials around per_mgr exec time"
        ),
    )


# ── Summary ───────────────────────────────────────────────────────────────

def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = _per_mgr_domain(manifest)

    rows = [
        ["vndservice_gate_flag", VNDSERVICE_GATE_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["gate_begin", gate.get("begin", "")],
        ["gate_result", gate.get("result", "")],
        ["gate_open", gate.get("gate_open", "")],
        ["gate_poll_count", gate.get("poll_count", "")],
        ["gate_elapsed_ms", gate.get("elapsed_ms", "")],
        ["per_mgr_obs_at_probe",
         contract.get("child.per_mgr.post_start_observable", "")],
        ["per_proxy_skipped",
         contract.get("child.per_proxy.start_skipped", "")],
        ["per_mgr_pre_drain_probe", domain.get("pre_drain_probe", "")],
        ["per_mgr_pre_drain_pid", domain.get("pre_drain_pid", "")],
        ["per_mgr_pre_drain_attr_captured", domain.get("pre_drain_attr_captured", "")],
        ["per_mgr_domain_value", domain.get("domain_value", "")],
    ]
    lines = [
        "# V1187 PM Per-Mgr Domain Capture Observer",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## Per-Mgr Domain Capture State",
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
    manifest["cycle"] = "v1187"
    manifest["generated_at"] = _now_iso()
    manifest["vndservice_gate_flag"] = VNDSERVICE_GATE_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1187(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = _per_mgr_domain(manifest)
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
    manifest["vndservice_gate_poll_count"] = gate.get("poll_count", "")
    manifest["vndservice_gate_elapsed_ms"] = gate.get("elapsed_ms", "")
    manifest["per_mgr_obs_at_probe"] = (
        contract.get("child.per_mgr.post_start_observable", "")
    )
    manifest["per_proxy_skipped"] = contract.get("child.per_proxy.start_skipped", "")
    manifest["per_mgr_pre_drain_probe"] = domain.get("pre_drain_probe", "")
    manifest["per_mgr_pre_drain_pid"] = domain.get("pre_drain_pid", "")
    manifest["per_mgr_pre_drain_attr_captured"] = domain.get("pre_drain_attr_captured", "")
    manifest["per_mgr_domain_value"] = domain.get("domain_value", "")
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

    print(f"decision                        : {manifest['decision']}")
    print(f"pass                            : {manifest['pass']}")
    print(f"reason                          : {manifest['reason'][:200]}")
    print(f"next                            : {manifest['next_step']}")
    print(f"firmware_mounts_executed        : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed                 : {manifest['reboot_executed']}")
    print(f"gate_begin                      : {manifest['vndservice_gate_begin']}")
    print(f"gate_result                     : {manifest['vndservice_gate_result']}")
    print(f"gate_open                       : {manifest['vndservice_gate_open']}")
    print(f"gate_poll_count                 : {manifest['vndservice_gate_poll_count']}")
    print(f"gate_elapsed_ms                 : {manifest['vndservice_gate_elapsed_ms']}ms")
    print(f"per_mgr_obs_at_probe            : {manifest['per_mgr_obs_at_probe']}")
    print(f"per_proxy_skipped               : {manifest['per_proxy_skipped']}")
    print(f"per_mgr_pre_drain_probe         : {manifest['per_mgr_pre_drain_probe']}")
    print(f"per_mgr_pre_drain_pid           : {manifest['per_mgr_pre_drain_pid']}")
    print(f"per_mgr_pre_drain_attr_captured : {manifest['per_mgr_pre_drain_attr_captured']}")
    print(f"per_mgr_domain_value            : {manifest['per_mgr_domain_value']!r}")
    print(f"wifi_hal_start_executed         : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed           : {manifest['wifi_bringup_executed']}")
    print(f"manifest                        : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
