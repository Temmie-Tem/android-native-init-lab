#!/usr/bin/env python3
"""V1204: PM observer — per_proxy late start (pph+20s) to allow state-0 dep flag.

V1203 confirmed: PCIe link training fails (pcie_link_state=absent, pci_dev_count=0,
mhi_bus_count=0 throughout 100s) when our trigger child opens subsys_esoc0 directly.
Root cause: PCIe PERST#/power not managed by PM framework — pm-service state machine
never opens esoc0 via PCIe-resourced path.

V1177/V1178 analysis:
  pm_proxy_helper state order [2, 3, 0, 1]:
  - state-0 runs at pph+15.99s (native). If per_proxy NOT yet connected at that time:
    dep at peripheral+0x40 is still state<1 → flag-set path runs → dep_flag=1.
  - state-2 (triggered by per_proxy connecting) checks dep_flag:
    if dep_flag=1 → opens /dev/subsys_esoc0 via PCIe-resourced path (PCIe PERST# voted).
    if dep_flag=0 → opens /dev/subsys_modem (no PCIe resources).
  V1200/V1203 flaw: per_proxy started at vndservice gate (~pph+1-2s), BEFORE state-0
    (pph+15.99s). This advances dep+0x40 to state=1 before state-0, blocking the flag.
  Android fix: per_proxy connects ~2.16s after pph, while state-0 runs earlier
    (pph+<2.16s in Android's faster init context).

V1204 fix: remove --pm-observer-per-proxy-after-vndservice-provider, add
  --pm-observer-per-proxy-pph-delta-ms 20000. Per_proxy starts at pph+20s,
  AFTER state-0 (pph+15.99s). dep_flag=1 is set by state-0, then per_proxy's
  connection triggers state-2, which opens esoc0 via PCIe-resourced path.

Expected outcome:
  - pci_dev_count > 0: MDM PCIe endpoint appears on bus after PCIe link trains
  - mhi_bus_count > 0: MHI devices enumerate (BHI + data channels)
  - ks_count > 0: ks spawns via mdm_helper
  - gpio142_fired: MDM fully powered on

Blocked: Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  GPIO writes, flash, partition write.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_pm_mdm_pcie_observe_v1203 as v1203
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183
from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1204-pm-dep-per-proxy-late-start")
LATEST_POINTER = Path("tmp/wifi/latest-v1204-pm-dep-per-proxy-late-start.txt")
DEFAULT_EXECNS_HELPER_SHA256 = v1203.DEFAULT_EXECNS_HELPER_SHA256
DEFAULT_EXECNS_HELPER_MARKER = v1203.DEFAULT_EXECNS_HELPER_MARKER
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1204"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1204/pm-dep-per-proxy-late-start-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1204/pm-dep-per-proxy-late-start-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1204/pm-dep-per-proxy-late-start-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1204-"

VNDSERVICE_GATE_FLAG = v1183.VNDSERVICE_GATE_FLAG  # --pm-observer-per-proxy-after-vndservice-provider
PPH_DELTA_OPTION = v1183.PPH_DELTA_OPTION           # --pm-observer-per-proxy-pph-delta-ms
PER_PROXY_PPH_DELTA_MS = 20000                       # 20s — after state-0 at pph+15.99s

_ORIG_V1204_PATCH_DEFAULTS = v1203.patch_defaults


def pm_dep_per_proxy_late_start_v1204_child_command(args: Any) -> list[str]:
    """Replace vndservice gate with pph-delta-ms=20000 for per_proxy late start."""
    base = v1203.pm_mdm_pcie_observe_v1203_child_command(args)
    # Remove vndservice gate flag (mutually exclusive with pph_delta_ms)
    result: list[str] = []
    i = 0
    while i < len(base):
        if base[i] == VNDSERVICE_GATE_FLAG:
            i += 1  # skip
        elif base[i] == PPH_DELTA_OPTION and i + 1 < len(base):
            i += 2  # skip old delta if present
        else:
            result.append(base[i])
            i += 1
    # Add pph-delta-ms=20000
    result.extend([PPH_DELTA_OPTION, str(PER_PROXY_PPH_DELTA_MS)])
    return result


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

    _ORIG_V1204_PATCH_DEFAULTS()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = (
        pm_dep_per_proxy_late_start_v1204_child_command
    )
    v1106.pm_cnss_child_command = pm_dep_per_proxy_late_start_v1204_child_command


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
    manifest["cycle"] = "v1204"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = v1203.decide_v1203(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    gate = v1183_mod._vndservice_gate(manifest)
    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_early = v1193._mdm_early(manifest)
    power_on = v1203._mdm_power_on_v1203(manifest)
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
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    summary = v1203.render_summary_v1203(manifest)
    summary = summary.replace(
        "# V1203 PM Observer: PCIe LTSSM + MHI Bus Monitoring",
        "# V1204 PM Observer: per_proxy Late Start (pph+20s) for dep_flag=1",
    )
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
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
    print(f"esoc0_fds_seen                   : {manifest['esoc0_fds_seen']}")
    print(f"mhi_fds_seen                     : {manifest['mhi_fds_seen']}")
    print(f"manifest                         : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
