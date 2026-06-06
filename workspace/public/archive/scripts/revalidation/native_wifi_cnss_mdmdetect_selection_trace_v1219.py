#!/usr/bin/env python3
"""V1219: trace why cnss-daemon still selects modem after SDXPRAIRIE readback.

This reuses the V1218 bounded PM/CNSS observer and helper v252 fake
`esoc_name=SDXPRAIRIE` setup, then adds tracefs uprobes on:

- `/mnt/vendor/bin/cnss-daemon` around the local PM vote/select function;
- `/mnt/vendor/lib64/libmdmdetect.so` around `get_system_info()`;
- the existing libperipheral_client/pm-service events from V1106.

The gate does not start Wi-Fi HAL, scan/connect, DHCP, routes, credentials, or
external ping.  It classifies whether the second type-0 `SDXPRAIRIE` vote is
called, whether libmdmdetect returns a matching type-0 name, and whether the PM
client registration is skipped after selection.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_json

import native_wifi_pm_esoc_sdxprairie_name_v1218 as v1218


base = v1218.base

HELPER_SHA256_V252 = v1218.HELPER_SHA256_V252
HELPER_MARKER_V252 = v1218.HELPER_MARKER_V252

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1219-cnss-mdmdetect-selection-trace")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1219-cnss-mdmdetect-selection-trace.txt")
base.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256_V252
base.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER_V252

ORIGINAL_PATCH_DEFAULTS = base.patch_defaults

CNSS_DAEMON = "/mnt/vendor/bin/cnss-daemon"
MDMDETECT = "/mnt/vendor/lib64/libmdmdetect.so"

CNSS_SELECTION_EVENT_SPECS = (
    ("cnss_pm_vote_entry", "cnss", "c39c", "vote_type=%x0 vote_name=+0(%x1):string"),
    ("cnss_get_system_info_ret", "cnss", "c448", "ret=%x0"),
    ("cnss_num_modems", "cnss", "c474", "num=%x3"),
    ("cnss_type_compare", "cnss", "c4dc", "request_type=%x19 entry_type=%x8 entry_name=+0(%x26):string"),
    ("cnss_strcmp_call", "cnss", "c4ec", "candidate=+0(%x0):string requested=+0(%x1):string"),
    ("cnss_strcmp_result", "cnss", "c4f0", "strcmp_ret=%x0"),
    ("cnss_named_register_call", "cnss", "c52c", "peripheral=+0(%x2):string client=+0(%x3):string"),
    ("cnss_nullname_loop_entry", "cnss", "c5e0", "request_type=%x19 entry_name=+0(%x26):string"),
    ("cnss_nullname_register_call", "cnss", "c624", "peripheral=+0(%x2):string client=+0(%x3):string"),
    ("mdm_get_system_info_entry", "mdm", "2c94", ""),
    ("mdm_get_esoc_details_call", "mdm", "2d94", ""),
    ("mdm_success_return", "mdm", "2f3c", "ret=%x0"),
    ("mdm_failure_return_after_info", "mdm", "2fec", "ret=%x0"),
)

LABEL_RE = re.compile(r":\s+(?P<label>[A-Za-z0-9_]+):")
KEYVAL_RE = re.compile(r'\b(?P<key>[A-Za-z0-9_]+)=(?P<value>"[^"]*"|\([^)]*\)|[^\s]+)')


def _patch_collector_script(original_collector):
    def tracefs_collector_script(args: Any) -> str:
        script = original_collector(args)
        script = script.replace("GROUP=a90pm1106", "GROUP=a90pm1219")
        script = script.replace("echo tracefs_uprobe_collector=v1106", "echo tracefs_uprobe_collector=v1219")
        script = script.replace(
            "SERVICE_BIN=",
            f"CNSS_BIN={CNSS_DAEMON}\nMDMDETECT_BIN={MDMDETECT}\nSERVICE_BIN=",
            1,
        )
        script = script.replace(
            'echo service_binary="$SERVICE_BIN"',
            'echo service_binary="$SERVICE_BIN"\necho cnss_binary="$CNSS_BIN"\necho mdmdetect_binary="$MDMDETECT_BIN"',
            1,
        )
        script = script.replace(
            'if ! $BB test -x "$CHILD"; then',
            'if ! $BB test -r "$CNSS_BIN"; then\n'
            '  echo result=tracefs-uprobe-cnss-binary-missing\n'
            '  exit 1\n'
            'fi\n'
            'if ! $BB test -r "$MDMDETECT_BIN"; then\n'
            '  echo result=tracefs-uprobe-mdmdetect-binary-missing\n'
            '  exit 1\n'
            'fi\n'
            'if ! $BB test -x "$CHILD"; then',
            1,
        )
        script = script.replace(
            '    service) bin="$SERVICE_BIN" ;;\n',
            '    service) bin="$SERVICE_BIN" ;;\n'
            '    cnss) bin="$CNSS_BIN" ;;\n'
            '    mdm) bin="$MDMDETECT_BIN" ;;\n',
            1,
        )
        return script

    return tracefs_collector_script


def patch_defaults() -> None:
    ORIGINAL_PATCH_DEFAULTS()

    import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod

    original_events = tuple(v1106_mod.EVENT_SPECS)
    existing_labels = {label for label, _binary_key, _offset, _fetch in original_events}
    extra_events = tuple(
        event for event in CNSS_SELECTION_EVENT_SPECS if event[0] not in existing_labels
    )
    v1106_mod.EVENT_SPECS = original_events + extra_events
    v1106_mod.tracefs_collector_script = _patch_collector_script(
        v1106_mod.tracefs_collector_script
    )


def _keyvals(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in KEYVAL_RE.finditer(line):
        values[match.group("key")] = match.group("value").strip('"')
    return values


def _extract_selection_trace(observer_text: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    lines_by_label: dict[str, list[str]] = {}
    parsed_by_label: dict[str, list[dict[str, str]]] = {}

    for line in observer_text.splitlines():
        match = LABEL_RE.search(line)
        if not match:
            continue
        label = match.group("label")
        if not label.startswith(("cnss_", "mdm_")):
            continue
        counts[label] = counts.get(label, 0) + 1
        lines_by_label.setdefault(label, []).append(line.rstrip())
        parsed_by_label.setdefault(label, []).append(_keyvals(line))

    pm_vote_entries = parsed_by_label.get("cnss_pm_vote_entry", [])
    vote_types = [entry.get("vote_type", "") for entry in pm_vote_entries]
    vote_names = [entry.get("vote_name", "") for entry in pm_vote_entries]
    type_compare_entries = parsed_by_label.get("cnss_type_compare", [])
    strcmp_calls = parsed_by_label.get("cnss_strcmp_call", [])
    strcmp_results = parsed_by_label.get("cnss_strcmp_result", [])

    sdxprairie_vote_seen = any(
        entry.get("vote_type") in {"0x0", "0"} and entry.get("vote_name") == "SDXPRAIRIE"
        for entry in pm_vote_entries
    )
    sdxprairie_candidate_seen = any(
        entry.get("candidate") == "SDXPRAIRIE" or entry.get("requested") == "SDXPRAIRIE"
        for entry in strcmp_calls
    )
    sdxprairie_register_call_seen = any(
        entry.get("peripheral") == "SDXPRAIRIE"
        for entry in parsed_by_label.get("cnss_named_register_call", [])
    )
    modem_register_call_seen = any(
        entry.get("peripheral") == "modem"
        for entry in parsed_by_label.get("cnss_nullname_register_call", [])
    )

    return {
        "counts": counts,
        "vote_types": vote_types,
        "vote_names": vote_names,
        "pm_vote_entries": pm_vote_entries,
        "type_compare_entries": type_compare_entries,
        "strcmp_calls": strcmp_calls,
        "strcmp_results": strcmp_results,
        "sdxprairie_vote_seen": sdxprairie_vote_seen,
        "sdxprairie_candidate_seen": sdxprairie_candidate_seen,
        "sdxprairie_register_call_seen": sdxprairie_register_call_seen,
        "modem_register_call_seen": modem_register_call_seen,
        "lines_by_label": {label: lines[:20] for label, lines in lines_by_label.items()},
    }


def _decide_v1219(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    selection = manifest.get("cnss_mdmdetect_selection_trace") or {}
    counts = selection.get("counts") or {}
    thread_analysis = manifest.get("thread_analysis") or {}
    cnss_peripherals = thread_analysis.get("cnss_registered_peripherals") or []

    if "SDXPRAIRIE" in cnss_peripherals:
        return (
            "v1219-sdxprairie-pm-client-registered",
            True,
            "cnss-daemon registered peripheral='SDXPRAIRIE'",
            "V1220: observe per_mgr subsys_esoc0 and MDM/WLFW path; still no scan/connect",
        )
    if counts.get("cnss_pm_vote_entry", 0) == 0:
        return (
            "v1219-cnss-selection-probe-missing",
            False,
            "cnss pm vote entry uprobe did not fire",
            "verify cnss-daemon text offset/path before retry",
        )
    if not selection.get("sdxprairie_vote_seen"):
        return (
            "v1219-second-sdxprairie-vote-skipped",
            False,
            f"pm vote entries seen but no type-0 SDXPRAIRIE vote: "
            f"types={selection.get('vote_types')} names={selection.get('vote_names')}",
            "trace caller state around cnss-daemon 0xec28-0xec48",
        )
    if not selection.get("sdxprairie_candidate_seen"):
        return (
            "v1219-mdmdetect-entry-not-sdxprairie",
            False,
            f"type-0 SDXPRAIRIE vote was called, but strcmp never compared "
            f"against SDXPRAIRIE; type_compare={selection.get('type_compare_entries')}; "
            f"strcmp_calls={selection.get('strcmp_calls')}",
            "classify libmdmdetect output array contents and type filtering",
        )
    if selection.get("sdxprairie_candidate_seen") and not selection.get("sdxprairie_register_call_seen"):
        return (
            "v1219-sdxprairie-compare-no-register",
            False,
            f"SDXPRAIRIE compare observed but no named pm_client_register call; "
            f"strcmp_results={selection.get('strcmp_results')}",
            "trace strcmp result branch and cnss local register call arguments",
        )
    return (
        "v1219-selection-path-inconclusive",
        False,
        f"cnss_peripherals={cnss_peripherals}; selection_counts={counts}",
        "inspect full observer trace and add narrower offsets",
    )


def _patch_manifest() -> int:
    try:
        run_dir = Path(base.LATEST_POINTER.read_text(encoding="utf-8").strip())
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 1

    observer_path = run_dir / "host/pm-server-wchan-tracefs-observer.txt"
    observer_text = observer_path.read_text(encoding="utf-8", errors="replace")
    selection = _extract_selection_trace(observer_text)
    manifest["cycle"] = "v1219"
    manifest["helper_version"] = HELPER_MARKER_V252
    manifest["helper_sha256"] = HELPER_SHA256_V252
    manifest["cnss_mdmdetect_selection_trace"] = selection

    decision, passed, reason, next_step = _decide_v1219(manifest)
    manifest.update(
        {
            "decision": decision,
            "pass": passed,
            "reason": reason,
            "next_step": next_step,
        }
    )
    write_private_json(manifest_path, manifest)

    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"selection_counts: {selection.get('counts')}")
    print(f"vote_types:       {selection.get('vote_types')}")
    print(f"vote_names:       {selection.get('vote_names')}")
    print(f"type_compare:     {selection.get('type_compare_entries')}")
    print(f"strcmp_calls:     {selection.get('strcmp_calls')}")
    print(f"evidence:         {run_dir}")
    return 0 if passed else 1


def main() -> int:
    base.patch_defaults = patch_defaults
    base.decide_v1216 = v1218.decide_v1218
    base.main()
    return _patch_manifest()


if __name__ == "__main__":
    raise SystemExit(main())
