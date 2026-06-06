#!/usr/bin/env python3
"""V1198 PM observer: subsys_esoc0 open + RELATED restart_level + mdm_helper fd/wchan listing.

V1197 root cause: --pm-observer-trigger-pcie-enumerate writes to the PCIe RC1
debug/enumerate sysfs node before the subsys_esoc0 fork. This write triggers a
PCIe enumeration on a link that may not be ready, causing a kernel panic / full
device reboot before the 300s GPIO poll window can run.

Fix: remove --pm-observer-trigger-pcie-enumerate. The collector now also uses
tail -f on the helper's CHILD_LOG so that pm_observer_mdm_power_on status lines
reach the host in real-time, even if the device reboots during observation.

V1197 also confirmed that observer output is only captured if the collector's
child_summary runs. With tail -f streaming added to v1106 collector, any output
written to CHILD_LOG is forwarded to serial immediately and available in the
observer step payload regardless of clean exit.

Goal: observe whether mdm_helper opens /dev/mhi* after ESOC_REQ_IMG, and
classify mdm_helper thread wchans during the 300s GPIO poll window.
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

DEFAULT_OUT_DIR = Path("tmp/wifi/v1198-pm-mdm-esoc-power-on-no-pcie")
LATEST_POINTER = Path(
    "tmp/wifi/latest-v1198-pm-mdm-esoc-power-on-no-pcie.txt"
)
DEFAULT_EXECNS_HELPER_SHA256 = (
    "a450e8274745144c23efbd57d56d51cce701391a8f919bc11be2994f4841b9df"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v237"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1198"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1198/pm-mdm-esoc-power-on-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1198/pm-mdm-esoc-power-on-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1198/pm-mdm-esoc-power-on-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1198-"

SUBSYS_ESOC0_FLAG = "--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc"
RESTART_LEVEL_FLAG = "--pm-observer-set-mdm3-restart-level-related"


def pm_mdm_esoc_power_on_v1198_child_command(args: Any) -> list[str]:
    result = v1193.v1191._ORIG_VNDSERVICE_GATE_CMD(args)
    if v1191.POLICY_LOAD_FLAG not in result:
        result.append(v1191.POLICY_LOAD_FLAG)
    if v1193.MDM_BEFORE_CNSS_FLAG not in result:
        result.append(v1193.MDM_BEFORE_CNSS_FLAG)
    if SUBSYS_ESOC0_FLAG not in result:
        result.append(SUBSYS_ESOC0_FLAG)
    if RESTART_LEVEL_FLAG not in result:
        result.append(RESTART_LEVEL_FLAG)
    # PCIe enumerate flag intentionally omitted — caused full device reboot in V1197
    return result


def _mdm_power_on(manifest: dict[str, Any]) -> dict[str, Any]:
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "begin": "",
        "restart_level_set": "",
        "restart_level_write_ok": "",
        "gpio142_before": "",
        "gpio142_after": "",
        "gpio142_fired": "",
        "gpio142_elapsed_ms": "",
        "child_status": "",
        "reboot_required": "",
        "end": "",
    }
    status_entries: list[dict[str, str]] = []
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
        current_status: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            for key in result:
                prefix = f"pm_observer_mdm_power_on.{key}="
                if line.startswith(prefix):
                    result[key] = line.split("=", 1)[1].strip()
            # collect status snapshots (v237: 8 fields)
            for skey in (
                "elapsed_ms",
                "gpio142_count",
                "mdm3_state",
                "mdm3_crash_count",
                "child_wchan",
                "mhi_dev_count",
                "mdm_helper_wchans",
                "mdm_helper_fds",
            ):
                prefix = f"pm_observer_mdm_power_on.status.{skey}="
                if line.startswith(prefix):
                    current_status[skey] = line.split("=", 1)[1].strip()
                    # flush when all 8 fields present
                    if len(current_status) == 8:
                        status_entries.append(dict(current_status))
                        current_status = {}
    result["_status_entries"] = status_entries  # type: ignore[assignment]
    return result


def decide_v1198(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1198-pm-mdm-esoc-power-on-no-pcie-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy helper v237 (if needed), then run V1198 live gate",
        )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)

    if gate.get("begin") != "1":
        return (
            "v1198-vndservice-gate-not-activated",
            False,
            "vndservice gate not activated; verify helper v237 and flags",
            "check helper version and command flags",
        )

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1198-policy-load-failed",
            False,
            f"precompiled policy load failed: {policy_result!r}",
            "verify selinuxfs is mounted and vendor precompiled_sepolicy exists",
        )

    esoc0_found = mdm_early.get("esoc0_found", "") == "1"
    if not esoc0_found:
        return (
            "v1198-mdm-helper-esoc0-not-found",
            False,
            "mdm_helper did not open esoc-0; subsys_esoc0 trigger not reached",
            "check mdm_helper SELinux domain and esoc-0 node",
        )

    power_begin = power_on.get("begin", "") == "1"
    if not power_begin:
        return (
            "v1198-mdm-power-on-not-triggered",
            False,
            "pm_observer_mdm_power_on block not reached",
            f"verify {SUBSYS_ESOC0_FLAG} is in command",
        )

    rl_ok = power_on.get("restart_level_write_ok", "") == "1"
    if not rl_ok:
        return (
            "v1198-restart-level-set-failed",
            False,
            "restart_level sysfs write failed",
            "check /sys/bus/msm_subsys/devices/subsys9/restart_level",
        )

    status_entries = power_on.get("_status_entries", [])
    gpio_fired = power_on.get("gpio142_fired", "") == "1"
    elapsed_ms = power_on.get("gpio142_elapsed_ms", "?")
    gpio_before = power_on.get("gpio142_before", "?")
    gpio_after = power_on.get("gpio142_after", "?")

    mdm3_states = list(dict.fromkeys(
        e.get("mdm3_state", "") for e in status_entries if e.get("mdm3_state")
    ))
    crash_counts = [e.get("mdm3_crash_count", "") for e in status_entries]
    max_crash = max((int(c) for c in crash_counts if c.isdigit()), default=0)

    mhi_fds_seen: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                if "/dev/mhi" in fd and fd not in mhi_fds_seen:
                    mhi_fds_seen.append(fd.strip())

    mhi_dev_counts = [int(e.get("mhi_dev_count", "0"))
                      for e in status_entries if e.get("mhi_dev_count", "0").isdigit()]
    max_mhi_dev = max(mhi_dev_counts, default=0)

    if not status_entries and not power_on.get("end", ""):
        return (
            "v1198-device-rebooted-before-polling",
            False,
            "no status entries and no end marker; device likely rebooted",
            "check mss restart_level; RELATED restart may still cascade to full reboot",
        )

    if gpio_fired:
        return (
            "v1198-gpio142-fired",
            True,
            (
                f"GPIO 142 fired: before={gpio_before} after={gpio_after} "
                f"elapsed={elapsed_ms}ms; MDM powered on and booted; "
                f"mhi_fds_seen={mhi_fds_seen}; check WLFW/BDF/wlan0"
            ),
            "GPIO 142 confirmed — check MHI device, ks, WLFW, wlan0",
        )

    if max_crash > 0:
        return (
            "v1198-mdm3-crash-count-nonzero",
            False,
            (
                f"mdm3 crash_count={max_crash}; MDM SSR with RELATED restart; "
                f"state_transitions={mdm3_states}; mhi_fds_seen={mhi_fds_seen}"
            ),
            "mdm_helper failed firmware transfer; check SELinux and firmware paths",
        )

    if mhi_fds_seen:
        return (
            "v1198-mhi-fd-opened-by-mdm-helper",
            False,
            (
                f"mdm_helper opened MHI fd(s): {mhi_fds_seen}; "
                f"MHI path is active but PCIe link still failing; "
                f"max_mhi_dev={max_mhi_dev}; mdm3_states={mdm3_states}"
            ),
            "MHI path confirmed; investigate PCIe PMIC GPIO / link training failure",
        )

    wchans_sample = [
        e.get("mdm_helper_wchans", "") for e in status_entries[:3]
    ]
    return (
        "v1198-subsys-esoc0-blocked-gpio142-silent",
        False,
        (
            f"subsys_esoc0 open blocking; GPIO 142 silent after "
            f"{len(status_entries)*10}s; "
            f"mdm3_states={mdm3_states}; crash_count=0; "
            f"mhi_fds_seen={mhi_fds_seen}; "
            f"max_mhi_dev={max_mhi_dev}; "
            f"mdm_helper_wchans_sample={wchans_sample}"
        ),
        (
            "MDM powerup stuck; classify mdm_helper path from wchans/fds; "
            "PCIe PMIC GPIO support needed for MHI path"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    status_entries = power_on.get("_status_entries", [])

    rows = [
        ["helper_version", DEFAULT_EXECNS_HELPER_MARKER],
        ["policy_load_result", policy.get("result", "")],
        ["gate_result", gate.get("result", "")],
        ["per_mgr_domain", domain.get("domain_value", "")],
        ["mdm_helper_esoc0_found", mdm_early.get("esoc0_found", "")],
        ["mdm_helper_esoc0_wait_ms", mdm_early.get("esoc0_wait_ms", "")],
        ["restart_level_set", power_on.get("restart_level_set", "")],
        ["restart_level_write_ok", power_on.get("restart_level_write_ok", "")],
        ["power_on_begin", power_on.get("begin", "")],
        ["child_status", power_on.get("child_status", "")[:80]],
        ["gpio142_before", power_on.get("gpio142_before", "")],
        ["gpio142_fired", power_on.get("gpio142_fired", "")],
        ["gpio142_elapsed_ms", power_on.get("gpio142_elapsed_ms", "")],
        ["status_entry_count", str(len(status_entries))],
    ]
    for i, e in enumerate(status_entries[:10]):
        rows.append([
            f"status[{i}]",
            f"t={e.get('elapsed_ms','')}ms gpio={e.get('gpio142_count','')} "
            f"mdm3={e.get('mdm3_state','')} crash={e.get('mdm3_crash_count','')} "
            f"mhi_dev={e.get('mhi_dev_count','')} "
            f"wchans={e.get('mdm_helper_wchans','')[:60]} "
            f"fds={e.get('mdm_helper_fds','')[:60]}",
        ])
    lines = [
        "# V1198 PM Observer: subsys_esoc0 + restart_level=RELATED (no PCIe enumerate)",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:400]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## MDM Power-On Gate",
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

    v1183.pm_per_proxy_vndservice_gate_child_command = pm_mdm_esoc_power_on_v1198_child_command
    v1106.pm_cnss_child_command = pm_mdm_esoc_power_on_v1198_child_command


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
    manifest["cycle"] = "v1198"
    manifest["generated_at"] = _now_iso()
    manifest["subsys_esoc0_flag"] = SUBSYS_ESOC0_FLAG
    manifest["restart_level_flag"] = RESTART_LEVEL_FLAG
    manifest["mdm_before_cnss_flag"] = v1193.MDM_BEFORE_CNSS_FLAG
    manifest["policy_load_flag"] = v1191.POLICY_LOAD_FLAG
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1198(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)

    status_entries = power_on.get("_status_entries", [])
    max_crash = max(
        (int(e.get("mdm3_crash_count", "0")) for e in status_entries
         if e.get("mdm3_crash_count", "0").isdigit()),
        default=0,
    )
    mdm3_states = list(dict.fromkeys(
        e.get("mdm3_state", "") for e in status_entries if e.get("mdm3_state")
    ))
    mhi_fds_all: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                fd = fd.strip()
                if fd and fd not in mhi_fds_all:
                    mhi_fds_all.append(fd)
    mhi_dev_max = max(
        (int(e.get("mhi_dev_count", "0")) for e in status_entries
         if e.get("mhi_dev_count", "0").isdigit()),
        default=0,
    )

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
    manifest["status_entry_count"] = len(status_entries)
    manifest["mdm3_crash_count_max"] = max_crash
    manifest["mdm3_state_transitions"] = mdm3_states
    manifest["mhi_fds_seen"] = mhi_fds_all
    manifest["mhi_dev_count_max"] = mhi_dev_max
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
    print(f"per_mgr_domain                   : {manifest['per_mgr_domain']!r}")
    print(f"mdm_helper_esoc0_found           : {manifest['mdm_helper_esoc0_found']}")
    print(f"restart_level_set                : {manifest['restart_level_set']!r}")
    print(f"restart_level_write_ok           : {manifest['restart_level_write_ok']}")
    print(f"power_on_begin                   : {manifest['power_on_begin']}")
    print(f"subsys_esoc0_opened              : {manifest['subsys_esoc0_opened']}")
    print(f"gpio142_fired                    : {manifest['gpio142_fired']}")
    print(f"gpio142_before                   : {manifest['gpio142_before']}")
    print(f"gpio142_after                    : {manifest['gpio142_after']}")
    print(f"status_entry_count               : {manifest['status_entry_count']}")
    print(f"mdm3_crash_count_max             : {manifest['mdm3_crash_count_max']}")
    print(f"mdm3_state_transitions           : {manifest['mdm3_state_transitions']}")
    print(f"mhi_fds_seen                     : {manifest['mhi_fds_seen']}")
    print(f"mhi_dev_count_max                : {manifest['mhi_dev_count_max']}")
    print(f"wifi_bringup_executed            : {manifest['wifi_bringup_executed']}")
    print(f"manifest                         : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
