#!/usr/bin/env python3
"""Host-only V3426 direct-PID1 phase-observer design validator.

This module defines the marker and evidence contract for a future observer-only
candidate. It never contacts a device, builds a boot image, flashes, inserts a
module, writes sysfs/configfs, or selects a reset transition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import subprocess
import tempfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_v3426_phase_observer_design_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
SOURCE_ARCHIVE_SHA256 = "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf"
MODULE_DIR = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
MODULE_NAME = "sec_log_buf.ko"
MODULE_RUNTIME_NAME = "sec_log_buf"
MODULE_SHA256 = "b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61"
MODULE_SIZE = 76688
MODULE_VERMAGIC = (
    "5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 "
    "SMP preempt mod_unload modversions aarch64"
)
MODULE_LOAD_POSITION = 2
DRIVER_NAME = "samsung,kernel_log_buf"
DRIVER_BIND = (
    "/sys/bus/platform/drivers/samsung,kernel_log_buf/"
    "8.samsung,kernel_log_buf"
)

MAIN_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_main.c"
)
LAST_KMSG_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_last_kmsg.c"
)
AP_KLOG_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_ap_klog.c"
)
LOGGER_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_logger.c"
)
VH_LOGBUF_SOURCE = (
    "kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/"
    "sec_log_buf_vh_logbuf.c"
)
PRINTK_SOURCE = "kernel_platform/common/kernel/printk/printk.c"

PHASE_PRECHECK = "PRECHECK"
PHASE_FINAL = "FINAL"
PHASE_SEQUENCES = {PHASE_PRECHECK: 1, PHASE_FINAL: 2}
FRAME_START = b"[[S22PO1|"
FRAME_END = b"]]"
MAX_PAYLOAD_BYTES = 1024
HEX_128_RE = re.compile(r"^[0-9a-f]{32}$")
HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")
PAYLOAD_RE = re.compile(
    r"^run=(?P<run>[0-9a-f]{32});"
    r"phase=(?P<phase>PRECHECK|FINAL);"
    r"seq=(?P<seq>[0-9a-f]{8});"
    r"module=(?P<module>[0-9a-f]{64});"
    r"contract=(?P<contract>[0-9a-f]{64});"
    r"context=(?P<context>[0-9a-f]{64})$"
)

GATE_ORDER = (
    ("host_manifest_pinned", "host_identity"),
    ("volatile_filesystems_ready", "environment"),
    ("module_identity_verified", "identity"),
    ("module_loaded", "load"),
    ("proc_modules_eof_live", "registration"),
    ("driver_bound", "bind"),
    ("proc_nodes_present", "probe"),
    ("baseline_negative_control", "negative_control"),
    ("precheck_emitted", "capture_stimulus"),
    ("precheck_current_ring_verified", "capture"),
    ("final_emitted", "retention_stimulus"),
    ("final_current_ring_verified", "capture"),
)

FORBIDDEN_COMPONENTS = (
    "usb",
    "dwc3",
    "configfs",
    "sysfs_write",
    "sec_debug.ko",
    "max77705",
    "panic",
    "watchdog",
    "block_write",
    "persistent_mount",
    "android_start",
)

CONSUMED_MARKER_FAMILIES = (
    "S22O3ACM01",
    "S22O3FACM01",
    "S22_NATIVE_INIT_RETAINED_O3R1",
)

RESET_UNKNOWNS = (
    "warm_reboot_reserved_memory_preservation",
    "cold_boot_reserved_memory_preservation",
    "panic_reset_reserved_memory_preservation",
    "watchdog_reset_reserved_memory_preservation",
    "rdx_transition_reserved_memory_preservation",
    "bootloader_transition_reserved_memory_preservation",
    "bootloader_or_tz_reserved_region_zeroing",
)

CONTRACT_CORE: dict[str, Any] = {
    "schema": SCHEMA,
    "target": TARGET,
    "status": "HOST_DESIGN_PASS_NO_LIVE",
    "module": {
        "filename": MODULE_NAME,
        "runtime_name": MODULE_RUNTIME_NAME,
        "sha256": MODULE_SHA256,
        "size": MODULE_SIZE,
        "vermagic": MODULE_VERMAGIC,
        "load_position": MODULE_LOAD_POSITION,
        "hard_dependencies": [],
        "soft_dependencies": [],
        "driver": DRIVER_NAME,
        "bind": DRIVER_BIND,
    },
    "marker": {
        "protocol": "S22PO1",
        "start": FRAME_START.decode("ascii"),
        "end": FRAME_END.decode("ascii"),
        "length": "four lowercase hexadecimal payload bytes",
        "integrity": "crc32 over canonical ASCII payload",
        "run_id_bits": 128,
        "run_id_source": "secrets.token_hex(16)",
        "sequences": PHASE_SEQUENCES,
        "module_identity_bound": True,
        "contract_identity_bound": True,
        "physical_buffer_offset_defines_order": False,
    },
    "stage_a": {
        "gates": [
            {"name": name, "evidence": evidence}
            for name, evidence in GATE_ORDER
        ],
        "module_allowlist": [MODULE_NAME],
        "proc_nodes": ["/proc/last_kmsg", "/proc/ap_klog"],
        "baseline_current_run_markers": 0,
        "precheck_current_run_markers": [PHASE_PRECHECK],
        "final_current_run_markers": [PHASE_PRECHECK, PHASE_FINAL],
        "precheck_eviction_at_final": "FAIL",
        "acceptance_retries": 0,
        "result_boundary": "current_session_capture_only",
    },
    "stage_b": {
        "entry_gate": "exact current-run FINAL recovered from later /proc/last_kmsg",
        "same_session_last_kmsg_is_not_capture_evidence": True,
        "transition_selected": False,
        "result_boundary": "cross_session_retention_only_after_exact_recovery",
    },
    "forbidden_components": FORBIDDEN_COMPONENTS,
    "consumed_marker_families": CONSUMED_MARKER_FAMILIES,
    "reset_unknowns": RESET_UNKNOWNS,
    "fail_matrix": [
        {
            "condition": "module or kernel identity mismatch",
            "result": "STOP_BEFORE_LOAD",
        },
        {
            "condition": "registration, bind, or proc-node gate failure",
            "result": "STAGE_A_FAIL_NO_MARKER",
        },
        {
            "condition": "current-run marker present in baseline",
            "result": "STAGE_A_FAIL_STALE_OR_COLLISION",
        },
        {
            "condition": "PRECHECK missing, malformed, duplicate, or wrong identity",
            "result": "STAGE_A_FAIL_FINAL_FORBIDDEN",
        },
        {
            "condition": "FINAL or PRECHECK missing from final current-ring snapshot",
            "result": "STAGE_A_FAIL_NO_TRANSITION",
        },
        {
            "condition": "exact FINAL absent from later last_kmsg",
            "result": "RETENTION_FAIL_STAGE_B_AND_USB_FORBIDDEN",
        },
        {
            "condition": "exact FINAL recovered from later last_kmsg",
            "result": "RETENTION_PASS_STAGE_B_DESIGN_MAY_START",
        },
    ],
    "live_authorized": False,
    "candidate_source_authorized": False,
    "image_build_authorized": False,
    "transition_selected": False,
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


CONTRACT_SHA256 = hashlib.sha256(canonical_json(CONTRACT_CORE)).hexdigest()
PINNED_CONTRACT_SHA256 = "dbd3efbdbaece277a34a54f40ab1f2785e8115efa7924c17408f53c9debba8a8"
if CONTRACT_SHA256 != PINNED_CONTRACT_SHA256:
    raise RuntimeError(
        "phase-observer contract changed without an explicit pin update: "
        f"{CONTRACT_SHA256} != {PINNED_CONTRACT_SHA256}"
    )


class DesignError(ValueError):
    pass


@dataclass(frozen=True)
class Marker:
    run_id: str
    phase: str
    sequence: int
    module_sha256: str
    contract_sha256: str
    context_sha256: str
    crc32: str
    offset: int = -1


@dataclass(frozen=True)
class MarkerIssue:
    offset: int
    reason: str
    run_hint: str = ""


@dataclass(frozen=True)
class MarkerScan:
    markers: tuple[Marker, ...]
    issues: tuple[MarkerIssue, ...]


@dataclass(frozen=True)
class MarkerExpectation:
    run_id: str
    module_sha256: str
    contract_sha256: str
    precheck_context_sha256: str
    final_context_sha256: str


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise DesignError(f"could not locate repository root from {current}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hex(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not pattern.fullmatch(value):
        raise DesignError(f"invalid {label}: {value!r}")
    return value


def make_expectation(
    run_id: str,
    precheck_context_sha256: str,
    final_context_sha256: str,
    *,
    module_sha256: str = MODULE_SHA256,
    contract_sha256: str = CONTRACT_SHA256,
) -> MarkerExpectation:
    return MarkerExpectation(
        run_id=require_hex(run_id, HEX_128_RE, "run id"),
        module_sha256=require_hex(module_sha256, HEX_256_RE, "module sha256"),
        contract_sha256=require_hex(
            contract_sha256, HEX_256_RE, "contract sha256"
        ),
        precheck_context_sha256=require_hex(
            precheck_context_sha256, HEX_256_RE, "precheck context sha256"
        ),
        final_context_sha256=require_hex(
            final_context_sha256, HEX_256_RE, "final context sha256"
        ),
    )


def generate_run_id() -> str:
    return secrets.token_hex(16)


def encode_marker(
    expectation: MarkerExpectation,
    phase: str,
    *,
    sequence: int | None = None,
) -> bytes:
    if phase not in PHASE_SEQUENCES:
        raise DesignError(f"unsupported marker phase: {phase}")
    expected_sequence = PHASE_SEQUENCES[phase]
    if sequence is None:
        sequence = expected_sequence
    if sequence < 0 or sequence > 0xFFFFFFFF:
        raise DesignError(f"sequence out of range: {sequence}")
    context = (
        expectation.precheck_context_sha256
        if phase == PHASE_PRECHECK
        else expectation.final_context_sha256
    )
    payload = (
        f"run={expectation.run_id};phase={phase};seq={sequence:08x};"
        f"module={expectation.module_sha256};"
        f"contract={expectation.contract_sha256};context={context}"
    ).encode("ascii")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise DesignError("marker payload exceeds bounded parser limit")
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    return (
        FRAME_START
        + f"{len(payload):04x}|".encode("ascii")
        + payload
        + f"|crc={checksum:08x}".encode("ascii")
        + FRAME_END
    )


def _run_hint(candidate: bytes) -> str:
    match = re.search(rb"run=([0-9a-f]{32})", candidate)
    return match.group(1).decode("ascii") if match else ""


def scan_markers(blob: bytes) -> MarkerScan:
    markers: list[Marker] = []
    issues: list[MarkerIssue] = []
    cursor = 0
    while True:
        offset = blob.find(FRAME_START, cursor)
        if offset < 0:
            break
        header = offset + len(FRAME_START)
        if header + 5 > len(blob):
            issues.append(MarkerIssue(offset, "truncated-length"))
            break
        length_text = blob[header : header + 4]
        if not re.fullmatch(rb"[0-9a-f]{4}", length_text):
            issues.append(
                MarkerIssue(
                    offset,
                    "invalid-length-field",
                    _run_hint(blob[offset : offset + MAX_PAYLOAD_BYTES]),
                )
            )
            cursor = offset + 1
            continue
        if blob[header + 4 : header + 5] != b"|":
            issues.append(MarkerIssue(offset, "missing-length-separator"))
            cursor = offset + 1
            continue
        payload_length = int(length_text, 16)
        if payload_length > MAX_PAYLOAD_BYTES:
            issues.append(MarkerIssue(offset, "payload-too-large"))
            cursor = offset + 1
            continue
        payload_start = header + 5
        payload_end = payload_start + payload_length
        trailer_end = payload_end + len(b"|crc=") + 8 + len(FRAME_END)
        candidate = blob[offset : min(trailer_end, len(blob))]
        if trailer_end > len(blob):
            issues.append(
                MarkerIssue(offset, "truncated-frame", _run_hint(candidate))
            )
            break
        if blob[payload_end : payload_end + 5] != b"|crc=":
            issues.append(
                MarkerIssue(offset, "missing-crc-field", _run_hint(candidate))
            )
            cursor = offset + 1
            continue
        crc_text = blob[payload_end + 5 : payload_end + 13]
        if not re.fullmatch(rb"[0-9a-f]{8}", crc_text):
            issues.append(
                MarkerIssue(offset, "invalid-crc-field", _run_hint(candidate))
            )
            cursor = offset + 1
            continue
        if blob[payload_end + 13 : trailer_end] != FRAME_END:
            issues.append(
                MarkerIssue(offset, "missing-end-sentinel", _run_hint(candidate))
            )
            cursor = offset + 1
            continue
        payload = blob[payload_start:payload_end]
        try:
            payload_text = payload.decode("ascii")
        except UnicodeDecodeError:
            issues.append(
                MarkerIssue(offset, "non-ascii-payload", _run_hint(candidate))
            )
            cursor = trailer_end
            continue
        match = PAYLOAD_RE.fullmatch(payload_text)
        if not match:
            issues.append(
                MarkerIssue(offset, "non-canonical-payload", _run_hint(candidate))
            )
            cursor = trailer_end
            continue
        expected_crc = f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}"
        actual_crc = crc_text.decode("ascii")
        if actual_crc != expected_crc:
            issues.append(
                MarkerIssue(offset, "crc-mismatch", match.group("run"))
            )
            cursor = trailer_end
            continue
        markers.append(
            Marker(
                run_id=match.group("run"),
                phase=match.group("phase"),
                sequence=int(match.group("seq"), 16),
                module_sha256=match.group("module"),
                contract_sha256=match.group("contract"),
                context_sha256=match.group("context"),
                crc32=actual_crc,
                offset=offset,
            )
        )
        cursor = trailer_end
    return MarkerScan(tuple(markers), tuple(issues))


def _marker_errors(marker: Marker, expectation: MarkerExpectation) -> list[str]:
    errors: list[str] = []
    if marker.module_sha256 != expectation.module_sha256:
        errors.append("module-identity-mismatch")
    if marker.contract_sha256 != expectation.contract_sha256:
        errors.append("contract-identity-mismatch")
    expected_sequence = PHASE_SEQUENCES[marker.phase]
    if marker.sequence != expected_sequence:
        errors.append(f"{marker.phase.lower()}-sequence-mismatch")
    expected_context = (
        expectation.precheck_context_sha256
        if marker.phase == PHASE_PRECHECK
        else expectation.final_context_sha256
    )
    if marker.context_sha256 != expected_context:
        errors.append(f"{marker.phase.lower()}-context-mismatch")
    return errors


def classify_marker_snapshot(
    stage: str, blob: bytes, expectation: MarkerExpectation
) -> dict[str, Any]:
    if stage not in {"baseline", "precheck", "final", "retention"}:
        raise DesignError(f"unsupported snapshot stage: {stage}")
    scan = scan_markers(blob)
    current = [marker for marker in scan.markers if marker.run_id == expectation.run_id]
    foreign = [marker for marker in scan.markers if marker.run_id != expectation.run_id]
    current_issues = [
        issue for issue in scan.issues if issue.run_hint == expectation.run_id
    ]
    errors = [f"current-run-malformed:{issue.reason}" for issue in current_issues]
    raw_current_tokens = blob.count(f"run={expectation.run_id}".encode("ascii"))
    if raw_current_tokens > len(current):
        errors.append("current-run-unframed-or-malformed")

    if stage == "baseline":
        if current:
            errors.append("current-run-marker-present-before-stimulus")
    else:
        for marker in current:
            errors.extend(_marker_errors(marker, expectation))
        prechecks = [m for m in current if m.phase == PHASE_PRECHECK]
        finals = [m for m in current if m.phase == PHASE_FINAL]
        if stage == "precheck":
            if len(prechecks) != 1:
                errors.append(f"precheck-count:{len(prechecks)}")
            if finals:
                errors.append("final-present-before-final-stimulus")
        elif stage == "final":
            if len(prechecks) != 1:
                errors.append(f"precheck-count:{len(prechecks)}")
            if len(finals) != 1:
                errors.append(f"final-count:{len(finals)}")
            if len(prechecks) == 1 and len(finals) == 1:
                if prechecks[0].sequence >= finals[0].sequence:
                    errors.append("embedded-sequence-order-invalid")
        elif stage == "retention":
            if len(finals) != 1:
                errors.append(f"retained-final-count:{len(finals)}")
            if len(prechecks) > 1:
                errors.append(f"retained-precheck-count:{len(prechecks)}")
            if len(prechecks) == 1 and len(finals) == 1:
                if prechecks[0].sequence >= finals[0].sequence:
                    errors.append("embedded-sequence-order-invalid")

    return {
        "stage": stage,
        "pass": not errors,
        "errors": errors,
        "current_run_markers": [asdict(marker) for marker in current],
        "foreign_run_marker_count": len(foreign),
        "all_issue_count": len(scan.issues),
        "current_run_issues": [asdict(issue) for issue in current_issues],
    }


def classify_gate_trace(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    observed = list(events)
    expected_names = [name for name, _ in GATE_ORDER]
    observed_names = [str(event.get("name", "")) for event in observed]
    errors: list[str] = []
    if observed_names != expected_names:
        errors.append("gate-order-or-membership-mismatch")
    for event in observed:
        if event.get("status") != "PASS":
            errors.append(f"gate-not-pass:{event.get('name', '')}")
    if len(set(observed_names)) != len(observed_names):
        errors.append("duplicate-gate")
    return {
        "pass": not errors,
        "errors": errors,
        "expected": expected_names,
        "observed": observed_names,
    }


def _tar_texts(archive: Path, members: Iterable[str]) -> dict[str, str]:
    requested = tuple(members)
    with tempfile.TemporaryDirectory(prefix="s22plus-v3426-source-") as temp:
        destination = Path(temp)
        result = subprocess.run(
            ["tar", "-xzf", str(archive), "-C", str(destination), "--", *requested],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise DesignError(f"source extraction failed: {result.stderr.strip()}")
        output: dict[str, str] = {}
        for member in requested:
            path = destination / member
            if not path.is_file():
                raise DesignError(f"source member missing: {member}")
            output[member] = path.read_text(encoding="utf-8")
        return output


def _require_tokens(text: str, tokens: Iterable[str], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise DesignError(f"{label} missing source tokens: {missing}")


def _require_order(text: str, tokens: Iterable[str], label: str) -> None:
    position = 0
    for token in tokens:
        next_position = text.find(token, position)
        if next_position < 0:
            raise DesignError(f"{label} missing ordered token: {token}")
        position = next_position + len(token)


def _extract_function(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise DesignError(f"function signature missing: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise DesignError(f"function body missing: {signature}")
    depth = 0
    for index in range(brace, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise DesignError(f"unterminated function: {signature}")


def _modinfo_field(module: Path, field: str) -> str:
    result = subprocess.run(
        ["modinfo", "-F", field, str(module)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DesignError(f"modinfo {field} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _undefined_symbols(module: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["aarch64-linux-gnu-nm", "-u", str(module)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DesignError(f"undefined-symbol audit failed: {result.stderr.strip()}")
    return tuple(sorted(line.split()[-1] for line in result.stdout.splitlines() if line.split()))


def _module_metadata(module_dir: Path) -> dict[str, Any]:
    dep_lines = (module_dir / "modules.dep").read_text(encoding="utf-8").splitlines()
    dep_matches = []
    for line in dep_lines:
        left, separator, right = line.partition(":")
        if separator and Path(left).name == MODULE_NAME:
            dep_matches.append((left, right.strip()))
    if len(dep_matches) != 1 or dep_matches[0][1]:
        raise DesignError(f"unexpected modules.dep entry: {dep_matches}")
    softdep_text = (module_dir / "modules.softdep").read_text(encoding="utf-8")
    if re.search(rf"(?m)^softdep\s+{re.escape(MODULE_RUNTIME_NAME)}(?:\s|$)", softdep_text):
        raise DesignError("sec_log_buf has unexpected soft dependencies")
    load_lines = [
        line.strip()
        for line in (module_dir / "modules.load").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    positions = [index for index, value in enumerate(load_lines, 1) if value == MODULE_NAME]
    if positions != [MODULE_LOAD_POSITION]:
        raise DesignError(f"unexpected stock load position: {positions}")
    return {
        "modules_dep_rhs": [],
        "modules_softdep_edges": [],
        "modules_load_position": positions[0],
    }


def validate_static_inputs(root: Path) -> dict[str, Any]:
    archive = root / SOURCE_ARCHIVE
    module_dir = root / MODULE_DIR
    module = module_dir / MODULE_NAME
    if sha256_file(archive) != SOURCE_ARCHIVE_SHA256:
        raise DesignError("kernel source archive SHA256 mismatch")
    if module.stat().st_size != MODULE_SIZE:
        raise DesignError("sec_log_buf.ko size mismatch")
    if sha256_file(module) != MODULE_SHA256:
        raise DesignError("sec_log_buf.ko SHA256 mismatch")
    vermagic = _modinfo_field(module, "vermagic")
    if vermagic != MODULE_VERMAGIC:
        raise DesignError(f"sec_log_buf.ko vermagic mismatch: {vermagic!r}")
    depends = _modinfo_field(module, "depends")
    if depends:
        raise DesignError(f"sec_log_buf.ko unexpected modinfo depends: {depends}")
    aliases = tuple(line for line in _modinfo_field(module, "alias").splitlines() if line)
    if "of:N*T*Csamsung,kernel_log_buf" not in aliases:
        raise DesignError(f"sec_log_buf.ko OF alias mismatch: {aliases}")
    undefined_symbols = _undefined_symbols(module)
    if any("sec_debug" in symbol.lower() for symbol in undefined_symbols):
        raise DesignError("sec_log_buf.ko has an unexpected sec_debug symbol reference")
    metadata = _module_metadata(module_dir)

    source_texts = _tar_texts(
        archive,
        (
            MAIN_SOURCE,
            LAST_KMSG_SOURCE,
            AP_KLOG_SOURCE,
            LOGGER_SOURCE,
            VH_LOGBUF_SOURCE,
            PRINTK_SOURCE,
        ),
    )
    main = source_texts[MAIN_SOURCE]
    last_kmsg = source_texts[LAST_KMSG_SOURCE]
    ap_klog = source_texts[AP_KLOG_SOURCE]
    logger = source_texts[LOGGER_SOURCE]
    vh_logbuf = source_texts[VH_LOGBUF_SOURCE]
    printk = source_texts[PRINTK_SOURCE]

    _require_order(
        main,
        (
            "DEVICE_BUILDER(__log_buf_parse_dt",
            "DEVICE_BUILDER(__log_buf_prepare_buffer",
            "DEVICE_BUILDER(__last_kmsg_alloc_buffer",
            "DEVICE_BUILDER(__last_kmsg_pull_last_log",
            "DEVICE_BUILDER(__last_kmsg_procfs_create",
            "DEVICE_BUILDER(__log_buf_pull_early_buffer",
            "DEVICE_BUILDER(__log_buf_logger_init",
            "DEVICE_BUILDER(__ap_klog_proc_init",
            "DEVICE_BUILDER(__log_buf_probe_epilog",
        ),
        "sec_log_buf probe",
    )
    prepare_buffer = _extract_function(main, "static int __log_buf_prepare_buffer")
    prepare_buffer_raw = _extract_function(
        main, "static inline void __log_buf_prepare_buffer_raw"
    )
    _require_order(
        prepare_buffer,
        (
            "if (s_log_buf->magic != SEC_LOG_MAGIC)",
            "__log_buf_prepare_buffer_raw(drvdata);",
        ),
        "invalid-magic reset dispatch",
    )
    _require_tokens(
        prepare_buffer_raw,
        (
            "s_log_buf->magic = SEC_LOG_MAGIC;",
            "s_log_buf->idx = 0;",
            "s_log_buf->prev_idx = 0;",
        ),
        "invalid-magic reset body",
    )
    _require_tokens(
        main,
        ('.compatible = "samsung,kernel_log_buf"',),
        "sec_log_buf compatible",
    )
    _require_tokens(
        last_kmsg,
        (
            "int __last_kmsg_pull_last_log",
            "last_kmsg->size = __log_buf_copy_to_buffer(buf);",
            'LAST_LOG_BUF_NODE\t\t"last_kmsg"',
        ),
        "last_kmsg snapshot",
    )
    _require_order(
        _extract_function(ap_klog, "static int sec_ap_klog_open"),
        (
            "ap_klog->buf = vmalloc(sz_buf);",
            "ap_klog->size = __log_buf_copy_to_buffer(ap_klog->buf);",
        ),
        "ap_klog fresh open",
    )
    _require_tokens(
        _extract_function(ap_klog, "static int sec_ap_klog_release"),
        ("vfree(ap_klog->buf);", "ap_klog->buf = NULL;"),
        "ap_klog release",
    )
    _require_tokens(
        logger,
        (
            "case SEC_LOG_BUF_STRATEGY_VH_LOGBUF:",
            "logger = __log_buf_logger_vh_logbuf_creator();",
            "return drvdata->logger->probe(drvdata);",
        ),
        "logger strategy",
    )
    _require_tokens(
        vh_logbuf,
        (
            "register_trace_android_vh_logbuf(__trace_android_vh_logbuf,",
            "register_trace_android_vh_logbuf_pr_cont(",
            "__log_buf_write(text, text_len);",
        ),
        "vh_logbuf capture",
    )

    devkmsg_write = _extract_function(printk, "static ssize_t devkmsg_write")
    devkmsg_emit = _extract_function(printk, "int devkmsg_emit")
    log_store = _extract_function(printk, "static int log_store")
    log_output = _extract_function(printk, "static size_t log_output")
    vprintk_store = _extract_function(printk, "int vprintk_store")
    vprintk_emit = _extract_function(printk, "asmlinkage int vprintk_emit")
    _require_order(
        devkmsg_write,
        ("devkmsg_emit(facility, level", "return ret;"),
        "devkmsg write return",
    )
    _require_tokens(devkmsg_emit, ("vprintk_emit(",), "devkmsg emit")
    _require_order(
        log_store,
        ("prb_final_commit(&e);", "trace_android_vh_logbuf(prb, &r);", "return"),
        "printk hook commit",
    )
    _require_order(
        vprintk_emit,
        ("printed_len = vprintk_store", "return printed_len;"),
        "vprintk return",
    )
    _require_tokens(
        vprintk_store,
        ("return log_output(",),
        "vprintk store dispatch",
    )
    _require_tokens(
        log_output,
        ("return log_store(",),
        "log output dispatch",
    )

    return {
        "source_archive": {
            "path": str(SOURCE_ARCHIVE),
            "sha256": SOURCE_ARCHIVE_SHA256,
        },
        "module": {
            "path": str(MODULE_DIR / MODULE_NAME),
            "sha256": MODULE_SHA256,
            "size": MODULE_SIZE,
            "vermagic": vermagic,
            "modinfo_depends": [],
            "modinfo_aliases": list(aliases),
            "undefined_symbol_count": len(undefined_symbols),
            "sec_debug_symbol_references": [],
            **metadata,
        },
        "source_proofs": {
            "probe_order": "VERIFIED",
            "last_kmsg_is_pre_probe_snapshot": "VERIFIED",
            "ap_klog_fresh_open_reads_current_ring": "VERIFIED",
            "ap_klog_release_frees_snapshot": "VERIFIED",
            "strategy_3_vh_logbuf_source_path": (
                "SOURCE_VERIFIED_RUNTIME_SELECTION_DEFERRED"
            ),
            "devkmsg_write_hook_return_is_synchronous": "VERIFIED",
            "invalid_magic_resets_ring": "VERIFIED",
            "reset_class_preservation": "UNVERIFIABLE",
        },
        "sec_debug_required": False,
    }


def build_design(root: Path) -> dict[str, Any]:
    evidence = validate_static_inputs(root)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": "HOST_DESIGN_PASS_NO_LIVE",
        "contract_sha256": CONTRACT_SHA256,
        "contract": CONTRACT_CORE,
        "static_evidence": evidence,
        "proof_boundaries": {
            "baseline": "negative control only",
            "precheck": "current-session hook and current-ring capture",
            "final": "current-session FINAL committed to current ring",
            "retention": "only a later-session exact FINAL in /proc/last_kmsg",
            "same_session_last_kmsg": "never capture evidence",
        },
        "unverifiable": list(RESET_UNKNOWNS),
        "next": (
            "select and host-prove one exact transition/recovery envelope before "
            "any candidate source or live authorization"
        ),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "module_insertion": False,
            "reboot": False,
            "image_build": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    design = build_design(root)
    rendered = json.dumps(design, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
                raise SystemExit(f"generated design is stale: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
