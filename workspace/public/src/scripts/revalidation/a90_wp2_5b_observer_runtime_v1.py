#!/usr/bin/env python3
"""Generate and validate the host-only A90 WP2-5b.3a observer contract.

The generated contract and header bind only the effect-free observer component:
its two scalar pipes, fixed inherited descriptors, FD-based exec transition,
exclusive-waiter core, launch-readback validation core, and post-open
confinement API.
They do not provide a parent effect dispatcher, durable final-name publisher,
receipt producer, runtime qualification, or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BASE = "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
DEFAULT_CONTRACT = ROOT / BASE / "schema/a90-wp2-5b-observer-runtime-v1.json"
DEFAULT_HEADER = (
    ROOT
    / "workspace/public/src/native-init/helpers/"
    "a90_wp2_5b_kmsg_owner.h"
)

PINNED_INPUTS = {
    "tests/a90_wp2_5b_kmsg_owner_test.c": (
        61710,
        "5ab281025cc6244063be8cd562580485aee9f229936f53964bdd0e10b0f82fb9",
    ),
    "docs/reports/A90_WLAN_WP2_5B_RUNTIME_OWNER_DURABLE_EVIDENCE_DESIGN_H0_2026-08-16.md": (
        38356,
        "4863299453e8b54c91513e65354e107264a6f85df17aa76feec870bdae4ba2a7",
    ),
    f"{BASE}/schema/a90-wp2-5b-kmsg-trace-v1.json": (
        8798,
        "26536cb17938d207d6ecfc0553ac80678c6f0bdff7152dc6c24a42233a5b2c7f",
    ),
    "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_contract.h": (
        3125,
        "0f83bb40c4a23f9c7f0374d472ab78974fff66cff717c4ad7d16346aaaf0fd77",
    ),
    "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_owner.c": (
        66782,
        "cc0cede60df6c5d2c4b6e9755fe9ef37e262427dbcfd52ca2aa601f4229ad91d",
    ),
    "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_stream.c": (
        16389,
        "4d7a2ca24a5b9ebe5ca2ef67742a3c9c2219604799a77c0f0ee5089a58954b62",
    ),
    "workspace/public/src/scripts/revalidation/a90_wp2_5b_kmsg_trace_v1.py": (
        53287,
        "56af5f5ee6082288a35d13476d309d1d12e0effe6c935f0c24a78caedf15357a",
    ),
}

SCHEMA = "a90-wp2-5b-observer-runtime-contract-v1"
STATUS = "H0_COMPONENT_IMPLEMENTED_EXECUTION_QUALIFICATION_ABSENT"
MAGIC = b"A90O3A1\x00"
VERSION = 1

DIRECTION_CONTROL = 1
DIRECTION_STATUS = 2
CONTROL_START = 1
CONTROL_CLOSE = 2
STATUS_ARMED = 1
STATUS_FAULTED = 2
STATUS_CLOSED = 3

CLOSE_NORMAL_AFTER_DRIVER_OUTCOME = 1
CLOSE_FAULT_AFTER_TERMINAL_INPUT = 2
CLOSE_PARENT_CONTROL_EOF = 3

FIXED_CONTROL_FD = 3
FIXED_STATUS_FD = 4
FIXED_RUN_DIR_FD = 5
FIXED_EXEC_FD = 6
PIPE_ATOMIC_MIN = 512
FILTER_CAPACITY = 192

PIPE_HEADER = struct.Struct(">8sHBBQHH")
START_PAYLOAD = struct.Struct(">32s32s32s32s32sIQIIIIIIII")
CLOSE_PAYLOAD = struct.Struct(">II")
STATUS_PAYLOAD = struct.Struct(">IiIIQQQQQQQ")
MAX_FRAME_SIZE = PIPE_HEADER.size + START_PAYLOAD.size
ZERO_SHA256 = "0" * 64
UINT64_MAX = (1 << 64) - 1
RUNTIME_RETRY_CEILING = 1_048_576
RUNTIME_POLL_TIMEOUT_CEILING_MS = 60_000

CONTROL_PAYLOAD_SIZES = {
    CONTROL_START: START_PAYLOAD.size,
    CONTROL_CLOSE: CLOSE_PAYLOAD.size,
}
STATUS_PAYLOAD_SIZES = {
    STATUS_ARMED: STATUS_PAYLOAD.size,
    STATUS_FAULTED: STATUS_PAYLOAD.size,
    STATUS_CLOSED: STATUS_PAYLOAD.size,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if any(type(key) is not str for key in left) or set(left) != set(right):
            return False
        return all(_strict_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _read_pinned_regular(rel: str) -> bytes:
    path = ROOT / rel
    root = ROOT.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ValueError(f"pinned input escapes repository: {rel}")
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError(f"unsafe pinned input: {rel}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after_open = os.fstat(fd)
    finally:
        os.close(fd)
    after_path = path.lstat()
    identity = (opened.st_dev, opened.st_ino)
    if (
        identity != (after_open.st_dev, after_open.st_ino)
        or identity != (after_path.st_dev, after_path.st_ino)
        or opened.st_size != after_open.st_size
        or opened.st_mtime_ns != after_open.st_mtime_ns
        or after_path.st_size != after_open.st_size
        or after_path.st_mtime_ns != after_open.st_mtime_ns
        or after_path.st_nlink != 1
    ):
        raise ValueError(f"pinned input changed during read: {rel}")
    return b"".join(chunks)


def _pinned_receipts() -> list[dict[str, Any]]:
    receipts = []
    for rel, expected in sorted(PINNED_INPUTS.items()):
        data = _read_pinned_regular(rel)
        actual = (len(data), _sha256(data))
        if actual != expected:
            raise ValueError(
                f"pinned input drift: {rel}: expected {expected[0]}/{expected[1]}, "
                f"got {actual[0]}/{actual[1]}"
            )
        receipts.append({"path": rel, "bytes": expected[0], "sha256": expected[1]})
    return receipts


def build_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "scope": {
            "target": "Samsung Galaxy A90 5G only",
            "workPackage": "WP2-5b.3a",
            "permanentInvariant": "WP2_5B_KMSG_STREAM_COMPLETENESS",
            "openGate": "WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT",
            "statement": (
                "This component implements only the effect-free static observer, "
                "generated scalar-pipe grammar, exact-file exec transition core, "
                "exclusive waiter reservation core, launch readback gate, and "
                "post-open confinement source. Parent integration, durable final-name "
                "publication/storage writer, "
                "receipt producers, measured profiles, qualification, and authority "
                "remain absent."
            ),
        },
        "authority": {
            "tier": "H0",
            "deviceContact": False,
            "candidateEligible": False,
            "d0Authorized": False,
            "d1Authorized": False,
            "f1Authorized": False,
            "liveExecutionAuthorized": False,
            "effectDispatchApiExposed": False,
            "propertyProvisionAuthorized": False,
            "ufsMutationAuthorized": False,
            "generationPromotionAuthorized": False,
        },
        "sourcePins": _pinned_receipts(),
        "fixedDescriptors": {
            "stdin": 0,
            "stdout": 1,
            "stderr": 2,
            "controlRead": FIXED_CONTROL_FD,
            "statusWrite": FIXED_STATUS_FD,
            "runDirectory": FIXED_RUN_DIR_FD,
            "execBeforeTransitionOnly": FIXED_EXEC_FD,
            "postOpenLiveSet": [0, 1, 2, 3, 4, "trace.pending", "/dev/kmsg"],
            "postOpenDynamicFdNumbersBoundBeforeSeal": True,
            "bootstrapFlags": {
                "controlRead": ["O_RDONLY", "O_NONBLOCK", "FD_CLOEXEC_AT_ENTRY"],
                "statusWrite": ["O_WRONLY", "O_NONBLOCK", "FD_CLOEXEC_AT_ENTRY"],
                "runDirectory": ["O_RDONLY", "FD_CLOEXEC_AT_ENTRY"],
            },
        },
        "pipeContract": {
            "magicHex": MAGIC.hex(),
            "version": VERSION,
            "header": ">8sHBBQHH",
            "headerBytes": PIPE_HEADER.size,
            "sequence": "UINT64_STARTS_ZERO_EXACT_PLUS_ONE_NO_WRAP",
            "byteOrder": "BIG_ENDIAN",
            "reserved": 0,
            "oneWriterOneReaderPerDirection": True,
            "successfulFrameWrite": "ONE_DIRECT_WRITE_AFTER_BOUNDED_POLLOUT",
            "partialAtEof": "TERMINAL_BOUNDARY_FAULT",
            "atomicMinimumBytes": PIPE_ATOMIC_MIN,
            "maximumFrameBytes": MAX_FRAME_SIZE,
            "controlFrames": [
                {
                    "id": CONTROL_START,
                    "name": "START",
                    "payload": ">32s32s32s32s32sIQIIIIIIII",
                    "payloadBytes": START_PAYLOAD.size,
                    "cardinality": "EXACTLY_ONE_FIRST",
                },
                {
                    "id": CONTROL_CLOSE,
                    "name": "CLOSE",
                    "payload": ">II",
                    "payloadBytes": CLOSE_PAYLOAD.size,
                    "cardinality": "ZERO_OR_ONE_AFTER_ARM_OR_FAULT",
                },
            ],
            "statusFrames": [
                {
                    "id": STATUS_ARMED,
                    "name": "ARMED",
                    "payload": ">IiIIQQQQQQQ",
                    "payloadBytes": STATUS_PAYLOAD.size,
                    "cardinality": "ZERO_OR_ONE_BEFORE_FAULT_OR_CLOSED",
                },
                {
                    "id": STATUS_FAULTED,
                    "name": "FAULTED",
                    "payload": ">IiIIQQQQQQQ",
                    "payloadBytes": STATUS_PAYLOAD.size,
                    "cardinality": "ZERO_OR_ONE_BEFORE_CLOSED",
                },
                {
                    "id": STATUS_CLOSED,
                    "name": "CLOSED",
                    "payload": ">IiIIQQQQQQQ",
                    "payloadBytes": STATUS_PAYLOAD.size,
                    "cardinality": "EXACTLY_ONE_LAST_WHEN_STATUS_CHANNEL_SURVIVES",
                },
            ],
            "closeCauses": {
                "NORMAL_AFTER_DRIVER_OUTCOME": CLOSE_NORMAL_AFTER_DRIVER_OUTCOME,
                "FAULT_AFTER_TERMINAL_INPUT": CLOSE_FAULT_AFTER_TERMINAL_INPUT,
                "PARENT_CONTROL_EOF": CLOSE_PARENT_CONTROL_EOF,
            },
            "statusPayloadFields": [
                "faultReason",
                "osErrno",
                "pollRevents",
                "reservedZero",
                "traceDev",
                "traceIno",
                "kmsgDev",
                "kmsgIno",
                "kmsgRdev",
                "durableTraceBytes",
                "auxiliary",
            ],
            "closeFrameRequiresControlWriterEof": True,
            "closeCauseStateCorrelation": (
                "NORMAL_WITHOUT_FAULTED_FAULT_WITH_FAULTED_"
                "PARENT_EOF_WITH_FAULTED"
            ),
            "invalidClosePoisonsSession": (
                "ANY_FRAME_HEADER_PAYLOAD_SEMANTIC_OR_DUPLICATE_FAILURE_"
                "NO_RESYNC_NO_EOF_AUTHORITY"
            ),
            "closedStatusSuccess": (
                "NO_FAULTED_REQUIRES_ZERO_FAULT_TUPLE_"
                "FAULTED_REQUIRES_EXACT_MATCH"
            ),
            "statusDurableProgression": (
                "STRICTLY_INCREASES_ARMED_TO_OPTIONAL_FAULTED_TO_CLOSED"
            ),
            "rejections": [
                "wrong magic/version/direction/kind/reserved/length",
                "initial sequence not zero",
                "forward gap, duplicate, regression, or wrap",
                "short write, partial EOF, trailing bytes, or extra frame",
                "EPIPE or bounded EAGAIN/EINTR exhaustion",
                "close before start, duplicate close, or status after closed",
                "close cause and observer fault-state mismatch",
            ],
        },
        "execBoundary": {
            "primitive": "execveat(EXEC_FD, empty-path, fixed-argv, empty-env, AT_EMPTY_PATH)",
            "temporarilyClearedCloexec": [3, 4, 5],
            "execFdRemainsCloexec": True,
            "rearmOnExecFailure": True,
            "pathExecForbidden": True,
            "procSelfFdFallbackForbidden": True,
            "interpreterOrDynamicLoaderForbidden": True,
            "parentIntegrationImplemented": False,
        },
        "waiterBoundary": {
            "directChildOnly": True,
            "sigchldMustBeBlocked": True,
            "sigchldDisposition": "SIG_DFL_NO_SIG_IGN_NO_SA_NOCLDWAIT",
            "reservationKey": ["pid", "starttime"],
            "genericReaperMustSkipReserved": True,
            "onlyExactWaiterMayReap": True,
            "residentReaperIntegrationImplemented": False,
        },
        "launchReadback": {
            "required": [
                "SCHED_OTHER priority zero reset-on-fork",
                "nonnegative qualified nice with exact profile digest",
                "bounded affinity/cpuset, ioprio, and uclamp digests",
                "dedicated aggregate cgroup and native reserve digests",
                "RLIMIT_RTPRIO zero and bounded nonzero RLIMIT_RTTIME",
                "CAP_SYS_NICE and CAP_SYS_RESOURCE absent",
                "SIGCHLD default/no-auto-reap and blocked through reservation",
                "exact static ELF FD, clean maps, exact inherited FD set",
                "fixed argv, empty environment, null stdio, root/cwd/umask",
                "credentials/groups/rlimits/capabilities/signals/parent identity",
            ],
            "numericProfileSelected": False,
            "cgroupBackendSelected": False,
            "runtimeNormalizationImplemented": False,
            "schemaValidatorImplemented": True,
        },
        "observerBoundary": {
            "traceLeaf": "trace.pending",
            "traceOpen": [
                "O_WRONLY",
                "O_APPEND",
                "O_CREAT",
                "O_EXCL",
                "O_NOFOLLOW",
                "O_CLOEXEC",
                "0600",
            ],
            "runDirectoryClosedBeforeKmsgOpen": True,
            "kmsgPath": "/dev/kmsg",
            "kmsgOpen": ["O_RDONLY", "O_NONBLOCK", "O_NOFOLLOW", "O_CLOEXEC"],
            "kmsgRdev": {"major": 1, "minor": 11},
            "initialSeek": "SEEK_END_OFFSET_ZERO_EXACTLY_ONCE",
            "consumedReadFaults": ["EINVAL_CURSOR_ADVANCED", "EFAULT_CURSOR_ADVANCED"],
            "noReadAfterTerminalFault": True,
            "terminalFaultReaderClose": "AFTER_DURABLE_FAULT_PREFIX_BEFORE_FAULTED_STATUS_EXACT_ONCE_NO_RETRY",
            "readerCloseFailure": "ALL_CLOSE_PATHS_NO_FAULTED_NO_END_NO_CLOSED_NO_CONTROL_WAIT_IMMEDIATE_PROCESS_EXIT",
            "faultPublicationFailure": "NO_CONTROL_WAIT_NO_END_NO_CLOSED_IMMEDIATE_PROCESS_EXIT",
            "durableLengthSource": "LAST_SUCCESSFUL_FSYNC_ONLY",
            "streamCoreFaultDurability": (
                "FSYNC_EMITTED_FAULT_PREFIX_ADVANCE_DURABLE_LENGTH_"
                "BEFORE_FAULTED"
            ),
            "finalPublicationFailure": (
                "END_WRITE_OR_FINAL_FSYNC_OR_TRACE_CLOSE_OR_CLOSED_WRITE_"
                "FAILURE_NO_CLOSED_NO_UNFSYNCED_DURABLE_LENGTH"
            ),
            "faultCloseWait": {
                "descriptor": FIXED_CONTROL_FD,
                "pollCallBudget": "START_BOUND_NONZERO",
                "timeoutPerCallMs": "START_BOUND_NONZERO",
                "budgetExhaustion": "EXIT_BOUNDED_PARTIAL_WITHOUT_CLOSED",
            },
            "noRetryClose": True,
            "noProcKmsgFallback": True,
            "effectApi": None,
        },
        "confinement": {
            "bootstrapOnlyKmsgOpenPrivilege": True,
            "emptySupplementaryGroupsRequired": True,
            "allCapabilitySetsAndBoundingSetDropped": True,
            "dumpable": False,
            "rlimitCore": 0,
            "noNewPrivileges": True,
            "seccomp": "STATIC_ARCH_CHECKED_DEFAULT_KILL_FIXED_FD_ALLOWLIST",
            "maximumFilterInstructions": FILTER_CAPACITY,
            "forbidden": [
                "path open after seal",
                "socket or ioctl",
                "exec or namespace/mount/root transition",
                "ptrace, process-vm, pidfd-getfd, keyring, BPF, or perf",
                "FD duplication or fcntl mutation",
                "unknown architecture or syscall",
            ],
            "liveKernelQualificationComplete": False,
        },
        "implementation": {
            "observerSourceImplemented": True,
            "generatedPipeContractImplemented": True,
            "fdExecTransitionCoreImplemented": True,
            "exclusiveWaiterCoreImplemented": True,
            "launchReadbackValidationCoreImplemented": True,
            "postOpenConfinementSourceImplemented": True,
            "filterBytecodeBuilderExposedForHostTests": True,
            "injectedOpsApiProductionExposed": False,
            "syscallInjectedHostTestsRequired": True,
            "syscallInjectedHostTestsImplemented": True,
            "durablePublicationWriterImplemented": False,
            "receiptProducersImplemented": False,
            "parentIntegrationImplemented": False,
            "measuredQualificationImplemented": False,
            "independentExecutionReviewComplete": False,
        },
        "sequencingConstraint": {
            "current": "WP2-5b.3a effect-free observer component H0 implementation",
            "next": "WP2-5b.3b strict raw writer/parser, storage reservation, and crash-prefix fixture",
            "gateRetiredByThisUnit": False,
            "deviceOrdinalsConsumed": 0,
        },
        "generatedDeterministically": True,
    }


def canonical_contract_text() -> str:
    return json.dumps(build_contract(), indent=2, sort_keys=True) + "\n"


def contract_sha256() -> str:
    return _sha256(canonical_contract_text().encode("ascii"))


def validate_contract(value: Any) -> list[str]:
    try:
        expected = build_contract()
    except (OSError, ValueError):
        return ["PINNED_SOURCE_MODEL_UNAVAILABLE"]
    if not _strict_json_equal(value, expected):
        return ["PINNED_SEMANTIC_MISMATCH"]
    return []


def encode_frame(direction: int, kind: int, sequence: int, payload: bytes) -> bytes:
    if type(direction) is not int or direction not in (DIRECTION_CONTROL, DIRECTION_STATUS):
        raise ValueError("invalid direction")
    if type(kind) is not int or type(sequence) is not int:
        raise ValueError("invalid kind or sequence type")
    if sequence < 0 or sequence > UINT64_MAX or type(payload) is not bytes:
        raise ValueError("invalid sequence or payload")
    sizes = CONTROL_PAYLOAD_SIZES if direction == DIRECTION_CONTROL else STATUS_PAYLOAD_SIZES
    if sizes.get(kind) != len(payload):
        raise ValueError("invalid payload size")
    return PIPE_HEADER.pack(MAGIC, VERSION, direction, kind, sequence, len(payload), 0) + payload


def parse_frame(raw: Any, expected_direction: int) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    if type(expected_direction) is not int or expected_direction not in (
        DIRECTION_CONTROL,
        DIRECTION_STATUS,
    ):
        return None, ["PIPE_EXPECTED_DIRECTION_TYPE"]
    if type(raw) is not bytes or len(raw) < PIPE_HEADER.size:
        return None, ["PIPE_FRAME_TRUNCATED"]
    try:
        magic, version, direction, kind, sequence, payload_length, reserved = PIPE_HEADER.unpack_from(raw)
    except struct.error:
        return None, ["PIPE_FRAME_TRUNCATED"]
    if magic != MAGIC:
        findings.append("PIPE_MAGIC_MISMATCH")
    if version != VERSION:
        findings.append("PIPE_VERSION_MISMATCH")
    if direction != expected_direction:
        findings.append("PIPE_DIRECTION_MISMATCH")
    if reserved != 0:
        findings.append("PIPE_RESERVED_NONZERO")
    sizes = CONTROL_PAYLOAD_SIZES if expected_direction == DIRECTION_CONTROL else STATUS_PAYLOAD_SIZES
    if kind not in sizes:
        findings.append("PIPE_KIND_UNKNOWN")
    elif sizes[kind] != payload_length:
        findings.append("PIPE_PAYLOAD_LENGTH_MISMATCH")
    if len(raw) != PIPE_HEADER.size + payload_length:
        findings.append("PIPE_FRAME_SIZE_MISMATCH")
    if findings:
        return None, findings
    return {
        "direction": direction,
        "kind": kind,
        "sequence": sequence,
        "payload": raw[PIPE_HEADER.size :],
        "sha256": _sha256(raw),
    }, []


def validate_transcript(raw_frames: Any, direction: int) -> list[str]:
    if type(direction) is not int or direction not in (
        DIRECTION_CONTROL,
        DIRECTION_STATUS,
    ):
        return ["PIPE_EXPECTED_DIRECTION_TYPE"]
    if not isinstance(raw_frames, list):
        return ["PIPE_TRANSCRIPT_TYPE"]
    parsed: list[dict[str, Any]] = []
    findings: list[str] = []
    for raw in raw_frames:
        frame, current = parse_frame(raw, direction)
        findings.extend(current)
        if frame is not None:
            parsed.append(frame)
    if findings:
        return sorted(set(findings))
    for index, frame in enumerate(parsed):
        if frame["sequence"] != index:
            findings.append("PIPE_SEQUENCE_MISMATCH")
    kinds = [frame["kind"] for frame in parsed]
    if direction == DIRECTION_CONTROL:
        if not kinds or kinds[0] != CONTROL_START or kinds.count(CONTROL_START) != 1:
            findings.append("CONTROL_START_CARDINALITY")
        if any(kind not in (CONTROL_START, CONTROL_CLOSE) for kind in kinds):
            findings.append("CONTROL_KIND_ORDER")
        if kinds.count(CONTROL_CLOSE) > 1 or (
            CONTROL_CLOSE in kinds and kinds[-1] != CONTROL_CLOSE
        ):
            findings.append("CONTROL_CLOSE_CARDINALITY")
        if kinds and kinds[0] == CONTROL_START:
            (
                run_binding,
                qualification,
                observer_binary,
                driver_epoch,
                close_binding,
                record_count_cap,
                record_byte_cap,
                _expected_uid,
                _expected_gid,
                read_budget,
                poll_budget,
                pipe_budget,
                poll_timeout_ms,
                fault_close_poll_budget,
                start_reserved,
            ) = START_PAYLOAD.unpack(parsed[0]["payload"])
            if any(
                digest == b"\x00" * 32
                for digest in (
                    run_binding,
                    qualification,
                    observer_binary,
                    driver_epoch,
                    close_binding,
                )
            ):
                findings.append("CONTROL_START_ZERO_DIGEST")
            if record_count_cap == 0 or record_byte_cap == 0:
                findings.append("CONTROL_START_CAP_INVALID")
            if (
                read_budget == 0
                or poll_budget == 0
                or pipe_budget == 0
                or read_budget > RUNTIME_RETRY_CEILING
                or poll_budget > RUNTIME_RETRY_CEILING
                or pipe_budget > RUNTIME_RETRY_CEILING
                or poll_timeout_ms == 0
                or poll_timeout_ms > RUNTIME_POLL_TIMEOUT_CEILING_MS
                or fault_close_poll_budget == 0
                or fault_close_poll_budget > RUNTIME_RETRY_CEILING
            ):
                findings.append("CONTROL_START_BUDGET_INVALID")
            if start_reserved != 0:
                findings.append("CONTROL_START_RESERVED_NONZERO")
        for close_frame in (
            frame for frame in parsed if frame["kind"] == CONTROL_CLOSE
        ):
            cause, reserved = CLOSE_PAYLOAD.unpack(close_frame["payload"])
            if cause not in (
                CLOSE_NORMAL_AFTER_DRIVER_OUTCOME,
                CLOSE_FAULT_AFTER_TERMINAL_INPUT,
            ) or reserved != 0:
                findings.append("CONTROL_CLOSE_CAUSE")
    else:
        allowed = (
            [STATUS_ARMED, STATUS_CLOSED],
            [STATUS_ARMED, STATUS_FAULTED, STATUS_CLOSED],
        )
        if kinds not in allowed:
            findings.append("STATUS_ORDER_OR_CARDINALITY")
        status_values = [STATUS_PAYLOAD.unpack(frame["payload"]) for frame in parsed]
        for values in status_values:
            _reason, _os_errno, _revents, reserved, *_rest = values
            if reserved != 0:
                findings.append("STATUS_RESERVED_NONZERO")
            trace_dev, trace_ino, kmsg_dev, kmsg_ino, kmsg_rdev = values[4:9]
            if 0 in (trace_dev, trace_ino, kmsg_dev, kmsg_ino, kmsg_rdev):
                findings.append("STATUS_IDENTITY_INVALID")
        if status_values:
            identities = [values[4:9] for values in status_values]
            if any(identity != identities[0] for identity in identities[1:]):
                findings.append("STATUS_IDENTITY_DRIFT")
            durable_lengths = [values[9] for values in status_values]
            if any(
                current < previous
                for previous, current in zip(durable_lengths, durable_lengths[1:])
            ):
                findings.append("STATUS_DURABLE_LENGTH_REGRESSION")
            if any(
                current == previous
                for previous, current in zip(durable_lengths, durable_lengths[1:])
            ):
                findings.append("STATUS_DURABLE_LENGTH_NOT_ADVANCED")
        if kinds and kinds[0] == STATUS_ARMED:
            armed = status_values[0]
            if armed[0:3] != (0, 0, 0) or armed[9] == 0 or armed[10] != armed[8]:
                findings.append("STATUS_ARMED_PAYLOAD_INVALID")
        if STATUS_FAULTED in kinds:
            fault = status_values[kinds.index(STATUS_FAULTED)]
            if not (1 <= fault[0] <= 10):
                findings.append("STATUS_FAULT_REASON_INVALID")
            closed = status_values[-1]
            if closed[0:3] != fault[0:3]:
                findings.append("STATUS_CLOSED_FAULT_MISMATCH")
        elif status_values:
            closed = status_values[-1]
            if closed[0:3] != (0, 0, 0):
                findings.append("STATUS_CLOSED_WITHOUT_FAULTED")
    return sorted(set(findings))


def validate_session_transcripts(
    control_frames: Any, status_frames: Any
) -> list[str]:
    findings = validate_transcript(control_frames, DIRECTION_CONTROL)
    findings.extend(validate_transcript(status_frames, DIRECTION_STATUS))
    if findings:
        return sorted(set(findings))

    parsed_control = [
        parse_frame(raw, DIRECTION_CONTROL)[0] for raw in control_frames
    ]
    parsed_status = [parse_frame(raw, DIRECTION_STATUS)[0] for raw in status_frames]
    if any(frame is None for frame in parsed_control + parsed_status):
        return ["PIPE_SESSION_INTERNAL_PARSE"]

    control_kinds = [frame["kind"] for frame in parsed_control]
    status_kinds = [frame["kind"] for frame in parsed_status]
    has_faulted = STATUS_FAULTED in status_kinds
    if CONTROL_CLOSE in control_kinds:
        close_frame = parsed_control[-1]
        close_cause, _reserved = CLOSE_PAYLOAD.unpack(close_frame["payload"])
        expected_faulted = close_cause == CLOSE_FAULT_AFTER_TERMINAL_INPUT
    else:
        expected_faulted = True
    if has_faulted != expected_faulted:
        findings.append("PIPE_CLOSE_STATUS_CAUSE_MISMATCH")
    return sorted(set(findings))


def validate_launch_snapshot(value: Any) -> list[str]:
    keys = {
        "schedOther",
        "priorityZero",
        "resetOnFork",
        "niceNonnegative",
        "profileSha256",
        "affinitySha256",
        "ioprioSha256",
        "uclampSha256",
        "cgroupSha256",
        "nativeReserveSha256",
        "rlimitRtprioZero",
        "rlimitRttimePositiveBounded",
        "capSysNiceAbsent",
        "capSysResourceAbsent",
        "sigchldBlocked",
        "sigchldDefault",
        "sigchldNoCldwaitAbsent",
        "waiterReserved",
        "staticElfFdValidated",
        "cleanMappings",
        "exactInheritedFdSet",
        "fixedArgv",
        "emptyEnvironment",
        "nullStdio",
        "rootSha256",
        "cwdSha256",
        "umaskSha256",
        "credentialsSha256",
        "groupsSha256",
        "rlimitsSha256",
        "capabilitiesSha256",
        "signalMaskSha256",
        "signalDispositionsSha256",
        "observerIdentitySha256",
        "parentIdentitySha256",
        "executableSha256",
        "fdSetSha256",
        "mappingSetSha256",
    }
    if not isinstance(value, dict) or set(value) != keys:
        return ["LAUNCH_SNAPSHOT_SCHEMA"]
    bool_keys = keys - {
        "profileSha256",
        "affinitySha256",
        "ioprioSha256",
        "uclampSha256",
        "cgroupSha256",
        "nativeReserveSha256",
        "rootSha256",
        "cwdSha256",
        "umaskSha256",
        "credentialsSha256",
        "groupsSha256",
        "rlimitsSha256",
        "capabilitiesSha256",
        "signalMaskSha256",
        "signalDispositionsSha256",
        "observerIdentitySha256",
        "parentIdentitySha256",
        "executableSha256",
        "fdSetSha256",
        "mappingSetSha256",
    }
    if any(type(value[key]) is not bool or not value[key] for key in bool_keys):
        return ["LAUNCH_SNAPSHOT_SAFETY_STATE"]
    for key in keys - bool_keys:
        item = value[key]
        if (
            not isinstance(item, str)
            or len(item) != 64
            or item == ZERO_SHA256
            or any(ch not in "0123456789abcdef" for ch in item)
        ):
            return ["LAUNCH_SNAPSHOT_DIGEST"]
    return []


def canonical_header_text() -> str:
    digest = bytes.fromhex(contract_sha256())
    digest_values = ", ".join(f"0x{byte:02x}" for byte in digest)
    return f'''/* Generated by a90_wp2_5b_observer_runtime_v1.py; do not edit. */
#ifndef A90_WP2_5B_KMSG_OWNER_V1_H
#define A90_WP2_5B_KMSG_OWNER_V1_H

#include <poll.h>
#include <signal.h>
#include <linux/filter.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>

#define A90_WP2_5B_OWNER_VERSION {VERSION}u
#define A90_WP2_5B_OWNER_PIPE_HEADER_SIZE {PIPE_HEADER.size}u
#define A90_WP2_5B_OWNER_START_PAYLOAD_SIZE {START_PAYLOAD.size}u
#define A90_WP2_5B_OWNER_CLOSE_PAYLOAD_SIZE {CLOSE_PAYLOAD.size}u
#define A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE {STATUS_PAYLOAD.size}u
#define A90_WP2_5B_OWNER_MAX_FRAME_SIZE {MAX_FRAME_SIZE}u
#define A90_WP2_5B_OWNER_PIPE_ATOMIC_MIN {PIPE_ATOMIC_MIN}u
#define A90_WP2_5B_OWNER_FILTER_CAPACITY {FILTER_CAPACITY}u

#define A90_WP2_5B_OWNER_DIRECTION_CONTROL {DIRECTION_CONTROL}u
#define A90_WP2_5B_OWNER_DIRECTION_STATUS {DIRECTION_STATUS}u
#define A90_WP2_5B_OWNER_CONTROL_START {CONTROL_START}u
#define A90_WP2_5B_OWNER_CONTROL_CLOSE {CONTROL_CLOSE}u
#define A90_WP2_5B_OWNER_STATUS_ARMED {STATUS_ARMED}u
#define A90_WP2_5B_OWNER_STATUS_FAULTED {STATUS_FAULTED}u
#define A90_WP2_5B_OWNER_STATUS_CLOSED {STATUS_CLOSED}u

#define A90_WP2_5B_OWNER_CLOSE_NORMAL {CLOSE_NORMAL_AFTER_DRIVER_OUTCOME}u
#define A90_WP2_5B_OWNER_CLOSE_FAULT {CLOSE_FAULT_AFTER_TERMINAL_INPUT}u
#define A90_WP2_5B_OWNER_CLOSE_PARENT_EOF {CLOSE_PARENT_CONTROL_EOF}u

#define A90_WP2_5B_OWNER_CONTROL_FD {FIXED_CONTROL_FD}
#define A90_WP2_5B_OWNER_STATUS_FD {FIXED_STATUS_FD}
#define A90_WP2_5B_OWNER_RUN_DIR_FD {FIXED_RUN_DIR_FD}
#define A90_WP2_5B_OWNER_EXEC_FD {FIXED_EXEC_FD}

static const unsigned char a90_wp2_5b_owner_magic[8] = {{
    0x41, 0x39, 0x30, 0x4f, 0x33, 0x41, 0x31, 0x00
}};
static const unsigned char a90_wp2_5b_owner_contract_sha256[32] = {{
    {digest_values}
}};

struct a90_wp2_5b_owner_ops;

struct a90_wp2_5b_owner_confinement {{
    int control_fd;
    int status_fd;
    int trace_fd;
    int kmsg_fd;
    uint32_t expected_uid;
    uint32_t expected_gid;
}};

struct a90_wp2_5b_owner_ops {{
    void *context;
    int (*openat_fn)(void *, int, const char *, int, mode_t);
    int (*close_fn)(void *, int);
    int (*fstat_fn)(void *, int, struct stat *);
    int (*fcntl_fn)(void *, int, int, long);
    off_t (*lseek_fn)(void *, int, off_t, int);
    ssize_t (*read_fn)(void *, int, void *, size_t);
    ssize_t (*write_fn)(void *, int, const void *, size_t);
    int (*poll_fn)(void *, struct pollfd *, nfds_t, int);
    int (*fsync_fn)(void *, int);
    int (*apply_confinement_fn)(void *, const struct a90_wp2_5b_owner_confinement *);
}};

struct a90_wp2_5b_owner_result {{
    uint32_t fault_reason;
    int32_t os_errno;
    uint32_t poll_revents;
    uint32_t armed;
    uint32_t faulted;
    uint32_t closed;
    uint32_t kmsg_read_calls;
    uint32_t kmsg_reads_after_fault;
    uint64_t trace_dev;
    uint64_t trace_ino;
    uint64_t kmsg_dev;
    uint64_t kmsg_ino;
    uint64_t kmsg_rdev;
    uint64_t durable_trace_bytes;
}};

struct a90_wp2_5b_launch_snapshot {{
    int sched_other;
    int priority_zero;
    int reset_on_fork;
    int nice_nonnegative;
    unsigned char profile_sha256[32];
    unsigned char affinity_sha256[32];
    unsigned char ioprio_sha256[32];
    unsigned char uclamp_sha256[32];
    unsigned char cgroup_sha256[32];
    unsigned char native_reserve_sha256[32];
    int rlimit_rtprio_zero;
    int rlimit_rttime_positive_bounded;
    int cap_sys_nice_absent;
    int cap_sys_resource_absent;
    int sigchld_blocked;
    int sigchld_default;
    int sigchld_no_cldwait_absent;
    int waiter_reserved;
    int static_elf_fd_validated;
    int clean_mappings;
    int exact_inherited_fd_set;
    int fixed_argv;
    int empty_environment;
    int null_stdio;
    unsigned char root_sha256[32];
    unsigned char cwd_sha256[32];
    unsigned char umask_sha256[32];
    unsigned char credentials_sha256[32];
    unsigned char groups_sha256[32];
    unsigned char rlimits_sha256[32];
    unsigned char capabilities_sha256[32];
    unsigned char signal_mask_sha256[32];
    unsigned char signal_dispositions_sha256[32];
    unsigned char observer_identity_sha256[32];
    unsigned char parent_identity_sha256[32];
    unsigned char executable_sha256[32];
    unsigned char fd_set_sha256[32];
    unsigned char mapping_set_sha256[32];
}};

struct a90_wp2_5b_waiter_reservation {{
    pid_t pid;
    uint64_t starttime;
    int active;
    int reaped;
}};

struct a90_wp2_5b_exec_ops {{
    void *context;
    int (*fcntl_fn)(void *, int, int, long);
    int (*execveat_fn)(void *, int, const char *, char *const[], char *const[], int);
}};

#ifdef A90_WP2_5B_HOST_TESTING
int a90_wp2_5b_owner_run_with_ops(const struct a90_wp2_5b_owner_ops *ops,
                                  struct a90_wp2_5b_owner_result *result);
#endif
int a90_wp2_5b_owner_run(void);
int a90_wp2_5b_owner_install_confinement(
    const struct a90_wp2_5b_owner_confinement *request);
int a90_wp2_5b_owner_build_filter(
    const struct a90_wp2_5b_owner_confinement *request,
    struct sock_filter *instructions, size_t capacity,
    unsigned short *instruction_count);
int a90_wp2_5b_validate_launch_snapshot(
    const struct a90_wp2_5b_launch_snapshot *snapshot);
int a90_wp2_5b_waiter_reserve(struct a90_wp2_5b_waiter_reservation *reservation,
                              pid_t pid, uint64_t starttime);
int a90_wp2_5b_waiter_generic_reaper_may_reap(
    const struct a90_wp2_5b_waiter_reservation *reservation,
    pid_t pid, uint64_t starttime);
int a90_wp2_5b_waiter_mark_reaped(
    struct a90_wp2_5b_waiter_reservation *reservation,
    pid_t pid, uint64_t starttime);
int a90_wp2_5b_waiter_release(struct a90_wp2_5b_waiter_reservation *reservation);
int a90_wp2_5b_child_exec_transition(const struct a90_wp2_5b_exec_ops *ops);

#endif
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-contract", type=Path, metavar="PATH")
    group.add_argument("--write-contract", type=Path, nargs="?", const=DEFAULT_CONTRACT)
    group.add_argument("--check-header", type=Path, metavar="PATH")
    group.add_argument("--write-header", type=Path, nargs="?", const=DEFAULT_HEADER)
    args = parser.parse_args()
    if args.check_contract is not None:
        if args.check_contract.read_text() != canonical_contract_text():
            raise SystemExit(f"contract drift: {args.check_contract}")
        return 0
    if args.write_contract is not None:
        args.write_contract.parent.mkdir(parents=True, exist_ok=True)
        args.write_contract.write_text(canonical_contract_text())
        return 0
    if args.check_header is not None:
        if args.check_header.read_text() != canonical_header_text():
            raise SystemExit(f"header drift: {args.check_header}")
        return 0
    if args.write_header is not None:
        args.write_header.parent.mkdir(parents=True, exist_ok=True)
        args.write_header.write_text(canonical_header_text())
        return 0
    print(canonical_contract_text(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
