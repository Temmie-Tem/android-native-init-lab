#!/usr/bin/env python3
"""V472 extended private property runtime live deploy and lookup proof.

The live path copies the V471 host-only property layout into a versioned private
SD workspace and verifies read-only property lookups against that private root.
It does not replace global `/dev/__properties__`, create a property-service
socket, mutate properties, start Wi-Fi daemons, or bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v472-extended-property-runtime-live")
DEFAULT_V471 = Path("tmp/wifi/v471-extended-private-property-runtime/manifest.json")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "9d219f2c28102a8c56d3b283b37c14af12603d9c89700240f3a3d980b5f7de7f"
REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317/v471"
REMOTE_PROP_ROOT = REMOTE_WORKDIR + "/dev/__properties__"
TOYBOX = "/cache/bin/toybox"
REMOTE_DIR_MODE = "755"
REMOTE_PROP_FILE_MODE = "444"
REMOTE_MANIFEST_FILE_MODE = "600"
CHUNK_SIZE = 1536
APPROVAL_PHRASE = (
    "approve v472 extended private property runtime deploy and lookup proof only; "
    "no daemon start and no Wi-Fi bring-up"
)
SAFE_DEVICE_PATH_RE = re.compile(r"^[A-Za-z0-9_./:+-]+$")
SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")

LOOKUP_KEYS = (
    "ro.property_service.version",
    "sys.boot_completed",
    "dev.bootcomplete",
    "wifi.interface",
    "wlan.driver.status",
    "init.svc.servicemanager",
    "init.svc.hwservicemanager",
    "init.svc.vendor.wifi_hal_ext",
    "init.svc.vendor.wifi_hal_legacy",
    "init.svc.vendor.wifi_hal",
    "init.svc.wificond",
    "init.svc.wpa_supplicant",
    "init.svc.cnss-daemon",
    "init.svc.cnss_diag",
)


@dataclass
class LayoutFile:
    role: str
    relative_path: str
    local_path: str
    remote_path: str
    bytes: int
    sha256: str
    status: str


@dataclass
class CommandRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass
class LookupResult:
    key: str
    expected: str
    actual: str
    rc: int | None
    status: str
    stdout_empty: bool
    context_warning_count: int
    access_denied_count: int
    ok: bool
    file: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v471-manifest", type=Path, default=DEFAULT_V471)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("lookup")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_relative_path(path: str) -> bool:
    if not path or "\x00" in path:
        return False
    value = Path(path)
    return not value.is_absolute() and ".." not in value.parts and path.startswith("layout/dev/__properties__/")


def validate_device_path(path: str) -> bool:
    return (
        bool(path)
        and "\x00" not in path
        and "'" not in path
        and path.startswith(REMOTE_WORKDIR + "/")
        and ".." not in Path(path).parts
        and bool(SAFE_DEVICE_PATH_RE.match(path))
    )


def layout_files(v471: dict[str, Any]) -> list[LayoutFile]:
    base_dir = Path(str(v471.get("path") or "")).parent
    files: list[LayoutFile] = []
    for item in v471.get("files", []):
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("relative_path") or "")
        expected_sha = str(item.get("sha256") or "")
        expected_size = int(item.get("bytes") or 0)
        local_path = base_dir / relative_path
        remote_suffix = relative_path.removeprefix("layout/")
        remote_path = f"{REMOTE_WORKDIR}/{remote_suffix}"
        status = "pass"
        if not validate_relative_path(relative_path) or not validate_device_path(remote_path):
            status = "unsafe-path"
        elif not local_path.exists():
            status = "missing-local"
        else:
            data = local_path.read_bytes()
            if sha256_bytes(data) != expected_sha or len(data) != expected_size:
                status = "hash-or-size-mismatch"
        files.append(LayoutFile(
            role=str(item.get("role") or ""),
            relative_path=relative_path,
            local_path=str(local_path),
            remote_path=remote_path,
            bytes=expected_size,
            sha256=expected_sha,
            status=status,
        ))
    return files


def expected_values(v471: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for seed in v471.get("seeds", []):
        if isinstance(seed, dict):
            values[str(seed.get("key") or "")] = str(seed.get("value") or "")
    return values


def quote_command(argv: list[str]) -> str:
    return " ".join(argv)


def write_command_record(store: EvidenceStore,
                         name: str,
                         argv: list[str],
                         result: ProtocolResult | None,
                         started: float,
                         error: str = "") -> CommandRecord:
    duration = time.monotonic() - started
    text = result.text if result is not None else error + "\n"
    path = store.write_text(f"commands/{name}.txt", text)
    ok = bool(result is not None and result.rc == 0 and result.status == "ok")
    return CommandRecord(
        name=name,
        command=quote_command(argv),
        ok=ok,
        rc=result.rc if result is not None else None,
        status=result.status if result is not None else "missing",
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        error=error,
    )


def device_cmd(args: argparse.Namespace,
               store: EvidenceStore,
               records: list[CommandRecord],
               name: str,
               argv: list[str],
               timeout: float | None = None) -> ProtocolResult:
    started = time.monotonic()
    try:
        result = run_cmdv1_command(args.host, args.port, timeout or args.timeout, argv, retry_unsafe=False)
    except Exception as exc:  # noqa: BLE001 - live evidence must preserve failures
        records.append(write_command_record(store, name, argv, None, started, str(exc)))
        raise
    records.append(write_command_record(store, name, argv, result, started))
    if result.rc != 0 or result.status != "ok":
        raise RuntimeError(f"device command failed: {name} rc={result.rc} status={result.status}")
    return result


def uuencode_base64_payload(data: bytes, name: str, mode: str = REMOTE_MANIFEST_FILE_MODE) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.+-]", "_", name) or "payload"
    encoded = base64.b64encode(data).decode("ascii")
    lines = [f"begin-base64 {mode} {safe_name}"]
    lines.extend(encoded[index:index + 76] for index in range(0, len(encoded), 76))
    lines.append("====")
    return "\n".join(lines) + "\n"


def upload_bytes(args: argparse.Namespace,
                 store: EvidenceStore,
                 records: list[CommandRecord],
                 remote_path: str,
                 data: bytes,
                 expected_sha: str,
                 label: str,
                 mode: str = REMOTE_PROP_FILE_MODE) -> None:
    if args.chunk_size < 256 or args.chunk_size > 1800:
        raise RuntimeError("chunk size must be between 256 and 1800")
    tmp_uue = remote_path + ".uue"
    tmp_file = remote_path + ".tmp"
    for path in (remote_path, tmp_uue, tmp_file):
        if not validate_device_path(path):
            raise RuntimeError(f"unsafe remote path: {path}")
    device_cmd(args, store, records, f"{label}-rm-old", ["run", TOYBOX, "rm", "-f", tmp_uue, tmp_file, remote_path])
    encoded_text = uuencode_base64_payload(data, Path(remote_path).name, mode)
    for index in range(0, len(encoded_text), args.chunk_size):
        chunk = encoded_text[index:index + args.chunk_size]
        device_cmd(args, store, records, f"{label}-chunk-{index // args.chunk_size:04d}", ["appendfile", tmp_uue, chunk])
    device_cmd(args, store, records, f"{label}-decode", ["run", TOYBOX, "uudecode", "-o", tmp_file, tmp_uue])
    sha_result = device_cmd(args, store, records, f"{label}-sha256", ["run", TOYBOX, "sha256sum", tmp_file])
    match = SHA256_RE.search(sha_result.text)
    actual_sha = match.group(1).lower() if match else ""
    if actual_sha != expected_sha:
        raise RuntimeError(f"sha256 mismatch for {remote_path}: expected={expected_sha} actual={actual_sha}")
    device_cmd(args, store, records, f"{label}-mv", ["run", TOYBOX, "mv", "-f", tmp_file, remote_path])
    device_cmd(args, store, records, f"{label}-chmod", ["run", TOYBOX, "chmod", mode, remote_path])
    device_cmd(args, store, records, f"{label}-rm-uue", ["run", TOYBOX, "rm", "-f", tmp_uue])


def mkdir_sequence(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord]) -> None:
    for index, path in enumerate((REMOTE_WORKDIR, REMOTE_WORKDIR + "/dev", REMOTE_PROP_ROOT), start=1):
        device_cmd(args, store, records, f"mkdir-{index}", ["mkdir", path])
        device_cmd(args, store, records, f"chmod-dir-{index}", ["run", TOYBOX, "chmod", REMOTE_DIR_MODE, path])


def cleanup_sequence(args: argparse.Namespace, store: EvidenceStore, records: list[CommandRecord]) -> None:
    device_cmd(args, store, records, "cleanup-workdir", ["run", TOYBOX, "rm", "-rf", REMOTE_WORKDIR])


def helper_lookup_argv(args: argparse.Namespace, key: str) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "property-lookup",
        "--target-profile",
        "system-getprop",
        "--null-device-mode",
        "dev-null-selinux",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--property-root",
        REMOTE_PROP_ROOT,
        "--property-key",
        key,
        "--timeout-sec",
        "3",
    ]


def extract_block(text: str, begin: str, end: str) -> str:
    pattern = re.compile(re.escape(begin) + r"\n(.*?)\n" + re.escape(end), re.S)
    match = pattern.search(text)
    return match.group(1).replace("\r", "") if match else ""


def run_lookup(args: argparse.Namespace,
               store: EvidenceStore,
               records: list[CommandRecord],
               expected: dict[str, str]) -> list[LookupResult]:
    results: list[LookupResult] = []
    for key in LOOKUP_KEYS:
        argv = helper_lookup_argv(args, key)
        record_count = len(records)
        result = device_cmd(args, store, records, f"lookup-{re.sub(r'[^A-Za-z0-9_.+-]+', '-', key)}", argv, timeout=args.timeout + 5.0)
        record = records[record_count]
        text = result.text
        stdout = extract_block(text, "A90_EXECNS_STDOUT_BEGIN", "A90_EXECNS_STDOUT_END")
        stderr = extract_block(text, "A90_EXECNS_STDERR_BEGIN", "A90_EXECNS_STDERR_END")
        context_warnings = len(re.findall(r"Could not find context for property", stderr))
        access_denied = len(re.findall(r"Access denied finding property", stderr))
        expected_value = expected.get(key, "")
        ok = (
            result.rc == 0
            and result.status == "ok"
            and stdout == expected_value
            and context_warnings == 0
            and access_denied == 0
        )
        results.append(LookupResult(
            key=key,
            expected=expected_value,
            actual=stdout,
            rc=result.rc,
            status=result.status,
            stdout_empty=stdout == "",
            context_warning_count=context_warnings,
            access_denied_count=access_denied,
            ok=ok,
            file=record.file,
        ))
    return results


def preflight_commands(args: argparse.Namespace,
                       store: EvidenceStore,
                       records: list[CommandRecord]) -> None:
    device_cmd(args, store, records, "version", ["version"])
    device_cmd(args, store, records, "status", ["status"])
    device_cmd(args, store, records, "selftest", ["selftest"])
    device_cmd(args, store, records, "mountsystem-ro", ["mountsystem", "ro"], timeout=20.0)
    device_cmd(args, store, records, "stat-helper", ["stat", args.helper])
    device_cmd(args, store, records, "sha-helper", ["run", TOYBOX, "sha256sum", args.helper])
    device_cmd(args, store, records, "stat-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"])
    device_cmd(args, store, records, "stat-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"])


def build_checks(args: argparse.Namespace,
                 v471: dict[str, Any],
                 files: list[LayoutFile],
                 records: list[CommandRecord],
                 lookups: list[LookupResult]) -> list[Check]:
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    sha_text = "\n".join(
        Path(record.file).name + " " + repo_path(args.out_dir).joinpath(record.file).read_text(encoding="utf-8", errors="replace")
        for record in records
        if record.name == "sha-helper"
    )
    lookup_failures = [item.key for item in lookups if not item.ok]
    command_failures = [record.name for record in records if not record.ok]
    return [
        Check(
            "v471-layout",
            "pass" if v471.get("decision") == "v471-extended-private-property-runtime-ready" and bool(v471.get("pass")) else "blocked",
            "blocker",
            f"decision={v471.get('decision')} pass={v471.get('pass')}",
            [str(v471.get("path", ""))],
            "regenerate V471 before live deploy",
        ),
        Check(
            "layout-files",
            "pass" if files and not bad_files else "blocked",
            "blocker",
            f"files={len(files)} bad={len(bad_files)} bytes={sum(item.bytes for item in files)}",
            bad_files[:8],
            "fix local V471 layout before live deploy",
        ),
        Check(
            "approval-gate",
            "pass" if approved(args) else "needs-operator",
            "approval",
            f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
            [APPROVAL_PHRASE],
            "provide exact approval phrase and flags before live private deploy",
        ),
        Check(
            "helper-v36",
            "pass" if args.command == "plan" or args.helper_sha256 in sha_text else "blocked",
            "blocker",
            f"expected_sha={args.helper_sha256}",
            [line for line in sha_text.splitlines() if args.helper in line][:2],
            "deploy helper v36 before property lookup proof",
        ),
        Check(
            "device-commands",
            "pass" if not command_failures else "blocked",
            "blocker",
            f"failed={len(command_failures)}",
            command_failures[:10],
            "inspect command evidence and recover native control before retry",
        ),
        Check(
            "property-lookups",
            "pass" if args.command not in ("lookup", "run") or (lookups and not lookup_failures) else "blocked",
            "blocker",
            f"lookups={len(lookups)} failures={len(lookup_failures)}",
            lookup_failures[:12],
            "fix extended property layout before Samsung registration retry",
        ),
    ]


def decide(args: argparse.Namespace, checks: list[Check], live_error: str) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    approvals = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if args.command == "plan":
        return "v472-extended-property-runtime-plan-ready", True, "plan generated without device mutation", "run preflight"
    if blockers:
        return "v472-extended-property-runtime-blocked", False, "blocked checks: " + ", ".join(blockers), "resolve blockers before live proof"
    if args.command == "preflight":
        return "v472-extended-property-runtime-preflight-ready", True, "preflight passed; live run still requires exact approval", "run approved V472 private deploy"
    if args.command == "lookup" and not live_error:
        return "v472-extended-property-runtime-lookup-pass", True, "selected property lookups passed against the deployed V471 private root", "rerun Samsung registration proof against the V471 root"
    if approvals:
        return "v472-extended-property-runtime-approval-required", False, "missing approval gates: " + ", ".join(approvals), "provide exact approval if live private deploy is intended"
    if live_error:
        return "v472-extended-property-runtime-failed", False, live_error, "inspect evidence and retry only after cleanup"
    return "v472-extended-property-runtime-lookup-pass", True, "V471 private property root deployed and selected property lookups passed", "rerun Samsung registration proof against the V471 root"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    store.mkdir("commands")
    v471 = load_json(args.v471_manifest)
    files = layout_files(v471)
    expected = expected_values(v471)
    records: list[CommandRecord] = []
    lookups: list[LookupResult] = []
    live_error = ""

    if args.command in ("preflight", "lookup", "run"):
        try:
            preflight_commands(args, store, records)
            if args.command == "lookup":
                lookups = run_lookup(args, store, records, expected)
            elif args.command == "run" and approved(args):
                cleanup_sequence(args, store, records)
                mkdir_sequence(args, store, records)
                for index, entry in enumerate(files, start=1):
                    upload_bytes(
                        args,
                        store,
                        records,
                        entry.remote_path,
                        Path(entry.local_path).read_bytes(),
                        entry.sha256,
                        f"file-{index:02d}",
                    )
                lookups = run_lookup(args, store, records, expected)
        except Exception as exc:  # noqa: BLE001 - keep evidence
            live_error = str(exc)
    checks = build_checks(args, v471, files, records, lookups)
    decision, pass_ok, reason, next_step = decide(args, checks, live_error)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "remote_workdir": REMOTE_WORKDIR,
        "remote_property_root": REMOTE_PROP_ROOT,
        "remote_modes": {
            "directories": REMOTE_DIR_MODE,
            "property_files": REMOTE_PROP_FILE_MODE,
            "manifest": REMOTE_MANIFEST_FILE_MODE,
            "basis": "AOSP property_info and prop_area files are world-readable read-only runtime artifacts",
        },
        "inputs": {
            "v471": {"path": v471.get("path"), "present": bool(v471.get("present")), "decision": v471.get("decision"), "pass": v471.get("pass")},
        },
        "checks": [asdict(check) for check in checks],
        "files": [asdict(entry) for entry in files],
        "commands": [asdict(record) for record in records],
        "lookups": [asdict(item) for item in lookups],
        "live_error": live_error,
        "device_commands_executed": bool(records),
        "device_mutations": args.command == "run" and approved(args) and any(record.name.startswith("file-") or record.name.startswith("mkdir") for record in records),
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "blocked_actions": [
            "global /dev/__properties__ replacement",
            "global bind mount over /dev/__properties__",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "persistent boot/autostart changes",
            "Android partition writes",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    file_rows = [[item["role"], item["relative_path"], str(item["bytes"]), item["status"]] for item in manifest["files"]]
    lookup_rows = [
        [item["key"], item["expected"], item["actual"], str(item["context_warning_count"]), str(item["access_denied_count"]), str(item["ok"])]
        for item in manifest["lookups"]
    ]
    return "\n".join([
        "# V472 Extended Private Property Runtime Live Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- remote_property_root: `{manifest['remote_property_root']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], check_rows),
        "",
        "## Files",
        "",
        markdown_table(["role", "relative_path", "bytes", "status"], file_rows),
        "",
        "## Lookups",
        "",
        markdown_table(["key", "expected", "actual", "context_warnings", "access_denied", "ok"], lookup_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
