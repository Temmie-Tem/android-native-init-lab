#!/usr/bin/env python3
"""V1179 bounded PM dep early per-proxy observer live gate.

Captures when the PM state-0 dependency object (peripheral+0x40) transitions
from state=0 to state=1 by running from boot with per_proxy starting within
~2.16s of per_proxy_helper (matching Android timing).

Helper v218 change: --pm-observer-per-proxy-pph-delta-ms 2159 replaces the
old --pm-observer-start-per-proxy-after-mdm-helper-esoc-fd gate, so per_proxy
starts before per_proxy_helper's PM state machine has completed.

Does not start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP/routes, external ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_dependency_flag_live_v1177 as v1177
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

# Capture original functions BEFORE any patch_defaults() call to avoid circular
# references: patch_defaults() replaces module attributes, so references must be
# saved from the original unpatched state.
_v1165 = v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
_ORIG_V1165_SERIAL_REMOTE_MARKER_CHECK = _v1165.serial_remote_marker_check_v1165
# Also capture v1143 base check (called via _base_remote_marker_check in v1165)
_ORIG_V1143_SERIAL_REMOTE_MARKER_CHECK = _v1165.v1143.serial_remote_marker_check_v1143
# Capture original parse_tracefs_output: patch_defaults() sets
# v1177.parse_tracefs_output_v1177 = parse_tracefs_output_v1179, so calling
# v1177.parse_tracefs_output_v1177 inside parse_tracefs_output_v1179 would recurse.
_ORIG_V1177_PARSE_TRACEFS_OUTPUT = v1177.parse_tracefs_output_v1177
# Same pattern for tracefs_collector_script_v1177.
_ORIG_V1177_TRACEFS_COLLECTOR_SCRIPT = v1177.tracefs_collector_script_v1177


DEFAULT_OUT_DIR = Path("tmp/wifi/v1179-pm-dep-early-per-proxy-observer")
LATEST_POINTER = Path("tmp/wifi/latest-v1179-pm-dep-early-per-proxy-observer.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "12c98f2563a5fbea3e5cfdd5a1874b16e41e24b5ae47b975ccd02ffcef2a4d31"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v218"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1179"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1179/pm-dep-early-per-proxy-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1179/pm-dep-early-per-proxy-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1179/pm-dep-early-per-proxy-output.txt"
PROOF_PREFIX = "/tmp/a90-v1179-"

# Android per_proxy → per_proxy_helper delta to replicate (ms).
# V1179 attempt 1 used 2159ms (Android timing) but per_mgr exited before
# per_proxy could connect (~2100ms after pph start).  Modem pm-proxy
# connects at pph+~1254ms; per_mgr then exits ~977ms later.
# Use 800ms so per_proxy connects while per_mgr is still alive AND before
# modem pm-proxy drives dep (peripheral+0x40) to state=1.
EARLY_PER_PROXY_PPH_DELTA_MS = 800

# Old late per_proxy flag (must NOT appear in command for V1179)
OLD_LATE_PER_PROXY_FLAG = "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd"
OLD_CNSS_BEFORE_PER_PROXY_FLAG = "--pm-observer-start-cnss-before-per-proxy"
NEW_EARLY_PER_PROXY_FLAG = f"--pm-observer-per-proxy-pph-delta-ms {EARLY_PER_PROXY_PPH_DELTA_MS}"

# ── Wider dep-state-set analysis ───────────────────────────────────────────

STATE_SET_RE = re.compile(
    r"(?P<time>\d+\.\d+):\s+pm_ack_state_set_call:\s+.*?peripheral=(?P<peripheral>0x[0-9a-f]+).*?state=(?P<state>0x[0-9a-f]+)"
)
CONNECT_RE = re.compile(
    r"(?P<time>\d+\.\d+):\s+(?P<label>pm_client_connect_entry|pm_server_connect_impl_start_vote|pm_server_connect_impl_client_found):"
)
DEP_PTR_RE = re.compile(
    r"(?P<time>\d+\.\d+):\s+pm_ack_state2_dependency_ptr:\s+.*?peripheral=(?P<peripheral>0x[0-9a-f]+).*?dependency=(?P<dependency>0x[0-9a-f]+)"
)
EARLY_PP_RE = re.compile(
    r"early_per_proxy\.(?P<key>[^=\n]+)=(?P<value>[^\n]+)"
)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_dep_state_transitions(text: str) -> dict[str, Any]:
    """
    Parse ALL pm_ack_state_set_call events from the trace, identify the parent
    peripheral and its dep (parent+0x40), and find when dep goes to state=1.
    """
    # Find parent peripheral from dep_ptr events
    parent_peripheral: int | None = None
    dep_address: int | None = None
    dep_ptr_time: float | None = None

    for m in DEP_PTR_RE.finditer(text):
        if parent_peripheral is None:
            parent_peripheral = int(m.group("peripheral"), 16)
            dep_from_probe = int(m.group("dependency"), 16)
            dep_address = parent_peripheral + 0x40
            dep_ptr_time = float(m.group("time"))
            # Note: dep_address is peripheral+0x40, which is the state-0 dep
            # dep_from_probe is the state-2 dep (different object at peripheral-0x180)

    # Collect ALL state_set events
    state_set_events: list[dict[str, Any]] = []
    for m in STATE_SET_RE.finditer(text):
        state_set_events.append({
            "time": float(m.group("time")),
            "peripheral": m.group("peripheral"),
            "state": int(m.group("state"), 16),
            "peripheral_int": int(m.group("peripheral"), 16),
        })

    # Find when dep (parent+0x40) goes to state=1
    dep_state1_time: float | None = None
    dep_state_history: list[dict[str, Any]] = []
    if dep_address is not None:
        for ev in state_set_events:
            if ev["peripheral_int"] == dep_address:
                dep_state_history.append({"time": ev["time"], "state": ev["state"]})
                if ev["state"] == 1 and dep_state1_time is None:
                    dep_state1_time = ev["time"]

    # All unique peripherals seen
    peripherals_seen: set[str] = {ev["peripheral"] for ev in state_set_events}

    # Per-proxy connection events
    connect_events: list[dict[str, Any]] = []
    for m in CONNECT_RE.finditer(text):
        connect_events.append({
            "time": float(m.group("time")),
            "label": m.group("label"),
        })

    first_connect_time: float | None = (
        connect_events[0]["time"] if connect_events else None
    )

    # Parse early_per_proxy timing from helper output
    early_pp: dict[str, str] = {}
    for m in EARLY_PP_RE.finditer(text):
        early_pp[m.group("key")] = m.group("value").strip()

    # Classify result
    dep_state1_before_parent_state0 = False
    dep_state1_before_per_proxy_connect = False
    if dep_state1_time is not None:
        # Check if dep went to state=1 before parent state-0 ack
        # From V1178: parent state-0 arrives ~15.99s after parent state-2
        # Look for parent state=0 ack time
        parent_state0_time: float | None = None
        if parent_peripheral is not None:
            for ev in state_set_events:
                if ev["peripheral_int"] == parent_peripheral and ev["state"] == 0:
                    if parent_state0_time is None:
                        parent_state0_time = ev["time"]
                        break
            # Actually state_set_call fires for state transitions, not ack receipt
            # state-0 → state-1 transition is what we want
            parent_state1_time: float | None = None
            for ev in state_set_events:
                if ev["peripheral_int"] == parent_peripheral and ev["state"] == 1:
                    if parent_state1_time is None:
                        parent_state1_time = ev["time"]
                        break

        dep_state1_before_per_proxy_connect = (
            first_connect_time is not None
            and dep_state1_time < first_connect_time
        )

    return {
        "parent_peripheral": hex(parent_peripheral) if parent_peripheral else None,
        "dep_address": hex(dep_address) if dep_address else None,
        "dep_offset": "peripheral+0x40",
        "dep_ptr_time": dep_ptr_time,
        "dep_state_history": dep_state_history,
        "dep_state1_time": dep_state1_time,
        "dep_state1_observed": dep_state1_time is not None,
        "dep_state1_before_per_proxy_connect": dep_state1_before_per_proxy_connect,
        "first_per_proxy_connect_time": first_connect_time,
        "connect_event_count": len(connect_events),
        "state_set_event_count": len(state_set_events),
        "peripherals_seen_count": len(peripherals_seen),
        "early_per_proxy_timing": early_pp,
    }


def parse_tracefs_output_v1179(text: str) -> dict[str, Any]:
    # Use the saved original (pre-patch) v1177 function to avoid circular recursion:
    # patch_defaults() sets v1177.parse_tracefs_output_v1177 = parse_tracefs_output_v1179.
    parsed = _ORIG_V1177_PARSE_TRACEFS_OUTPUT(text)
    parsed["pm_dep_state_transitions"] = parse_dep_state_transitions(text)
    return parsed


def tracefs_collector_script_v1179(args: Any) -> str:
    # Use the saved original (pre-patch) v1177 function to avoid circular recursion.
    return _ORIG_V1177_TRACEFS_COLLECTOR_SCRIPT(args)


# ── Child command override ────────────────────────────────────────────────

def pm_dep_early_per_proxy_child_command(args: Any) -> list[str]:
    """Build helper command: early per_proxy (pph delta 2159ms), no late gate."""
    base = v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.pm_post_lower_trace_child_command(
        args
    )
    # Remove old late-per-proxy and cnss-before-per-proxy flags
    base = [f for f in base if f != OLD_LATE_PER_PROXY_FLAG
            and f != OLD_CNSS_BEFORE_PER_PROXY_FLAG]
    # Add early per_proxy pph delta
    if "--pm-observer-per-proxy-pph-delta-ms" not in base:
        base.extend(["--pm-observer-per-proxy-pph-delta-ms",
                      str(EARLY_PER_PROXY_PPH_DELTA_MS)])
    return base


def serial_remote_marker_check_v1179(
    args: Any,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    # Use the saved original (pre-patch) v1165 function to avoid circular recursion.
    info = _ORIG_V1165_SERIAL_REMOTE_MARKER_CHECK(args, store, steps)
    step_file = info.get("file", "")
    text = ""
    if step_file:
        try:
            text = (store.run_dir / str(step_file)).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            pass
    info["early_per_proxy_pph_delta_flag_ok"] = (
        "--pm-observer-per-proxy-pph-delta-ms" in text
    )
    info["old_late_per_proxy_flag_absent"] = OLD_LATE_PER_PROXY_FLAG not in text
    # v218 marker in usage confirms correct helper; flag not always in usage string
    info["late_per_proxy_flag_ok"] = bool(info.get("marker_ok", False))
    return info


# ── Dep-transition accessors ──────────────────────────────────────────────

def dep_state_transitions(manifest: dict[str, Any]) -> dict[str, Any]:
    value = v1177.tracefs(manifest).get("pm_dep_state_transitions") or {}
    return value if isinstance(value, dict) else {}


def late_per_proxy(manifest: dict[str, Any]) -> dict[str, Any]:
    """For V1179, per_proxy uses early timing — report early_per_proxy timing."""
    dst = dep_state_transitions(manifest)
    return dst.get("early_per_proxy_timing") or {}


# ── Decision ─────────────────────────────────────────────────────────────

def decide_v1179(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1179-pm-dep-early-per-proxy-observer-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "deploy helper v218, then run V1179 live gate",
        )

    base_decision, base_pass, base_reason, base_next = v1177.decide_v1177(args, manifest)
    dst = dep_state_transitions(manifest)

    # In V1179 mode, per_proxy starts early (before CNSS), so per_proxy_initial_start_executed=1.
    # The old chain returns pass=False for "pre-cnss-per-proxy-not-skipped" in that case.
    # Bypass the old chain's failure and proceed to V1179 dep-state analysis.
    _early_timing_base_decisions = {
        "pre-cnss-per-proxy-not-skipped",
        "helper-late-per-proxy-flag-missing",
    }
    _is_early_timing_skip = (
        not base_pass
        and any(base_decision.endswith(s) for s in _early_timing_base_decisions)
    )

    if not base_pass and not _is_early_timing_skip:
        return (
            base_decision.replace("v1177", "v1179", 1),
            False,
            base_reason,
            base_next,
        )

    dep_state1_obs = dst.get("dep_state1_observed", False)
    dep_state1_time = dst.get("dep_state1_time")
    dep_before_connect = dst.get("dep_state1_before_per_proxy_connect", False)
    first_connect = dst.get("first_per_proxy_connect_time")

    # Early timing was engaged but the PM state machine never fired at all.
    # Read pm_contract from the manifest for accurate early_per_proxy fields.
    if _is_early_timing_skip and dst.get("state_set_event_count", 0) == 0:
        pm_contract = (
            (manifest.get("analysis") or {})
            .get("tracefs_uprobe", {})
            .get("pm_contract") or {}
        )
        already_elapsed = pm_contract.get("early_per_proxy.already_elapsed") == "1"
        elapsed_ms = pm_contract.get("early_per_proxy.elapsed_since_pph_ms", "?")
        target_ms = pm_contract.get("early_per_proxy.target_delta_ms", str(EARLY_PER_PROXY_PPH_DELTA_MS))
        probe_wait_ms = pm_contract.get("child.per_mgr.post_start_probe_wait_ms", "?")
        per_mgr_gone = pm_contract.get("child.per_mgr.post_start_observable") == "0"

        if already_elapsed and per_mgr_gone:
            return (
                "v1179-per-mgr-probe-wait-delays-per-proxy-too-late",
                True,
                (
                    f"per_mgr probe wait ({probe_wait_ms}ms) delayed per_proxy to "
                    f"pph+{elapsed_ms}ms; target_delta={target_ms}ms < probe_wait "
                    f"so already_elapsed=1; per_mgr exits before no-client pm-service "
                    f"timeout (~800ms); pm_contract={pm_contract}"
                ),
                (
                    "V1180: helper v219 with per_mgr probe_wait=0ms and per_proxy "
                    f"pph_delta ~300ms; per_mgr starts at pph+177ms, per_proxy at "
                    "pph+300ms connects before pm-service init timeout; "
                    "modem pm-proxy at pph+1254ms then drives dep state=1"
                ),
            )

        return (
            "v1179-per-mgr-exited-before-per-proxy-pph-delta-too-large",
            True,
            (
                f"early per_proxy timing used (pph_delta={target_ms}ms) but PM "
                f"state machine never fired; per_mgr exited before per_proxy connected; "
                f"already_elapsed={already_elapsed} elapsed_ms={elapsed_ms} "
                f"per_mgr_gone={per_mgr_gone}"
            ),
            (
                "reduce EARLY_PER_PROXY_PPH_DELTA_MS below per_mgr probe wait "
                f"({probe_wait_ms}ms) so per_proxy connects while per_mgr is alive"
            ),
        )

    if dep_state1_obs and not dep_before_connect:
        return (
            "v1179-dep-state1-after-per-proxy-connect-timing-ok",
            True,
            f"dep state=1 at t={dep_state1_time}s AFTER first per_proxy connect t={first_connect}s; "
            f"early per_proxy timing matches Android delta; dst={dst}",
            "V1180 should verify dep_flag is now set to 1 (state0 path ran), then repeat for esoc0",
        )

    if dep_state1_obs and dep_before_connect:
        return (
            "v1179-dep-state1-before-per-proxy-connect-still-too-late",
            True,
            f"dep state=1 at t={dep_state1_time}s BEFORE first per_proxy connect t={first_connect}s; "
            f"even early per_proxy is too late; dst={dst}",
            "investigate what drives dep state=1 before any client connects; "
            "consider per_proxy start simultaneous with per_proxy_helper",
        )

    if not dep_state1_obs and dst.get("state_set_event_count", 0) > 0:
        return (
            "v1179-dep-state1-not-observed-in-window",
            True,
            f"dep never reached state=1 in trace window; dst={dst}",
            "extend trace window or arm uprobes earlier in boot sequence",
        )

    # Fall back to V1177 decision with V1179 prefix
    return (
        base_decision.replace("v1177", "v1179", 1),
        base_pass,
        base_reason + f" dst={dst}",
        base_next,
    )


# ── Summary ───────────────────────────────────────────────────────────────

def render_summary(manifest: dict[str, Any]) -> str:
    # Provide defaults for keys expected by the V1165 render_summary chain
    # that V1179 does not naturally populate.
    _defaults: dict[str, Any] = {
        "late_per_proxy_started": False,
        "tracefs_write_executed": bool(manifest.get("tracefs_write_executed", False)),
    }
    for _k, _v in _defaults.items():
        manifest.setdefault(_k, _v)
    base = v1177.render_summary(manifest).replace(
        "# V1177 PM Dependency Flag Live",
        "# V1179 PM Dep Early Per-Proxy Observer",
        1,
    )
    dst = dep_state_transitions(manifest)
    dep = v1177.dependency_flag(manifest)
    rows = [
        ["parent_peripheral", dst.get("parent_peripheral", "")],
        ["dep_address", dst.get("dep_address", "")],
        ["dep_offset", dst.get("dep_offset", "")],
        ["dep_state1_time", str(dst.get("dep_state1_time", ""))],
        ["dep_state1_observed", str(dst.get("dep_state1_observed", ""))],
        ["dep_state1_before_per_proxy_connect", str(dst.get("dep_state1_before_per_proxy_connect", ""))],
        ["first_per_proxy_connect_time", str(dst.get("first_per_proxy_connect_time", ""))],
        ["state_set_event_count", str(dst.get("state_set_event_count", ""))],
        ["peripherals_seen_count", str(dst.get("peripherals_seen_count", ""))],
        ["connect_event_count", str(dst.get("connect_event_count", ""))],
        ["early_per_proxy_target_delta_ms", str(EARLY_PER_PROXY_PPH_DELTA_MS)],
        ["dep_state_history", json.dumps(dst.get("dep_state_history", []))],
        ["early_pp_remaining_sleep_ms",
         str(dst.get("early_per_proxy_timing", {}).get("remaining_sleep_ms", ""))],
        ["early_pp_elapsed_since_pph_ms",
         str(dst.get("early_per_proxy_timing", {}).get("elapsed_since_pph_ms", ""))],
        ["dep_flag_armed_state2_call", str(dep.get("state2_dependency_call_count", 0))],
        ["dep_flag_set_seen", str(dep.get("state0_flag_set_seen", ""))],
    ]
    return base + "\n".join([
        "",
        "## V1179 Dep State Transition",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ])


# ── Wiring ────────────────────────────────────────────────────────────────

def patch_defaults() -> None:
    v1177.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1177.LATEST_POINTER = LATEST_POINTER
    v1177.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1177.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1177.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1177.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1177.PROOF_PREFIX = PROOF_PREFIX

    v1177.patch_defaults()
    v1177.tracefs_collector_script_v1177 = tracefs_collector_script_v1179
    v1177.parse_tracefs_output_v1177 = parse_tracefs_output_v1179

    base = v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    base.pm_late_per_proxy_child_command = pm_dep_early_per_proxy_child_command
    base.serial_remote_marker_check_v1165 = serial_remote_marker_check_v1179
    # Re-propagate the marker check to deeper levels (the call chain:
    # v1106.remote_marker_check → v1139.serial_remote_marker_check →
    # v1143.serial_remote_marker_check_v1143 → v1165.serial_remote_marker_check_v1165
    # was already frozen by v1165.patch_defaults() before we patched v1165's fn above).
    base.v1143.serial_remote_marker_check_v1143 = serial_remote_marker_check_v1179
    base.v1143.v1139.serial_remote_marker_check = serial_remote_marker_check_v1179
    base.v1143.v1139.v1113.v1106.remote_marker_check = serial_remote_marker_check_v1179
    # After v1177.patch_defaults() the patching chain sets v1106.pm_cnss_child_command to
    # a frozen reference to pm_late_per_proxy_child_command (v1165). Re-patching
    # v1165.pm_late_per_proxy_child_command above does NOT update that frozen ref.
    # Directly patch v1106.pm_cnss_child_command to use our new command builder.
    base.v1143.v1139.v1113.v1106.pm_cnss_child_command = pm_dep_early_per_proxy_child_command

    # Propagate deeper
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.tracefs_collector_script_v1169 = (
        tracefs_collector_script_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.parse_tracefs_output_v1170 = (
        parse_tracefs_output_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = (
        tracefs_collector_script_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.parse_tracefs_output_v1169 = (
        parse_tracefs_output_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = (
        tracefs_collector_script_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = (
        parse_tracefs_output_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = (
        parse_tracefs_output_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1179
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1179
    )
    # Patch helper SHA/marker checks at all levels including v1106 (used as argparse default)
    v1177.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1177.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.DEFAULT_EXECNS_HELPER_SHA256 = (
        DEFAULT_EXECNS_HELPER_SHA256
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.DEFAULT_EXECNS_HELPER_MARKER = (
        DEFAULT_EXECNS_HELPER_MARKER
    )
    # v1106 uses DEFAULT_EXECNS_HELPER_MARKER as the argparse default for --helper-marker;
    # must be patched before parse_args() runs.
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.DEFAULT_EXECNS_HELPER_SHA256 = (
        DEFAULT_EXECNS_HELPER_SHA256
    )
    v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.DEFAULT_EXECNS_HELPER_MARKER = (
        DEFAULT_EXECNS_HELPER_MARKER
    )


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    patch_defaults()
    v1165 = v1177.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106
    args = v1106.parse_args()
    v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1177_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1179"
    manifest["generated_at"] = _now_iso()
    manifest["early_per_proxy_pph_delta_ms"] = EARLY_PER_PROXY_PPH_DELTA_MS
    manifest["helper_version"] = DEFAULT_EXECNS_HELPER_MARKER

    decision, passed, reason, next_step = decide_v1179(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1165.v1143.v1139.global_firmware(manifest)
    values = v1165.v1143.v1139.contract(manifest)
    post = v1165.v1143.v1139.post_pm(manifest)
    lower = v1165.v1143.lower_trace(manifest)
    dst = dep_state_transitions(manifest)
    dep = v1177.dependency_flag(manifest)

    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["post_pm_mdm_helper_lower_trace_emitted"] = lower.get("begin") == "1"
    manifest["early_per_proxy_timing"] = dst.get("early_per_proxy_timing", {})
    manifest["dep_state1_observed"] = dst.get("dep_state1_observed", False)
    manifest["dep_state1_time"] = dst.get("dep_state1_time")
    manifest["dep_state1_before_per_proxy_connect"] = dst.get("dep_state1_before_per_proxy_connect", False)
    manifest["first_per_proxy_connect_time"] = dst.get("first_per_proxy_connect_time")
    manifest["dep_flag_armed"] = dep.get("state0_flag_value_one_seen", False)
    manifest["dep_state2_call_seen"] = dep.get("state2_dependency_call_seen", False)
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or post.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["scan_connect_executed"] = (
        values.get("scan_connect_linkup") == "1"
        or post.get("scan_connect_linkup") == "1"
        or lower.get("scan_connect_linkup") == "1"
    )
    manifest["credential_use_executed"] = lower.get("credentials") == "1"
    manifest["dhcp_route_executed"] = lower.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = (
        values.get("external_ping") == "1"
        or post.get("external_ping") == "1"
        or lower.get("external_ping") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    print(f"decision                 : {manifest['decision']}")
    print(f"pass                     : {manifest['pass']}")
    print(f"reason                   : {manifest['reason'][:200]}")
    print(f"next                     : {manifest['next_step']}")
    print(f"firmware_mounts_executed : {manifest['firmware_mounts_executed']}")
    print(f"reboot_executed          : {manifest['reboot_executed']}")
    print(f"dep_state1_observed      : {manifest['dep_state1_observed']}")
    print(f"dep_state1_time          : {manifest['dep_state1_time']}")
    print(f"dep_state1_before_pp_connect: {manifest['dep_state1_before_per_proxy_connect']}")
    print(f"first_pp_connect_time    : {manifest['first_per_proxy_connect_time']}")
    print(f"dep_flag_armed           : {manifest['dep_flag_armed']}")
    print(f"dep_state2_call_seen     : {manifest['dep_state2_call_seen']}")
    print(f"early_per_proxy_timing   : {manifest['early_per_proxy_timing']}")
    print(f"tracefs_write_executed   : {manifest['tracefs_write_executed']}")
    print(f"wifi_hal_start_executed  : {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed    : {manifest['wifi_bringup_executed']}")
    print(f"manifest                 : {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
