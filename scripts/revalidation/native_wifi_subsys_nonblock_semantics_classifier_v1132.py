#!/usr/bin/env python3
"""V1132 host-only classifier for subsys char-device nonblock semantics."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1132-subsys-nonblock-semantics-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1132-subsys-nonblock-semantics-classifier.txt")
DEFAULT_SOURCE = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/subsystem_restart.c")
DEFAULT_V1131_CLASSIFIER = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/manifest.json")
DEFAULT_V1131_LIVE = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def line_number(text: str, pattern: str) -> int:
    for index, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return index
    return 0


def extract_function(text: str, name: str) -> dict[str, Any]:
    match = re.search(rf"^[^\n;]*\b{re.escape(name)}\s*\([^)]*\)\s*\{{", text, re.MULTILINE)
    if not match:
        return {"present": False, "start": 0, "end": 0, "body": ""}
    start_offset = match.start()
    brace_offset = text.find("{", match.end() - 1)
    depth = 0
    end_offset = brace_offset
    for index in range(brace_offset, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end_offset = index + 1
                break
    start_line = text[:start_offset].count("\n") + 1
    end_line = text[:end_offset].count("\n") + 1
    return {
        "present": True,
        "start": start_line,
        "end": end_line,
        "body": text[start_offset:end_offset],
    }


def source_analysis(source_text: str) -> dict[str, Any]:
    open_fn = extract_function(source_text, "subsys_device_open")
    get_fn = extract_function(source_text, "__subsystem_get")
    start_fn = extract_function(source_text, "subsys_start")
    open_body = open_fn.get("body", "")
    get_body = get_fn.get("body", "")
    start_body = start_fn.get("body", "")
    return {
        "source_present": bool(source_text),
        "subsys_device_open": {
            "present": open_fn["present"],
            "start_line": open_fn["start"],
            "end_line": open_fn["end"],
            "calls_subsystem_get_with_fwname": "subsystem_get_with_fwname" in open_body,
            "uses_file_f_flags": "file->f_flags" in open_body or "f_flags" in open_body,
            "mentions_o_nonblock": "O_NONBLOCK" in open_body or "FMODE_NONBLOCK" in open_body or "nonblock" in open_body.lower(),
            "returns_open_result_only_after_get": "return PTR_ERR(retval)" in open_body and "return 0" in open_body,
        },
        "__subsystem_get": {
            "present": get_fn["present"],
            "start_line": get_fn["start"],
            "end_line": get_fn["end"],
            "locks_track": "mutex_lock(&track->lock)" in get_body,
            "starts_when_count_zero": "!subsys->count" in get_body and "subsys_start(subsys)" in get_body,
            "increments_count_after_start": "subsys->count++" in get_body,
            "line_subsys_start": line_number(source_text, "ret = subsys_start(subsys);"),
        },
        "subsys_start": {
            "present": start_fn["present"],
            "start_line": start_fn["start"],
            "end_line": start_fn["end"],
            "calls_powerup_directly": "subsys->desc->powerup(subsys->desc)" in start_body,
            "waits_for_err_ready": "wait_for_err_ready(subsys)" in start_body,
        },
        "file_operations": {
            "line": line_number(source_text, "static const struct file_operations subsys_device_fops"),
            "open_registered": ".open = subsys_device_open" in source_text,
            "release_registered": ".release = subsys_device_close" in source_text,
        },
    }


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def summarize_v1131(classifier: dict[str, Any], live_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = nested_get(classifier, ("analysis", "summary"), {})
    flags = nested_get(classifier, ("analysis", "flags"), {})
    live_trace = nested_get(live_manifest, ("analysis", "tracefs_uprobe"), {})
    contract = live_trace.get("pm_contract") if isinstance(live_trace, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    blocker_entries: list[dict[str, str]] = []
    for key, value in sorted(contract.items()):
        if key.endswith(".path.value") and value == "/dev/subsys_modem":
            prefix = key.rsplit(".path.value", 1)[0]
            blocker_entries.append({
                "prefix": prefix,
                "path": str(value),
                "wchan": str(contract.get(prefix + ".wchan", "")),
                "comm": str(contract.get(prefix + ".comm", "")),
                "syscall": str(contract.get(prefix + ".name", "")),
            })
    return {
        "classifier_decision": classifier.get("decision", ""),
        "classifier_pass": bool(classifier.get("pass")),
        "holder_requested": bool(summary.get("holder_requested")),
        "holder_allowed": bool(summary.get("holder_allowed")),
        "holder_start_attempted": bool(summary.get("holder_start_attempted")),
        "holder_child_chroot": bool(summary.get("holder_child_chroot")),
        "holder_plain_retry": str(summary.get("holder_plain_retry", "")),
        "holder_open_reported": bool(summary.get("holder_open_reported")),
        "holder_result_reported": bool(summary.get("holder_result_reported")),
        "holder_confirmed": bool(summary.get("holder_confirmed")),
        "provider_seen": bool(summary.get("provider_seen")),
        "cnss_register_ret": summary.get("cnss_register_ret") or [],
        "cnss_connect_ret": summary.get("cnss_connect_ret") or [],
        "subsys_modem_binder_open_blocked": bool(summary.get("subsys_modem_binder_open_blocked")),
        "mss_after": summary.get("mss_after", ""),
        "mdm3_after": summary.get("mdm3_after", ""),
        "no_wlfw_wlan0": bool(summary.get("no_wlfw_wlan0")),
        "flags": flags,
        "blocker_entries": blocker_entries,
    }


def classify(source: dict[str, Any], v1131: dict[str, Any]) -> dict[str, Any]:
    open_fn = source["subsys_device_open"]
    get_fn = source["__subsystem_get"]
    start_fn = source["subsys_start"]
    source_flags = {
        "open_calls_get": open_fn["present"] and open_fn["calls_subsystem_get_with_fwname"],
        "open_no_nonblock_branch": open_fn["present"] and not open_fn["uses_file_f_flags"] and not open_fn["mentions_o_nonblock"],
        "get_sync_start": get_fn["present"] and get_fn["locks_track"] and get_fn["starts_when_count_zero"],
        "start_sync_powerup": start_fn["present"] and start_fn["calls_powerup_directly"],
        "fops_registers_open": source["file_operations"]["open_registered"],
    }
    evidence_flags = {
        "v1131_pass": v1131["classifier_decision"] == "v1131-modem-pre-holder-open-pending-subsys-modem-blocker-confirmed"
        and v1131["classifier_pass"],
        "holder_attempted_no_result": v1131["holder_requested"]
        and v1131["holder_allowed"]
        and v1131["holder_start_attempted"]
        and v1131["holder_child_chroot"]
        and v1131["holder_plain_retry"] == "0"
        and not v1131["holder_open_reported"]
        and not v1131["holder_result_reported"]
        and not v1131["holder_confirmed"],
        "provider_cnss_ok": v1131["provider_seen"]
        and "0x0" in v1131["cnss_register_ret"]
        and "0x0" in v1131["cnss_connect_ret"],
        "binder_worker_blocked": v1131["subsys_modem_binder_open_blocked"]
        and any(item.get("wchan") == "__subsystem_get" for item in v1131["blocker_entries"]),
        "lower_still_blocked": v1131["mss_after"] == "OFFLINING"
        and v1131["mdm3_after"] == "OFFLINING"
        and v1131["no_wlfw_wlan0"],
    }
    all_required = {**source_flags, **evidence_flags}
    missing = [key for key, value in all_required.items() if not value]
    if not missing:
        decision = "v1132-subsys-open-nonblock-unsupported-route-closed"
        passed = True
        reason = (
            "subsys_device_open ignores file flags and synchronously enters subsystem_get/subsys_start; "
            "V1131 proved O_NONBLOCK /dev/subsys_modem pre-holder still open-pends"
        )
        next_step = "stop /dev/subsys_modem nonblocking pre-holder retries; classify lower eSoC/SDX50M powerup preconditions"
    else:
        decision = "v1132-subsys-nonblock-classifier-incomplete"
        passed = False
        reason = "missing=" + ",".join(missing)
        next_step = "inspect source/evidence inputs before deciding the next live gate"
    return {
        "source_flags": source_flags,
        "evidence_flags": evidence_flags,
        "missing": missing,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    source = analysis["source"]
    v1131 = analysis["v1131"]
    classification = analysis["classification"]
    source_rows = [
        ["subsys_device_open", f"{source['subsys_device_open']['start_line']}:{source['subsys_device_open']['end_line']}"],
        ["open_calls_get", str(classification["source_flags"]["open_calls_get"])],
        ["open_no_nonblock_branch", str(classification["source_flags"]["open_no_nonblock_branch"])],
        ["get_sync_start", str(classification["source_flags"]["get_sync_start"])],
        ["start_sync_powerup", str(classification["source_flags"]["start_sync_powerup"])],
    ]
    evidence_rows = [
        ["v1131_decision", v1131["classifier_decision"]],
        ["holder_attempted_no_result", str(classification["evidence_flags"]["holder_attempted_no_result"])],
        ["provider_cnss_ok", str(classification["evidence_flags"]["provider_cnss_ok"])],
        ["binder_worker_blocked", str(classification["evidence_flags"]["binder_worker_blocked"])],
        ["mss_after", v1131["mss_after"]],
        ["mdm3_after", v1131["mdm3_after"]],
    ]
    return "\n".join([
        "# V1132 Subsys Nonblock Semantics Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Source",
        "",
        markdown_table(["key", "value"], source_rows),
        "",
        "## V1131 Evidence",
        "",
        markdown_table(["key", "value"], evidence_rows),
        "",
        "## Missing",
        "",
        json.dumps(classification["missing"], indent=2, sort_keys=True),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--v1131-classifier", type=Path, default=DEFAULT_V1131_CLASSIFIER)
    parser.add_argument("--v1131-live", type=Path, default=DEFAULT_V1131_LIVE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    source_text = read_text(args.source)
    source = source_analysis(source_text)
    v1131 = summarize_v1131(load_json(args.v1131_classifier), load_json(args.v1131_live))
    classification = classify(source, v1131)
    manifest = {
        "cycle": "v1132",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "source": str(repo_path(args.source)),
            "v1131_classifier": str(repo_path(args.v1131_classifier)),
            "v1131_live": str(repo_path(args.v1131_live)),
        },
        "analysis": {
            "source": source,
            "v1131": v1131,
            "classification": classification,
        },
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
