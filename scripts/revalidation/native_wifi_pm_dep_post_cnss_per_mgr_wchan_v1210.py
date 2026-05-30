#!/usr/bin/env python3
"""V1210: per_mgr thread wchan capture after cnss-daemon connects.

Removes --pm-observer-open-subsys-esoc0-after-mdm-helper-esoc so the device
does NOT reboot early.  Thread sampling then extends through cnss-daemon
startup (pph+25s) to observe whether per_mgr enters mdm_subsys_powerup after
cnss-daemon's pm_client_register.

Decision matrix:
  v1210-per-mgr-mdm-subsys-powerup-after-cnss  – per_mgr tries subsys_esoc0
  v1210-per-mgr-binder-only-after-cnss          – per_mgr stays binder_ioctl_write_read
  v1210-cnss-daemon-not-seen                    – cnss still absent (window too short)
  v1210-per-mgr-not-found                       – pm-service disappeared
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore
import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
import native_wifi_pm_mdm_helper_selinux_context_v1200 as v1200
import native_wifi_pm_dep_pm_proxy_helper_esoc_observe_v1209 as v1209

DEFAULT_OUT_DIR = Path("tmp/wifi/v1210-post-cnss-per-mgr-wchan")
LATEST_POINTER = Path("tmp/wifi/latest-v1210-post-cnss-per-mgr-wchan.txt")
DEFAULT_EXECNS_HELPER_SHA256 = v1209.DEFAULT_EXECNS_HELPER_SHA256
DEFAULT_EXECNS_HELPER_MARKER = v1209.DEFAULT_EXECNS_HELPER_MARKER

SUBSYS_ESOC0_FLAG = v1200.SUBSYS_ESOC0_FLAG

_ORIG_V1210_PATCH_DEFAULTS = None


def _no_esoc0_child_command(args: Any) -> list[str]:
    """V1204 child command with esoc0 open flag removed to prevent early reboot."""
    base = v1204.pm_dep_per_proxy_late_start_v1204_child_command(args)
    return [x for x in base if x != SUBSYS_ESOC0_FLAG]


def patch_defaults() -> None:
    global _ORIG_V1210_PATCH_DEFAULTS
    import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
    import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod
    import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod

    if _ORIG_V1210_PATCH_DEFAULTS is None:
        _ORIG_V1210_PATCH_DEFAULTS = v1209.patch_defaults

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1205.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1209.patch_defaults()

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    # Override child command: remove esoc0 open flag so device does not reboot
    v1183_mod.pm_per_proxy_vndservice_gate_child_command = _no_esoc0_child_command
    v1106.pm_cnss_child_command = _no_esoc0_child_command

    for module in [v1177_chain, v1165, v1106]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
        module.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER


def _parse_thread_samples(tracefs: dict) -> dict:
    """Classify per_mgr threads across all samples.

    Also extracts cnss-daemon pm_client_register peripheral name from tracefs.
    Uses dynamic threshold: 'late' = last half of captured samples.
    """
    thread_samples = tracefs.get("thread_samples", [])
    # Build per-sample index: {index: [list of thread dicts]}
    by_index: dict[int, list[dict]] = {}
    for ts in thread_samples:
        idx = int(ts.get("index", -1))
        by_index.setdefault(idx, []).append(ts)

    last_idx = max(by_index) if by_index else None
    mid_idx = (last_idx // 2) if last_idx is not None else 0

    # Collect all unique wchans
    all_pm_wchans: list[str] = []
    late_pm_wchans: list[str] = []  # last half of samples
    for idx in sorted(by_index):
        for ts in by_index[idx]:
            wc = ts.get("wchan", "")
            if not wc:
                continue
            if wc not in all_pm_wchans:
                all_pm_wchans.append(wc)
            if idx >= mid_idx and wc not in late_pm_wchans:
                late_pm_wchans.append(wc)

    # cnss-daemon peripheral name from tracefs uprobe
    client_args_by_comm = tracefs.get("client_register_args_by_comm") or {}
    cnss_peripherals = [
        entry.get("peripheral", "")
        for entry in client_args_by_comm.get("cnss-daemon", [])
        if entry.get("peripheral")
    ]

    return {
        "thread_sample_count": len(by_index),
        "last_sample_idx": last_idx,
        "all_pm_wchans": all_pm_wchans,
        "late_pm_wchans": late_pm_wchans,
        "mdm_subsys_powerup_any": "mdm_subsys_powerup" in all_pm_wchans,
        "mdm_subsys_powerup_late": "mdm_subsys_powerup" in late_pm_wchans,
        "binder_ioctl_late": "binder_ioctl_write_read" in late_pm_wchans,
        "cnss_registered_peripherals": cnss_peripherals,
        "cnss_registered_sdx50m": "SDX50M" in cnss_peripherals,
        "cnss_registered_modem": "modem" in cnss_peripherals,
    }


def decide_v1210(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    pm_pid = tracefs.get("pm_service_pid")
    thread_analysis = manifest.get("thread_analysis", {})
    thread_count = thread_analysis.get("thread_sample_count", 0)
    last_idx = thread_analysis.get("last_sample_idx", 0) or 0
    mdm_any = thread_analysis.get("mdm_subsys_powerup_any", False)
    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals", [])
    cnss_sdx50m = thread_analysis.get("cnss_registered_sdx50m", False)
    cnss_modem = thread_analysis.get("cnss_registered_modem", False)
    binder_late = thread_analysis.get("binder_ioctl_late", False)

    if not pm_pid and thread_count == 0:
        # Check if tracefs ran but pm-service PID simply wasn't tracked
        pids = tracefs.get("pm_service_pids_by_sample") or {}
        if not pids:
            return (
                "v1210-per-mgr-not-found",
                False,
                "pm-service PID not found and no thread samples",
                "check pm-service start sequence",
            )

    # Definitive finding: cnss-daemon peripheral name
    if cnss_peripherals:
        if cnss_sdx50m and not mdm_any:
            return (
                "v1210-cnss-peripheral-sdx50m-no-powerup",
                False,
                f"cnss-daemon peripheral={cnss_peripherals}; SDX50M registered but mdm_subsys_powerup absent",
                "V1211: classify MDM hardware GPIO unblock path",
            )
        if cnss_modem and not cnss_sdx50m:
            return (
                "v1210-cnss-peripheral-modem-only",
                True,
                f"cnss-daemon peripheral={cnss_peripherals}; registered 'modem' not 'SDX50M' → "
                "per_mgr opens subsys_modem only; subsys_esoc0/MDM never triggered",
                "V1211: determine why cnss-daemon uses 'modem' not 'SDX50M' "
                "(ro.* build_prop, CNSS driver ioctl, or config file)",
            )
    if mdm_any:
        return (
            "v1210-per-mgr-mdm-subsys-powerup",
            True,
            "per_mgr thread in mdm_subsys_powerup; per_mgr tries subsys_esoc0",
            "V1211: classify what unblocks mdm_subsys_powerup (GPIO142 / MDM hardware)",
        )
    if binder_late and thread_count > 0:
        return (
            "v1210-per-mgr-binder-only",
            True,
            f"per_mgr stays in binder_ioctl_write_read (thread_count={thread_count}); "
            "no mdm_subsys_powerup; cnss peripheral not captured",
            "V1211: inspect cnss-daemon pm_client_register peripheral arg directly",
        )
    return (
        "v1210-insufficient-data",
        False,
        f"thread_count={thread_count} last_idx={last_idx} cnss_peripherals={cnss_peripherals}",
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
    manifest["cycle"] = "v1210"
    manifest["generated_at"] = _now_iso()
    manifest["per_proxy_pph_delta_ms"] = v1204.PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER
    manifest["esoc0_open_removed"] = True
    manifest["_run_dir"] = str(store.run_dir)

    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = _parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    decision, passed, reason, next_step = decide_v1210(args, manifest)
    manifest.update(
        {"decision": decision, "pass": passed, "reason": reason, "next_step": next_step}
    )

    # Also inherit pph_samples from v1209 if available
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
    print(f"thread_sample_count:        {thread_analysis.get('thread_sample_count', 0)}")
    print(f"last_sample_idx:            {thread_analysis.get('last_sample_idx')}")
    print(f"cnss_registered_peripherals:{thread_analysis.get('cnss_registered_peripherals')}")
    print(f"cnss_registered_sdx50m:     {thread_analysis.get('cnss_registered_sdx50m')}")
    print(f"cnss_registered_modem:      {thread_analysis.get('cnss_registered_modem')}")
    print(f"mdm_subsys_powerup_any:     {thread_analysis.get('mdm_subsys_powerup_any')}")
    print(f"all_pm_wchans:              {thread_analysis.get('all_pm_wchans')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
