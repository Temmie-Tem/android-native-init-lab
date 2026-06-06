#!/usr/bin/env python3
"""V1205: PM dep observer — per_proxy pph+20s + extended tracefs + esoc0/vndbinder scan.

Combines Path A and Path B observations in a single run:

Path A (dep+0x40 root cause via tracefs):
  V1204's dep state uprobes registered but events NOT captured because the
  tracefs window (SAMPLE_COUNT=80 x 0.25s = 20s) closes before per_proxy
  connects at pph+20s. Fix: --thread-sample-count 600 (150s window).
  Expected dep state events at pph+20s+delta will now be captured.

Path B (cnss-daemon vndbinder → pm-service):
  Helper v243 adds per_mgr_has_esoc0 and cnss_has_vndbinder to status loop.
  per_mgr_has_esoc0: does pm-service ever open /dev/subsys_esoc0?
  cnss_has_vndbinder: does cnss-daemon connect to pm-service via vndbinder?
  These are observed simultaneously across all 10 status samples.

Key decisions:
  v1205-pcie-linked:               pci_dev_count > 0 (PCIe link trained!)
  v1205-pm-service-opened-esoc0:   per_mgr_has_esoc0=1 (pm-service opened esoc0)
  v1205-cnss-vndbinder-connected:  cnss_has_vndbinder=1 at some status sample
  v1205-dep-flag-set:              dep state tracefs shows state-0 flag_set fired
  v1205-pcie-link-training-failed: pci_dev_count=0 throughout (same as V1203/V1204)

Does NOT add PCIe debug/enumerate write (Path C — V1206 separate run).
Does NOT change per_proxy timing (still pph+20s).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
import native_wifi_pm_mdm_pcie_observe_v1203 as v1203
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1205-pm-dep-per-proxy-late-esoc-observe")
LATEST_POINTER = Path("tmp/wifi/latest-v1205-pm-dep-per-proxy-late-esoc-observe.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "ae628a539268be5f70c59208839da0fff485c6befc07bd467d874480fb6866bd"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v243"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1205"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1205/pm-dep-per-proxy-late-esoc-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1205/pm-dep-per-proxy-late-esoc-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1205/pm-dep-per-proxy-late-esoc-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1205-"

_STATUS_FIELDS_V243 = v1203._STATUS_FIELDS_V242 + (
    "per_mgr_has_esoc0",   # new in v243
    "cnss_has_vndbinder",  # new in v243
)
_STATUS_FIELD_COUNT = len(_STATUS_FIELDS_V243)

_ORIG_V1205_PATCH_DEFAULTS = v1204.patch_defaults


def _mdm_power_on_v1205(manifest: dict[str, Any]) -> dict[str, Any]:
    """Parse 15-field v243 status entries."""
    steps = manifest.get("steps", [])
    result: dict[str, Any] = {
        "begin": "", "restart_level_set": "", "restart_level_write_ok": "",
        "gpio142_before": "", "gpio142_after": "", "gpio142_fired": "",
        "gpio142_elapsed_ms": "", "child_status": "", "reboot_required": "", "end": "",
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
            for skey in _STATUS_FIELDS_V243:
                prefix = f"pm_observer_mdm_power_on.status.{skey}="
                if line.startswith(prefix):
                    current_status[skey] = line.split("=", 1)[1].strip()
                    if len(current_status) == _STATUS_FIELD_COUNT:
                        status_entries.append(dict(current_status))
                        current_status = {}
    result["_status_entries"] = status_entries  # type: ignore[assignment]
    return result


def decide_v1205(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1205-pm-dep-per-proxy-late-esoc-observe-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy v243, run V1205 live gate (Path A + B)",
        )

    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod
    import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
    import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193

    gate = v1183_mod._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on_v1205(manifest)
    mdm_domain = v1203.v1200._mdm_helper_domain(manifest)

    # Gate check: V1205 removes vndservice gate, use pph-delta instead
    # Gate "begin" marker still expected from pm_service_trigger_observer block
    policy_result = policy.get("result", "")
    if not policy_result or "pass" not in policy_result:
        return (
            "v1205-policy-load-failed", False,
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
        e.get("pcie_link_state", "") for e in status_entries if e.get("pcie_link_state")
    ))
    per_mgr_esoc0_any = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    cnss_vndbinder_any = any(
        e.get("cnss_has_vndbinder", "0") == "1" for e in status_entries
    )
    max_pci_dev = max(pci_dev_counts, default=0)
    max_mhi_bus = max(mhi_bus_counts, default=0)

    esoc0_fds_seen: list[str] = []
    for e in status_entries:
        fds = e.get("mdm_helper_fds", "none")
        if fds and fds != "none":
            for fd in fds.split(","):
                fd = fd.strip()
                if "/dev/esoc" in fd and fd not in esoc0_fds_seen:
                    esoc0_fds_seen.append(fd)

    context_ok = mdm_domain.get("selinux_current_ok") == "1"
    context_after = mdm_domain.get("selinux_current_after", "?")

    if not status_entries:
        return (
            "v1205-no-status-entries",
            False,
            "no status entries captured; device may have rebooted",
            "check restart_level RELATED setting",
        )

    if gpio_fired:
        return (
            "v1205-gpio142-fired", True,
            f"GPIO 142 fired! pci_dev={max_pci_dev} mhi_bus={max_mhi_bus} "
            f"per_mgr_esoc0={per_mgr_esoc0_any} cnss_vnd={cnss_vndbinder_any}",
            "MDM fully powered on — check WLFW/BDF/wlan0",
        )

    if max_pci_dev > 0 or max_mhi_bus > 0:
        return (
            "v1205-pcie-linked", True,
            f"PCIe linked! pci_dev_max={max_pci_dev} mhi_bus_max={max_mhi_bus}; "
            f"per_mgr_esoc0={per_mgr_esoc0_any}; cnss_vnd={cnss_vndbinder_any}",
            "PCIe enumerated — follow MHI/ks/firmware sequence",
        )

    if per_mgr_esoc0_any:
        return (
            "v1205-pm-service-opened-esoc0", True,
            f"pm-service opened subsys_esoc0! (per_mgr_has_esoc0=1); "
            f"pci_dev={max_pci_dev} mhi_bus={max_mhi_bus} cnss_vnd={cnss_vndbinder_any}; "
            f"pcie_states={pcie_link_states}",
            "pm-service opened esoc0 but PCIe didn't link — investigate PCIe resource vote",
        )

    summary = (
        f"pcie_link_states={pcie_link_states}; pci_dev_max={max_pci_dev}; "
        f"mhi_bus_max={max_mhi_bus}; per_mgr_esoc0={per_mgr_esoc0_any}; "
        f"cnss_vnd={cnss_vndbinder_any}; esoc0_fds={esoc0_fds_seen}; "
        f"context_ok={context_ok} context_after={context_after!r}; "
        f"status_count={len(status_entries)}"
    )

    if cnss_vndbinder_any and not per_mgr_esoc0_any:
        return (
            "v1205-cnss-vndbinder-no-esoc0", True,
            f"cnss-daemon has vndbinder but pm-service did NOT open esoc0; {summary}",
            "cnss-daemon connected to pm-service but didn't trigger esoc0 open; "
            "investigate cnss-daemon pm_client_connect payload",
        )

    return (
        "v1205-pcie-link-training-failed", True,
        f"PCIe link training still failed; {summary}",
        "Check dep state tracefs events: did state-0 flag_set fire? "
        "If yes: dep_flag set but PCIe still fails. If no: dep+0x40 still advancing early. "
        "Next: Path C (debug/enumerate at ESOC_REQ_IMG timing).",
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

    _ORIG_V1205_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = (
        v1204.pm_dep_per_proxy_late_start_v1204_child_command
    )
    v1106.pm_cnss_child_command = v1204.pm_dep_per_proxy_late_start_v1204_child_command


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
    manifest["cycle"] = "v1205"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1205(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183_mod._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = _mdm_power_on_v1205(manifest)
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
        e.get("pcie_link_state", "") for e in status_entries if e.get("pcie_link_state")
    ))

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_esoc0_found"] = mdm_early.get("esoc0_found", "") == "1"
    manifest["mdm_helper_context_ok"] = mdm_domain.get("selinux_current_ok") == "1"
    manifest["mdm_helper_context_after"] = mdm_domain.get("selinux_current_after", "")
    manifest["gpio142_fired"] = power_on.get("gpio142_fired", "") == "1"
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
    manifest["per_mgr_esoc0_any"] = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    manifest["cnss_vndbinder_any"] = any(
        e.get("cnss_has_vndbinder", "0") == "1" for e in status_entries
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", f"""# V1205 PM Dep per_proxy Late + Esoc0/Vndbinder Observe

**Decision**: `{manifest['decision']}`
**Pass**: `{manifest['pass']}`
**Reason**: {manifest['reason'][:500]}
**Next**: {manifest['next_step']}

| key | value |
|---|---|
| per_mgr_esoc0_any | {manifest['per_mgr_esoc0_any']} |
| cnss_vndbinder_any | {manifest['cnss_vndbinder_any']} |
| pci_dev_count_max | {manifest['pci_dev_count_max']} |
| mhi_bus_count_max | {manifest['mhi_bus_count_max']} |
| pcie_link_states | {manifest['pcie_link_states']} |
| esoc0_fds_seen | {manifest['esoc0_fds_seen']} |
| status_entry_count | {manifest['status_entry_count']} |
""")
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision             : {manifest['decision']}")
    print(f"pass                 : {manifest['pass']}")
    print(f"reason               : {manifest['reason'][:200]}")
    print(f"per_mgr_esoc0_any    : {manifest['per_mgr_esoc0_any']}")
    print(f"cnss_vndbinder_any   : {manifest['cnss_vndbinder_any']}")
    print(f"pci_dev_count_max    : {manifest['pci_dev_count_max']}")
    print(f"mhi_bus_count_max    : {manifest['mhi_bus_count_max']}")
    print(f"pcie_link_states     : {manifest['pcie_link_states']}")
    print(f"esoc0_fds_seen       : {manifest['esoc0_fds_seen']}")
    print(f"status_entry_count   : {manifest['status_entry_count']}")
    print(f"manifest             : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
