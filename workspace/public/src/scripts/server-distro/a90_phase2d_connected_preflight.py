#!/usr/bin/env python3
"""Prepare exact read-only A90 V3406 connected evidence.

The default audit mode is host-only.  The explicit connected mode performs
bounded D0 reads against one exact by-id bridge: bridge continuity, V2321
baseline health, and absence of the three run-derived SD paths.  It cannot
flash, reboot, transfer a payload, stage a rootfs, or modify the device.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_absent_only_staging as staging  # noqa: E402


SCHEMA = "a90_phase2d_connected_preflight_v1"
PASS_DECISION = "A90_PHASE2D_CONNECTED_D0_AND_PATHS_PASS"
PRIVATE_RUN_BASE = staging.PRIVATE_RUN_BASE
RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$"
)
SEQUENCE_RE = re.compile(r"^[0-9]{2}$")
BRIDGE_DEVICE_PREFIX = "/dev/serial/by-id/"
USB_SYSFS = Path("/sys/bus/usb/devices")
TTY_SYSFS = Path("/sys/class/tty")
USB_VENDOR = "04e8"
USB_PRODUCT = "6861"
SELFTEST_RE = re.compile(
    r"\bpass=(?P<pass>[0-9]+)\b.*"
    r"\bwarn=(?P<warn>[0-9]+)\b.*"
    r"\bfail=(?P<fail>[0-9]+)\b.*"
    r"\bduration_ms=(?P<duration>[0-9]+)\b",
    re.DOTALL,
)
PSTORE_ENTRIES_RE = re.compile(r"\bpstore=[^\r\n]*\bentries=(?P<count>[0-9]+)\b")
PATH_MARKER_RE = re.compile(
    r"^A90_PHASE2D_PATH "
    r"final=(?P<final>absent|present) "
    r"work=(?P<work>absent|present) "
    r"stage=(?P<stage>absent|present)$",
    re.MULTILINE,
)


class ContractError(RuntimeError):
    """Raised when the bounded connected contract is not exact."""


def utc_now() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    return staging.sha256_file(path)


def require_regular_private(
    path: Path,
    *,
    expected_sha256: str,
) -> os.stat_result:
    lexical = path.lstat()
    if stat.S_ISLNK(lexical.st_mode):
        raise ContractError(f"artifact path must not be a symbolic link: {path}")
    resolved = path.resolve(strict=True)
    staging.require_below(resolved, staging.PRIVATE_ROOT, "private artifact")
    info = resolved.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o022
    ):
        raise ContractError(f"artifact is not an immutable regular file: {resolved}")
    if sha256_file(resolved) != expected_sha256:
        raise ContractError(f"artifact sha256 mismatch: {resolved}")
    return info


def exact_run_dir(run_id: str) -> Path:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("run ID is not the exact V3406 display form")
    run_dir = (PRIVATE_RUN_BASE / run_id).resolve(strict=True)
    staging.require_below(run_dir, PRIVATE_RUN_BASE, "run directory")
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ContractError("exact private run directory is not a directory")
    summary = run_dir / "keyed-rootfs-summary.json"
    info = summary.lstat()
    if (
        summary.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o077
    ):
        raise ContractError("keyed-rootfs summary is not exact private evidence")
    value = json.loads(summary.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("schema") != "a90-phase2d-keyed-rootfs-v1"
        or value.get("decision") != "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"
        or value.get("run_id") != run_id
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
        or value.get("f1_authorized") is not False
    ):
        raise ContractError("keyed-rootfs summary semantics are not exact")
    return run_dir


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict").strip()
    except OSError:
        return ""


def _usb_parent(path: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    for parent in (resolved, *resolved.parents):
        if _read_text(parent / "idVendor") and _read_text(parent / "idProduct"):
            return parent
    return None


def exact_usb_identity(expect_realpath: str) -> dict[str, Any]:
    realpath = Path(expect_realpath)
    if staging.BRIDGE_REALPATH_RE.fullmatch(expect_realpath) is None:
        raise ContractError("expected bridge realpath is not exact ttyACM")
    bridge_parent = _usb_parent(TTY_SYSFS / realpath.name)
    if bridge_parent is None:
        raise ContractError("exact bridge has no USB parent")
    matches: list[Path] = []
    for entry in USB_SYSFS.iterdir():
        if (
            _read_text(entry / "idVendor").lower() == USB_VENDOR
            and _read_text(entry / "idProduct").lower() == USB_PRODUCT
        ):
            matches.append(entry.resolve(strict=True))
    if len(matches) != 1 or bridge_parent not in matches:
        raise ContractError("exactly one matching A90 USB parent is required")
    serial = _read_text(bridge_parent / "serial")
    if not serial:
        raise ContractError("A90 USB serial is absent")
    return {
        "matching_a90_usb_devices": 1,
        "bridge_selected_realpath": expect_realpath,
        "usb_serial_sha256": hashlib.sha256(
            serial.encode("utf-8")
        ).hexdigest(),
        "usb_vendor_product": f"{USB_VENDOR}:{USB_PRODUCT}",
        "product_name": _read_text(bridge_parent / "product") or "A90",
    }


def require_exact_bridge(
    bridge_device: str,
    expect_realpath: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if not bridge_device.startswith(BRIDGE_DEVICE_PREFIX):
        raise ContractError("bridge device must be one exact /dev/serial/by-id path")
    selected = Path(bridge_device)
    if not selected.is_symlink() or str(selected.resolve(strict=True)) != expect_realpath:
        raise ContractError("bridge by-id path does not resolve to expected tty")
    spec = SimpleNamespace(
        bridge_device=bridge_device,
        bridge_realpath=expect_realpath,
    )
    payload = staging.require_exact_bridge(spec, args)
    if payload.get("selected_realpath") != expect_realpath:
        raise ContractError("bridge helper returned a different realpath")
    return payload


def parse_health(baseline: dict[str, Any]) -> dict[str, Any]:
    version = baseline["version"]
    status = baseline["status"]
    selftest = baseline["selftest"]
    selftest_text = str(selftest.get("text") or "")
    status_text = str(status.get("text") or "")
    selftest_match = SELFTEST_RE.search(selftest_text)
    pstore_match = PSTORE_ENTRIES_RE.search(status_text)
    if (
        selftest_match is None
        or int(selftest_match.group("fail")) != 0
        or pstore_match is None
        or int(pstore_match.group("count")) != 0
        or version.get("rc") != 0
        or status.get("rc") != 0
        or selftest.get("rc") != 0
    ):
        raise ContractError("V2321 health framing is not exact")
    return {
        "bridge_exact": True,
        "bridge_running": True,
        "version": staging.EXPECTED_BASELINE_VERSION,
        "version_build": staging.EXPECTED_BASELINE_BUILD,
        "pstore_entries": 0,
        "version_framed_rc": version["rc"],
        "status_framed_rc": status["rc"],
        "selftest": {
            "pass": int(selftest_match.group("pass")),
            "warn": int(selftest_match.group("warn")),
            "fail": 0,
            "duration_ms": int(selftest_match.group("duration")),
        },
    }


def write_private_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    staging.write_private_json_exclusive(path, payload)


def path_read_script(final: str, work: str, stage_dir: str) -> str:
    assignments = (
        f"FINAL={staging.shlex.quote(final)}",
        f"WORK={staging.shlex.quote(work)}",
        f"STAGE={staging.shlex.quote(stage_dir)}",
    )
    checks = (
        'if [ -e "$FINAL" ] || [ -L "$FINAL" ]; then F=present; else F=absent; fi',
        'if [ -e "$WORK" ] || [ -L "$WORK" ]; then W=present; else W=absent; fi',
        'if [ -e "$STAGE" ] || [ -L "$STAGE" ]; then S=present; else S=absent; fi',
        'printf "A90_PHASE2D_PATH final=%s work=%s stage=%s\\n" "$F" "$W" "$S"',
    )
    return "\n".join(("set -eu", *assignments, *checks))


def write_connected_result(
    *,
    run_dir: Path,
    run_id: str,
    sequence: str,
    bridge_device: str,
    usb_identity: dict[str, Any],
    host_ncm: dict[str, bool],
    health: dict[str, Any],
    candidate: Path,
    candidate_info: os.stat_result,
    candidate_sha256: str,
    rollback: Path,
    rollback_info: os.stat_result,
    rollback_sha256: str,
) -> Path:
    runner = (REVAL_DIR / "native_init_flash.py").resolve(strict=True)
    result = {
        "schema": staging.D0_RESULT_SCHEMA,
        "timestamp_utc": utc_now(),
        "run_id": f"{run_id}-connected-d0-{sequence}",
        "outcome": staging.D0_RESULT_OUTCOME,
        "target": {
            "profile": staging.TARGET_PROFILE,
            "matching_a90_usb_devices": 1,
            "bridge_device": bridge_device,
            **usb_identity,
        },
        "host_ncm": host_ncm,
        "health": health,
        "artifacts": {
            "candidate_boot": {
                "path": str(candidate),
                "size": candidate_info.st_size,
                "sha256": candidate_sha256,
            },
            "rollback_boot": {
                "path": str(rollback),
                "size": rollback_info.st_size,
                "sha256": rollback_sha256,
            },
        },
        "repository": {
            "runner": str(runner),
            "runner_sha256": sha256_file(runner),
            "connected_preflight": str(Path(__file__).resolve()),
            "connected_preflight_size": Path(__file__).stat().st_size,
            "connected_preflight_sha256": sha256_file(
                Path(__file__).resolve()
            ),
        },
        "safety": {
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rootfs_staged": False,
            "userdata_touched": False,
        },
        "next_gate": {
            "selected": "exact V3406 path-absence preflight",
            "prepared_f1_manifest_exists": False,
            "fresh_f1_approval_exists": False,
        },
    }
    output = run_dir / f"connected-d0-{sequence}.json"
    write_private_json_exclusive(output, result)
    return output


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if SEQUENCE_RE.fullmatch(args.evidence_sequence) is None:
        raise ContractError("evidence sequence must be exactly two digits")
    run_dir = exact_run_dir(args.run_id)
    candidate = args.candidate.resolve(strict=True)
    rollback = args.rollback.resolve(strict=True)
    candidate_sha256 = staging.validate_sha256(
        args.expect_candidate_sha256,
        "candidate sha256",
    )
    rollback_sha256 = staging.validate_sha256(
        args.expect_rollback_sha256,
        "rollback sha256",
    )
    candidate_info = require_regular_private(
        candidate,
        expected_sha256=candidate_sha256,
    )
    rollback_info = require_regular_private(
        rollback,
        expected_sha256=rollback_sha256,
    )
    require_exact_bridge(args.bridge_device, args.expect_realpath, args)
    usb_identity = exact_usb_identity(args.expect_realpath)
    host_ncm = staging.require_host_ncm_ready(
        args.device_ip,
        args.expect_realpath,
    )
    baseline = staging.require_baseline(
        args,
        input_mode="slow",
        input_char_delay_sec=0.02,
    )
    health = parse_health(baseline)
    connected_path = write_connected_result(
        run_dir=run_dir,
        run_id=args.run_id,
        sequence=args.evidence_sequence,
        bridge_device=args.bridge_device,
        usb_identity=usb_identity,
        host_ncm=host_ncm,
        health=health,
        candidate=candidate,
        candidate_info=candidate_info,
        candidate_sha256=candidate_sha256,
        rollback=rollback,
        rollback_info=rollback_info,
        rollback_sha256=rollback_sha256,
    )
    connected_size = connected_path.stat().st_size
    connected_sha256 = sha256_file(connected_path)
    final = str(staging.derive_remote_final(args.run_id))
    work = str(staging.REMOTE_WORK)
    stage_dir = str(staging.derive_stage_dir(args.run_id))
    remote = staging.run_remote(
        args,
        path_read_script(final, work, stage_dir),
    )
    text = str(remote.get("text") or "")
    matches = list(PATH_MARKER_RE.finditer(text))
    paths = (
        matches[0].groupdict()
        if len(matches) == 1
        else {"final": "invalid", "work": "invalid", "stage": "invalid"}
    )
    if (
        remote.get("rc") != 0
        or remote.get("status") != "ok"
        or paths != {"final": "absent", "work": "absent", "stage": "absent"}
    ):
        failure = {
            "schema": SCHEMA,
            "timestamp_utc": utc_now(),
            "run_id": args.run_id,
            "decision": "STOP_PATHS_NOT_EXACTLY_ABSENT",
            "connected_d0": {
                "path": str(connected_path),
                "size": connected_size,
                "sha256": connected_sha256,
            },
            "observed_states": paths,
            "safety": {
                "device_write": False,
                "flash": False,
                "payload_sent": False,
                "reboot_requested": False,
            },
        }
        write_private_json_exclusive(
            run_dir / f"connected-path-preflight-{args.evidence_sequence}-stop.json",
            failure,
        )
        raise ContractError("one or more exact V3406 device paths are not absent")
    path_result = {
        "schema": staging.PATH_PREFLIGHT_SCHEMA,
        "timestamp_utc": utc_now(),
        "run_id": args.run_id,
        "target_binding": {
            "connected_d0_result": str(connected_path),
            "connected_d0_result_sha256": connected_sha256,
            "target_profile": staging.TARGET_PROFILE,
            "exact_a90_bridge": True,
        },
        "read": {
            "kind": "bounded-connected-read-only",
            "framed_command": "run",
            "framed_rc": remote["rc"],
            "framed_status": remote["status"],
            "paths": {
                final: "absent",
                work: "absent",
                stage_dir: "absent",
            },
        },
        "safety": {
            "device_write": False,
            "payload_sent": False,
            "reboot_requested": False,
            "flash": False,
            "userdata_touched": False,
        },
    }
    path_output = (
        run_dir / f"connected-path-preflight-{args.evidence_sequence}.json"
    )
    write_private_json_exclusive(path_output, path_result)
    return {
        "schema": SCHEMA,
        "decision": PASS_DECISION,
        "run_id": args.run_id,
        "connected_d0": {
            "path": str(connected_path),
            "size": connected_size,
            "sha256": connected_sha256,
        },
        "connected_path_preflight": {
            "path": str(path_output),
            "size": path_output.stat().st_size,
            "sha256": sha256_file(path_output),
        },
        "candidate_authority": False,
        "f1_authorized": False,
        "live_authority": False,
        "device_contact": True,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
        "reboot_requested": False,
    }


def source_contract_issues(source: str) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ("connected D0 source is not valid Python",)
    validator_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "source_contract_issues"
        ),
        None,
    )
    if validator_node is None:
        return ("connected D0 source validator boundary is missing",)
    lines = source.splitlines(keepends=True)
    subject = "".join(
        lines[: validator_node.lineno - 1]
        + lines[validator_node.end_lineno :]
    )
    for token in (
        "staging.require_exact_bridge(spec, args)",
        "staging.require_host_ncm_ready(",
        "staging.require_baseline(",
        "path_read_script(final, work, stage_dir)",
        '"device_write": False',
        '"flash": False',
        '"payload_sent": False',
        '"reboot_requested": False',
        'mode.add_argument("--audit-only", action="store_true")',
        'mode.add_argument("--execute-connected-d0", action="store_true")',
    ):
        if token not in subject:
            issues.append(f"connected D0 source contract missing: {token!r}")
    for forbidden in (
        "--execute-approved-f1",
        "--execute-approved-stage",
        "flash_command(",
        "invoke_rollback(",
        "install_image(",
        "/bin/busybox rm",
        "/bin/busybox reboot",
        "/bin/busybox dd",
        '"device_write": True',
        '"flash": True',
        '"payload_sent": True',
        '"reboot_requested": True',
    ):
        if forbidden in subject:
            issues.append(
                f"connected D0 source contains forbidden action: {forbidden!r}"
            )
    ncm_gate = subject.find("host_ncm = staging.require_host_ncm_ready(")
    baseline_gate = subject.find("baseline = staging.require_baseline(")
    if ncm_gate < 0 or baseline_gate < 0 or ncm_gate >= baseline_gate:
        issues.append("connected D0 host NCM gate must precede baseline reads")
    return tuple(issues)


def audit_payload() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    issues = source_contract_issues(source)
    return {
        "schema": SCHEMA,
        "mode": "host-only-audit",
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "contract_issues": list(issues),
        "ready_for_connected_d0": not issues,
        "device_contact": False,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
        "reboot_requested": False,
        "f1_authorized": False,
        "live_authority": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--execute-connected-d0", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-sequence", default="01")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--expect-candidate-sha256")
    parser.add_argument("--rollback", type=Path)
    parser.add_argument("--expect-rollback-sha256")
    parser.add_argument("--bridge-device")
    parser.add_argument("--expect-realpath")
    parser.add_argument("--device-ip")
    parser.add_argument("--bridge-host", default="localhost")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--remote-timeout", type=float, default=60.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        for name in (
            "run_id",
            "candidate",
            "expect_candidate_sha256",
            "rollback",
            "expect_rollback_sha256",
            "bridge_device",
            "expect_realpath",
            "device_ip",
        ):
            if getattr(args, name) is not None:
                raise ContractError("audit mode accepts no connected inputs")
        result = audit_payload()
    else:
        for name in (
            "run_id",
            "candidate",
            "expect_candidate_sha256",
            "rollback",
            "expect_rollback_sha256",
            "bridge_device",
            "expect_realpath",
            "device_ip",
        ):
            if getattr(args, name) is None:
                raise ContractError(f"connected D0 requires --{name.replace('_', '-')}")
        result = execute(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-phase2d-connected-preflight: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
