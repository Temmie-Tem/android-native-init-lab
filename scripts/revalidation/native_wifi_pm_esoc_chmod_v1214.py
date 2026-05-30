#!/usr/bin/env python3
"""V1214: PM observer with /dev/esoc-0 chmod 0666 before cnss-daemon (helper v249).

V1213 FAIL root cause (revised hypothesis):
  - /dev/esoc-0 present (0660 root:radio), /sys/class/esoc-dev/ bound
  - cnss-daemon still peripheral='modem'
  - libmdmdetect esoc_framework_supported() may try open("/dev/esoc-0", O_RDONLY)
  - cnss-daemon uid=1000 gid=1000 groups={3003,3004,3005} — radio(1001) missing
  - Android cnss-daemon: group includes radio(1001) → open succeeds
  - Private namespace: no radio group → EACCES → false → peripheral='modem'

V1214 fix (helper v249):
  After mknod attempt, calls chmod(esoc0_path, 0666) to make /dev/esoc-0
  world-readable/writable so uid=system can open it regardless of radio group.

Expected: cnss-daemon peripheral='SDX50M' → per_mgr opens subsys_esoc0 →
          MDM power-on → WLFW → BDF → wlan0

Decision matrix: same as V1213 with v1214-* prefix
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore
import native_wifi_pm_esoc_class_dev_bind_v1213 as v1213
import native_wifi_pm_esoc_dev_node_before_cnss_v1212 as v1212
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204

DEFAULT_OUT_DIR = Path("tmp/wifi/v1214-esoc-chmod")
LATEST_POINTER = Path("tmp/wifi/latest-v1214-esoc-chmod.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "53698377bcc86468da971b917106fc9c8cc5b8eb2b64cfce0c4acb6bb572c239"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v249"

_ORIG_V1214_PATCH_DEFAULTS = None


def patch_defaults() -> None:
    global _ORIG_V1214_PATCH_DEFAULTS

    if _ORIG_V1214_PATCH_DEFAULTS is None:
        _ORIG_V1214_PATCH_DEFAULTS = v1213.patch_defaults

    import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1205.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1213.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1213.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1212.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1212.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1213.patch_defaults()

    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

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


def decide_v1214(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    thread_analysis = manifest.get("thread_analysis", {})
    esoc_node = manifest.get("esoc_node_evidence", {})
    cnss_sdx50m = thread_analysis.get("cnss_registered_sdx50m", False)
    cnss_modem = thread_analysis.get("cnss_registered_modem", False)
    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals", [])
    per_mgr_esoc0_any = manifest.get("per_mgr_esoc0_any", False)
    wlan0_up = manifest.get("wlan0_up", False)
    mdm_subsys_powerup_any = thread_analysis.get("mdm_subsys_powerup_any", False)
    chmod_rc = esoc_node.get("esoc_chmod_rc")
    esoc_mknod_rc = esoc_node.get("esoc_node_mknod_rc")

    if wlan0_up:
        return (
            "v1214-wlan0-up",
            True,
            "wlan0 appeared after esoc-0 chmod fix",
            "V1215: verify wlan0 link/DHCP gate",
        )

    if cnss_sdx50m and per_mgr_esoc0_any:
        return (
            "v1214-peripheral-sdx50m-per-mgr-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M'; per_mgr opened subsys_esoc0; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1215: MDM power-on completion / WLFW service 69 / BDF / wlan0",
        )

    if cnss_sdx50m and not per_mgr_esoc0_any:
        return (
            "v1214-peripheral-sdx50m-no-esoc0",
            True,
            f"cnss-daemon peripheral='SDX50M' confirmed; per_mgr esoc0 not yet seen",
            "V1215: extend observation window or add MDM power-on observer",
        )

    if cnss_modem and not cnss_sdx50m:
        chmod_info = f"chmod_rc={chmod_rc}"
        return (
            "v1214-peripheral-modem-dac-hypothesis-disproven",
            False,
            f"cnss-daemon still peripheral='modem' after chmod 0666; {chmod_info}; "
            f"esoc_mknod_rc={esoc_mknod_rc}",
            "V1215: disassemble libmdmdetect esoc_framework_supported for actual check",
        )

    thread_count = thread_analysis.get("thread_sample_count", 0)
    return (
        "v1214-insufficient-data",
        False,
        f"thread_count={thread_count} cnss_peripherals={cnss_peripherals}",
        "re-run with longer window",
    )


def _parse_chmod_rc(child_text: str) -> int | None:
    for line in child_text.splitlines():
        line = line.strip()
        if line.startswith("pm_service_trigger_observer.esoc_dev_node_before_cnss.chmod_rc="):
            try:
                return int(line.split("=", 1)[1])
            except ValueError:
                pass
    return None


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
    manifest["cycle"] = "v1214"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["esoc_dev_node_flag"] = v1212.ESOC_DEV_NODE_FLAG
    manifest["esoc_chmod_0666"] = True
    manifest["_run_dir"] = str(store.run_dir)

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
    esoc_node_evidence["esoc_chmod_rc"] = _parse_chmod_rc(child_output_text)
    manifest["esoc_node_evidence"] = esoc_node_evidence

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

    import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = v1210._parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    decision, passed, reason, next_step = decide_v1214(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

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
    print(f"esoc_node_mknod_rc:  {esoc_node_evidence.get('esoc_node_mknod_rc')}")
    print(f"esoc_chmod_rc:       {esoc_node_evidence.get('esoc_chmod_rc')}")
    print(f"cnss_peripherals:    {thread_analysis.get('cnss_registered_peripherals')}")
    print(f"cnss_sdx50m:         {thread_analysis.get('cnss_registered_sdx50m')}")
    print(f"per_mgr_esoc0_any:   {per_mgr_esoc0_any}")
    print(f"wlan0_up:            {wlan0_up}")
    print(f"mdm_powerup_any:     {thread_analysis.get('mdm_subsys_powerup_any')}")
    print(f"all_pm_wchans:       {thread_analysis.get('all_pm_wchans')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
