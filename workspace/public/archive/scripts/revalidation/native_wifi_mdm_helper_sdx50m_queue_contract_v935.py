#!/usr/bin/env python3
"""V935 host-only mdm_helper SDX50M queue/property-context contract classifier.

This classifier consumes the latest CNSS/service-manager live evidence and the
helper source to decide the next native Wi-Fi gate after V934 proved fresh
cnss-daemon Binder failures are cleared but WLFW is still absent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v935-mdm-helper-sdx50m-queue-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v935-mdm-helper-sdx50m-queue-contract.txt")
DEFAULT_V934_MANIFEST = Path("tmp/wifi/v934-cnss-fresh-pid-attribution/manifest.json")
DEFAULT_V931_DIR = Path("tmp/wifi/v931-cnss-service-manager-matrix-live")
DEFAULT_V933_DIR = Path("tmp/wifi/v933-cnss-service-manager-before-cnss-live")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
PROPERTY_CONTEXT_GLOBS = [
    "tmp/wifi/v*-property-*/native/*property_contexts*.txt",
    "tmp/wifi/v*/native/*property_contexts*.txt",
    "tmp/wifi/v*/android/*property_contexts*.txt",
]

PROPERTY_KEYS_OF_INTEREST = [
    "arm64.memtag.process.mdm_helper",
    "persist.vendor.mdm_helper.fail_action",
    "persist.vendor.mdm_helper.timeout",
    "persist.log.tag.mdm_helper",
    "log.tag.mdm_helper",
]

BASE_PROPERTY_PREFIXES = [
    "persist.log.tag",
    "log.tag",
]

SHIM_ALLOWLIST_KEYS = [
    "hwservicemanager.ready",
    "ctl.stop",
    "vendor.peripheral.SDX50M.state",
    "vendor.peripheral.modem.state",
    "vendor.peripheral.shutdown_critical_list",
]


@dataclass(frozen=True)
class RunCase:
    label: str
    decision: str
    order: str
    mdm_helper_pid: int | None
    mdm_helper_thread_pids: list[int]
    cnss_pid: int | None
    service_manager_started: bool
    mdm_helper_esoc0_fd_seen: bool
    wlfw_precondition_observed: bool
    subsys_esoc0_open_attempted: bool
    current_mdm_queue_failures: int
    any_mdm_queue_failures: int
    current_cnss_binder_failures: int
    current_cnss_cld80211: int
    current_cnss_wlfw: int
    property_context_missing_keys: dict[str, int]
    property_access_denied_keys: dict[str, int]
    shim_requests_allowed: int
    shim_requests_denied: int
    shim_requested_names: list[str]


@dataclass(frozen=True)
class ContextCoverage:
    exact_key_hits: dict[str, list[str]]
    base_prefix_hits: dict[str, list[str]]
    files_scanned: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v934-manifest", type=Path, default=DEFAULT_V934_MANIFEST)
    parser.add_argument("--v931-dir", type=Path, default=DEFAULT_V931_DIR)
    parser.add_argument("--v933-dir", type=Path, default=DEFAULT_V933_DIR)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace").replace("\0", "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})


def last_int(pattern: str, text: str) -> int | None:
    values = re.findall(pattern, text)
    if not values:
        return None
    return int(values[-1])


def child_pid(child: str, text: str) -> int | None:
    return last_int(rf"wifi_hal_composite_start\.child\.{re.escape(child)}\.pid=(\d+)", text)


def child_thread_pids(child: str, text: str) -> list[int]:
    marker = f"capture.wifi_hal_composite_{child}.fd_links"
    lines = text.splitlines()
    indices = [idx for idx, line in enumerate(lines) if marker in line]
    if not indices:
        return []
    window = "\n".join(lines[max(0, indices[0] - 80):min(len(lines), indices[-1] + 260)])
    return sorted({int(value) for value in re.findall(r"\[anon:stack_and_tls:(\d+)\]", window)})


def pid_lines(dmesg: str, comm: str, pid: int | None) -> list[str]:
    if pid is None:
        return []
    pattern = re.compile(rf"\b{re.escape(comm)}:\s*{pid}\]", re.IGNORECASE)
    return [line for line in dmesg.splitlines() if pattern.search(line)]


def mdm_lines(dmesg: str, pids: set[int]) -> list[str]:
    rows: list[str] = []
    for line in dmesg.splitlines():
        if "mdm_helper:" not in line:
            continue
        if any(re.search(rf"\b{pid}\]", line) for pid in pids):
            rows.append(line)
    return rows


def count(rows: list[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for row in rows if regex.search(row))


def property_key_counts(text: str, prefix: str) -> dict[str, int]:
    counts = {key: 0 for key in PROPERTY_KEYS_OF_INTEREST}
    for key in re.findall(rf'{re.escape(prefix)} "([^"]+)"', text):
        if key in counts:
            counts[key] += 1
    return {key: value for key, value in counts.items() if value}


def shim_request_names(text: str) -> list[str]:
    names = re.findall(r"wifi_hal_composite_start\.property_service_shim\.request\.\d+\.name=([^\n]+)", text)
    return sorted(set(name.strip() for name in names if name.strip()))


def shim_allowed_count(text: str, allowed: bool) -> int:
    value = "1" if allowed else "0"
    return len(re.findall(rf"wifi_hal_composite_start\.property_service_shim\.request\.\d+\.allowed={value}\b", text))


def case_from_dir(label: str, run_dir: Path) -> RunCase:
    manifest = load_json(run_dir / "manifest.json")
    helper = read_text(run_dir / "native/mdm-helper-cnss-before-esoc.txt")
    dmesg = read_text(run_dir / "native/post-dmesg-wifi-esoc-tail.txt")
    data = contract(manifest)
    mdm_pid = child_pid("mdm_helper", helper)
    mdm_threads = child_thread_pids("mdm_helper", helper)
    cnss_pid = child_pid("cnss_daemon", helper)
    mdm_pid_set = {pid for pid in [mdm_pid, *mdm_threads] if pid is not None}
    current_mdm_rows = mdm_lines(dmesg, mdm_pid_set)
    current_cnss_rows = pid_lines(dmesg, "cnss-daemon", cnss_pid)
    return RunCase(
        label=label,
        decision=str(manifest.get("decision")),
        order=str(data.get("service_manager_order") or "none"),
        mdm_helper_pid=mdm_pid,
        mdm_helper_thread_pids=mdm_threads,
        cnss_pid=cnss_pid,
        service_manager_started=str(data.get("service_manager_started") or "0") == "1",
        mdm_helper_esoc0_fd_seen=str(data.get("mdm_helper_esoc0_fd_seen") or "0") == "1",
        wlfw_precondition_observed=bool(manifest.get("wlfw_precondition_observed")),
        subsys_esoc0_open_attempted=bool(manifest.get("subsys_esoc0_open_attempted")),
        current_mdm_queue_failures=count(current_mdm_rows, r"unable to queue event for SDX50M"),
        any_mdm_queue_failures=count(dmesg.splitlines(), r"mdm_helper.*unable to queue event for SDX50M"),
        current_cnss_binder_failures=count(current_cnss_rows, r"transaction failed|returned -22|ioctl 40046210"),
        current_cnss_cld80211=count(current_cnss_rows, r"cld80211"),
        current_cnss_wlfw=count(current_cnss_rows, r"wlfw"),
        property_context_missing_keys=property_key_counts(helper, "Could not find context for property"),
        property_access_denied_keys=property_key_counts(helper, "Access denied finding property"),
        shim_requests_allowed=shim_allowed_count(helper, True),
        shim_requests_denied=shim_allowed_count(helper, False),
        shim_requested_names=shim_request_names(helper),
    )


def collect_property_context_coverage() -> ContextCoverage:
    files: list[Path] = []
    for pattern in PROPERTY_CONTEXT_GLOBS:
        files.extend(repo_path(".").glob(pattern))
    unique_files = sorted(set(files))
    exact_hits = {key: [] for key in PROPERTY_KEYS_OF_INTEREST}
    base_hits = {key: [] for key in BASE_PROPERTY_PREFIXES}
    for path in unique_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(repo_path(".")))
        for key in PROPERTY_KEYS_OF_INTEREST:
            if re.search(rf"(^|\s){re.escape(key)}(\s|$)", text, re.MULTILINE):
                exact_hits[key].append(rel)
        for key in BASE_PROPERTY_PREFIXES:
            if re.search(rf"(^|\s){re.escape(key)}(\s|$)", text, re.MULTILINE):
                base_hits[key].append(rel)
    return ContextCoverage(
        exact_key_hits={key: value for key, value in exact_hits.items() if value},
        base_prefix_hits={key: value for key, value in base_hits.items() if value},
        files_scanned=[str(path.relative_to(repo_path("."))) for path in unique_files],
    )


def helper_source_contract(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return {
        "source": str(repo_path(path)),
        "property_shim_set_allowed_present": "property_shim_set_allowed" in text,
        "property_shim_handle_client_present": "property_shim_handle_client" in text,
        "property_service_shim_child_present": "property_service_shim_child" in text,
        "allowed_setprop_keys_present": {
            key: key in text for key in SHIM_ALLOWLIST_KEYS
        },
        "read_property_context_repair_present": bool(re.search(r"property_context|property_info", text, re.IGNORECASE)),
        "note": "helper property shim handles property_service set requests; bionic property-info context lookup repair is not implemented in this source",
    }


def decide(cases: list[RunCase], coverage: ContextCoverage, source_contract: dict[str, Any], v934: dict[str, Any]) -> tuple[str, bool, str, str]:
    service_manager_cases = [case for case in cases if case.service_manager_started]
    binder_cleared = bool(service_manager_cases) and all(case.current_cnss_binder_failures == 0 for case in service_manager_cases)
    wlfw_missing = bool(service_manager_cases) and all(case.current_cnss_wlfw == 0 for case in service_manager_cases)
    queue_reproduced = any(case.current_mdm_queue_failures > 0 for case in service_manager_cases)
    property_misses = any(case.property_context_missing_keys or case.property_access_denied_keys for case in service_manager_cases)
    no_subsys_open = all(not case.subsys_esoc0_open_attempted for case in service_manager_cases)
    shim_limited = source_contract["property_shim_handle_client_present"] and not source_contract["read_property_context_repair_present"]
    v934_ok = v934.get("decision") == "v934-fresh-pid-binder-cleared-wlfw-still-missing"
    if binder_cleared and wlfw_missing and queue_reproduced and no_subsys_open and property_misses and shim_limited and v934_ok:
        return (
            "v935-mdm-helper-sdx50m-queue-property-gap-classified",
            True,
            (
                "Fresh service-manager runs no longer show current cnss-daemon Binder failures, but mdm_helper current worker PIDs still emit "
                "'unable to queue event for SDX50M' while WLFW remains absent. The helper source only shims property_service set requests; "
                "mdm_helper's bionic property-context lookups still miss/deny several runtime keys. This co-occurrence is a lower-contract blocker, "
                "not proof that service-manager ordering remains wrong."
            ),
            (
                "implement V936 source/build-only mdm_helper lower-contract diagnostics: capture bounded property-info/context coverage, "
                "mdm_helper property get defaults, SDX50M queue readiness, and per_mgr state before any new live trigger"
            ),
        )
    return (
        "v935-mdm-helper-sdx50m-queue-contract-review",
        False,
        "Evidence does not yet prove the fresh Binder-cleared + mdm_helper queue/property-context lower-contract pattern.",
        "inspect V935 manifest before live retry",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        case_from_dir("v931-after-mdm-helper-esoc-fd", args.v931_dir),
        case_from_dir("v933-before-cnss", args.v933_dir),
    ]
    coverage = collect_property_context_coverage()
    source_contract = helper_source_contract(args.helper_source)
    v934 = load_json(args.v934_manifest)
    decision, pass_ok, reason, next_step = decide(cases, coverage, source_contract, v934)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v934_manifest": str(repo_path(args.v934_manifest)),
            "v931_dir": str(repo_path(args.v931_dir)),
            "v933_dir": str(repo_path(args.v933_dir)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "v934_decision": v934.get("decision"),
        "cases": [asdict(case) for case in cases],
        "property_context_coverage": asdict(coverage),
        "helper_source_contract": source_contract,
        "classification": {
            "service_manager_order_retry_closed": pass_ok,
            "property_context_gap_proven_as_root_cause": False,
            "property_context_gap_is_co_present": any(
                case.property_context_missing_keys or case.property_access_denied_keys for case in cases
            ),
            "mdm_helper_queue_failure_is_current_blocking_symptom": any(case.current_mdm_queue_failures for case in cases),
            "binder_is_current_primary_blocker": False,
            "requires_next_source_build_before_live_retry": pass_ok,
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    case_rows = []
    for case in manifest["cases"]:
        missing = ", ".join(f"{key}:{value}" for key, value in case["property_context_missing_keys"].items()) or "none"
        denied = ", ".join(f"{key}:{value}" for key, value in case["property_access_denied_keys"].items()) or "none"
        names = ", ".join(case["shim_requested_names"]) or "none"
        case_rows.append([
            case["label"],
            case["order"],
            case["mdm_helper_pid"],
            ",".join(str(pid) for pid in case["mdm_helper_thread_pids"]) or "none",
            case["current_mdm_queue_failures"],
            case["current_cnss_binder_failures"],
            case["current_cnss_cld80211"],
            case["current_cnss_wlfw"],
            missing,
            denied,
            case["shim_requests_allowed"],
            case["shim_requests_denied"],
            names,
        ])
    coverage = manifest["property_context_coverage"]
    context_rows = []
    for key in PROPERTY_KEYS_OF_INTEREST:
        context_rows.append([
            key,
            ", ".join(coverage["exact_key_hits"].get(key, [])) or "none",
        ])
    for key in BASE_PROPERTY_PREFIXES:
        context_rows.append([
            key,
            ", ".join(coverage["base_prefix_hits"].get(key, [])) or "none",
        ])
    source_rows = [[key, value] for key, value in manifest["helper_source_contract"].items() if key != "allowed_setprop_keys_present"]
    source_rows.extend(
        [[f"allowlist.{key}", value] for key, value in manifest["helper_source_contract"]["allowed_setprop_keys_present"].items()]
    )
    return "\n".join([
        "# V935 mdm_helper SDX50M Queue Contract Summary",
        "",
        f"decision: `{manifest['decision']}`",
        f"pass: `{manifest['pass']}`",
        f"reason: {manifest['reason']}",
        f"next: {manifest['next_step']}",
        "",
        "## Current Service-Manager Cases",
        "",
        markdown_table(
            [
                "case",
                "order",
                "mdm_pid",
                "mdm_threads",
                "queue_fail",
                "cnss_binder",
                "cnss_cld80211",
                "cnss_wlfw",
                "missing_context_keys",
                "access_denied_keys",
                "shim_allowed",
                "shim_denied",
                "shim_names",
            ],
            case_rows,
        ),
        "",
        "## Property Context Evidence Coverage",
        "",
        markdown_table(["key", "evidence_files"], context_rows),
        "",
        "## Helper Source Contract",
        "",
        markdown_table(["field", "value"], source_rows),
        "",
        "## Classification",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest["classification"].items()]),
        "",
        "## Guardrails",
        "",
        "- host-only classifier",
        "- no device command",
        "- no daemon or service-manager start",
        "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
        "- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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
