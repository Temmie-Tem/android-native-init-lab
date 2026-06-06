#!/usr/bin/env python3
"""V1195 PM observer: subsys_esoc0 open with mdm3 restart_level=RELATED.

V1194 root cause: subsys_esoc0 open triggered device unexpected reboot because
mdm3/subsys9 has restart_level=SYSTEM. When MDM SSR fires (e.g. firmware
transfer failure during mdm_subsys_powerup), the kernel does a full system
restart. GPIO 142 polling loop output was lost (page cache not synced).

Fix: helper v229 writes restart_level=RELATED to
/sys/bus/msm_subsys/devices/subsys9/restart_level before forking the
subsys_esoc0 child. With RELATED, MDM SSR causes only subsystem-coupled
restart (no full device reboot), allowing GPIO 142 polling to continue.

Expected outcomes:
- v1195-gpio142-fired: GPIO 142 fired → MDM booted → check WLFW/BDF/wlan0
- v1195-subsys-esoc0-open-gpio142-still-silent: subsys_esoc0 opened, GPIO 142
  silent after 300s; MDM SSR may have occurred but device stayed up
- v1195-restart-level-set-failed: sysfs write to restart_level failed
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

_ORIG_V1193_PATCH_DEFAULTS = v1193.patch_defaults

DEFAULT_OUT_DIR = Path("tmp/wifi/v1195-pm-mdm-esoc-power-on-related")
LATEST_POINTER = Path("tmp/wifi/latest-v1195-pm-mdm-esoc-power-on-related.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "aac9094a0c583e51f5fadca6a8451599ce6148a5f7c1a9f92e3a66b2310806ea"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v229"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1195"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1195/pm-mdm-esoc-power-on-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1195/pm-mdm-esoc-power-on-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1195/pm-mdm-esoc-power-on-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1195-"

SUBSYS_ESOC0_FLAG = "--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc"
RESTART_LEVEL_FLAG = "--pm-observer-set-mdm3-restart-level-related"


def pm_mdm_esoc_power_on_v1195_child_command(args: Any) -> list[str]:
    """Add subsys_esoc0 trigger + restart_level=RELATED flag to the V1193 command."""
    result = v1193.v1191._ORIG_VNDSERVICE_GATE_CMD(args)
    if v1191.POLICY_LOAD_FLAG not in result:
        result.append(v1191.POLICY_LOAD_FLAG)
    if v1193.MDM_BEFORE_CNSS_FLAG not in result:
        result.append(v1193.MDM_BEFORE_CNSS_FLAG)
    if SUBSYS_ESOC0_FLAG not in result:
        result.append(SUBSYS_ESOC0_FLAG)
    if RESTART_LEVEL_FLAG not in result:
        result.append(RESTART_LEVEL_FLAG)
    return result


def _mdm_power_on(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract MDM power-on trigger evidence from observer output."""
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "begin": "",
        "path": "",
        "restart_level_set": "",
        "restart_level_write_ok": "",
        "gpio142_before": "",
        "gpio142_after": "",
        "gpio142_fired": "",
        "gpio142_elapsed_ms": "",
        "child_status": "",
        "restart_level_restored": "",
        "reboot_required": "",
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
            for key in result:
                prefix = f"pm_observer_mdm_power_on.{key}="
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
    return result


def _mdm_early(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1193._mdm_early(manifest)


def decide_v1195(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1195-pm-mdm-esoc-power-on-related-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, "
            "subsys_esoc0 open, restart_level change, reboot, or Wi-Fi action executed",
            "deploy helper v229, then run V1195 live MDM power-on gate",
        )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)
    power_on = _mdm_power_on(manifest)

    if gate.get("begin") != "1":
        return (
            "v1195-vndservice-gate-not-activated",
            False,
            "vndservice gate not activated; verify helper v229 and flags",
            "check helper version and command flags",
        )

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1195-policy-load-failed",
            False,
            f"precompiled policy load failed: {policy_result!r}",
            "verify selinuxfs is mounted and vendor precompiled_sepolicy exists",
        )

    esoc0_found = mdm_early.get("esoc0_found", "") == "1"
    if not esoc0_found:
        return (
            "v1195-mdm-helper-esoc0-not-found",
            False,
            "mdm_helper did not open esoc-0; subsys_esoc0 trigger not reached",
            "check mdm_helper SELinux domain and esoc-0 node",
        )

    power_begin = power_on.get("begin", "") == "1"
    if not power_begin:
        return (
            "v1195-mdm-power-on-not-triggered",
            False,
            "pm_observer_mdm_power_on block not reached; check helper flag",
            f"verify {SUBSYS_ESOC0_FLAG} is in command",
        )

    rl_ok = power_on.get("restart_level_write_ok", "") == "1"
    rl_set = power_on.get("restart_level_set", "")
    if not rl_ok:
        return (
            "v1195-restart-level-set-failed",
            False,
            f"restart_level sysfs write failed: restart_level_set={rl_set!r}; "
            f"device reboot risk remains",
            "check sysfs path /sys/bus/msm_subsys/devices/subsys9/restart_level",
        )

    gpio_fired = power_on.get("gpio142_fired", "") == "1"
    gpio_before = power_on.get("gpio142_before", "?")
    gpio_after = power_on.get("gpio142_after", "?")
    elapsed_ms = power_on.get("gpio142_elapsed_ms", "?")
    child_status = power_on.get("child_status", "")
    subsys_opened = "subsys_esoc0_opened=1" in child_status

    if not subsys_opened and not power_on.get("end", ""):
        return (
            "v1195-device-rebooted-before-polling",
            False,
            "gpio polling output absent and end marker missing; "
            "device likely rebooted despite restart_level=RELATED; "
            "check if subsys0/mss restart_level=SYSTEM caused cascade",
            "check mss restart_level; consider changing subsys0 to RELATED also",
        )

    if not subsys_opened:
        return (
            "v1195-subsys-esoc0-open-failed",
            False,
            f"subsys_esoc0 open failed: child_status={child_status!r}",
            "check subsys_esoc0 node permissions and kernel state",
        )

    if gpio_fired:
        return (
            "v1195-gpio142-fired",
            True,
            (
                f"GPIO 142 fired: before={gpio_before} after={gpio_after} "
                f"elapsed={elapsed_ms}ms; MDM powered on and booted; "
                f"check WLFW/BDF/wlan0 in evidence"
            ),
            "GPIO 142 confirmed — check MHI device, ks, WLFW, wlan0",
        )

    return (
        "v1195-subsys-esoc0-open-gpio142-still-silent",
        False,
        (
            f"subsys_esoc0 opened but GPIO 142 still silent after {elapsed_ms}ms: "
            f"before={gpio_before} after={gpio_after}; "
            f"MDM hardware powered but did not reach ready state; "
            f"mdm_helper firmware transfer may be incomplete or failing"
        ),
        (
            "check ESOC_WAIT_FOR_REQ state in mdm_helper; "
            "verify firmware files accessible from vendor mount; "
            "check ESOC kernel events in dmesg after reboot"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)
    power_on = _mdm_power_on(manifest)

    rows = [
        ["policy_load_flag", v1191.POLICY_LOAD_FLAG],
        ["mdm_before_cnss_flag", v1193.MDM_BEFORE_CNSS_FLAG],
        ["subsys_esoc0_flag", SUBSYS_ESOC0_FLAG],
        ["restart_level_flag", RESTART_LEVEL_FLAG],
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["policy_load_result", policy.get("result", "")],
        ["gate_result", gate.get("result", "")],
        ["per_mgr_domain", domain.get("domain_value", "")],
        ["mdm_helper_esoc0_found", mdm_early.get("esoc0_found", "")],
        ["mdm_helper_esoc0_wait_ms", mdm_early.get("esoc0_wait_ms", "")],
        ["restart_level_set", power_on.get("restart_level_set", "")],
        ["restart_level_write_ok", power_on.get("restart_level_write_ok", "")],
        ["power_on_begin", power_on.get("begin", "")],
        ["subsys_esoc0_child_status", power_on.get("child_status", "")[:80]],
        ["gpio142_before", power_on.get("gpio142_before", "")],
        ["gpio142_after", power_on.get("gpio142_after", "")],
        ["gpio142_fired", power_on.get("gpio142_fired", "")],
        ["gpio142_elapsed_ms", power_on.get("gpio142_elapsed_ms", "")],
        ["restart_level_restored", power_on.get("restart_level_restored", "")],
        ["reboot_required", power_on.get("reboot_required", "")],
    ]
    lines = [
        "# V1195 PM Observer: subsys_esoc0 Open + mdm3 restart_level=RELATED",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## MDM Power-On Gate (restart_level=RELATED)",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def patch_defaults() -> None:
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180

    v1193.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1193.LATEST_POINTER = LATEST_POINTER
    v1193.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1193.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1193.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1193.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1193.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1193.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1193.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1193_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1183.pm_per_proxy_vndservice_gate_child_command = pm_mdm_esoc_power_on_v1195_child_command
    v1106.pm_cnss_child_command = pm_mdm_esoc_power_on_v1195_child_command


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
    manifest["cycle"] = "v1195"
    manifest["generated_at"] = _now_iso()
    manifest["subsys_esoc0_flag"] = SUBSYS_ESOC0_FLAG
    manifest["restart_level_flag"] = RESTART_LEVEL_FLAG
    manifest["mdm_before_cnss_flag"] = v1193.MDM_BEFORE_CNSS_FLAG
    manifest["policy_load_flag"] = v1191.POLICY_LOAD_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1195(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = _mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["gate_open"] = gate.get("gate_open") == "1"
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_esoc0_found"] = mdm_early.get("esoc0_found", "") == "1"
    manifest["mdm_helper_esoc0_wait_ms"] = mdm_early.get("esoc0_wait_ms", "")
    manifest["restart_level_set"] = power_on.get("restart_level_set", "")
    manifest["restart_level_write_ok"] = power_on.get("restart_level_write_ok", "") == "1"
    manifest["power_on_begin"] = power_on.get("begin", "") == "1"
    manifest["subsys_esoc0_opened"] = "subsys_esoc0_opened=1" in power_on.get("child_status", "")
    manifest["gpio142_fired"] = power_on.get("gpio142_fired", "") == "1"
    manifest["gpio142_before"] = power_on.get("gpio142_before", "")
    manifest["gpio142_after"] = power_on.get("gpio142_after", "")
    manifest["gpio142_elapsed_ms"] = power_on.get("gpio142_elapsed_ms", "")
    manifest["restart_level_restored"] = power_on.get("restart_level_restored", "")
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                         : {manifest['decision']}")
    print(f"pass                             : {manifest['pass']}")
    print(f"reason                           : {manifest['reason'][:200]}")
    print(f"next                             : {manifest['next_step']}")
    print(f"firmware_mounts_executed         : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed                  : {manifest['reboot_executed']}")
    print(f"policy_load_result               : {manifest['policy_load_result']}")
    print(f"gate_open                        : {manifest['gate_open']}")
    print(f"per_mgr_domain                   : {manifest['per_mgr_domain']!r}")
    print(f"mdm_helper_esoc0_found           : {manifest['mdm_helper_esoc0_found']}")
    print(f"mdm_helper_esoc0_wait_ms         : {manifest['mdm_helper_esoc0_wait_ms']}")
    print(f"restart_level_set                : {manifest['restart_level_set']!r}")
    print(f"restart_level_write_ok           : {manifest['restart_level_write_ok']}")
    print(f"power_on_begin                   : {manifest['power_on_begin']}")
    print(f"subsys_esoc0_opened              : {manifest['subsys_esoc0_opened']}")
    print(f"gpio142_fired                    : {manifest['gpio142_fired']}")
    print(f"gpio142_before                   : {manifest['gpio142_before']}")
    print(f"gpio142_after                    : {manifest['gpio142_after']}")
    print(f"gpio142_elapsed_ms               : {manifest['gpio142_elapsed_ms']}")
    print(f"restart_level_restored           : {manifest['restart_level_restored']!r}")
    print(f"wifi_hal_start_executed          : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed            : {manifest['wifi_bringup_executed']}")
    print(f"manifest                         : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
