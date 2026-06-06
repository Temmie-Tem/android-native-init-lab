#!/usr/bin/env python3
"""V1206: PM observer — per_mgr starts before modem holder (dep+0x40 = mss hypothesis).

V1205 confirmed: per_proxy correctly connects at pph+20s, but pm-service still opens
subsys_modem (count=1) not subsys_esoc0 (count=0). Per_proxy timing is NOT the issue.

Root cause hypothesis: dep+0x40 = mss subsystem state.
  - In native flow (V1204/V1205): modem holder opens BEFORE per_mgr starts (via
    start_global_holder). mss ONLINE at pph=0. State-0 at pph+15.99s sees
    dep+0x40 = ONLINE (state≥1) → dep_flag stays 0 → modem path.
  - In Android: per_mgr starts very early in boot, BEFORE mss ONLINE → dep_flag=1.

V1206 fix: defer modem holder until pph+16s (AFTER state-0 at pph+15.99s).
  - start_global_holder: firmware mounts only, NO modem holder open.
  - Helper v244: opens /dev/subsys_modem at pph+16s (inside private namespace).
  - Per_proxy: still at pph+20s.
  - If dep+0x40=mss hypothesis is correct: state-0 fires with mss OFFLINING →
    dep_flag=1 → per_proxy connect at pph+20s → state-2 → opens subsys_esoc0 →
    PCIe/MHI path (per_mgr_has_esoc0=1, pci_dev_count>0).

Decision outcomes:
  v1206-pcie-linked:           pci_dev_count > 0 (PCIe link trained!)
  v1206-pm-service-opened-esoc0: per_mgr_has_esoc0=1 (esoc0 path selected)
  v1206-dep-hypothesis-refuted: mss still ONLINE at pph; dep+0x40 != mss
  v1206-pcie-link-training-failed: esoc0 opened but PCIe still fails

Safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  GPIO writes, flash, partition write. sda29 read-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
import native_wifi_pm_mdm_pcie_observe_v1203 as v1203
import native_wifi_global_firmware_pm_connect_live_v1113 as v1113
import native_wifi_holder_lower_companion_v733 as holder
import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1206-pm-per-mgr-before-modem-holder")
LATEST_POINTER = Path("tmp/wifi/latest-v1206-pm-per-mgr-before-modem-holder.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "693b6c306734abdf339492603db98277a1d585f37205012bb72a562ff4d2d7b9"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v244"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1206"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1206/pm-per-mgr-before-modem-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1206/pm-per-mgr-before-modem-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1206/pm-per-mgr-before-modem-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1206-"

# Deferred modem holder: open at pph + 16s (after state-0 at pph+15.99s)
DEFER_MODEM_HOLDER_PPH_MS = 16000
PER_PROXY_PPH_DELTA_MS = 20000

_STATUS_FIELDS_V244 = v1205._STATUS_FIELDS_V243  # same fields as v243/v244
_STATUS_FIELD_COUNT = len(_STATUS_FIELDS_V244)

_ORIG_V1206_PATCH_DEFAULTS = v1205.patch_defaults

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG
PPH_DELTA_OPTION = v1183.PPH_DELTA_OPTION
_DEFER_MODEM_HOLDER_OPTION = "--pm-observer-defer-modem-holder-pph-ms"
_ALLOW_DEFER_MODEM_HOLDER = "--allow-pm-observer-defer-modem-holder"


def pm_per_mgr_before_modem_holder_v1206_child_command(
    args: argparse.Namespace,
) -> list[str]:
    """V1204 child command + deferred modem holder flags."""
    base = v1204.pm_dep_per_proxy_late_start_v1204_child_command(args)
    # Remove any existing defer-modem-holder args (idempotent)
    result: list[str] = []
    i = 0
    while i < len(base):
        if base[i] in (_DEFER_MODEM_HOLDER_OPTION, _ALLOW_DEFER_MODEM_HOLDER):
            i += 1
            if base[i - 1] == _DEFER_MODEM_HOLDER_OPTION and i < len(base):
                i += 1  # skip value
        else:
            result.append(base[i])
            i += 1
    result.extend([
        _ALLOW_DEFER_MODEM_HOLDER,
        _DEFER_MODEM_HOLDER_OPTION, str(DEFER_MODEM_HOLDER_PPH_MS),
    ])
    return result


def start_global_firmware_mounts_only(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    preflight: dict[str, Any],
    proof_base: str,
) -> dict[str, Any]:
    """Firmware mounts only — NO modem holder open, NO qrtr_rx wait.

    V1206 hypothesis: per_mgr must start with mss OFFLINING. The modem holder is
    deferred to pph+16s inside the helper binary (helper v244 flag). Skip the
    Python-side modem holder and bypass qrtr_rx_wait (helper handles timing).
    """
    before = holder.run_step(
        args, store, steps, "global-dmesg-before",
        ["run", args.toybox, "dmesg"], 60.0, proof_base,
    )
    mount_results: list[str] = []
    for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
        item = holder.run_step(args, store, steps, f"global-{name}", command, timeout,
                               proof_base)
        mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
    holder.run_step(args, store, steps, "global-proc-mounts-mounted",
                    ["cat", "/proc/mounts"], 20.0, proof_base)
    holder.run_step(args, store, steps, "global-firmware-class-path-mounted",
                    ["cat", holder.FIRMWARE_CLASS_PATH], 10.0, proof_base)
    for path in holder.GLOBAL_MODEM_BLOB_PATHS + holder.WLAN_FIRMWARE_PATHS:
        safe = path.replace("/", "_").strip("_")
        holder.run_step(args, store, steps, f"global-stat-{safe}", ["stat", path],
                        10.0, proof_base)
    # Capture mss state BEFORE per_mgr starts (should be OFFLINING)
    holder.run_step(args, store, steps, "global-mss-state-before-per-mgr",
                    ["cat", holder.MSS_STATE], 10.0, proof_base)
    holder.run_step(args, store, steps, "global-mdm3-state-before-per-mgr",
                    ["cat", holder.MDM3_STATE], 10.0, proof_base)
    # No modem holder, no qrtr_rx wait — bypass with seen=True so observer proceeds.
    # The helper will open the modem holder at pph+16s internally.
    return {
        "proof_base": proof_base,
        "mount_results": mount_results,
        "holder_opened": False,
        "deferred_modem_holder_to_helper": True,
        "qrtr_rx_wait": {"seen": True, "deferred": True},
    }


def decide_v1206(
    args: argparse.Namespace, manifest: dict[str, Any]
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1206-pm-per-mgr-before-modem-holder-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy v244, run V1206 live gate (per_mgr before modem holder)",
        )

    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod
    import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
    import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193

    policy = v1191._policy_load(manifest)
    power_on = v1205._mdm_power_on_v1205(manifest)
    mdm_domain = v1203.v1200._mdm_helper_domain(manifest)

    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1206-policy-load-failed", False,
            f"precompiled policy load failed: {policy_result!r}",
            "verify selinuxfs and vendor precompiled_sepolicy",
        )

    status_entries = power_on.get("_status_entries", [])
    gpio_fired = power_on.get("gpio142_fired", "") == "1"

    pci_dev_counts = [
        int(e.get("pci_dev_count", "0"))
        for e in status_entries if e.get("pci_dev_count", "0").isdigit()
    ]
    mhi_bus_counts = [
        int(e.get("mhi_bus_count", "0"))
        for e in status_entries if e.get("mhi_bus_count", "0").isdigit()
    ]
    pcie_link_states = list(dict.fromkeys(
        e.get("pcie_link_state", "") for e in status_entries
        if e.get("pcie_link_state")
    ))
    per_mgr_esoc0_any = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    cnss_vndbinder_any = any(
        e.get("cnss_has_vndbinder", "0") == "1" for e in status_entries
    )
    max_pci_dev = max(pci_dev_counts, default=0)
    max_mhi_bus = max(mhi_bus_counts, default=0)

    mss_states_before = [
        s.get("mss_state", "") for s in status_entries
    ]
    context_ok = mdm_domain.get("selinux_current_ok") == "1"
    context_after = mdm_domain.get("selinux_current_after", "?")

    summary = (
        f"pcie_link_states={pcie_link_states}; pci_dev_max={max_pci_dev}; "
        f"mhi_bus_max={max_mhi_bus}; per_mgr_esoc0={per_mgr_esoc0_any}; "
        f"cnss_vnd={cnss_vndbinder_any}; context_ok={context_ok} "
        f"context_after={context_after!r}; status_count={len(status_entries)}"
    )

    if not status_entries:
        return (
            "v1206-no-status-entries", False,
            "no status entries captured; device may have rebooted",
            "check restart_level / mss / deferred modem holder",
        )

    if gpio_fired:
        return (
            "v1206-gpio142-fired", True,
            f"GPIO 142 fired! pci_dev={max_pci_dev} mhi_bus={max_mhi_bus} "
            f"per_mgr_esoc0={per_mgr_esoc0_any}; {summary}",
            "MDM fully powered on — check WLFW/BDF/wlan0",
        )

    if max_pci_dev > 0 or max_mhi_bus > 0:
        return (
            "v1206-pcie-linked", True,
            f"PCIe linked! pci_dev_max={max_pci_dev} mhi_bus_max={max_mhi_bus}; "
            f"per_mgr_esoc0={per_mgr_esoc0_any}; cnss_vnd={cnss_vndbinder_any}",
            "PCIe enumerated — follow MHI/ks/firmware sequence",
        )

    if per_mgr_esoc0_any:
        return (
            "v1206-pm-service-opened-esoc0", True,
            f"pm-service opened subsys_esoc0! (per_mgr_has_esoc0=1); {summary}",
            "pm-service opened esoc0 but PCIe didn't link — investigate PCIe resource vote",
        )

    # Check if mss was OFFLINING at start (dep hypothesis test)
    mss_at_start = status_entries[0].get("mss_state", "") if status_entries else ""
    if mss_at_start in ("ONLINE", "ONLINE_CHARGING"):
        return (
            "v1206-dep-hypothesis-refuted", False,
            f"mss already ONLINE at first status sample (mss={mss_at_start!r}); "
            f"dep+0x40 != mss, or modem holder opened too early; {summary}",
            "dep+0x40 is not mss state; investigate alternative dep-state sources",
        )

    return (
        "v1206-pcie-link-training-failed", True,
        f"PCIe link training still failed with mss deferred; {summary}",
        "dep+0x40=mss hypothesis may be confirmed if per_mgr_esoc0 was 0 "
        "despite mss OFFLINING at pph; investigate other dep+0x40 candidates",
    )


def patch_defaults() -> None:
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

    v1203.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1203.LATEST_POINTER = LATEST_POINTER
    v1203.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1203.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1193.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1193.LATEST_POINTER = LATEST_POINTER
    v1193.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1193.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1193.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1193.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1193.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1193.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1193.PROOF_PREFIX = PROOF_PREFIX

    _ORIG_V1206_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    # Replace pm_cnss_child_command with V1206 version (adds defer-modem-holder flags)
    v1183_mod.pm_per_proxy_vndservice_gate_child_command = (
        pm_per_mgr_before_modem_holder_v1206_child_command
    )
    v1106.pm_cnss_child_command = pm_per_mgr_before_modem_holder_v1206_child_command

    # Override start_global_holder to skip modem holder
    v1113.start_global_holder = start_global_firmware_mounts_only


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    patch_defaults()
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
    import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1206"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = PER_PROXY_PPH_DELTA_MS
    manifest["defer_modem_holder_pph_ms"] = DEFER_MODEM_HOLDER_PPH_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1206(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183_mod._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = v1205._mdm_power_on_v1205(manifest)
    mdm_domain = v1203.v1200._mdm_helper_domain(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    lower = v1165.v1143.lower_trace(manifest)
    status_entries = power_on.get("_status_entries", [])

    esoc0_fds_all: list[str] = []
    mhi_fds_all: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                fd = fd.strip()
                if fd:
                    if "/dev/esoc" in fd and fd not in esoc0_fds_all:
                        esoc0_fds_all.append(fd)
                    if "/dev/mhi" in fd and fd not in mhi_fds_all:
                        mhi_fds_all.append(fd)

    pci_dev_counts = [
        int(e.get("pci_dev_count", "0"))
        for e in status_entries if e.get("pci_dev_count", "0").isdigit()
    ]
    mhi_bus_counts = [
        int(e.get("mhi_bus_count", "0"))
        for e in status_entries if e.get("mhi_bus_count", "0").isdigit()
    ]
    pcie_link_states = list(dict.fromkeys(
        e.get("pcie_link_state", "") for e in status_entries
        if e.get("pcie_link_state")
    ))
    per_mgr_esoc0_any = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    cnss_vndbinder_any = any(
        e.get("cnss_has_vndbinder", "0") == "1" for e in status_entries
    )

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["gate_open"] = gate.get("gate_open") == "1"
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_esoc0_found"] = mdm_early.get("esoc0_found", "") == "1"
    manifest["mdm_helper_context_ok"] = mdm_domain.get("selinux_current_ok") == "1"
    manifest["mdm_helper_context_after"] = mdm_domain.get("selinux_current_after", "")
    manifest["power_on_begin"] = power_on.get("begin", "") == "1"
    manifest["gpio142_fired"] = power_on.get("gpio142_fired", "") == "1"
    manifest["gpio142_elapsed_ms"] = power_on.get("gpio142_elapsed_ms", "")
    manifest["status_entry_count"] = len(status_entries)
    manifest["esoc0_fds_seen"] = esoc0_fds_all
    manifest["mhi_fds_seen"] = mhi_fds_all
    manifest["mhi_dev_count_max"] = max(
        (int(e.get("mhi_dev_count", "0"))
         for e in status_entries if e.get("mhi_dev_count", "0").isdigit()),
        default=0,
    )
    manifest["pci_dev_count_max"] = max(pci_dev_counts, default=0)
    manifest["mhi_bus_count_max"] = max(mhi_bus_counts, default=0)
    manifest["pcie_link_states"] = pcie_link_states
    manifest["per_mgr_esoc0_any"] = per_mgr_esoc0_any
    manifest["cnss_vndbinder_any"] = cnss_vndbinder_any
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                         : {manifest['decision']}")
    print(f"pass                             : {manifest['pass']}")
    print(f"reason                           : {manifest['reason'][:200]}")
    print(f"next                             : {manifest['next_step'][:100]}")
    print(f"per_mgr_domain                   : {manifest['per_mgr_domain']!r}")
    print(f"mdm_helper_context_ok            : {manifest['mdm_helper_context_ok']}")
    print(f"gpio142_fired                    : {manifest['gpio142_fired']}")
    print(f"status_entry_count               : {manifest['status_entry_count']}")
    print(f"pci_dev_count_max                : {manifest['pci_dev_count_max']}")
    print(f"mhi_bus_count_max                : {manifest['mhi_bus_count_max']}")
    print(f"pcie_link_states                 : {manifest['pcie_link_states']}")
    print(f"per_mgr_esoc0_any                : {manifest['per_mgr_esoc0_any']}")
    print(f"cnss_vndbinder_any               : {manifest['cnss_vndbinder_any']}")
    print(f"esoc0_fds_seen                   : {manifest['esoc0_fds_seen']}")
    print(f"mhi_fds_seen                     : {manifest['mhi_fds_seen']}")
    print(f"manifest                         : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


def _render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V1206 PM Observer: per_mgr Before Modem Holder (dep+0x40=mss Hypothesis)",
        "",
        f"**Decision**: `{manifest.get('decision')}`  ",
        f"**Pass**: `{manifest.get('pass')}`  ",
        f"**Reason**: {manifest.get('reason', '')}",
        "",
        "## Key Results",
        f"- `pci_dev_count_max`: `{manifest.get('pci_dev_count_max')}`",
        f"- `mhi_bus_count_max`: `{manifest.get('mhi_bus_count_max')}`",
        f"- `pcie_link_states`: `{manifest.get('pcie_link_states')}`",
        f"- `per_mgr_esoc0_any`: `{manifest.get('per_mgr_esoc0_any')}`",
        f"- `cnss_vndbinder_any`: `{manifest.get('cnss_vndbinder_any')}`",
        f"- `gpio142_fired`: `{manifest.get('gpio142_fired')}`",
        f"- `status_entry_count`: `{manifest.get('status_entry_count')}`",
        f"- `per_mgr_domain`: `{manifest.get('per_mgr_domain')}`",
        f"- `mdm_helper_context_ok`: `{manifest.get('mdm_helper_context_ok')}`",
        f"- `policy_load_result`: `{manifest.get('policy_load_result')}`",
        f"- `firmware_mounts_executed`: `{manifest.get('firmware_mounts_executed')}`",
        f"- `reboot_executed`: `{manifest.get('reboot_executed')}`",
        "",
        "## Timing",
        f"- `per_proxy_pph_delta_ms`: `{manifest.get('per_proxy_pph_delta_ms')}`",
        f"- `defer_modem_holder_pph_ms`: `{manifest.get('defer_modem_holder_pph_ms')}`",
        "",
        "## Next Step",
        manifest.get("next_step", ""),
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
