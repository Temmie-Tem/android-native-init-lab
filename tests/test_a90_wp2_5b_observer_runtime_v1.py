from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "a90_wp2_5b_observer_runtime_v1.py"
)
CONTRACT = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "schema/a90-wp2-5b-observer-runtime-v1.json"
)
HEADER = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_owner.h"
SOURCE = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_owner.c"
TRACE_SOURCE = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_stream.c"
C_TEST = ROOT / "tests/a90_wp2_5b_kmsg_owner_test.c"
REPORT = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_OBSERVER_RUNTIME_COMPONENT_H0_2026-08-16.md"
)
GOAL = ROOT / "GOAL_A90.md"
DESIGN = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_RUNTIME_OWNER_DURABLE_EVIDENCE_DESIGN_H0_2026-08-16.md"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_wp2_5b_owner_contract", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observer contract generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A90Wp25bObserverRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_generator()
        cls.contract = json.loads(CONTRACT.read_text())

    def start_payload(self) -> bytes:
        return self.module.START_PAYLOAD.pack(
            b"\x11" * 32,
            b"\x22" * 32,
            b"\x33" * 32,
            b"\x44" * 32,
            b"\x55" * 32,
            8,
            16384,
            1000,
            1000,
            4,
            4,
            4,
            10,
            4,
            0,
        )

    def close_payload(self, cause: int | None = None) -> bytes:
        if cause is None:
            cause = self.module.CLOSE_NORMAL_AFTER_DRIVER_OUTCOME
        return self.module.CLOSE_PAYLOAD.pack(cause, 0)

    def status_payload(
        self,
        *,
        reason: int = 0,
        os_errno: int = 0,
        revents: int = 0,
        reserved: int = 0,
        trace_dev: int = 11,
        trace_ino: int = 22,
        kmsg_dev: int = 12,
        kmsg_ino: int = 23,
        kmsg_rdev: int = 267,
        durable_bytes: int = 4096,
        auxiliary: int = 267,
    ) -> bytes:
        return self.module.STATUS_PAYLOAD.pack(
            reason,
            os_errno,
            revents,
            reserved,
            trace_dev,
            trace_ino,
            kmsg_dev,
            kmsg_ino,
            kmsg_rdev,
            durable_bytes,
            auxiliary,
        )

    def launch_snapshot(self) -> dict[str, object]:
        digest_keys = {
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
        keys = {
            "schedOther",
            "priorityZero",
            "resetOnFork",
            "niceNonnegative",
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
        } | digest_keys
        return {
            key: (f"{index + 1:02x}" * 32 if key in digest_keys else True)
            for index, key in enumerate(sorted(keys))
        }

    def test_generated_contract_and_header_are_exact(self) -> None:
        subprocess.run(
            [sys.executable, str(GENERATOR), "--check-contract", str(CONTRACT)],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(GENERATOR), "--check-header", str(HEADER)],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(self.module.validate_contract(self.contract), [])

    def test_contract_is_h0_effect_free_and_leaves_runtime_gates_open(self) -> None:
        authority = self.contract["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key != "tier":
                self.assertIs(value, False, key)
        self.assertEqual(self.contract["scope"]["workPackage"], "WP2-5b.3a")
        self.assertEqual(
            self.contract["scope"]["openGate"],
            "WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT",
        )
        implementation = self.contract["implementation"]
        self.assertFalse(implementation["parentIntegrationImplemented"])
        self.assertFalse(implementation["durablePublicationWriterImplemented"])
        self.assertFalse(implementation["receiptProducersImplemented"])
        self.assertFalse(implementation["measuredQualificationImplemented"])
        observer = self.contract["observerBoundary"]
        self.assertEqual(
            observer["terminalFaultReaderClose"],
            "AFTER_DURABLE_FAULT_PREFIX_BEFORE_FAULTED_STATUS_EXACT_ONCE_NO_RETRY",
        )
        self.assertEqual(observer["faultCloseWait"]["descriptor"], 3)
        self.assertEqual(
            observer["readerCloseFailure"],
            "ALL_CLOSE_PATHS_NO_FAULTED_NO_END_NO_CLOSED_NO_CONTROL_WAIT_IMMEDIATE_PROCESS_EXIT",
        )
        self.assertEqual(
            observer["faultPublicationFailure"],
            "NO_CONTROL_WAIT_NO_END_NO_CLOSED_IMMEDIATE_PROCESS_EXIT",
        )
        self.assertEqual(observer["durableLengthSource"], "LAST_SUCCESSFUL_FSYNC_ONLY")
        self.assertEqual(
            observer["streamCoreFaultDurability"],
            "FSYNC_EMITTED_FAULT_PREFIX_ADVANCE_DURABLE_LENGTH_BEFORE_FAULTED",
        )
        self.assertEqual(
            observer["finalPublicationFailure"],
            "END_WRITE_OR_FINAL_FSYNC_OR_TRACE_CLOSE_OR_CLOSED_WRITE_FAILURE_NO_CLOSED_NO_UNFSYNCED_DURABLE_LENGTH",
        )
        self.assertEqual(
            observer["faultCloseWait"]["budgetExhaustion"],
            "EXIT_BOUNDED_PARTIAL_WITHOUT_CLOSED",
        )
        self.assertEqual(
            self.contract["pipeContract"]["closeCauseStateCorrelation"],
            "NORMAL_WITHOUT_FAULTED_FAULT_WITH_FAULTED_PARENT_EOF_WITH_FAULTED",
        )
        self.assertEqual(
            self.contract["pipeContract"]["invalidClosePoisonsSession"],
            "ANY_FRAME_HEADER_PAYLOAD_SEMANTIC_OR_DUPLICATE_FAILURE_NO_RESYNC_NO_EOF_AUTHORITY",
        )
        self.assertEqual(
            self.contract["pipeContract"]["closedStatusSuccess"],
            "NO_FAULTED_REQUIRES_ZERO_FAULT_TUPLE_FAULTED_REQUIRES_EXACT_MATCH",
        )
        self.assertEqual(
            self.contract["pipeContract"]["statusDurableProgression"],
            "STRICTLY_INCREASES_ARMED_TO_OPTIONAL_FAULTED_TO_CLOSED",
        )

    def test_contract_validator_rejects_semantic_drift(self) -> None:
        for path, replacement in (
            (("status",), "LIVE_READY"),
            (("authority", "liveExecutionAuthorized"), True),
            (("fixedDescriptors", "controlRead"), 9),
            (("pipeContract", "closeFrameRequiresControlWriterEof"), False),
            (("confinement", "noNewPrivileges"), False),
        ):
            with self.subTest(path=path):
                changed = copy.deepcopy(self.contract)
                cursor = changed
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = replacement
                self.assertEqual(
                    self.module.validate_contract(changed),
                    ["PINNED_SEMANTIC_MISMATCH"],
                )

    def test_control_and_status_transcripts_are_exact(self) -> None:
        start = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_START,
            0,
            self.start_payload(),
        )
        close = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            1,
            self.close_payload(),
        )
        self.assertEqual(
            self.module.validate_transcript(
                [start, close], self.module.DIRECTION_CONTROL
            ),
            [],
        )
        armed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_ARMED,
            0,
            self.status_payload(durable_bytes=100),
        )
        faulted = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_FAULTED,
            1,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=200
            ),
        )
        closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            2,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=300
            ),
        )
        self.assertEqual(
            self.module.validate_transcript(
                [armed, faulted, closed], self.module.DIRECTION_STATUS
            ),
            [],
        )
        self.assertLessEqual(len(start), self.contract["pipeContract"]["atomicMinimumBytes"])

    def test_pipe_parser_rejects_framing_and_counter_mutations(self) -> None:
        valid = bytearray(
            self.module.encode_frame(
                self.module.DIRECTION_CONTROL,
                self.module.CONTROL_START,
                0,
                self.start_payload(),
            )
        )
        mutations = {
            "magic": (0, valid[0] ^ 1, "PIPE_MAGIC_MISMATCH"),
            "version": (9, valid[9] ^ 1, "PIPE_VERSION_MISMATCH"),
            "direction": (10, self.module.DIRECTION_STATUS, "PIPE_DIRECTION_MISMATCH"),
            "kind": (11, 99, "PIPE_KIND_UNKNOWN"),
            "reserved": (23, 1, "PIPE_RESERVED_NONZERO"),
            "length": (21, valid[21] ^ 1, "PIPE_PAYLOAD_LENGTH_MISMATCH"),
        }
        for name, (offset, value, expected) in mutations.items():
            with self.subTest(name=name):
                changed = bytearray(valid)
                changed[offset] = value
                _parsed, findings = self.module.parse_frame(
                    bytes(changed), self.module.DIRECTION_CONTROL
                )
                self.assertIn(expected, findings)
        _parsed, findings = self.module.parse_frame(
            bytes(valid) + b"x", self.module.DIRECTION_CONTROL
        )
        self.assertIn("PIPE_FRAME_SIZE_MISMATCH", findings)
        gap = bytearray(valid)
        struct.pack_into(">Q", gap, 12, 1)
        self.assertIn(
            "PIPE_SEQUENCE_MISMATCH",
            self.module.validate_transcript(
                [bytes(gap)], self.module.DIRECTION_CONTROL
            ),
        )
        duplicate = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            1,
            self.close_payload(),
        )
        duplicate_two = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            2,
            self.close_payload(),
        )
        self.assertIn(
            "CONTROL_CLOSE_CARDINALITY",
            self.module.validate_transcript(
                [bytes(valid), duplicate, duplicate_two],
                self.module.DIRECTION_CONTROL,
            ),
        )

    def test_pipe_codec_is_strict_about_python_types(self) -> None:
        for direction in (True, False, 1.0, "1", None):
            with self.subTest(direction=direction):
                with self.assertRaises(ValueError):
                    self.module.encode_frame(
                        direction,
                        self.module.CONTROL_START,
                        0,
                        self.start_payload(),
                    )
                _parsed, findings = self.module.parse_frame(b"", direction)
                self.assertEqual(findings, ["PIPE_EXPECTED_DIRECTION_TYPE"])
        with self.assertRaises(ValueError):
            self.module.encode_frame(
                self.module.DIRECTION_CONTROL,
                self.module.CONTROL_START,
                True,
                self.start_payload(),
            )

    def test_close_cause_and_status_reserved_are_fail_closed(self) -> None:
        start = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_START,
            0,
            self.start_payload(),
        )
        close = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            1,
            self.close_payload(99),
        )
        self.assertIn(
            "CONTROL_CLOSE_CAUSE",
            self.module.validate_transcript(
                [start, close], self.module.DIRECTION_CONTROL
            ),
        )
        closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            0,
            self.status_payload(reserved=1),
        )
        self.assertIn(
            "STATUS_RESERVED_NONZERO",
            self.module.validate_transcript(
                [closed], self.module.DIRECTION_STATUS
            ),
        )

    def test_close_cause_and_status_state_are_correlated(self) -> None:
        start = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_START,
            0,
            self.start_payload(),
        )
        close_normal = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            1,
            self.close_payload(self.module.CLOSE_NORMAL_AFTER_DRIVER_OUTCOME),
        )
        close_fault = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            1,
            self.close_payload(self.module.CLOSE_FAULT_AFTER_TERMINAL_INPUT),
        )
        armed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_ARMED,
            0,
            self.status_payload(durable_bytes=100),
        )
        healthy_closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            1,
            self.status_payload(durable_bytes=200),
        )
        faulted = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_FAULTED,
            1,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=200
            ),
        )
        fault_closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            2,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=300
            ),
        )
        healthy_status = [armed, healthy_closed]
        fault_status = [armed, faulted, fault_closed]

        for control, status in (
            ([start, close_normal], healthy_status),
            ([start, close_fault], fault_status),
            ([start], fault_status),
        ):
            with self.subTest(control_count=len(control), status_count=len(status)):
                self.assertEqual(
                    self.module.validate_session_transcripts(control, status), []
                )
        for control, status in (
            ([start, close_normal], fault_status),
            ([start, close_fault], healthy_status),
            ([start], healthy_status),
        ):
            with self.subTest(control_count=len(control), status_count=len(status)):
                self.assertEqual(
                    self.module.validate_session_transcripts(control, status),
                    ["PIPE_CLOSE_STATUS_CAUSE_MISMATCH"],
                )
        false_durable_closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            1,
            self.status_payload(reason=9, os_errno=28, durable_bytes=200),
        )
        self.assertEqual(
            self.module.validate_session_transcripts(
                [start, close_normal], [armed, false_durable_closed]
            ),
            ["STATUS_CLOSED_WITHOUT_FAULTED"],
        )

    def test_invalid_first_close_cannot_resynchronize(self) -> None:
        start = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_START,
            0,
            self.start_payload(),
        )
        valid_fault_close = self.module.encode_frame(
            self.module.DIRECTION_CONTROL,
            self.module.CONTROL_CLOSE,
            2,
            self.close_payload(self.module.CLOSE_FAULT_AFTER_TERMINAL_INPUT),
        )
        armed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_ARMED,
            0,
            self.status_payload(durable_bytes=100),
        )
        faulted = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_FAULTED,
            1,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=200
            ),
        )
        closed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_CLOSED,
            2,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=300
            ),
        )
        first_frames = (
            self.module.encode_frame(
                self.module.DIRECTION_CONTROL,
                self.module.CONTROL_CLOSE,
                1,
                self.close_payload(99),
            ),
            self.module.encode_frame(
                self.module.DIRECTION_CONTROL,
                self.module.CONTROL_CLOSE,
                1,
                self.module.CLOSE_PAYLOAD.pack(
                    self.module.CLOSE_NORMAL_AFTER_DRIVER_OUTCOME, 1
                ),
            ),
            self.module.PIPE_HEADER.pack(
                self.module.MAGIC,
                self.module.VERSION,
                self.module.DIRECTION_CONTROL,
                99,
                1,
                0,
                0,
            ),
        )
        for first in first_frames:
            with self.subTest(first_kind=first[11]):
                findings = self.module.validate_session_transcripts(
                    [start, first, valid_fault_close], [armed, faulted, closed]
                )
                self.assertNotEqual(findings, [])
                self.assertTrue(
                    {"CONTROL_CLOSE_CARDINALITY", "CONTROL_CLOSE_CAUSE", "PIPE_KIND_UNKNOWN"}
                    & set(findings)
                )

    def test_status_identity_durability_and_fault_correlation_are_bound(self) -> None:
        armed = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_ARMED,
            0,
            self.status_payload(durable_bytes=100),
        )
        faulted = self.module.encode_frame(
            self.module.DIRECTION_STATUS,
            self.module.STATUS_FAULTED,
            1,
            self.status_payload(
                reason=3, os_errno=32, revents=8, durable_bytes=200, auxiliary=1
            ),
        )
        for name, closed_payload, expected in (
            (
                "identity",
                self.status_payload(
                    reason=3,
                    os_errno=32,
                    revents=8,
                    trace_ino=99,
                    durable_bytes=300,
                    auxiliary=1,
                ),
                "STATUS_IDENTITY_DRIFT",
            ),
            (
                "durability",
                self.status_payload(
                    reason=3,
                    os_errno=32,
                    revents=8,
                    durable_bytes=150,
                    auxiliary=1,
                ),
                "STATUS_DURABLE_LENGTH_REGRESSION",
            ),
            (
                "fault",
                self.status_payload(
                    reason=4,
                    os_errno=32,
                    revents=8,
                    durable_bytes=300,
                    auxiliary=1,
                ),
                "STATUS_CLOSED_FAULT_MISMATCH",
            ),
        ):
            with self.subTest(name=name):
                closed = self.module.encode_frame(
                    self.module.DIRECTION_STATUS,
                    self.module.STATUS_CLOSED,
                    2,
                    closed_payload,
                )
                self.assertIn(
                    expected,
                    self.module.validate_transcript(
                        [armed, faulted, closed], self.module.DIRECTION_STATUS
                    ),
                )
        for name, stale_faulted_bytes, stale_closed_bytes in (
            ("faulted-equals-armed", 100, 300),
            ("closed-equals-faulted", 200, 200),
        ):
            with self.subTest(name=name):
                stale_faulted = self.module.encode_frame(
                    self.module.DIRECTION_STATUS,
                    self.module.STATUS_FAULTED,
                    1,
                    self.status_payload(
                        reason=3,
                        os_errno=32,
                        revents=8,
                        durable_bytes=stale_faulted_bytes,
                        auxiliary=1,
                    ),
                )
                stale_closed = self.module.encode_frame(
                    self.module.DIRECTION_STATUS,
                    self.module.STATUS_CLOSED,
                    2,
                    self.status_payload(
                        reason=3,
                        os_errno=32,
                        revents=8,
                        durable_bytes=stale_closed_bytes,
                        auxiliary=1,
                    ),
                )
                self.assertIn(
                    "STATUS_DURABLE_LENGTH_NOT_ADVANCED",
                    self.module.validate_transcript(
                        [armed, stale_faulted, stale_closed],
                        self.module.DIRECTION_STATUS,
                    ),
                )

    def test_start_rejects_zero_digests_caps_budgets_and_reserved(self) -> None:
        fields = list(self.module.START_PAYLOAD.unpack(self.start_payload()))
        mutations = {
            "digest": (0, b"\x00" * 32, "CONTROL_START_ZERO_DIGEST"),
            "count-cap": (5, 0, "CONTROL_START_CAP_INVALID"),
            "byte-cap": (6, 0, "CONTROL_START_CAP_INVALID"),
            "read-budget": (9, 0, "CONTROL_START_BUDGET_INVALID"),
            "poll-timeout": (12, 0, "CONTROL_START_BUDGET_INVALID"),
            "fault-close-poll-budget": (13, 0, "CONTROL_START_BUDGET_INVALID"),
            "reserved": (14, 1, "CONTROL_START_RESERVED_NONZERO"),
        }
        for name, (index, replacement, expected) in mutations.items():
            with self.subTest(name=name):
                changed = list(fields)
                changed[index] = replacement
                frame = self.module.encode_frame(
                    self.module.DIRECTION_CONTROL,
                    self.module.CONTROL_START,
                    0,
                    self.module.START_PAYLOAD.pack(*changed),
                )
                self.assertIn(
                    expected,
                    self.module.validate_transcript(
                        [frame], self.module.DIRECTION_CONTROL
                    ),
                )

    def test_launch_snapshot_requires_every_safety_fact_and_digest(self) -> None:
        snapshot = self.launch_snapshot()
        self.assertEqual(self.module.validate_launch_snapshot(snapshot), [])
        for key, replacement, expected in (
            ("schedOther", False, "LAUNCH_SNAPSHOT_SAFETY_STATE"),
            ("fixedArgv", 1, "LAUNCH_SNAPSHOT_SAFETY_STATE"),
            ("rootSha256", "0" * 64, "LAUNCH_SNAPSHOT_DIGEST"),
            ("fdSetSha256", "AA" * 32, "LAUNCH_SNAPSHOT_DIGEST"),
        ):
            with self.subTest(key=key):
                changed = dict(snapshot)
                changed[key] = replacement
                self.assertEqual(
                    self.module.validate_launch_snapshot(changed), [expected]
                )
        changed = dict(snapshot)
        changed["extra"] = True
        self.assertEqual(
            self.module.validate_launch_snapshot(changed),
            ["LAUNCH_SNAPSHOT_SCHEMA"],
        )

    def test_source_exposes_no_effect_or_journal_api(self) -> None:
        header = HEADER.read_text()
        source = SOURCE.read_text()
        self.assertNotIn("dispatch", header.lower())
        self.assertNotIn("journal", header.lower())
        self.assertNotIn("receipt", header.lower())
        self.assertNotIn("terminal", header.lower())
        self.assertNotIn("/proc/kmsg", source)
        self.assertNotIn("system(", source)
        self.assertNotIn("popen(", source)
        self.assertIn('OWNER_KMSG_PATH "/dev/kmsg"', source)
        self.assertIn("SECCOMP_RET_KILL_PROCESS", source)
        self.assertIn("PR_SET_NO_NEW_PRIVS", source)
        self.assertIn("PR_CAPBSET_DROP", source)
        self.assertIn(
            "FD duplication", self.contract["confinement"]["forbidden"][-2]
        )

    @unittest.skipUnless(shutil.which("gcc"), "host C compiler unavailable")
    def test_syscall_injected_c_state_machine_and_faults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "a90-owner-test"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=all",
                    "-DA90_WP2_5B_HOST_TESTING",
                    "-I",
                    str(HEADER.parent),
                    str(C_TEST),
                    str(SOURCE),
                    str(TRACE_SOURCE),
                    "-o",
                    str(binary),
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(binary)], cwd=ROOT, check=True)

    @unittest.skipUnless(
        shutil.which("gcc") and shutil.which("nm"),
        "host C compiler or nm unavailable",
    )
    def test_production_object_exposes_no_injected_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "a90-owner-production.o"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(HEADER.parent),
                    "-c",
                    str(SOURCE),
                    "-o",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
            )
            symbols = subprocess.run(
                ["nm", "-g", str(output)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn("a90_wp2_5b_owner_run_with_ops", symbols)
            self.assertIn("a90_wp2_5b_owner_run", symbols)

    @unittest.skipUnless(
        shutil.which("aarch64-linux-gnu-gcc"),
        "AArch64 cross compiler unavailable",
    )
    def test_owner_and_fixture_cross_compile_warning_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for source in (SOURCE, C_TEST):
                output = Path(temporary) / f"{source.stem}.o"
                subprocess.run(
                    [
                        "aarch64-linux-gnu-gcc",
                        "-std=c11",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-I",
                        str(HEADER.parent),
                        "-c",
                        str(source),
                        "-o",
                        str(output),
                    ],
                    cwd=ROOT,
                    check=True,
                )
                identified = subprocess.run(
                    ["file", str(output)], check=True, capture_output=True, text=True
                ).stdout
                self.assertIn("ARM aarch64", identified)

    def test_report_goal_and_design_keep_the_unit_h0(self) -> None:
        report = REPORT.read_text()
        goal = GOAL.read_text()
        design = DESIGN.read_text()
        for token in (
            "WP2-5b.3a",
            "H0_COMPONENT_IMPLEMENTED_EXECUTION_QUALIFICATION_ABSENT",
            "WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT",
            "device ordinals consumed: 0",
            "durable final-name publication writer",
        ):
            self.assertIn(token, report)
        self.assertIn(REPORT.name, goal)
        self.assertIn("WP2-5b.3a", goal)
        self.assertIn("WP2-5b.3a", design)
        self.assertIn("WP2-5b.3b", design)


if __name__ == "__main__":
    unittest.main()
