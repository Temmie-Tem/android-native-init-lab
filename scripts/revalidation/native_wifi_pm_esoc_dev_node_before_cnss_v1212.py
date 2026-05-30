#!/usr/bin/env python3
"""V1212: PM observer with /dev/esoc-0 materialised before cnss-daemon.

V1211 LIVE PASS classified the root cause:
  libmdmdetect.so esoc_framework_supported() scans /dev/ for esoc*.
  /dev/esoc-0 absent in native (no ueventd, major=484 minor=0)
    → returns false → cnss-daemon registers peripheral='modem'
    → per_mgr opens subsys_modem only
    → subsys_esoc0 never opened → MDM never powered → WLFW/BDF/wlan0 absent.

V1212 fix: materialise /dev/esoc-0 (c 484:0) inside the helper's private
namespace immediately before spawning cnss-daemon via the new helper v247
flag --pm-observer-mknod-esoc-dev-node-before-cnss.

Expected outcomes (tracefs uprobe, V1106 framework):
  pm_client_register_entry peripheral='SDX50M'   (not 'modem')
  per_mgr_esoc0_any=True  (pm-service opens subsys_esoc0)
  mdm3 advances beyond OFFLINING
  WLFW service 69 / BDF / wlan0 may appear

Decision matrix:
  v1212-peripheral-sdx50m-per-mgr-esoc0  — cnss uses SDX50M, per_mgr opens esoc0
  v1212-peripheral-sdx50m-no-esoc0       — SDX50M but per_mgr still modem-only
  v1212-peripheral-modem-esoc0-node-fail — esoc-0 mknod failed; modem still used
  v1212-peripheral-modem-no-esoc0        — unexpected: SDX50M path not triggered
  v1212-wlan0-up                         — wlan0 interface appeared
  v1212-insufficient-data                — uprobe not captured or window too short

Safety:
  No Wi-Fi scan/connect/link-up/DHCP/routing
  No persistent writes outside private namespace
  No HAL/credential/external-ping
  Cleanup reboot restores healthy v724
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore
import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210
import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
import native_wifi_pm_mdm_helper_selinux_context_v1200 as v1200

DEFAULT_OUT_DIR = Path("tmp/wifi/v1212-esoc-dev-node-before-cnss")
LATEST_POINTER = Path("tmp/wifi/latest-v1212-esoc-dev-node-before-cnss.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "ab95cb2379083833b59da84cad111379252c29f61092767a5c4fcc95e5328c81"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v247"

ESOC_DEV_NODE_FLAG = "--pm-observer-mknod-esoc-dev-node-before-cnss"
SUBSYS_ESOC0_FLAG = v1200.SUBSYS_ESOC0_FLAG

_ORIG_V1212_PATCH_DEFAULTS = None


def _v1212_child_command(args: Any) -> list[str]:
    """V1210 child command + esoc-0 dev node materialisation before cnss-daemon.

    Removes --pm-observer-open-subsys-esoc0-after-mdm-helper-esoc (reboot-trigger)
    and adds --pm-observer-mknod-esoc-dev-node-before-cnss (V1212 fix).
    """
    base = v1204.pm_dep_per_proxy_late_start_v1204_child_command(args)
    result: list[str] = []
    for x in base:
        if x == SUBSYS_ESOC0_FLAG:
            continue  # remove early-reboot trigger
        result.append(x)
    if ESOC_DEV_NODE_FLAG not in result:
        result.append(ESOC_DEV_NODE_FLAG)
    return result


def patch_defaults() -> None:
    global _ORIG_V1212_PATCH_DEFAULTS
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

    if _ORIG_V1212_PATCH_DEFAULTS is None:
        _ORIG_V1212_PATCH_DEFAULTS = v1210.patch_defaults

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1205.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1210.patch_defaults()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = _v1212_child_command
    v1106.pm_cnss_child_command = _v1212_child_command

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER


def _parse_esoc_node_evidence(child_output_text: str) -> dict:
    """Extract /dev/esoc-0 mknod result and peripheral name from child log."""
    result: dict[str, Any] = {
        "esoc_node_path": "",
        "esoc_node_mknod_rc": None,
        "esoc_node_mknod_errno": None,
        "esoc_node_created": None,
    }
    for line in child_output_text.splitlines():
        line = line.strip()
        if line.startswith("pm_service_trigger_observer.esoc_dev_node_before_cnss."):
            rest = line[len("pm_service_trigger_observer.esoc_dev_node_before_cnss."):]
            if rest.startswith("path="):
                result["esoc_node_path"] = rest[5:]
            elif rest.startswith("mknod_rc="):
                try:
                    result["esoc_node_mknod_rc"] = int(rest[9:])
                except ValueError:
                    pass
            elif rest.startswith("mknod_errno="):
                try:
                    result["esoc_node_mknod_errno"] = int(rest[12:])
                except ValueError:
                    pass
            elif rest.startswith("created="):
                try:
                    result["esoc_node_created"] = int(rest[8:]) == 1
                except ValueError:
                    pass
    return result


def decide_v1212(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = manifest.get("thread_analysis", {})
    esoc_node = manifest.get("esoc_node_evidence", {})

    esoc_created = esoc_node.get("esoc_node_created", False)
    esoc_mknod_rc = esoc_node.get("esoc_node_mknod_rc")

    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals", [])
    cnss_sdx50m = thread_analysis.get("cnss_registered_sdx50m", False)
    cnss_modem = thread_analysis.get("cnss_registered_modem", False)
    mdm_subsys_powerup_any = thread_analysis.get("mdm_subsys_powerup_any", False)

    # Check for per_mgr_esoc0 from child output
    per_mgr_esoc0_any = manifest.get("per_mgr_esoc0_any", False)

    # Check for wlan0
    wlan0_up = manifest.get("wlan0_up", False)

    if wlan0_up:
        return (
            "v1212-wlan0-up",
            True,
            "wlan0 interface appeared after esoc-0 node materialisation",
            "V1213: verify wlan0 full bring-up with link/DHCP gate",
        )

    if not cnss_peripherals and esoc_mknod_rc is None:
        return (
            "v1212-insufficient-data",
            False,
            "esoc node evidence and peripheral capture both absent",
            "check helper deploy and child command",
        )

    if not esoc_created and esoc_mknod_rc is not None:
        return (
            "v1212-peripheral-modem-esoc0-node-fail",
            False,
            f"mknod /dev/esoc-0 failed (rc={esoc_mknod_rc}); "
            f"cnss peripheral={cnss_peripherals}",
            "V1213: diagnose mknod failure (EACCES/EEXIST/etc)",
        )

    if cnss_sdx50m and per_mgr_esoc0_any:
        return (
            "v1212-peripheral-sdx50m-per-mgr-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M'; per_mgr opened subsys_esoc0; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1213: observe MDM power-on completion / WLFW service 69 / BDF / wlan0",
        )

    if cnss_sdx50m and not per_mgr_esoc0_any:
        return (
            "v1212-peripheral-sdx50m-no-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M' confirmed; per_mgr esoc0 not yet seen "
            f"(window may be short); mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1213: extend observation window or add MDM power-on observer",
        )

    if cnss_modem and not cnss_sdx50m:
        return (
            "v1212-peripheral-modem-no-esoc0",
            False,
            f"cnss-daemon still uses peripheral='modem'; esoc_node_created={esoc_created}; "
            f"mknod_rc={esoc_mknod_rc}",
            "V1213: diagnose why libmdmdetect still returns modem despite /dev/esoc-0",
        )

    thread_count = thread_analysis.get("thread_sample_count", 0)
    return (
        "v1212-insufficient-data",
        False,
        f"thread_count={thread_count} esoc_created={esoc_created} cnss_peripherals={cnss_peripherals}",
        "re-run with longer window or inspect observer output",
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
    manifest["cycle"] = "v1212"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["esoc_dev_node_flag"] = ESOC_DEV_NODE_FLAG
    manifest["esoc0_open_removed"] = True
    manifest["_run_dir"] = str(store.run_dir)

    # Extract esoc node evidence from child output
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

    esoc_node_evidence = _parse_esoc_node_evidence(child_output_text)
    manifest["esoc_node_evidence"] = esoc_node_evidence

    # Parse per_mgr_esoc0 from child output
    per_mgr_esoc0_any = False
    wlan0_up = False
    for line in child_output_text.splitlines():
        line = line.strip()
        if "per_mgr_has_esoc0=1" in line or "per_mgr_esoc0_any=1" in line:
            per_mgr_esoc0_any = True
        if "wlan0" in line and ("UP" in line or "wlan0_up=1" in line):
            wlan0_up = True
    manifest["per_mgr_esoc0_any"] = per_mgr_esoc0_any
    manifest["wlan0_up"] = wlan0_up

    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = v1210._parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    decision, passed, reason, next_step = decide_v1212(args, manifest)
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
