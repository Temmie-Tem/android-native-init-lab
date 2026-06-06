#!/usr/bin/env python3
"""V1213: PM observer with /sys/class/esoc-dev/ bind-mounted (helper v248 fix).

V1212 FAIL root cause:
  - /dev/esoc-0 was already present in private namespace (EEXIST from mknod)
  - /sys/class/esoc-dev/ was ABSENT from private namespace
    (sys/class not bind-mounted for PM observer mode)
  - libmdmdetect esoc_framework_supported() scans /sys/class/esoc-dev/
    → ENOENT → returns false → cnss-daemon peripheral='modem'

V1213 fix (helper v248):
  materialize_rmt_modem_detect_surface() now also bind-mounts
  /sys/class/esoc-dev/ into paths->sys_class_esoc_dev, making it
  visible to child processes in the chroot.

Expected: cnss-daemon calls pm_client_register(peripheral='SDX50M')
          per_mgr opens subsys_esoc0 → MDM power-on → WLFW → wlan0

Decision matrix:
  v1213-peripheral-sdx50m-per-mgr-esoc0  — SDX50M registered, per_mgr opens esoc0
  v1213-peripheral-sdx50m-no-esoc0       — SDX50M but per_mgr still modem-only
  v1213-peripheral-modem-sys-class-check — still modem (hypothesis disproven)
  v1213-wlan0-up                         — wlan0 appeared
  v1213-insufficient-data                — window too short

Safety: same as V1212 (no scan/connect/DHCP/HAL/credentials/external-ping)
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore
import native_wifi_pm_esoc_dev_node_before_cnss_v1212 as v1212
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204

DEFAULT_OUT_DIR = Path("tmp/wifi/v1213-esoc-class-dev-bind")
LATEST_POINTER = Path("tmp/wifi/latest-v1213-esoc-class-dev-bind.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "e8c367e877bc96ad37beb3397e3bf519887f43651425f6f1fae1386403403f0c"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v248"

_ORIG_V1213_PATCH_DEFAULTS = None


def patch_defaults() -> None:
    global _ORIG_V1213_PATCH_DEFAULTS

    if _ORIG_V1213_PATCH_DEFAULTS is None:
        _ORIG_V1213_PATCH_DEFAULTS = v1212.patch_defaults

    import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1205.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1212.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1212.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1212.patch_defaults()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod
    import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_tmp

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = v1212._v1212_child_command
    v1106.pm_cnss_child_command = v1212._v1212_child_command

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER


def decide_v1213(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    """V1213 decision: did /sys/class/esoc-dev/ fix make cnss use SDX50M?"""
    thread_analysis = manifest.get("thread_analysis", {})
    esoc_node = manifest.get("esoc_node_evidence", {})
    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals", [])
    cnss_sdx50m = thread_analysis.get("cnss_registered_sdx50m", False)
    cnss_modem = thread_analysis.get("cnss_registered_modem", False)
    per_mgr_esoc0_any = manifest.get("per_mgr_esoc0_any", False)
    wlan0_up = manifest.get("wlan0_up", False)
    mdm_subsys_powerup_any = thread_analysis.get("mdm_subsys_powerup_any", False)
    esoc_mknod_rc = esoc_node.get("esoc_node_mknod_rc")

    if wlan0_up:
        return (
            "v1213-wlan0-up",
            True,
            "wlan0 appeared after sys/class/esoc-dev bind-mount fix",
            "V1214: verify wlan0 with link/DHCP gate",
        )

    if cnss_sdx50m and per_mgr_esoc0_any:
        return (
            "v1213-peripheral-sdx50m-per-mgr-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M'; per_mgr opened subsys_esoc0; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1214: MDM power-on completion / WLFW service 69 / BDF / wlan0",
        )

    if cnss_sdx50m and not per_mgr_esoc0_any:
        return (
            "v1213-peripheral-sdx50m-no-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M' confirmed; per_mgr esoc0 not yet seen; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1214: extend observation window or add MDM power-on observer",
        )

    if cnss_modem and not cnss_sdx50m:
        return (
            "v1213-peripheral-modem-sys-class-check",
            False,
            f"cnss-daemon still uses peripheral='modem' after sys/class/esoc-dev fix; "
            f"esoc_mknod_rc={esoc_mknod_rc}",
            "V1214: disassemble libmdmdetect esoc_framework_supported for actual check path",
        )

    thread_count = thread_analysis.get("thread_sample_count", 0)
    return (
        "v1213-insufficient-data",
        False,
        f"thread_count={thread_count} cnss_peripherals={cnss_peripherals}",
        "re-run with longer window",
    )


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
    manifest["cycle"] = "v1213"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["esoc_dev_node_flag"] = v1212.ESOC_DEV_NODE_FLAG
    manifest["esoc_class_dev_bind_added"] = True
    manifest["_run_dir"] = str(store.run_dir)

    # Extract evidence from child output
    child_output_text = ""
    steps = manifest.get("steps", [])
    run_dir = manifest.get("_run_dir", "")
    for step in steps:
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            try:
                child_output_text += Path(run_dir, step_file).read_text(errors="replace")
            except OSError:
                pass
        child_output_text += step.get("text", "") or ""

    esoc_node_evidence = v1212._parse_esoc_node_evidence(child_output_text)
    manifest["esoc_node_evidence"] = esoc_node_evidence

    per_mgr_esoc0_any = False
    wlan0_up = False
    sys_class_esoc_dev_bound = False
    for line in child_output_text.splitlines():
        line = line.strip()
        if "per_mgr_has_esoc0=1" in line or "per_mgr_esoc0_any=1" in line:
            per_mgr_esoc0_any = True
        if "wlan0" in line and ("UP" in line or "wlan0_up=1" in line):
            wlan0_up = True
        if "esoc_dev.exists=1" in line or "esoc-dev.exists=1" in line or \
           "sys_class_esoc_dev" in line:
            sys_class_esoc_dev_bound = True

    manifest["per_mgr_esoc0_any"] = per_mgr_esoc0_any
    manifest["wlan0_up"] = wlan0_up
    manifest["sys_class_esoc_dev_bound"] = sys_class_esoc_dev_bound

    import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = v1210._parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    decision, passed, reason, next_step = decide_v1213(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    pph_obs = manifest.get("pm_service_trigger_observer", {})
    manifest["pph_samples"] = pph_obs.get("pph_samples", [])

    store.write_json("manifest.json", manifest)
    if LATEST_POINTER:
        try:
            LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
            LATEST_POINTER.write_text(str(store.run_dir))
        except Exception:
            pass

    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"esoc_node_created:          {esoc_node_evidence.get('esoc_node_created')}")
    print(f"esoc_node_mknod_rc:         {esoc_node_evidence.get('esoc_node_mknod_rc')}")
    print(f"sys_class_esoc_dev_bound:   {sys_class_esoc_dev_bound}")
    print(f"cnss_registered_peripherals:{thread_analysis.get('cnss_registered_peripherals')}")
    print(f"cnss_registered_sdx50m:     {thread_analysis.get('cnss_registered_sdx50m')}")
    print(f"per_mgr_esoc0_any:          {per_mgr_esoc0_any}")
    print(f"wlan0_up:                   {wlan0_up}")
    print(f"mdm_subsys_powerup_any:     {thread_analysis.get('mdm_subsys_powerup_any')}")
    print(f"all_pm_wchans:              {thread_analysis.get('all_pm_wchans')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
