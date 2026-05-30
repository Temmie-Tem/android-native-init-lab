#!/usr/bin/env python3
"""V1216: PM observer with fake esoc_name="SDXPRAIRIE" bind-mount (helper v250).

V1215 HOST-ONLY PASS root cause (full disassembly of libmdmdetect.so + cnss-daemon):
  get_system_info() performs two scans:
    1. esoc bus scan: /sys/bus/esoc/devices/esoc0/esoc_name -> "SDX50M"
       stored as esoc_entry[0]: type=0, name="SDX50M"
    2. msm_subsys scan: /sys/bus/msm_subsys/devices/subsys0/name -> "modem"
       stored as esoc_entry[1]: type=1, name="modem"
  cnss-daemon pm_client_register first call (type=1 search):
    -> matches esoc_entry[1] (modem) -> peripheral='modem' (FIRES)
  cnss-daemon pm_client_register second call (type=0 + strcmp("SDXPRAIRIE")):
    -> esoc_entry[0] type=0 but "SDX50M" != "SDXPRAIRIE" -> NO MATCH
  per_mgr sees peripheral='modem' -> opens subsys_modem -> MDM never powered.

V1216 fix (helper v250):
  bind-mount a fake file containing "SDXPRAIRIE\n" over
  /sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_name in private chroot.
  -> get_soc_name("esoc0") returns "SDXPRAIRIE"
  -> esoc_entry[0]: type=0, name="SDXPRAIRIE"
  -> cnss-daemon second call: type=0 + strcmp("SDXPRAIRIE") == 0 -> MATCH
  -> pm_client_register(peripheral='SDXPRAIRIE')
  -> per_mgr opens subsys_esoc0
  -> MDM power-on -> WLFW service 69 -> BDF -> wlan0

Expected outcomes (tracefs uprobe, V1106 framework):
  pm_client_register_entry peripheral='SDXPRAIRIE'   (not 'modem')
  per_mgr_esoc0_any=True  (pm-service opens subsys_esoc0)
  mdm3 advances beyond OFFLINING
  WLFW service 69 / BDF / wlan0 may appear

Decision matrix:
  v1216-peripheral-sdxprairie-per-mgr-esoc0  -- correct peripheral + esoc0 open
  v1216-peripheral-sdxprairie-no-esoc0       -- peripheral correct, esoc0 not yet seen
  v1216-peripheral-modem-bind-fail           -- bind failed; modem still used
  v1216-peripheral-modem-unexpected          -- bind ok but peripheral still modem
  v1216-wlan0-up                             -- wlan0 appeared
  v1216-insufficient-data                   -- uprobe missing or window too short

Safety:
  No Wi-Fi scan/connect/link-up/DHCP/routing
  No persistent writes outside private namespace (bind is private mount ns only)
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
import native_wifi_pm_esoc_dev_node_before_cnss_v1212 as v1212
import native_wifi_pm_esoc_class_dev_bind_v1213 as v1213
import native_wifi_pm_esoc_chmod_v1214 as v1214

DEFAULT_OUT_DIR = Path("tmp/wifi/v1216-fake-esoc-name-sdxprairie")
LATEST_POINTER = Path("tmp/wifi/latest-v1216-fake-esoc-name-sdxprairie.txt")
DEFAULT_EXECNS_HELPER_SHA256 = (
    "db9531f09f2c69b7028fe2fcb10ffdbed1051f81542787a43c36fb8a553e7886"
)
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v250"

FAKE_ESOC_NAME_FLAG = "--pm-observer-fake-esoc-name-sdxprairie"

_ORIG_V1216_PATCH_DEFAULTS = None


def _v1216_child_command(args: Any) -> list[str]:
    """V1214 child command + fake esoc_name bind mount.

    Adds --pm-observer-fake-esoc-name-sdxprairie.
    Keeps --pm-observer-mknod-esoc-dev-node-before-cnss (from v247/v1212)
    and --pm-observer-mknod-esoc-dev-node-before-cnss chmod (v249/v1214)
    so the test includes all prior steps plus the new bind.
    """
    base = v1204.pm_dep_per_proxy_late_start_v1204_child_command(args)
    result: list[str] = []
    for x in base:
        # Remove the subsys_esoc0 early-open trigger (reboot-required)
        if x == v1212.SUBSYS_ESOC0_FLAG:
            continue
        result.append(x)
    if v1212.ESOC_DEV_NODE_FLAG not in result:
        result.append(v1212.ESOC_DEV_NODE_FLAG)
    if FAKE_ESOC_NAME_FLAG not in result:
        result.append(FAKE_ESOC_NAME_FLAG)
    return result


def patch_defaults() -> None:
    global _ORIG_V1216_PATCH_DEFAULTS
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

    if _ORIG_V1216_PATCH_DEFAULTS is None:
        _ORIG_V1216_PATCH_DEFAULTS = v1214.patch_defaults

    import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1205.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1214.patch_defaults()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = _v1216_child_command
    v1106.pm_cnss_child_command = _v1216_child_command

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER


def _parse_fake_esoc_name_evidence(child_output_text: str) -> dict:
    """Extract fake esoc_name bind mount result from child log."""
    result: dict[str, Any] = {
        "bind_rc": None,
        "source": None,
        "target": None,
        "content": None,
    }
    for line in child_output_text.splitlines():
        line = line.strip()
        if line.startswith("fake_esoc_name."):
            rest = line[len("fake_esoc_name."):]
            if rest.startswith("bind_rc="):
                try:
                    result["bind_rc"] = int(rest[8:])
                except ValueError:
                    pass
            elif rest.startswith("source="):
                result["source"] = rest[7:]
            elif rest.startswith("target="):
                result["target"] = rest[7:]
            elif rest.startswith("content="):
                result["content"] = rest[8:]
    return result


def decide_v1216(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    thread_analysis = manifest.get("thread_analysis", {})
    fake_esoc = manifest.get("fake_esoc_name_evidence", {})
    esoc_node = manifest.get("esoc_node_evidence", {})

    bind_rc = fake_esoc.get("bind_rc")
    bind_ok = bind_rc == 0

    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals", [])
    cnss_sdxprairie = "SDXPRAIRIE" in cnss_peripherals
    cnss_modem = thread_analysis.get("cnss_registered_modem", False)
    mdm_subsys_powerup_any = thread_analysis.get("mdm_subsys_powerup_any", False)
    per_mgr_esoc0_any = manifest.get("per_mgr_esoc0_any", False)
    wlan0_up = manifest.get("wlan0_up", False)

    if wlan0_up:
        return (
            "v1216-wlan0-up",
            True,
            "wlan0 appeared after fake esoc_name=SDXPRAIRIE bind mount",
            "V1217: verify wlan0 link/DHCP gate",
        )

    if not bind_ok and bind_rc is not None:
        return (
            "v1216-peripheral-modem-bind-fail",
            False,
            f"fake esoc_name bind mount failed (bind_rc={bind_rc}); "
            f"cnss_peripherals={cnss_peripherals}",
            "V1217: diagnose bind mount failure (ENOENT/EPERM/etc)",
        )

    if cnss_sdxprairie and per_mgr_esoc0_any:
        return (
            "v1216-peripheral-sdxprairie-per-mgr-esoc0",
            True,
            f"cnss-daemon peripheral='SDXPRAIRIE'; per_mgr opened subsys_esoc0; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1217: MDM power-on completion / WLFW service 69 / BDF / wlan0",
        )

    if cnss_sdxprairie and not per_mgr_esoc0_any:
        return (
            "v1216-peripheral-sdxprairie-no-esoc0",
            True,
            f"cnss-daemon peripheral='SDXPRAIRIE' confirmed; per_mgr esoc0 not yet seen; "
            f"mdm_subsys_powerup={mdm_subsys_powerup_any}",
            "V1217: extend observation window or add MDM power-on observer",
        )

    if cnss_modem and bind_ok:
        return (
            "v1216-peripheral-modem-unexpected",
            False,
            f"bind_rc=0 but cnss-daemon still peripheral='modem'; "
            f"esoc_mknod_rc={esoc_node.get('esoc_node_mknod_rc')}; "
            f"peripherals={cnss_peripherals}",
            "V1217: re-disassemble libmdmdetect with fake esoc_name context; "
            "check if get_soc_name actually reads through symlink inside chroot",
        )

    if not cnss_peripherals:
        return (
            "v1216-insufficient-data",
            False,
            f"peripheral capture absent; bind_rc={bind_rc}; "
            f"thread_count={thread_analysis.get('thread_sample_count', 0)}",
            "check helper deploy and child command",
        )

    return (
        "v1216-insufficient-data",
        False,
        f"cnss_peripherals={cnss_peripherals} bind_rc={bind_rc}",
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
    manifest["cycle"] = "v1216"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["esoc_dev_node_flag"] = v1212.ESOC_DEV_NODE_FLAG
    manifest["fake_esoc_name_flag"] = FAKE_ESOC_NAME_FLAG
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

    fake_esoc_evidence = _parse_fake_esoc_name_evidence(child_output_text)
    esoc_node_evidence = v1212._parse_esoc_node_evidence(child_output_text)
    manifest["fake_esoc_name_evidence"] = fake_esoc_evidence
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

    import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = v1210_mod._parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    decision, passed, reason, next_step = decide_v1216(args, manifest)
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
    print(f"fake_esoc_name_bind_rc:      {fake_esoc_evidence.get('bind_rc')}")
    print(f"fake_esoc_name_content:      {fake_esoc_evidence.get('content')}")
    print(f"esoc_node_mknod_rc:          {esoc_node_evidence.get('esoc_node_mknod_rc')}")
    print(f"cnss_registered_peripherals: {thread_analysis.get('cnss_registered_peripherals')}")
    print(f"cnss_registered_sdxprairie:  {'SDXPRAIRIE' in (thread_analysis.get('cnss_registered_peripherals') or [])}")
    print(f"per_mgr_esoc0_any:           {per_mgr_esoc0_any}")
    print(f"wlan0_up:                    {wlan0_up}")
    print(f"mdm_subsys_powerup_any:      {thread_analysis.get('mdm_subsys_powerup_any')}")
    print(f"all_pm_wchans:               {thread_analysis.get('all_pm_wchans')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
