#!/usr/bin/env python3
"""V1189 PM per_mgr domain transition fix live observer.

Helper v224 adds a setcurrent write in the child process before exec for
per_mgr/per_proxy/per_proxy_helper: writes u:r:vendor_per_mgr:s0 to
/proc/self/attr/current (dynamic relabeling). In permissive mode the
dyntransition AVC is logged but not enforced, so the running domain becomes
vendor_per_mgr before execv(). The stock type_transition rule then keeps
per_mgr in vendor_per_mgr after exec.

V1188 root cause: V490 policy has no 'allow kernel vendor_per_mgr:process
transition', so exec-context write alone was not enough. The setcurrent
approach bypasses this missing rule by relabeling before exec.

Objective: validate per_mgr_domain_value='u:r:vendor_per_mgr:s0' via
pre-drain attr/current capture, then check whether per_mgr opens
/dev/vndbinder (vndservice gate passes).

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

_ORIG_V1183_PATCH_DEFAULTS = v1183.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1189-pm-per-mgr-domain-fix")
LATEST_POINTER = Path("tmp/wifi/latest-v1189-pm-per-mgr-domain-fix.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "5c2af22eb0a331e9b12470a5ae77e3be2c8d6a1809e48092b412ff9f82005a5d"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v224"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1189"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1189/pm-per-mgr-domain-fix-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1189/pm-per-mgr-domain-fix-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1189/pm-per-mgr-domain-fix-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1189-"

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG
PPH_DELTA_OPTION = v1183.PPH_DELTA_OPTION

_PRE_DRAIN_DOMAIN_KEY = "pm_service_trigger_observer.child.per_mgr.pre_drain_domain_probe"
_PRE_DRAIN_ATTR_KEY = "pm_service_trigger_observer.child.per_mgr.pre_drain_domain_value"

EXPECTED_DOMAIN = "u:r:vendor_per_mgr:s0"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _per_mgr_domain(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract per_mgr pre-drain domain data from observer output step.

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

def decide_v1189(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1189-pm-per-mgr-domain-fix-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v224, then run V1189 live domain fix validation",
        )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = _per_mgr_domain(manifest)

    if gate.get("begin") != "1":
        return (
            "v1189-vndservice-gate-not-activated",
            False,
            (
                f"per_proxy_vndservice_gate.begin not found; "
                f"gate flag may be missing or helper is wrong version; "
                f"contract={contract}"
            ),
            f"verify helper v224 is deployed and {VNDSERVICE_GATE_FLAG} is in command",
        )

    gate_result = gate.get("result", "")
    poll_count = gate.get("poll_count", "?")
    elapsed_ms = gate.get("elapsed_ms", "?")
    gate_open = gate.get("gate_open", "0") == "1"

    domain_value = domain.get("domain_value", "")
    pre_drain_captured = domain.get("pre_drain_attr_captured") == "1"
    per_mgr_obs = contract.get("child.per_mgr.post_start_observable", "?")
    per_proxy_skipped = contract.get("child.per_proxy.start_skipped", "?")

    if not pre_drain_captured:
        return (
            "v1189-per-mgr-domain-not-captured",
            False,
            (
                f"pre-drain attr/current capture failed; "
                f"pre_drain_probe={domain.get('pre_drain_probe')} "
                f"pre_drain_pid={domain.get('pre_drain_pid')} "
                f"per_mgr_obs={per_mgr_obs}; "
                f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            "per_mgr exited before pre-drain probe; check whether v224 deployed",
        )

    domain_fixed = domain_value == EXPECTED_DOMAIN
    if not domain_fixed:
        return (
            "v1189-per-mgr-domain-still-kernel",
            False,
            (
                f"setcurrent fix did not land: domain={domain_value!r} "
                f"(expected {EXPECTED_DOMAIN!r}); "
                f"pre_drain_pid={domain.get('pre_drain_pid')} "
                f"per_mgr_obs={per_mgr_obs}; "
                f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            (
                "check selinux_current.ok in full child output; "
                "verify permissive mode was active during run"
            ),
        )

    if not gate_open:
        return (
            "v1189-per-mgr-domain-fixed-gate-still-closed",
            False,
            (
                f"domain fix confirmed: domain={domain_value!r}; "
                f"but vndservice gate still closed after {elapsed_ms}ms "
                f"(poll_count={poll_count}); per_mgr may still exit early; "
                f"per_mgr_obs={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}"
            ),
            (
                "domain is now correct — next blocker is per_mgr runtime behavior "
                "in vendor_per_mgr domain: check vndbinder open and "
                "vndservicemanager registration"
            ),
        )

    return (
        "v1189-per-mgr-domain-fixed-gate-open",
        True,
        (
            f"domain fix confirmed AND vndservice gate open: "
            f"domain={domain_value!r}; "
            f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms; "
            f"per_mgr_obs={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}"
        ),
        (
            "per_mgr now runs in vendor_per_mgr domain and registered with "
            "vndservicemanager; next is per_proxy spawn and PM subsystem open"
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
        ["expected_domain", EXPECTED_DOMAIN],
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
        ["domain_fixed", str(domain.get("domain_value", "") == EXPECTED_DOMAIN)],
    ]
    lines = [
        "# V1189 PM Per-Mgr Domain Transition Fix Observer",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## Per-Mgr Domain Fix State",
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
    manifest["cycle"] = "v1189"
    manifest["generated_at"] = _now_iso()
    manifest["vndservice_gate_flag"] = VNDSERVICE_GATE_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1189(args, manifest)
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
    manifest["per_mgr_domain_fixed"] = domain.get("domain_value", "") == EXPECTED_DOMAIN
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
    print(f"per_mgr_domain_fixed            : {manifest['per_mgr_domain_fixed']}")
    print(f"wifi_hal_start_executed         : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed           : {manifest['wifi_bringup_executed']}")
    print(f"manifest                        : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
