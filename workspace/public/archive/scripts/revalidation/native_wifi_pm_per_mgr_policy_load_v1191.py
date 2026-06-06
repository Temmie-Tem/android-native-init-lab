#!/usr/bin/env python3
"""V1191 PM per_mgr domain fix via precompiled policy load live observer.

V1190 root cause: no SELinux policy is loaded when the PM trigger observer
runs. write_selinux_attr("exec"/"current") fails with EINVAL because
security_context_to_sid() cannot resolve u:r:vendor_per_mgr:s0 without a
loaded policy. Per_mgr always runs in kernel domain.

Fix: helper v225 adds --pm-observer-load-precompiled-policy. Before spawning
PM children, the helper loads /vendor/etc/selinux/precompiled_sepolicy to
/sys/fs/selinux/load and writes 0 to enforce (permissive mode). With a policy
loaded, write_selinux_attr("exec", "u:r:vendor_per_mgr:s0") succeeds and the
exec domain transition from kernel to vendor_per_mgr proceeds in permissive
mode (AVC denial logged but not enforced).

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
import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

_ORIG_V1189_PATCH_DEFAULTS = v1189.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1191-pm-per-mgr-policy-load")
LATEST_POINTER = Path("tmp/wifi/latest-v1191-pm-per-mgr-policy-load.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "cfe70c8879ab956670d8502ffd0d51c7544c26dd2a641db12c29129613d40664"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v225"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1191"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1191/pm-per-mgr-policy-load-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1191/pm-per-mgr-policy-load-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1191/pm-per-mgr-policy-load-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1191-"

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG
POLICY_LOAD_FLAG = "--pm-observer-load-precompiled-policy"

_ORIG_VNDSERVICE_GATE_CMD = None


def pm_per_mgr_policy_load_child_command(args: Any) -> list[str]:
    """Build helper command: add policy load flag to the vndservice gate command."""
    result = _ORIG_VNDSERVICE_GATE_CMD(args)
    if POLICY_LOAD_FLAG not in result:
        result.append(POLICY_LOAD_FLAG)
    return result


def _policy_load(manifest: dict[str, Any]) -> dict[str, str]:
    """Extract policy load result from observer output steps."""
    steps = manifest.get("steps", [])
    result: dict[str, str] = {
        "result": "",
        "bytes": "",
        "enforce_written": "",
        "end": "",
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
            for key in ("result", "bytes", "enforce_written", "end"):
                prefix = f"pm_service_trigger_observer.policy_load.{key}="
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
    return result


def decide_v1191(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1191-pm-per-mgr-policy-load-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v225, then run V1191 live policy-load domain fix",
        )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = _policy_load(manifest)

    if gate.get("begin") != "1":
        return (
            "v1191-vndservice-gate-not-activated",
            False,
            (
                f"per_proxy_vndservice_gate.begin not found; "
                f"gate flag may be missing or helper is wrong version; "
                f"contract={contract}"
            ),
            f"verify helper v225 is deployed and {VNDSERVICE_GATE_FLAG} is in command",
        )

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1191-policy-load-failed",
            False,
            (
                f"precompiled policy load did not pass: policy_result={policy_result!r}; "
                f"per_mgr_domain={domain.get('domain_value')!r}"
            ),
            (
                "check pm_service_trigger_observer.policy_load.* fields; "
                "verify selinuxfs is mounted and vendor precompiled_sepolicy exists"
            ),
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
            "v1191-per-mgr-domain-not-captured",
            False,
            (
                f"policy_load={policy_result}; "
                f"pre-drain attr/current capture failed; "
                f"pre_drain_probe={domain.get('pre_drain_probe')} "
                f"pre_drain_pid={domain.get('pre_drain_pid')} "
                f"per_mgr_obs={per_mgr_obs}; "
                f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            "per_mgr exited before pre-drain probe; check full child output",
        )

    expected = v1189.EXPECTED_DOMAIN
    domain_fixed = domain_value == expected
    if not domain_fixed:
        return (
            "v1191-per-mgr-domain-still-kernel",
            False,
            (
                f"policy_load={policy_result} but domain still wrong: "
                f"domain={domain_value!r} (expected {expected!r}); "
                f"pre_drain_pid={domain.get('pre_drain_pid')} "
                f"per_mgr_obs={per_mgr_obs}; "
                f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms"
            ),
            (
                "check selinux_current.ok and selinux_exec.ok in full child output; "
                "verify enforce=0 was written and policy bytes > 0"
            ),
        )

    if not gate_open:
        return (
            "v1191-per-mgr-domain-fixed-gate-still-closed",
            False,
            (
                f"domain fix confirmed: domain={domain_value!r}; "
                f"but vndservice gate still closed after {elapsed_ms}ms "
                f"(poll_count={poll_count}); per_mgr may still exit early; "
                f"per_mgr_obs={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}"
            ),
            (
                "domain is now correct — next blocker is per_mgr runtime behavior "
                "in vendor_per_mgr domain: check vndbinder open, "
                "vndservicemanager registration, and exit reason"
            ),
        )

    return (
        "v1191-per-mgr-domain-fixed-gate-open",
        True,
        (
            f"policy load and domain fix confirmed AND vndservice gate open: "
            f"domain={domain_value!r}; "
            f"gate_result={gate_result} poll_count={poll_count} elapsed_ms={elapsed_ms}ms; "
            f"per_mgr_obs={per_mgr_obs} per_proxy_skipped={per_proxy_skipped}"
        ),
        (
            "per_mgr now runs in vendor_per_mgr domain and registered with "
            "vndservicemanager; next is per_proxy spawn and PM subsystem open"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = _policy_load(manifest)

    rows = [
        ["policy_load_flag", POLICY_LOAD_FLAG],
        ["vndservice_gate_flag", VNDSERVICE_GATE_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["expected_domain", v1189.EXPECTED_DOMAIN],
        ["policy_load_result", policy.get("result", "")],
        ["policy_load_bytes", policy.get("bytes", "")],
        ["policy_load_enforce_written", policy.get("enforce_written", "")],
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
        ["domain_fixed",
         str(domain.get("domain_value", "") == v1189.EXPECTED_DOMAIN)],
    ]
    lines = [
        "# V1191 PM Per-Mgr Policy Load + Domain Fix Observer",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## Policy Load + Domain Fix State",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def patch_defaults() -> None:
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180

    v1189.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1189.LATEST_POINTER = LATEST_POINTER
    v1189.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1189.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1189.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1189.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1189.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1189.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1189.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1189_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    global _ORIG_VNDSERVICE_GATE_CMD
    _ORIG_VNDSERVICE_GATE_CMD = v1183.pm_per_proxy_vndservice_gate_child_command
    v1183.pm_per_proxy_vndservice_gate_child_command = pm_per_mgr_policy_load_child_command
    v1106.pm_cnss_child_command = pm_per_mgr_policy_load_child_command


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    patch_defaults()
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1191"
    manifest["generated_at"] = _now_iso()
    manifest["vndservice_gate_flag"] = VNDSERVICE_GATE_FLAG
    manifest["policy_load_flag"] = POLICY_LOAD_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1191(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    contract = v1183._pm_contract(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = _policy_load(manifest)
    post = v1183._post_pm(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["policy_load_bytes"] = policy.get("bytes", "")
    manifest["policy_load_enforce_written"] = policy.get("enforce_written", "")
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
    manifest["per_mgr_domain_fixed"] = (
        domain.get("domain_value", "") == v1189.EXPECTED_DOMAIN
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

    print(f"decision                        : {manifest['decision']}")
    print(f"pass                            : {manifest['pass']}")
    print(f"reason                          : {manifest['reason'][:200]}")
    print(f"next                            : {manifest['next_step']}")
    print(f"firmware_mounts_executed        : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed                 : {manifest['reboot_executed']}")
    print(f"policy_load_result              : {manifest['policy_load_result']}")
    print(f"policy_load_bytes               : {manifest['policy_load_bytes']}")
    print(f"policy_load_enforce_written     : {manifest['policy_load_enforce_written']}")
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
