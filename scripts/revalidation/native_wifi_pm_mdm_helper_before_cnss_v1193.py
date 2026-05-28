#!/usr/bin/env python3
"""V1193 PM observer: mdm_helper before cnss_daemon for eSoC image transfer.

V1192 root cause: mdm_helper holds /dev/esoc-0 and blocks in esoc_dev_ioctl
(active eSoC ioctls), but per_mgr tries subsys_esoc0 open (triggered by
cnss-daemon modem peripheral request) while mdm_helper is still doing the
image transfer. The blocked open fails with a reference count mismatch
(subsystem_put esoc0 count:0) causing modem SSR at t=261s.

Fix: start mdm_helper BEFORE cnss_daemon so the eSoC image transfer begins
and MDM advances past mdm_subsys_powerup before per_mgr serves cnss modem
peripheral power-up requests. New helper v226 adds
--pm-observer-start-mdm-helper-before-cnss which polls for mdm_helper
esoc-0 fd (up to 30s) before spawning cnss_daemon.

Objective: observe mdm_helper esoc-0 fd, eSoC ioctls completing, GPIO 142
IRQ firing, ks spawning MHI pipe, and per_mgr subsys_esoc0 opening
successfully (enabling WLFW publication).

Does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

_ORIG_V1191_PATCH_DEFAULTS = v1191.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1193-pm-mdm-helper-before-cnss")
LATEST_POINTER = Path("tmp/wifi/latest-v1193-pm-mdm-helper-before-cnss.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "79f1ec51434c18a0bbcc3168a0a027d2e87ca2e7deac5ee63e5e8b7695b2d47b"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v226"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1193"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1193/pm-mdm-helper-before-cnss-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1193/pm-mdm-helper-before-cnss-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1193/pm-mdm-helper-before-cnss-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1193-"

MDM_BEFORE_CNSS_FLAG = "--pm-observer-start-mdm-helper-before-cnss"


def pm_mdm_before_cnss_child_command(args: Any) -> list[str]:
    """Add mdm-before-cnss flag to the V1191 policy-load command."""
    result = v1191._ORIG_VNDSERVICE_GATE_CMD(args)
    if v1191.POLICY_LOAD_FLAG not in result:
        result.append(v1191.POLICY_LOAD_FLAG)
    if MDM_BEFORE_CNSS_FLAG not in result:
        result.append(MDM_BEFORE_CNSS_FLAG)
    return result


def _mdm_early(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract mdm_helper early spawn evidence."""
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "esoc0_poll_count": "",
        "esoc0_found": "",
        "esoc0_wait_ms": "",
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
            for key in ("esoc0_poll_count", "esoc0_found", "esoc0_wait_ms"):
                prefix = f"pm_service_trigger_observer.child.mdm_helper_early.{key}="
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
    return result


def decide_v1193(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1193-pm-mdm-before-cnss-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "reboot, or Wi-Fi action executed",
            "deploy helper v226, then run V1193 live mdm-before-cnss gate",
        )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)

    if gate.get("begin") != "1":
        return (
            "v1193-vndservice-gate-not-activated",
            False,
            "per_proxy_vndservice_gate.begin not found; "
            "verify helper v226 is deployed and flags are correct",
            "check helper version and command flags",
        )

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1193-policy-load-failed",
            False,
            f"precompiled policy load did not pass: {policy_result!r}",
            "verify selinuxfs is mounted and vendor precompiled_sepolicy exists",
        )

    esoc0_found = mdm_early.get("esoc0_found", "") == "1"
    esoc0_wait_ms = mdm_early.get("esoc0_wait_ms", "?")

    if not esoc0_found:
        return (
            "v1193-mdm-helper-esoc0-not-found",
            False,
            (
                f"mdm_helper early spawn: esoc0_found=0 after "
                f"{mdm_early.get('esoc0_poll_count', '?')} polls "
                f"({esoc0_wait_ms}ms); mdm_helper did not open esoc-0"
            ),
            (
                "check mdm_helper SELinux domain and esoc-0 node existence; "
                "extend poll timeout if needed"
            ),
        )

    # Check if subsys_esoc0 was eventually opened (post-mdm_helper window)
    steps = manifest.get("steps", [])
    run_dir = manifest.get("_run_dir", "")
    per_mgr_esoc0_count = 0
    mdm_helper_mhi_count = 0
    for step in steps:
        text = ""
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            try:
                text = (Path(run_dir) / step_file).read_text(errors="replace")
            except OSError:
                pass
        if not text:
            text = step.get("payload", "") or ""
        for line in text.splitlines():
            line = line.strip()
            if "after_per_proxy_per_mgr_subsys_esoc0.count=" in line:
                try:
                    per_mgr_esoc0_count = max(per_mgr_esoc0_count,
                                             int(line.split("=", 1)[1]))
                except ValueError:
                    pass
            if "mdm_helper_esoc_observer.fd_esoc0_count.window=" in line:
                pass
            if "fd_match.*mdm_helper_mhi_pipe.count=" in line or \
               "mdm_helper_mhi_pipe.count=" in line or \
               "fd_mhi_pipe_count.window=" in line:
                try:
                    val = int(line.split("=", 1)[1])
                    if val > 0:
                        mdm_helper_mhi_count = val
                except ValueError:
                    pass

    if per_mgr_esoc0_count > 0:
        return (
            "v1193-per-mgr-subsys-esoc0-open",
            True,
            (
                f"esoc0_found after {esoc0_wait_ms}ms; "
                f"per_mgr subsys_esoc0 count={per_mgr_esoc0_count}; "
                f"mhi_pipe_count={mdm_helper_mhi_count}"
            ),
            "per_mgr opened subsys_esoc0 — check WLFW/BDF/wlan0 in evidence",
        )

    return (
        "v1193-mdm-helper-esoc0-found-subsys-still-blocked",
        False,
        (
            f"mdm_helper got esoc0 after {esoc0_wait_ms}ms "
            f"(poll_count={mdm_early.get('esoc0_poll_count', '?')}); "
            f"but per_mgr subsys_esoc0 still 0; "
            f"mhi_pipe_count={mdm_helper_mhi_count}"
        ),
        (
            "mdm_helper eSoC ioctls active but image transfer may not be complete; "
            "check GPIO 142 IRQ count, ks process, MHI pipe in full evidence"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)

    rows = [
        ["policy_load_flag", v1191.POLICY_LOAD_FLAG],
        ["mdm_before_cnss_flag", MDM_BEFORE_CNSS_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["policy_load_result", policy.get("result", "")],
        ["policy_load_bytes", policy.get("bytes", "")],
        ["gate_result", gate.get("result", "")],
        ["gate_open", gate.get("gate_open", "")],
        ["per_mgr_domain", domain.get("domain_value", "")],
        ["mdm_helper_early_esoc0_poll_count", mdm_early.get("esoc0_poll_count", "")],
        ["mdm_helper_early_esoc0_found", mdm_early.get("esoc0_found", "")],
        ["mdm_helper_early_esoc0_wait_ms", mdm_early.get("esoc0_wait_ms", "")],
    ]
    lines = [
        "# V1193 PM Observer: mdm_helper Before cnss_daemon",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## mdm_helper Early Spawn + eSoC Gate",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def patch_defaults() -> None:
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180

    v1191.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1191.LATEST_POINTER = LATEST_POINTER
    v1191.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1191.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1191.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1191.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1191.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1191.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1191.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1191_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1183.pm_per_proxy_vndservice_gate_child_command = pm_mdm_before_cnss_child_command
    v1106.pm_cnss_child_command = pm_mdm_before_cnss_child_command


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
    manifest["cycle"] = "v1193"
    manifest["generated_at"] = _now_iso()
    manifest["mdm_before_cnss_flag"] = MDM_BEFORE_CNSS_FLAG
    manifest["policy_load_flag"] = v1191.POLICY_LOAD_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1193(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["policy_load_bytes"] = policy.get("bytes", "")
    manifest["gate_begin"] = gate.get("begin") == "1"
    manifest["gate_result"] = gate.get("result", "")
    manifest["gate_open"] = gate.get("gate_open") == "1"
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_early_esoc0_poll_count"] = mdm_early.get("esoc0_poll_count", "")
    manifest["mdm_helper_early_esoc0_found"] = mdm_early.get("esoc0_found", "") == "1"
    manifest["mdm_helper_early_esoc0_wait_ms"] = mdm_early.get("esoc0_wait_ms", "")
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                              : {manifest['decision']}")
    print(f"pass                                  : {manifest['pass']}")
    print(f"reason                                : {manifest['reason'][:200]}")
    print(f"next                                  : {manifest['next_step']}")
    print(f"firmware_mounts_executed              : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed                       : {manifest['reboot_executed']}")
    print(f"policy_load_result                    : {manifest['policy_load_result']}")
    print(f"gate_open                             : {manifest['gate_open']}")
    print(f"per_mgr_domain                        : {manifest['per_mgr_domain']!r}")
    print(f"mdm_helper_early_esoc0_found          : {manifest['mdm_helper_early_esoc0_found']}")
    print(f"mdm_helper_early_esoc0_poll_count     : {manifest['mdm_helper_early_esoc0_poll_count']}")
    print(f"mdm_helper_early_esoc0_wait_ms        : {manifest['mdm_helper_early_esoc0_wait_ms']}")
    print(f"wifi_hal_start_executed               : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed                 : {manifest['wifi_bringup_executed']}")
    print(f"manifest                              : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
