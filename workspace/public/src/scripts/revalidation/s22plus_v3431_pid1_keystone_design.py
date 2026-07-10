#!/usr/bin/env python3
"""Host-only V3431 S22+ direct-PID1 keystone proof design validator.

This unit defines a minimal positive-evidence contract. It does not contact a
device, build an image, authorize live work, or flash anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import tarfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import s22plus_v3426_phase_observer_design as observer


SCHEMA = "s22plus_v3431_pid1_keystone_design_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_LIVE_OSRELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EMBEDDED_MODULE_PATH = "/observer/sec_log_buf.ko"

SOURCE_ARCHIVE = observer.SOURCE_ARCHIVE
SOURCE_ARCHIVE_SHA256 = observer.SOURCE_ARCHIVE_SHA256
MODULE_NAME = observer.MODULE_NAME
MODULE_SHA256 = observer.MODULE_SHA256
MODULE_SIZE = observer.MODULE_SIZE
MODULE_VERMAGIC = observer.MODULE_VERMAGIC

GKI_CONFIG = "kernel_platform/msm-kernel/arch/arm64/configs/gki_defconfig"
WAIPIO_GKI_CONFIG = (
    "kernel_platform/msm-kernel/arch/arm64/configs/vendor/waipio-gki_defconfig"
)
WAIPIO_SEC_CONFIG = (
    "kernel_platform/msm-kernel/arch/arm64/configs/vendor/waipio_sec_defconfig"
)
KERNEL_INIT_SOURCE = "kernel_platform/common/init/main.c"
KERNEL_MODULE_SOURCE = "kernel_platform/common/kernel/module.c"
BUILDER_PATTERN_SOURCE = (
    "kernel_platform/msm-kernel/include/linux/samsung/builder_pattern.h"
)
SEC_LOG_MAIN_SOURCE = observer.MAIN_SOURCE

REPORT_PINS = {
    "stock_transition_positive_control": {
        "path": (
            "docs/reports/"
            "NATIVE_INIT_V3428R_S22PLUS_STOCK_TRANSITION_POSITIVE_CONTROL_"
            "LIVE_PASS_2026-07-10.md"
        ),
        "sha256": "21e233829a583b186377cb9aa0b330821e928fa41d13a7ab965cf6e06254ea3d",
    },
    "v3430_no_proof": {
        "path": (
            "docs/reports/"
            "NATIVE_INIT_V3430_S22PLUS_V3429_PHASE_OBSERVER_LIVE_NO_PROOF_"
            "2026-07-10.md"
        ),
        "sha256": "951a7749a3ba90c3998945e1e4c6de73969f0ac2ce937f15e6de1b854cf12c19",
    },
    "android_sec_debug_positive_control": {
        "path": "docs/reports/S22PLUS_SEC_DEBUG_MID_SYSRQ_LIVE_RESULT_2026-07-08.md",
        "sha256": "34bac6f3a09242361b1f7a72900972037f5c804a4eec226fe4d8d2627ce5e466",
    },
    "native_sec_debug_no_hit": {
        "path": "docs/reports/S22PLUS_SEC_DEBUG_M18_LIVE_RESULT_2026-07-08.md",
        "sha256": "c434ecbc269544751b4685ee50197d9554263d8da061de1bda8dc0e4dcff647e",
    },
    "native_pmsg_no_hit": {
        "path": "docs/reports/S22PLUS_M24_PMSG_STEPS_LIVE_RESULT_2026-07-08.md",
        "sha256": "e002c17c72138db19e753a4a9510457bc12870e9535708af9c57b66e8b234011",
    },
    "native_ramoops_no_hit": {
        "path": (
            "docs/reports/"
            "S22PLUS_RAMOOPS_DTBO_M22_SYSRQ_PANIC_LIVE_RESULT_2026-07-08.md"
        ),
        "sha256": "ab5b52d9b36b6f827eb160a33d5fe85d345948d413e51faaffe887506b3da8ff",
    },
}

PHASE = "PID1_ENTER"
SEQUENCE = 1
FRAME_START = b"[[S22P1K1|"
FRAME_END = b"]]"
MAX_PAYLOAD_BYTES = 1024
HEX_128_RE = re.compile(r"^[0-9a-f]{32}$")
HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")
PAYLOAD_RE = re.compile(
    r"^run=(?P<run>[0-9a-f]{32});"
    r"phase=(?P<phase>PID1_ENTER);"
    r"seq=(?P<seq>[0-9a-f]{8});"
    r"pid=(?P<pid>[0-9a-f]{8});"
    r"module=(?P<module>[0-9a-f]{64});"
    r"contract=(?P<contract>[0-9a-f]{64});"
    r"context=(?P<context>[0-9a-f]{64})$"
)

CANDIDATE_GATE_ORDER = (
    "raw_getpid_returned_one",
    "volatile_proc_sys_dev_ready",
    "embedded_module_opened_read_only",
    "finit_module_returned_zero",
    "last_kmsg_and_ap_klog_nodes_present",
    "pid1_enter_marker_full_write_returned",
    "quiet_nonreturning_park",
)

FORBIDDEN_PROOF_CHANNELS = {
    "intentional_panic": (
        "sec_debug is CONFIG_SEC_DEBUG=m and early direct-PID1 panic retention "
        "was not proved"
    ),
    "pmsg": "native M24 produced no retained marker",
    "ramoops": "native M22 produced no retained pstore marker",
    "usb": "host USB enumeration is a later capability, not PID1 proof",
    "timed_reboot_or_download": (
        "bare-PID1 reboot behavior and manual transition timing are ambiguous"
    ),
    "persistent_partition_marker": "persistent partition writes are forbidden",
}

CONTRACT_CORE: dict[str, Any] = {
    "schema": SCHEMA,
    "target": TARGET,
    "status": "HOST_DESIGN_PASS_NO_LIVE",
    "claim": (
        "positive marker proves the exact candidate reached its marker path as "
        "PID 1 and the exact sec_log_buf observer was active"
    ),
    "claim_kind": "conjunctive_pid1_execution_and_observer_load",
    "kernel": {
        "expected_connected_live_osrelease": EXPECTED_LIVE_OSRELEASE,
        "connected_preflight_exact_equality_required": True,
        "candidate_runtime_osrelease_gate_before_marker": False,
    },
    "observer": {
        "filename": MODULE_NAME,
        "embedded_path": EMBEDDED_MODULE_PATH,
        "sha256": MODULE_SHA256,
        "size": MODULE_SIZE,
        "vermagic": MODULE_VERMAGIC,
        "hard_dependencies": [],
        "soft_dependencies": [],
        "only_runtime_module": True,
    },
    "candidate": {
        "runtime": "freestanding_raw_aarch64_syscalls",
        "entry_pid_check": "raw getpid return must equal 1",
        "marker_pid_source": "raw getpid return value, not a literal claim",
        "candidate_gate_order": CANDIDATE_GATE_ORDER,
        "marker_reachable_only_after_all_prior_gates": True,
        "fork_clone_exec_before_marker": False,
        "failure_behavior": "quiet_nonreturning_park_without_run_token",
        "marker_write_count": 1,
        "marker_acceptance_retry_count": 0,
    },
    "marker": {
        "protocol": "S22P1K1",
        "phase": PHASE,
        "sequence": SEQUENCE,
        "pid": 1,
        "start": FRAME_START.decode("ascii"),
        "end": FRAME_END.decode("ascii"),
        "length": "four lowercase hexadecimal payload bytes",
        "integrity": "crc32 over canonical ASCII payload",
        "run_id_bits": 128,
        "run_id_source": "secrets.token_hex(16)",
        "module_contract_context_bound": True,
    },
    "host_preflight": {
        "exact_target_and_magisk_boot_health": True,
        "exact_live_osrelease_equality": EXPECTED_LIVE_OSRELEASE,
        "current_run_absent_from_ap_klog_and_last_kmsg": True,
        "candidate_and_rollback_artifacts_sha_pinned": True,
        "single_target_transport": True,
    },
    "collection": {
        "transition": "attended_manual_rdx_download_then_magisk_boot_rollback",
        "first_rollback_boot_health_required": True,
        "first_last_kmsg_reads": 2,
        "both_reads_eof_complete_and_byte_identical": True,
        "positive": "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD",
        "absence": "NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP",
        "integrity_error": "FAIL_STOP",
    },
    "forbidden_proof_channels": FORBIDDEN_PROOF_CHANNELS,
    "live_authorized": False,
    "candidate_source_authorized": False,
    "image_build_authorized": False,
    "flash_authorized": False,
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


CONTRACT_SHA256 = hashlib.sha256(canonical_json(CONTRACT_CORE)).hexdigest()
PINNED_CONTRACT_SHA256 = "686207c75d2530f90049de6b6945fbd3134019ca402f84cb97418c43804a4ca5"
if CONTRACT_SHA256 != PINNED_CONTRACT_SHA256:
    raise RuntimeError(
        "PID1 keystone contract changed without an explicit pin update: "
        f"{CONTRACT_SHA256} != {PINNED_CONTRACT_SHA256}"
    )


class DesignError(ValueError):
    pass


@dataclass(frozen=True)
class MarkerExpectation:
    run_id: str
    module_sha256: str
    contract_sha256: str
    context_sha256: str


@dataclass(frozen=True)
class Marker:
    run_id: str
    phase: str
    sequence: int
    pid: int
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


def _require_hex(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not pattern.fullmatch(value):
        raise DesignError(f"invalid {label}: {value!r}")
    return value


def make_expectation(
    run_id: str,
    context_sha256: str,
    *,
    module_sha256: str = MODULE_SHA256,
    contract_sha256: str = CONTRACT_SHA256,
) -> MarkerExpectation:
    return MarkerExpectation(
        run_id=_require_hex(run_id, HEX_128_RE, "run id"),
        module_sha256=_require_hex(module_sha256, HEX_256_RE, "module sha256"),
        contract_sha256=_require_hex(
            contract_sha256, HEX_256_RE, "contract sha256"
        ),
        context_sha256=_require_hex(
            context_sha256, HEX_256_RE, "context sha256"
        ),
    )


def generate_run_id() -> str:
    return secrets.token_hex(16)


def encode_marker(
    expectation: MarkerExpectation,
    *,
    pid: int = 1,
    sequence: int = SEQUENCE,
) -> bytes:
    if pid < 0 or pid > 0xFFFFFFFF:
        raise DesignError(f"pid out of range: {pid}")
    if sequence < 0 or sequence > 0xFFFFFFFF:
        raise DesignError(f"sequence out of range: {sequence}")
    payload = (
        f"run={expectation.run_id};phase={PHASE};seq={sequence:08x};"
        f"pid={pid:08x};module={expectation.module_sha256};"
        f"contract={expectation.contract_sha256};"
        f"context={expectation.context_sha256}"
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
            issues.append(
                MarkerIssue(
                    offset,
                    "missing-length-separator",
                    _run_hint(blob[offset : offset + MAX_PAYLOAD_BYTES]),
                )
            )
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
                pid=int(match.group("pid"), 16),
                module_sha256=match.group("module"),
                contract_sha256=match.group("contract"),
                context_sha256=match.group("context"),
                crc32=actual_crc,
                offset=offset,
            )
        )
        cursor = trailer_end
    return MarkerScan(tuple(markers), tuple(issues))


def classify_snapshot(
    stage: str, blob: bytes, expectation: MarkerExpectation
) -> dict[str, Any]:
    if stage not in {"baseline", "retention"}:
        raise DesignError(f"unsupported snapshot stage: {stage}")
    scan = scan_markers(blob)
    current = [m for m in scan.markers if m.run_id == expectation.run_id]
    foreign = [m for m in scan.markers if m.run_id != expectation.run_id]
    current_issues = [
        issue for issue in scan.issues if issue.run_hint == expectation.run_id
    ]
    errors = [f"current-run-malformed:{issue.reason}" for issue in current_issues]
    raw_token = f"run={expectation.run_id}".encode("ascii")
    raw_current_tokens = blob.count(raw_token)
    if raw_current_tokens > len(current):
        errors.append("current-run-unframed-or-malformed")

    classification = "PASS_BASELINE_NEGATIVE"
    if stage == "baseline":
        if current:
            errors.append("current-run-marker-present-before-candidate")
        if errors:
            classification = "FAIL_STOP"
    else:
        if not errors and not current:
            classification = "NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP"
        else:
            if len(current) != 1:
                errors.append(f"pid1-enter-count:{len(current)}")
            if len(current) == 1:
                marker = current[0]
                if marker.sequence != SEQUENCE:
                    errors.append("sequence-mismatch")
                if marker.pid != 1:
                    errors.append("pid-is-not-one")
                if marker.module_sha256 != expectation.module_sha256:
                    errors.append("module-identity-mismatch")
                if marker.contract_sha256 != expectation.contract_sha256:
                    errors.append("contract-identity-mismatch")
                if marker.context_sha256 != expectation.context_sha256:
                    errors.append("context-identity-mismatch")
            classification = (
                "FAIL_STOP"
                if errors
                else "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD"
            )

    return {
        "stage": stage,
        "pass": classification.startswith("PASS_"),
        "classification": classification,
        "errors": errors,
        "current_run_markers": [asdict(marker) for marker in current],
        "foreign_run_marker_count": len(foreign),
        "all_issue_count": len(scan.issues),
        "current_run_issues": [asdict(issue) for issue in current_issues],
        "raw_current_token_count": raw_current_tokens,
    }


def _tar_members(archive: Path, members: Iterable[str]) -> dict[str, str]:
    requested = tuple(members)
    output: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as handle:
        for member in requested:
            extracted = handle.extractfile(member)
            if extracted is None:
                raise DesignError(f"source member missing: {member}")
            output[member] = extracted.read().decode("utf-8")
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


def _config_value(text: str, name: str) -> str:
    enabled = re.search(rf"(?m)^{re.escape(name)}=(.+)$", text)
    if enabled:
        return enabled.group(1)
    if re.search(rf"(?m)^# {re.escape(name)} is not set$", text):
        return "n"
    return "unset"


def _validate_report_pins(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, pin in REPORT_PINS.items():
        path = root / pin["path"]
        actual = sha256_file(path)
        if actual != pin["sha256"]:
            raise DesignError(f"report SHA256 mismatch for {name}: {actual}")
        result[name] = dict(pin)
    return result


def validate_static_inputs(root: Path) -> dict[str, Any]:
    archive = root / SOURCE_ARCHIVE
    if sha256_file(archive) != SOURCE_ARCHIVE_SHA256:
        raise DesignError("kernel source archive SHA256 mismatch")

    observer_evidence = observer.validate_static_inputs(root)
    texts = _tar_members(
        archive,
        (
            GKI_CONFIG,
            WAIPIO_GKI_CONFIG,
            WAIPIO_SEC_CONFIG,
            KERNEL_INIT_SOURCE,
            KERNEL_MODULE_SOURCE,
            BUILDER_PATTERN_SOURCE,
            SEC_LOG_MAIN_SOURCE,
        ),
    )

    config = {
        "gki_modules": _config_value(texts[GKI_CONFIG], "CONFIG_MODULES"),
        "gki_pstore": _config_value(texts[GKI_CONFIG], "CONFIG_PSTORE"),
        "gki_pstore_ram": _config_value(texts[GKI_CONFIG], "CONFIG_PSTORE_RAM"),
        "gki_magic_sysrq": _config_value(texts[GKI_CONFIG], "CONFIG_MAGIC_SYSRQ"),
        "waipio_gki_sec_debug": _config_value(
            texts[WAIPIO_GKI_CONFIG], "CONFIG_SEC_DEBUG"
        ),
        "waipio_sec_debug": _config_value(
            texts[WAIPIO_SEC_CONFIG], "CONFIG_SEC_DEBUG"
        ),
    }
    expected_config = {
        "gki_modules": "y",
        "gki_pstore": "y",
        "gki_pstore_ram": "y",
        "gki_magic_sysrq": "y",
        "waipio_gki_sec_debug": "m",
        "waipio_sec_debug": "m",
    }
    if config != expected_config:
        raise DesignError(f"kernel config evidence drift: {config}")

    _require_tokens(
        texts[KERNEL_INIT_SOURCE],
        (
            'static char *ramdisk_execute_command = "/init";',
            "We need to spawn init first so that it obtains pid 1",
            "pid = kernel_thread(kernel_init, NULL, CLONE_FS);",
            "ret = run_init_process(ramdisk_execute_command);",
            "return kernel_execve(init_filename, argv_init, envp_init);",
        ),
        "kernel PID1 init path",
    )
    module_init = observer._extract_function(
        texts[KERNEL_MODULE_SOURCE], "static noinline int do_init_module"
    )
    _require_order(
        module_init,
        (
            "ret = do_one_initcall(mod->init);",
            "mod->state = MODULE_STATE_LIVE;",
            "return 0;",
        ),
        "module init synchrony",
    )
    _require_tokens(
        texts[KERNEL_MODULE_SOURCE],
        (
            "SYSCALL_DEFINE3(finit_module",
            "return load_module(&info, uargs, flags);",
            "return do_init_module(mod);",
        ),
        "finit_module dispatch",
    )
    director_construct = observer._extract_function(
        texts[BUILDER_PATTERN_SOURCE],
        "static inline int sec_director_construct_dev",
    )
    _require_order(
        director_construct,
        (
            "for (i = 0; i < n; i++)",
            "err = __bp_call_concrete_construct_dev(bd, builder, i);",
            "return 0;",
        ),
        "synchronous sec director",
    )
    _require_order(
        texts[SEC_LOG_MAIN_SOURCE],
        (
            "DEVICE_BUILDER(__last_kmsg_procfs_create",
            "DEVICE_BUILDER(__log_buf_logger_init",
            "DEVICE_BUILDER(__ap_klog_proc_init",
            "DEVICE_BUILDER(__log_buf_probe_epilog",
        ),
        "sec_log_buf synchronous observer path",
    )
    _require_tokens(
        texts[SEC_LOG_MAIN_SOURCE],
        (
            "return sec_director_probe_dev(&drvdata->bd, builder, n);",
            "return platform_driver_register(&sec_log_buf_driver);",
        ),
        "sec_log_buf synchronous dispatch",
    )

    if observer_evidence["module"]["modules_dep_rhs"]:
        raise DesignError("sec_log_buf hard dependencies are no longer empty")
    if observer_evidence["module"]["modules_softdep_edges"]:
        raise DesignError("sec_log_buf soft dependencies are no longer empty")

    return {
        "source_archive": {
            "path": str(SOURCE_ARCHIVE),
            "sha256": SOURCE_ARCHIVE_SHA256,
        },
        "module": observer_evidence["module"],
        "kernel_config": config,
        "source_proofs": {
            "kernel_executes_initramfs_init_as_pid1": "VERIFIED",
            "finit_module_success_is_after_module_init_live": "VERIFIED",
            "sec_log_buf_required_observer_builders_are_synchronous": "VERIFIED",
            "devkmsg_write_hook_return_is_synchronous": observer_evidence[
                "source_proofs"
            ]["devkmsg_write_hook_return_is_synchronous"],
            "sec_debug_is_loadable_module_not_builtin": "VERIFIED",
        },
        "report_pins": _validate_report_pins(root),
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
        "proof_boundary": {
            "positive": (
                "exact retained marker is conclusive for direct PID1 execution "
                "and exact observer activation"
            ),
            "absence": (
                "inconclusive because PID1 non-entry, pre-marker failure, observer "
                "load failure, and transition loss remain indistinguishable"
            ),
            "not_pure_module_free": True,
            "observer_is_part_of_the_keystone": True,
        },
        "web_cross_check": {
            "kernel_initramfs_init_pid1": "SUPPORTED_BY_UPSTREAM_KERNEL_DOCS",
            "android_first_stage_init_from_ramdisk": "SUPPORTED_BY_AOSP_DOCS",
            "finit_module_init_completion": "SUPPORTED_BY_ANDROID_COMMON_SOURCE",
            "ramoops_requires_reserved_persistent_ram": "SUPPORTED_BY_KERNEL_DOCS",
            "samsung_specific_behavior_source": "PINNED_FYG8_SOURCE_IS_AUTHORITATIVE",
        },
        "next": (
            "implement and statically/QEMU-validate one exact freestanding candidate "
            "under this contract; do not create a live helper or exception yet"
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
