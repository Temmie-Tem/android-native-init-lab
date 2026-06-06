#!/usr/bin/env python3
"""V1221: bounded PM/CNSS observer with private patched cnss-daemon SDX50M.

V1219 proved that the second type-0 vote path executes but the stock
cnss-daemon literal requests ``SDXPRAIRIE`` while libmdmdetect exposes the real
eSoC name ``SDX50M``.  V1220 staged a private patched cnss-daemon artifact that
changes only that selection literal.  This V1221 gate bind-mounts that private
artifact over ``/vendor/bin/cnss-daemon`` inside the helper's private namespace
and keeps the rest of the bounded PM/CNSS observer unchanged.

Safety:
  No Wi-Fi HAL, scan/connect/link-up, credential use, DHCP/route setup, or
  external ping.  No boot image or vendor partition write.  The private binary
  is deployed to /cache by a separate deploy-only gate and is used only through
  a private mount namespace.
"""

from __future__ import annotations

import datetime as dt
import json
import shlex
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_json, write_private_text

import native_wifi_cnss_mdmdetect_selection_trace_v1219 as v1219
import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
import native_wifi_pm_dep_per_proxy_late_esoc_observe_v1205 as v1205
import native_wifi_pm_dep_per_proxy_late_start_v1204 as v1204
import native_wifi_pm_esoc_chmod_v1214 as v1214
import native_wifi_pm_esoc_dev_node_before_cnss_v1212 as v1212
import native_wifi_pm_per_proxy_vndservice_gate_v1183 as v1183_mod
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod


DEFAULT_OUT_DIR = Path("tmp/wifi/v1221-private-cnss-daemon-sdx50m-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1221-private-cnss-daemon-sdx50m-live.txt")
HELPER_SHA256_V253 = "d61cae5e8b6de997aff6c06ca08140e8d8b38951ca408b3e91b6e39577329f36"
HELPER_MARKER_V253 = "a90_android_execns_probe v253"
PRIVATE_CNSS_FLAG = "--pm-observer-private-cnss-daemon-sdx50m"
PRIVATE_CNSS_PATH_FLAG = "--private-cnss-daemon-path"
PRIVATE_CNSS_PATH = "/cache/bin/cnss-daemon.sdx50m"
PATCHED_CNSS_SHA256 = "784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _v1221_child_command(args: Any) -> list[str]:
    base_command = v1204.pm_dep_per_proxy_late_start_v1204_child_command(args)
    result: list[str] = []
    skip_next = False
    for index, item in enumerate(base_command):
        if skip_next:
            skip_next = False
            continue
        if item == v1212.SUBSYS_ESOC0_FLAG:
            continue
        if item == "--pm-observer-fake-esoc-name-sdxprairie":
            continue
        if item == "--pm-observer-fake-esoc-name-readback-only":
            continue
        if item == PRIVATE_CNSS_PATH_FLAG and index + 1 < len(base_command):
            skip_next = True
            continue
        result.append(item)
    if v1212.ESOC_DEV_NODE_FLAG not in result:
        result.append(v1212.ESOC_DEV_NODE_FLAG)
    if PRIVATE_CNSS_FLAG not in result:
        result.append(PRIVATE_CNSS_FLAG)
    if PRIVATE_CNSS_PATH_FLAG not in result:
        result.extend([PRIVATE_CNSS_PATH_FLAG, PRIVATE_CNSS_PATH])
    return result


def _write_child_script_v1221(args: Any, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    command = v1106_mod.pm_cnss_child_command(args)
    grep_pattern = (
        r"^(A90_EXECNS_(BEGIN|END|STDOUT_END)|"
        r"private_cnss_daemon\.|"
        r"pm_service_trigger_observer\.|"
        r"wifi_vndservice_query\.|"
        r"wifi_companion_qrtr_readback\.)"
    )
    script = "\n".join([
        f"#!{args.busybox} sh",
        f"OUT={shlex.quote(args.child_output)}",
        f"{args.busybox} mkdir -p {shlex.quote(args.work_dir)}",
        " ".join(shlex.quote(part) for part in command) + ' > "$OUT" 2>&1',
        "rc=$?",
        f"{args.busybox} grep -E {shlex.quote(grep_pattern)} \"$OUT\" || true",
        f"echo v1106.child_full_output={shlex.quote(args.child_output)}",
        "echo v1106.child_rc=$rc",
        "exit $rc",
        "",
    ])
    store.write_text("host/pm-cnss-voter-child-script.txt", script)
    v1106_mod.base.run_a90ctl(args, store, steps, "workdir-mkdir", ["run", args.busybox, "mkdir", "-p", args.work_dir], timeout=12.0)
    v1106_mod.append_device_file(args, store, steps, args.child_script, script, "child-script")


def patch_defaults() -> None:
    v1214.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1214.LATEST_POINTER = LATEST_POINTER
    v1214.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256_V253
    v1214.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER_V253
    v1214.patch_defaults()

    v1205.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1205.LATEST_POINTER = LATEST_POINTER
    v1205.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256_V253
    v1205.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER_V253

    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    v1183_mod.pm_per_proxy_vndservice_gate_child_command = _v1221_child_command
    v1106.pm_cnss_child_command = _v1221_child_command
    v1106_mod.pm_cnss_child_command = _v1221_child_command
    v1106_mod.write_child_script = _write_child_script_v1221

    for module in [v1177_chain, v1165, v1106, v1106_mod]:
        module.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256_V253
        module.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER_V253

    original_events = tuple(v1106_mod.EVENT_SPECS)
    existing_labels = {label for label, _binary_key, _offset, _fetch in original_events}
    extra_events = tuple(
        event for event in v1219.CNSS_SELECTION_EVENT_SPECS
        if event[0] not in existing_labels
    )
    v1106_mod.EVENT_SPECS = original_events + extra_events
    v1106_mod.tracefs_collector_script = v1219._patch_collector_script(
        v1106_mod.tracefs_collector_script
    )


def _parse_prefixed_lines(text: str, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix) and "=" in line:
            key, value = line[len(prefix):].split("=", 1)
            result[key] = value
    return result


def _read_child_output(manifest: dict[str, Any]) -> str:
    child_output_text = ""
    run_dir = manifest.get("_run_dir", "")
    for step in manifest.get("steps", []):
        step_file = step.get("file", "") or ""
        if run_dir and step_file:
            try:
                child_output_text += Path(run_dir, step_file).read_text(errors="replace")
            except OSError:
                pass
        child_output_text += step.get("text", "") or ""
    return child_output_text


def _extract_sdx50m_selection(selection: dict[str, Any]) -> dict[str, Any]:
    parsed_by_label = selection.get("parsed_by_label") or {}
    pm_vote_entries = selection.get("pm_vote_entries") or []
    strcmp_calls = selection.get("strcmp_calls") or []
    named_register = parsed_by_label.get("cnss_named_register_call", [])
    null_register = parsed_by_label.get("cnss_nullname_register_call", [])
    return {
        "sdx50m_vote_seen": any(
            entry.get("vote_type") in {"0x0", "0"} and entry.get("vote_name") == "SDX50M"
            for entry in pm_vote_entries
        ),
        "sdx50m_candidate_seen": any(
            entry.get("candidate") == "SDX50M" or entry.get("requested") == "SDX50M"
            for entry in strcmp_calls
        ),
        "sdx50m_register_call_seen": any(
            entry.get("peripheral") == "SDX50M" for entry in named_register
        ),
        "modem_register_call_seen": any(
            entry.get("peripheral") == "modem" for entry in null_register
        ),
    }


def _extract_selection_trace(observer_text: str) -> dict[str, Any]:
    selection = v1219._extract_selection_trace(observer_text)
    parsed_by_label: dict[str, list[dict[str, str]]] = {}
    for label, lines in (selection.get("lines_by_label") or {}).items():
        parsed_by_label[label] = [v1219._keyvals(line) for line in lines]
    selection["parsed_by_label"] = parsed_by_label
    selection.update(_extract_sdx50m_selection(selection))
    return selection


def decide_v1221(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1221-private-cnss-daemon-plan-ready",
            True,
            "plan-only; no tracefs write, daemon start, or Wi-Fi action executed",
            "deploy helper v253 and patched cnss-daemon artifact before bounded live run",
        )

    private_cnss = manifest.get("private_cnss_daemon") or {}
    selection = manifest.get("cnss_mdmdetect_selection_trace") or {}
    thread_analysis = manifest.get("thread_analysis") or {}
    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals") or []
    per_mgr_esoc0_any = manifest.get("per_mgr_esoc0_any", False)
    wlan0_up = manifest.get("wlan0_up", False)
    bind_rc_text = private_cnss.get("bind_rc")
    bind_rc = None
    if bind_rc_text is not None:
        try:
            bind_rc = int(bind_rc_text)
        except (TypeError, ValueError):
            bind_rc = None

    if wlan0_up:
        return (
            "v1221-wlan0-up",
            True,
            "wlan0 appeared during private patched cnss-daemon SDX50M observer",
            "V1222: bounded link/DHCP gate; no credential persistence beyond explicit connect test",
        )
    if bind_rc not in {None, 0}:
        return (
            "v1221-private-cnss-bind-failed",
            False,
            f"private cnss-daemon bind failed bind_rc={bind_rc}",
            "inspect helper namespace path/SELinux/cache artifact permissions",
        )
    if "SDX50M" in cnss_peripherals and per_mgr_esoc0_any:
        return (
            "v1221-sdx50m-per-mgr-esoc0",
            True,
            "patched cnss-daemon registered SDX50M and per_mgr opened subsys_esoc0",
            "V1222: observe MDM power-on completion / WLFW service 69 / BDF / wlan0",
        )
    if "SDX50M" in cnss_peripherals or selection.get("sdx50m_register_call_seen"):
        return (
            "v1221-sdx50m-registered-no-esoc0",
            True,
            f"SDX50M registration confirmed but per_mgr_esoc0_any={per_mgr_esoc0_any}",
            "V1222: extend PM observer or trace pm-service esoc0 open after SDX50M registration",
        )
    if selection.get("counts", {}).get("cnss_pm_vote_entry", 0) == 0:
        return (
            "v1221-cnss-selection-probe-missing",
            False,
            "cnss pm vote entry uprobe did not fire",
            "verify private bind and cnss-daemon text mapping",
        )
    if not selection.get("sdx50m_vote_seen"):
        return (
            "v1221-sdx50m-vote-not-seen",
            False,
            f"type-0 SDX50M vote missing; vote_names={selection.get('vote_names')}",
            "verify patched artifact was selected and executed inside private namespace",
        )
    if not selection.get("sdx50m_candidate_seen"):
        return (
            "v1221-mdmdetect-entry-not-sdx50m",
            False,
            f"SDX50M vote was called but strcmp never saw SDX50M; type_compare={selection.get('type_compare_entries')}",
            "re-check libmdmdetect eSoC filtering under real SDX50M path",
        )
    if selection.get("sdx50m_candidate_seen") and not selection.get("sdx50m_register_call_seen"):
        return (
            "v1221-sdx50m-compare-no-register",
            False,
            f"SDX50M compare observed but no named register call; strcmp_results={selection.get('strcmp_results')}",
            "trace branch after strcmp result",
        )
    if "modem" in cnss_peripherals:
        return (
            "v1221-still-registers-modem",
            False,
            f"cnss-daemon still registered modem; cnss_peripherals={cnss_peripherals}",
            "inspect private bind markers and cnss-daemon mapping identity",
        )
    return (
        "v1221-insufficient-data",
        False,
        f"cnss_peripherals={cnss_peripherals}; selection_counts={selection.get('counts')}",
        "inspect full observer trace and child output",
    )


def main() -> int:
    patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1221"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = HELPER_MARKER_V253
    manifest["helper_sha256"] = HELPER_SHA256_V253
    manifest["private_cnss_daemon_flag"] = PRIVATE_CNSS_FLAG
    manifest["private_cnss_daemon_path"] = PRIVATE_CNSS_PATH
    manifest["patched_cnss_sha256"] = PATCHED_CNSS_SHA256
    manifest["esoc_dev_node_flag"] = v1212.ESOC_DEV_NODE_FLAG
    manifest["_run_dir"] = str(store.run_dir)

    child_output_text = _read_child_output(manifest)
    manifest["private_cnss_daemon"] = _parse_prefixed_lines(child_output_text, "private_cnss_daemon.")
    manifest["esoc_node_evidence"] = v1212._parse_esoc_node_evidence(child_output_text)

    per_mgr_esoc0_any = False
    wlan0_up = False
    for line in child_output_text.splitlines():
        stripped = line.strip()
        if (
            "per_mgr_has_esoc0=1" in stripped
            or "per_mgr_esoc0_any=1" in stripped
            or "__subsystem_get: esoc0" in stripped
            or "Changing subsys fw_name to esoc0" in stripped
        ):
            per_mgr_esoc0_any = True
        if "wlan0" in stripped and ("UP" in stripped or "wlan0_up=1" in stripped):
            wlan0_up = True
    manifest["per_mgr_esoc0_any"] = per_mgr_esoc0_any
    manifest["wlan0_up"] = wlan0_up

    import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    thread_analysis = v1210_mod._parse_thread_samples(tracefs)
    manifest["thread_analysis"] = thread_analysis

    observer_path = store.run_dir / "host/pm-server-wchan-tracefs-observer.txt"
    observer_text = observer_path.read_text(encoding="utf-8", errors="replace") if observer_path.exists() else ""
    selection = _extract_selection_trace(observer_text)
    manifest["cnss_mdmdetect_selection_trace"] = selection

    decision, passed, reason, next_step = decide_v1221(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"private_cnss_bind_rc:       {manifest['private_cnss_daemon'].get('bind_rc')}")
    print(f"cnss_registered_peripherals:{thread_analysis.get('cnss_registered_peripherals')}")
    print(f"sdx50m_vote_seen:           {selection.get('sdx50m_vote_seen')}")
    print(f"sdx50m_candidate_seen:      {selection.get('sdx50m_candidate_seen')}")
    print(f"sdx50m_register_call_seen:  {selection.get('sdx50m_register_call_seen')}")
    print(f"per_mgr_esoc0_any:          {per_mgr_esoc0_any}")
    print(f"wlan0_up:                   {wlan0_up}")
    print(f"selection_counts:           {selection.get('counts')}")
    print(f"vote_names:                 {selection.get('vote_names')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
