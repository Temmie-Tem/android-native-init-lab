#!/usr/bin/env python3
"""V523 Android companion-service contract synthesizer.

This is a host-only classifier. It merges V521 Android recapture evidence with
older Android runtime-gap captures to identify the exact companion-service
contracts that should be proven next in native init. It does not run device
commands, start daemons, scan, connect, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v523-companion-contract")
DEFAULT_V521_DIR = Path("tmp/wifi/v522-android-companion-recapture-handoff/v521-android-companion-recapture-run")
DEFAULT_V431_DIR = Path("tmp/wifi/v431-android-runtime-gap-handoff-live-fix-20260520-151152/v431-android-runtime-gap-run")
SERVICE_RE = re.compile(r"(?:^|:)service\s+([A-Za-z0-9_.-]+)\s+(\S+)(.*)$")
RUNNING_PROP_RE = re.compile(r"^\[init\.svc\.([^]]+)\]:\s+\[running\]", re.IGNORECASE)


@dataclass(frozen=True)
class ServiceSpec:
    key: str
    role: str
    required: bool
    names: tuple[str, ...]
    binaries: tuple[str, ...]
    process_re: re.Pattern[str]
    log_re: re.Pattern[str]


@dataclass
class EvidenceHit:
    file: str
    line: str


@dataclass
class ServiceContract:
    key: str
    role: str
    required: bool
    observed_state: str
    android_service_names: list[str] = field(default_factory=list)
    android_path: str = ""
    android_argv: str = ""
    native_candidate_path: str = ""
    path_source: str = "missing"
    process_hits: list[EvidenceHit] = field(default_factory=list)
    init_hits: list[EvidenceHit] = field(default_factory=list)
    binary_hits: list[EvidenceHit] = field(default_factory=list)
    prop_hits: list[EvidenceHit] = field(default_factory=list)
    log_hits: list[EvidenceHit] = field(default_factory=list)


SERVICE_SPECS: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        "qrtr_ns",
        "QRTR nameservice",
        True,
        ("vendor.qrtr-ns", "qrtr-ns"),
        ("qrtr-ns",),
        re.compile(r"\bqrtr-ns\b", re.IGNORECASE),
        re.compile(r"\bqrtr-ns\b|Modem QMI Readiness", re.IGNORECASE),
    ),
    ServiceSpec(
        "pd_mapper",
        "Protection-domain mapper",
        True,
        ("vendor.pd_mapper", "pd-mapper"),
        ("pd-mapper",),
        re.compile(r"\bpd-mapper\b", re.IGNORECASE),
        re.compile(r"\bpd-mapper\b|pd-mapper-svc", re.IGNORECASE),
    ),
    ServiceSpec(
        "rmt_storage",
        "Remote-storage companion",
        True,
        ("vendor.rmt_storage", "rmt_storage", "rmtfs"),
        ("rmt_storage", "rmtfs"),
        re.compile(r"\brmt_storage\b|\brmtfs\b", re.IGNORECASE),
        re.compile(r"\brmt_storage\b|\brmtfs\b", re.IGNORECASE),
    ),
    ServiceSpec(
        "tftp_server",
        "RFS/TFTP firmware server",
        True,
        ("vendor.tftp_server", "tftp_server", "tqftpserv"),
        ("tftp_server", "tqftpserv"),
        re.compile(r"\btftp_server\b|\btqftpserv\b", re.IGNORECASE),
        re.compile(r"\btftp_server\b|\btftp-server\b|\btqftpserv\b", re.IGNORECASE),
    ),
    ServiceSpec(
        "qmiproxy",
        "QMI proxy",
        False,
        ("qmiproxy",),
        ("qmiproxy",),
        re.compile(r"\bqmiproxy\b", re.IGNORECASE),
        re.compile(r"\bqmiproxy\b", re.IGNORECASE),
    ),
    ServiceSpec(
        "cnss_diag",
        "CNSS diagnostic companion",
        True,
        ("cnss_diag",),
        ("cnss_diag",),
        re.compile(r"\bcnss_diag\b", re.IGNORECASE),
        re.compile(r"\bcnss_diag\b|CLD80211", re.IGNORECASE),
    ),
    ServiceSpec(
        "cnss_daemon",
        "CNSS WLFW daemon",
        True,
        ("cnss-daemon",),
        ("cnss-daemon",),
        re.compile(r"\bcnss-daemon\b", re.IGNORECASE),
        re.compile(r"\bcnss-daemon\b|wlfw_start|QMI Server Connected|BDF file|WLAN FW is ready", re.IGNORECASE),
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v521-dir", type=Path, default=DEFAULT_V521_DIR)
    parser.add_argument("--v431-dir", type=Path, default=DEFAULT_V431_DIR)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def gather_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    command_dirs = [root / "android" / "commands", root / "commands"]
    command_files: list[Path] = []
    for command_dir in command_dirs:
        if command_dir.exists():
            command_files.extend(sorted(command_dir.glob("*.txt")))
    if command_files:
        return command_files
    files: list[Path] = []
    for candidate in root.rglob("*"):
        if candidate.is_file() and candidate.suffix in {".txt", ".md", ".json"}:
            files.append(candidate)
    return sorted(files)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def line_hits(files: list[Path], pattern: re.Pattern[str], limit: int = 40) -> list[EvidenceHit]:
    hits: list[EvidenceHit] = []
    seen: set[str] = set()
    for path in files:
        for raw_line in safe_read(path).splitlines():
            line = raw_line.strip()
            if not line or "$ adb " in line:
                continue
            if "grep -Ei" in line or "command:s:" in line or "app_process /system/bin com.android.commands" in line:
                continue
            if not pattern.search(line):
                continue
            key = f"{relative(path)}:{line}"
            if key in seen:
                continue
            seen.add(key)
            hits.append(EvidenceHit(relative(path), line))
            if len(hits) >= limit:
                return hits
    return hits


def tagged_files(files: list[Path], *tags: str) -> list[Path]:
    lowered = tuple(tag.lower() for tag in tags)
    return [path for path in files if any(tag in path.name.lower() for tag in lowered)]


def parse_init_services(files: list[Path]) -> list[tuple[str, str, str, EvidenceHit]]:
    services: list[tuple[str, str, str, EvidenceHit]] = []
    for path in files:
        for raw_line in safe_read(path).splitlines():
            line = raw_line.strip()
            match = SERVICE_RE.search(line)
            if not match:
                continue
            service, binary, argv = match.groups()
            services.append((service, binary, argv.strip(), EvidenceHit(relative(path), line)))
    return services


def parse_running_props(files: list[Path]) -> list[tuple[str, EvidenceHit]]:
    props: list[tuple[str, EvidenceHit]] = []
    for path in files:
        for raw_line in safe_read(path).splitlines():
            line = raw_line.strip()
            match = RUNNING_PROP_RE.match(line)
            if match:
                props.append((match.group(1), EvidenceHit(relative(path), line)))
    return props


def binary_pattern(spec: ServiceSpec) -> re.Pattern[str]:
    joined = "|".join(re.escape(item) for item in spec.binaries)
    return re.compile(rf"/(?:system|system_ext|vendor|odm|product)/[^\s:]*?(?:{joined})(?:\s|$)", re.IGNORECASE)


def init_service_matches(spec: ServiceSpec, service: str, binary: str, argv: str) -> bool:
    text = " ".join((service, binary, argv)).lower()
    return any(name.lower() in text for name in spec.names) or any(binary_name.lower() in text for binary_name in spec.binaries)


def map_native_path(android_path: str) -> str:
    if android_path.startswith("/system/vendor/"):
        return "/vendor/" + android_path.removeprefix("/system/vendor/")
    return android_path


def build_contracts(files: list[Path]) -> list[ServiceContract]:
    init_files = tagged_files(files, "init")
    prop_files = tagged_files(files, "prop")
    process_files = tagged_files(files, "process")
    binary_files = tagged_files(files, "binary")
    log_files = tagged_files(files, "logcat", "dmesg")
    init_services = parse_init_services(init_files)
    running_props = parse_running_props(prop_files)
    contracts: list[ServiceContract] = []
    for spec in SERVICE_SPECS:
        init_hits: list[EvidenceHit] = []
        prop_hits: list[EvidenceHit] = []
        android_service_names: list[str] = []
        android_path = ""
        android_argv = ""
        for service, binary, argv, hit in init_services:
            if init_service_matches(spec, service, binary, argv):
                init_hits.append(hit)
                if service not in android_service_names:
                    android_service_names.append(service)
                if not android_path:
                    android_path = binary
                    android_argv = argv
        for service, hit in running_props:
            if any(name.lower() == service.lower() for name in spec.names):
                prop_hits.append(hit)
                if service not in android_service_names:
                    android_service_names.append(service)
        process_hits = line_hits(process_files, spec.process_re, 30)
        log_hits = line_hits(log_files, spec.log_re, 30)
        binary_hits = line_hits(binary_files + init_files, binary_pattern(spec), 20)
        if process_hits:
            observed_state = "process-running"
        elif prop_hits:
            observed_state = "property-running"
        elif log_hits:
            observed_state = "log-observed"
        elif init_hits:
            observed_state = "init-declared"
        elif binary_hits:
            observed_state = "binary-present"
        else:
            observed_state = "missing"
        if not android_path and binary_hits:
            match = binary_pattern(spec).search(binary_hits[0].line)
            if match:
                android_path = match.group(0).strip()
        native_path = map_native_path(android_path) if android_path else ""
        path_source = "init-rc" if init_hits and android_path else "binary" if binary_hits and android_path else "missing"
        contracts.append(
            ServiceContract(
                key=spec.key,
                role=spec.role,
                required=spec.required,
                observed_state=observed_state,
                android_service_names=android_service_names,
                android_path=android_path,
                android_argv=android_argv,
                native_candidate_path=native_path,
                path_source=path_source,
                process_hits=process_hits,
                init_hits=init_hits,
                binary_hits=binary_hits,
                prop_hits=prop_hits,
                log_hits=log_hits,
            )
        )
    return contracts


def decide(command: str, contracts: list[ServiceContract]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v523-companion-contract-plan-ready", True, "plan-only; no evidence scan or device command executed", "run host-only contract synthesis"
    missing_required = [item.key for item in contracts if item.required and item.observed_state == "missing"]
    missing_paths = [item.key for item in contracts if item.required and item.observed_state != "missing" and not item.native_candidate_path]
    if missing_required:
        return "v523-companion-contract-blocked-missing-evidence", False, "missing required companion evidence: " + ", ".join(missing_required), "rerun Android recapture with widened exact service filters"
    if missing_paths:
        return "v523-companion-contract-path-gap", True, "required companions were observed but exact native paths are unresolved for: " + ", ".join(missing_paths), "recapture exact init rc and binaries for unresolved services before native start-only"
    return "v523-companion-contract-ready", True, "required companion service contracts have startable native candidate paths", "implement bounded native companion start-only proof"


def start_order(contracts: list[ServiceContract]) -> list[dict[str, str]]:
    order = ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper", "cnss_diag", "cnss_daemon")
    by_key = {item.key: item for item in contracts}
    rows: list[dict[str, str]] = []
    for index, key in enumerate(order, start=1):
        item = by_key[key]
        rows.append(
            {
                "order": str(index),
                "key": item.key,
                "path": item.native_candidate_path or "<unresolved>",
                "argv": item.android_argv,
                "state": item.observed_state,
                "path_source": item.path_source,
            }
        )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    contracts = manifest["contracts"]
    contract_rows = [
        [
            item["key"],
            item["role"],
            str(item["required"]),
            item["observed_state"],
            ", ".join(item["android_service_names"]) or "-",
            item["native_candidate_path"] or "-",
            item["path_source"],
        ]
        for item in contracts
    ]
    order_rows = [[row["order"], row["key"], row["path"], row["argv"] or "-", row["state"]] for row in manifest["proposed_start_order"]]
    return "\n".join(
        [
            "# V523 Companion Contract",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence Inputs",
            "",
            markdown_table(["input", "exists", "file_count"], [[item["path"], str(item["exists"]), str(item["file_count"])] for item in manifest["inputs"]]),
            "",
            "## Contracts",
            "",
            markdown_table(["key", "role", "required", "state", "android services", "native path", "path source"], contract_rows),
            "",
            "## Proposed Native Start Order",
            "",
            markdown_table(["order", "key", "path", "argv", "state"], order_rows),
            "",
            "## Important Evidence",
            "",
            *render_evidence_sections(contracts),
            "",
        ]
    )


def render_evidence_sections(contracts: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in contracts:
        lines.append(f"### {item['key']}")
        lines.append("")
        for section in ("init_hits", "prop_hits", "process_hits", "binary_hits", "log_hits"):
            hits = item.get(section) or []
            lines.append(f"- {section}:")
            if not hits:
                lines.append("  - none")
                continue
            for hit in hits[:5]:
                lines.append(f"  - `{hit['file']}`: {hit['line'][:220]}")
        lines.append("")
    return lines


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v521 = repo_path(args.v521_dir)
    v431 = repo_path(args.v431_dir)
    files = [] if args.command == "plan" else [*gather_files(v521), *gather_files(v431)]
    contracts = build_contracts(files) if files else [
        ServiceContract(spec.key, spec.role, spec.required, "not-scanned") for spec in SERVICE_SPECS
    ]
    decision, pass_ok, reason, next_step = decide(args.command, contracts)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": [
            {"path": str(v521), "exists": v521.exists(), "file_count": len(gather_files(v521)) if v521.exists() else 0},
            {"path": str(v431), "exists": v431.exists(), "file_count": len(gather_files(v431)) if v431.exists() else 0},
        ],
        "contracts": [asdict(contract) for contract in contracts],
        "proposed_start_order": start_order(contracts),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
