#!/usr/bin/env python3
"""V1208: pm_proxy_helper spawn-time esoc-0 fd observer.

V1207 host-only PASS (dep+0x40 classifier):
  V1205 (mss=ONLINE at per_mgr start) → modem path
  V1206 (mss=OFFLINING at per_mgr start, mss=ONLINE at per_proxy) → modem path
  Android (mss=ONLINE at per_proxy, mdm3=OFFLINING) → esoc0 path
  V1206 and Android are identical at per_proxy connect time → dep decided BEFORE per_proxy.

  New hypothesis: pm_proxy_helper reads ESOC hardware link state (GET_LINK_ID or similar)
  at spawn time (order=4, before per_mgr order=5). Native returns errno=22 (no PCIe link)
  → modem fallback. Android hardware returns valid link ID → esoc0 path.

  V1208 adds helper v245 early probe: 300ms settle after pm_proxy_helper spawn, then
  fd scan for /dev/esoc-0, /dev/subsys_esoc0, /dev/subsys_modem + wchan capture.

Decisions:
  v1208-pm-proxy-helper-opens-esoc0:        esoc0_count > 0 at 300ms settle
  v1208-pm-proxy-helper-opens-subsys-esoc0: subsys_esoc0_count > 0 (no BOOT_DONE)
  v1208-pm-proxy-helper-alive-no-esoc0:     alive=1 but all fd counts = 0
  v1208-pm-proxy-helper-exits-before-settle: alive=0 at 300ms settle (quick exit)
  v1208-pcie-link-training-failed:           fallback — same as V1205

Does NOT use deferred modem holder (V1206 approach — proved not to help).
Does NOT change per_proxy timing from V1205 baseline.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1208-pm-proxy-helper-esoc-probe")
LATEST_POINTER = Path("tmp/wifi/latest-v1208-pm-proxy-helper-esoc-probe.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "1a80cc3a113f0dd2b2aaf02d9cbe653f9bbfccfc7d3dbb24e3069d7301b2e50e"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v245"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1208"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1208/pm-dep-pm-proxy-helper-esoc-probe-child.sh"
DEFAULT_COLLECTOR_SCRIPT = (
    "/cache/a90-runtime/v1208/pm-dep-pm-proxy-helper-esoc-probe-collector.sh"
)
DEFAULT_CHILD_OUTPUT = (
    "/cache/a90-runtime/v1208/pm-dep-pm-proxy-helper-esoc-probe-output.txt"
)
PROOF_PREFIX = "/tmp/a90-v1208-"

_ORIG_V1208_PATCH_DEFAULTS = v1205.patch_defaults


def _pph_probe(manifest: dict[str, Any]) -> dict[str, Any]:
    """Parse after_pm_proxy_helper_spawn.* fields from step output."""
    steps = manifest.get("steps", [])
    result: dict[str, str] = {}
    run_dir = manifest.get("_run_dir", "")
    _keys = (
        "alive", "settle_ms", "esoc0_count",
        "subsys_esoc0_count", "subsys_modem_count", "wchan",
    )
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
            for key in _keys:
                prefix = f"pm_service_trigger_observer.after_pm_proxy_helper_spawn.{key}="
                if line.startswith(prefix) and key not in result:
                    result[key] = line.split("=", 1)[1].strip()
    return result


def _int_field(probe: dict[str, str], key: str, default: int = -1) -> int:
    raw = probe.get(key, "")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def decide_v1208(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1208-pm-proxy-helper-esoc-probe-plan-ready",
            True,
            "plan-only; no device mutation",
            "deploy v245, run V1208 live gate (pm_proxy_helper spawn-time esoc-0 probe)",
        )

    # Re-use V1205 baseline checks (policy, status entries, PCIe)
    base_decision, base_pass, base_reason, base_next = v1205.decide_v1205(args, manifest)

    # Early exit on infrastructure failures
    if base_decision in ("v1205-policy-load-failed", "v1205-no-status-entries"):
        return (
            base_decision.replace("v1205", "v1208"),
            False,
            base_reason,
            base_next,
        )

    probe = _pph_probe(manifest)
    pph_alive = _int_field(probe, "alive", -1)
    esoc0_count = _int_field(probe, "esoc0_count", -1)
    subsys_esoc0_count = _int_field(probe, "subsys_esoc0_count", -1)
    subsys_modem_count = _int_field(probe, "subsys_modem_count", -1)
    wchan = probe.get("wchan", "unknown")
    settle_ms = probe.get("settle_ms", "?")

    probe_summary = (
        f"pph_alive={pph_alive} esoc0_count={esoc0_count} "
        f"subsys_esoc0_count={subsys_esoc0_count} "
        f"subsys_modem_count={subsys_modem_count} wchan={wchan!r} "
        f"settle_ms={settle_ms}"
    )

    if pph_alive == -1:
        # probe fields not captured at all
        return (
            "v1208-pph-probe-not-captured",
            False,
            f"after_pm_proxy_helper_spawn fields missing from output; {probe_summary}",
            "check helper v245 version marker and child output",
        )

    if pph_alive == 1 and esoc0_count > 0:
        return (
            "v1208-pm-proxy-helper-opens-esoc0",
            True,
            f"pm_proxy_helper opened /dev/esoc-0! {probe_summary}; "
            f"GET_LINK_ID errno=22 → modem dep path confirmed via pm_proxy_helper",
            "V1208 confirms dep+0x40 via pm_proxy_helper ESOC GET_LINK_ID failure. "
            "Next: classify what pm_proxy_helper does with esoc-0 "
            "(sysfs write / NOTIFY to unlock GET_LINK_ID response).",
        )

    if pph_alive == 1 and subsys_esoc0_count > 0:
        return (
            "v1208-pm-proxy-helper-opens-subsys-esoc0",
            True,
            f"pm_proxy_helper opened /dev/subsys_esoc0! {probe_summary}",
            "pm_proxy_helper uses subsys_esoc0 path (not raw esoc-0); "
            "classify subsys_esoc0 open contract before BOOT_DONE.",
        )

    if pph_alive == 0:
        return (
            "v1208-pm-proxy-helper-exits-before-settle",
            True,
            f"pm_proxy_helper exited before 300ms settle; {probe_summary}; "
            f"{base_reason[:150]}",
            "pm_proxy_helper is short-lived — it sets dep and exits. "
            "dep may be set via property write. "
            "Next: add strace/property intercept to capture what pm_proxy_helper writes.",
        )

    if pph_alive == 1:
        return (
            "v1208-pm-proxy-helper-alive-no-esoc0",
            True,
            f"pm_proxy_helper alive at {settle_ms}ms but no esoc-0 fd; {probe_summary}",
            "pm_proxy_helper does NOT use /dev/esoc-0 — dep+0x40 via ESOC GET_LINK_ID "
            "hypothesis closed. Classify next dep source (property, binder, hwbinder?).",
        )

    # Fallback: reuse V1205 result
    return (
        base_decision.replace("v1205", "v1208"),
        base_pass,
        f"pph_probe_missing=1; {base_reason[:200]}",
        base_next,
    )


def patch_defaults() -> None:
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_mdm_pcie_observe_v1203 as v1203

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

    _ORIG_V1208_PATCH_DEFAULTS()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    patch_defaults()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_mdm_helper_before_cnss_v1193 as v1193
    import native_wifi_pm_mdm_pcie_observe_v1203 as v1203
    import native_wifi_pm_per_mgr_domain_fix_v1189 as v1189
    import native_wifi_pm_per_mgr_policy_load_v1191 as v1191
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod
    import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1208"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["_run_dir"] = str(store.run_dir)

    decision, passed, reason, next_step = decide_v1208(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    probe = _pph_probe(manifest)
    pph_alive = _int_field(probe, "alive", -1)
    esoc0_count = _int_field(probe, "esoc0_count", -1)
    subsys_esoc0_count = _int_field(probe, "subsys_esoc0_count", -1)
    subsys_modem_count = _int_field(probe, "subsys_modem_count", -1)

    # V1205-style status entry fields
    power_on = v1205._mdm_power_on_v1205(manifest)
    status_entries = power_on.get("_status_entries", [])
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

    domain = v1189._per_mgr_domain(manifest)
    policy = v1191._policy_load(manifest)
    mdm_domain = v1203.v1200._mdm_helper_domain(manifest)
    fw = v1165.v1143.v1139.global_firmware(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["policy_load_result"] = policy.get("result", "")
    manifest["per_mgr_domain"] = domain.get("domain_value", "")
    manifest["mdm_helper_context_ok"] = mdm_domain.get("selinux_current_ok") == "1"
    manifest["status_entry_count"] = len(status_entries)
    manifest["pci_dev_count_max"] = max(pci_dev_counts, default=0)
    manifest["mhi_bus_count_max"] = max(mhi_bus_counts, default=0)
    manifest["pcie_link_states"] = pcie_link_states
    manifest["per_mgr_esoc0_any"] = any(
        e.get("per_mgr_has_esoc0", "0") == "1" for e in status_entries
    )
    manifest["after_pm_proxy_helper_spawn"] = {
        "alive": pph_alive,
        "esoc0_count": esoc0_count,
        "subsys_esoc0_count": subsys_esoc0_count,
        "subsys_modem_count": subsys_modem_count,
        "wchan": probe.get("wchan", ""),
        "settle_ms": probe.get("settle_ms", ""),
    }
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", f"""# V1208 PM pm_proxy_helper Spawn-time Esoc-0 Probe

**Decision**: `{manifest['decision']}`
**Pass**: `{manifest['pass']}`
**Reason**: {manifest['reason'][:500]}
**Next**: {manifest['next_step']}

| key | value |
|---|---|
| pph_alive | {pph_alive} |
| pph_esoc0_count | {esoc0_count} |
| pph_subsys_esoc0_count | {subsys_esoc0_count} |
| pph_subsys_modem_count | {subsys_modem_count} |
| pph_wchan | {probe.get('wchan', '')} |
| per_mgr_esoc0_any | {manifest['per_mgr_esoc0_any']} |
| pci_dev_count_max | {manifest['pci_dev_count_max']} |
| pcie_link_states | {manifest['pcie_link_states']} |
| status_entry_count | {manifest['status_entry_count']} |
""")
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision              : {manifest['decision']}")
    print(f"pass                  : {manifest['pass']}")
    print(f"reason                : {manifest['reason'][:200]}")
    print(f"pph_alive             : {pph_alive}")
    print(f"pph_esoc0_count       : {esoc0_count}")
    print(f"pph_subsys_esoc0_count: {subsys_esoc0_count}")
    print(f"pph_subsys_modem_count: {subsys_modem_count}")
    print(f"pph_wchan             : {probe.get('wchan', '')}")
    print(f"per_mgr_esoc0_any     : {manifest['per_mgr_esoc0_any']}")
    print(f"pci_dev_count_max     : {manifest['pci_dev_count_max']}")
    print(f"pcie_link_states      : {manifest['pcie_link_states']}")
    print(f"status_entry_count    : {manifest['status_entry_count']}")
    print(f"manifest              : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
