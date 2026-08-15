"""Host-only hostile tests for the A90 WP2-5b.1 kmsg trace core."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/a90_wp2_5b_kmsg_trace_v1.py"
)
CONTRACT = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "schema/a90-wp2-5b-kmsg-trace-v1.json"
)
HEADER = (
    ROOT
    / "workspace/public/src/native-init/helpers/"
    "a90_wp2_5b_kmsg_contract.h"
)
SOURCE = (
    ROOT
    / "workspace/public/src/native-init/helpers/"
    "a90_wp2_5b_kmsg_stream.c"
)
REPORT = ROOT / "docs/reports/A90_WLAN_WP2_5B_KMSG_TRACE_CORE_H0_2026-08-16.md"
REQUIREMENT_REPORT = (
    ROOT
    / "docs/reports/A90_WLAN_WP2_5B_STREAMING_KMSG_OBSERVER_H0_2026-08-16.md"
)
PROPOSAL = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "proposals/wlan-vendor-property-ablation.md"
)
HARDENING = PROPOSAL.parents[1] / "hardening.md"
CONTEXT = PROPOSAL.parents[1] / "context.md"
HARDENING_JSON = PROPOSAL.parents[1] / "hardening.json"


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_wp2_5b_trace", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load WP2-5b.1 generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class A90Wp25bKmsgTraceV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_generator()
        cls.contract = json.loads(CONTRACT.read_text())
        cls.wp2 = cls.module._load_wp2_module()

    def base_property_result(self, decision: str = "FALSE") -> dict:
        roles = ["cnss_daemon"]
        events: list[dict] = []
        process_instances = [
            {
                "instanceId": f"cnss-daemon-{epoch.lower()}",
                "role": "cnss_daemon",
                "launchEpoch": epoch,
                "pid": index + 100,
                "starttime": index + 1000,
                "executableSha256": sha(f"executable-{epoch}"),
                "identitySha256": sha(f"identity-{epoch}"),
                "launchReceiptSha256": sha(f"launch-{epoch}"),
                "exitReceiptSha256": sha(f"exit-{epoch}"),
                "lifecycleClosure": "EXITED_REAPED_BOUND",
            }
            for index, epoch in enumerate(("INITIAL", "COLD_RELAUNCH"))
        ]
        result = {
            "schema": self.wp2.RESULT_SCHEMA,
            "terminal": "PROPERTY_ABSENT_PROVED",
            "bindings": {
                "target": "Samsung Galaxy A90 5G",
                "residentBuild": "synthetic-host-fixture",
                "candidateSha256": sha("candidate"),
                "parentGenerationSha256": sha("parent"),
                "componentManifestSha256": sha("manifest"),
                "bootIdSha256": sha("boot"),
                "runNonce": "synthetic-run-nonce",
                "observerSha256": sha("observer"),
                "observationBudgetSha256": "",
                "qualificationSha256": sha("qualification"),
                "traceSha256": self.wp2._event_digest(events),
            },
            "expectedRoles": roles,
            "coldRelaunchRoles": roles,
            "persistentAcrossRelaunchRoles": [],
            "processInstances": process_instances,
            "coverage": [
                {
                    "role": role,
                    "phase": phase,
                    "state": "RUNNING_OBSERVED",
                    "observerComplete": True,
                    "startBoundaryProved": True,
                    "endBoundaryProved": True,
                    "eventLossCount": 0,
                    "processInstanceIds": [
                        "cnss-daemon-cold_relaunch"
                        if phase == "COLD_RELAUNCH"
                        else "cnss-daemon-initial"
                    ],
                }
                for role in roles
                for phase in self.wp2.PHASES
            ],
            "events": events,
            "trace": {
                "observerOutcome": "VALID_COMPLETE",
                "closed": True,
                "mixedRun": False,
                "truncated": False,
                "droppedEvents": 0,
                "duplicateEvents": 0,
                "fabricatedDefaultEvents": 0,
                "malformedEvents": 0,
                "unknownEvents": 0,
                "declaredEventCount": 0,
                "firstSequence": -1,
                "lastSequence": -1,
                "eventCountCap": 32,
                "traceBytes": len(self.wp2._event_bytes(events)),
                "traceByteCap": 65536,
            },
            "seedEntries": [],
            "seedFilesystem": {
                "state": "ABSENT",
                "rootPath": None,
                "rootReadOnly": None,
                "memberNames": [],
                "memberSetSha256": self.wp2._member_digest([]),
                "unexpectedMembers": [],
                "symlinkCount": 0,
                "hardlinkAliasCount": 0,
                "specialFileCount": 0,
                "generationMatches": True,
                "digestStable": True,
            },
            "macProvisioningEffect": {
                "sameBoot": True,
                "sameRun": True,
                "sourceIdentityBound": True,
                "driverIdentityBound": True,
                "debugfsIdentityBound": True,
                "readComplete": True,
                "cnssUtilsMacState": "ABSENT_PARSED",
                "wlanOutcome": "WLAN0_UP_EXACT_DRIVER",
                "provisionedAbsenceAtDriverLookup": (
                    "TYPE0_ABSENT_EXACT_BOUND_DRIVER_INIT"
                ),
                "decision": "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
            },
            "deviceSafetyState": "RESIDENT_HEALTHY",
            "experimentProof": "PROVED",
            "workflowState": "TERMINAL",
        }
        if decision == "TRUE":
            result["macProvisioningEffect"].update(
                wlanOutcome="MAC_INIT_FAILED_EXACT_SIGNATURE",
                provisionedAbsenceAtDriverLookup="NOT_PROVED",
                decision="MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
            )
        result["bindings"]["observationBudgetSha256"] = (
            self.wp2._observation_budget_digest(
                result["trace"]["eventCountCap"],
                result["trace"]["traceByteCap"],
            )
        )
        return result

    def property_expectation(self, result: dict) -> dict:
        return {
            "bindingProjection": {
                key: copy.deepcopy(result["bindings"][key])
                for key in self.wp2.QUALIFIED_BINDING_KEYS
            },
            "expectedRoles": copy.deepcopy(result["expectedRoles"]),
            "coldRelaunchRoles": copy.deepcopy(result["coldRelaunchRoles"]),
            "persistentAcrossRelaunchRoles": copy.deepcopy(
                result["persistentAcrossRelaunchRoles"]
            ),
            "eventCountCap": result["trace"]["eventCountCap"],
            "seedContractSha256": self.wp2._seed_contract_digest(result),
            "traceByteCap": result["trace"]["traceByteCap"],
        }

    def qualified(self, result: dict) -> dict:
        property_expectation = self.property_expectation(result)
        return {
            "schema": self.module.QUALIFIED_SCHEMA,
            "propertyExpectation": property_expectation,
            "runBindingSha256": self.module._run_binding_digest(
                property_expectation["bindingProjection"]
            ),
            "qualificationSha256": result["bindings"]["qualificationSha256"],
            "observerBinarySha256": result["bindings"]["observerSha256"],
            "contractSha256": self.module.contract_sha256(),
            "driverInitEpochSha256": sha("driver-init-epoch"),
            "captureCloseBindingSha256": sha("capture-close-binding"),
            "proofSubjectSha256": sha("proof-subject"),
            "effectCommandSha256": sha("effect-command"),
            "recordCountCap": 8,
            "recordByteCap": 16384,
        }

    def driver_outcome_receipt(self, result: dict, qualified: dict) -> dict:
        return {
            "schema": self.module.DRIVER_OUTCOME_SCHEMA,
            "bootIdSha256": result["bindings"]["bootIdSha256"],
            "driverIdentityReceiptSha256": sha("driver-identity-receipt"),
            "driverInitEpochSha256": qualified["driverInitEpochSha256"],
            "interfaceOutcomeReceiptSha256": sha("interface-outcome-receipt"),
            "runBindingSha256": qualified["runBindingSha256"],
            "wlanOutcome": result["macProvisioningEffect"]["wlanOutcome"],
        }

    @staticmethod
    def record(
        sequence: int,
        body: str,
        *,
        priority: int = 3,
        timestamp: int = 1000,
        flag: str = "-",
        dictionary: bytes = b"",
    ) -> bytes:
        raw = f"{priority},{sequence},{timestamp},{flag};{body}\n".encode()
        return raw + dictionary

    def trace(self, qualified: dict, records: list[bytes], fault: bytes | None = None) -> bytes:
        arm = self.module.ARM_PAYLOAD.pack(
            bytes.fromhex(qualified["runBindingSha256"]),
            bytes.fromhex(qualified["qualificationSha256"]),
            bytes.fromhex(qualified["observerBinarySha256"]),
            bytes.fromhex(qualified["contractSha256"]),
            qualified["recordCountCap"],
            qualified["recordByteCap"],
        )
        output = self.module._trace_prefix() + self.module._frame(
            self.module.FRAME_ARM, arm
        )
        for record in records:
            output += self.module._frame(self.module.FRAME_RECORD, record)
        if fault is not None:
            output += self.module._frame(self.module.FRAME_FAULT, fault)
        first = (
            self.module.parse_kmsg_record(records[0])[0]["sequence"]
            if records
            else self.module.UINT64_MAX
        )
        last = (
            self.module.parse_kmsg_record(records[-1])[0]["sequence"]
            if records
            else self.module.UINT64_MAX
        )
        end = self.module.END_PAYLOAD.pack(
            bytes.fromhex(qualified["driverInitEpochSha256"]),
            bytes.fromhex(qualified["captureCloseBindingSha256"]),
            len(records),
            sum(map(len, records)),
            first,
            last,
        )
        return output + self.module._frame(self.module.FRAME_END, end)

    def full_journal(self, raw_trace: bytes, result: dict, qualified: dict) -> list[dict]:
        trace_summary, findings = self.module.validate_trace(
            raw_trace, self.module.trace_expectation_from_qualified(qualified)
        )
        self.assertEqual(findings, [])
        payloads = {
            "OBSERVER_ARMED": trace_summary["armReceiptSha256"],
            "EFFECT_INTENT": qualified["proofSubjectSha256"],
            "EFFECT_DISPATCHED": qualified["effectCommandSha256"],
            "DRIVER_OUTCOME_BOUND": hashlib.sha256(
                self.module._canonical_bytes(
                    self.driver_outcome_receipt(result, qualified)
                )
            ).hexdigest(),
            "CAPTURE_CLOSED": hashlib.sha256(raw_trace).hexdigest(),
            "TERMINAL": hashlib.sha256(
                self.module._canonical_bytes(result)
            ).hexdigest(),
        }
        return self.module.build_journal(
            qualified["runBindingSha256"], payloads
        )

    @staticmethod
    def journal_payloads(records: list[dict]) -> dict[str, str]:
        return {record["event"]: record["payloadSha256"] for record in records}

    def test_generated_contract_and_header_are_exact(self) -> None:
        self.assertEqual(CONTRACT.read_text(), self.module.canonical_contract_text())
        self.assertEqual(HEADER.read_text(), self.module.canonical_header_text())
        self.assertEqual(self.module.validate_contract(self.contract), [])
        self.assertEqual(self.contract["authority"]["tier"], "H0")
        self.assertFalse(self.contract["authority"]["liveExecutionAuthorized"])
        self.assertFalse(self.contract["journalContract"]["durableWriterImplemented"])
        self.assertFalse(
            self.contract["journalContract"]["rawCanonicalParserImplemented"]
        )

    def test_contract_mutation_fails_closed(self) -> None:
        value = copy.deepcopy(self.contract)
        value["authority"]["d0Authorized"] = True
        self.assertEqual(
            self.module.validate_contract(value), ["PINNED_SEMANTIC_MISMATCH"]
        )

    def test_pinned_source_drift_is_a_finding_not_an_exception(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        saved = copy.deepcopy(self.module.PINNED_INPUTS)
        rel = self.module.WP2_SCHEMA_REL
        size, digest = self.module.PINNED_INPUTS[rel]
        try:
            self.module.PINNED_INPUTS[rel] = (size + 1, digest)
            _summary, findings = self.module.validate_trace(
                raw, self.module.trace_expectation_from_qualified(qualified)
            )
            self.assertIn("PINNED_SOURCE_MODEL_UNAVAILABLE", findings)
            bound = self.module.build_bound_result(
                raw,
                result,
                qualified,
                self.driver_outcome_receipt(result, qualified),
                [],
            )
            self.assertIn("PINNED_SOURCE_MODEL_UNAVAILABLE", bound["findings"])
            self.assertEqual(
                bound["bindings"]["contractSha256"], self.module.ZERO_SHA256
            )
        finally:
            self.module.PINNED_INPUTS.clear()
            self.module.PINNED_INPUTS.update(saved)
        value = copy.deepcopy(self.contract)
        value["extra"] = True
        self.assertEqual(
            self.module.validate_contract(value), ["PINNED_SEMANTIC_MISMATCH"]
        )

    def test_valid_type0_trace_is_sequence_complete(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(
            qualified,
            [
                self.record(100, self.module.TYPE0_ABSENT),
                self.record(101, "wlan0: link up", priority=6, timestamp=1001),
            ],
        )
        summary, findings = self.module.validate_trace(
            raw, self.module.trace_expectation_from_qualified(qualified)
        )
        self.assertEqual(findings, [])
        self.assertEqual(summary["outcome"], "VALID_COMPLETE")
        self.assertEqual(summary["recordCount"], 2)
        self.assertEqual(summary["firstSequence"], 100)
        self.assertEqual(summary["lastSequence"], 101)
        self.assertEqual(summary["type0AbsentCount"], 1)
        self.assertEqual(summary["type1AbsentCount"], 0)

    def test_kmsg_record_grammar_rejects_noncanonical_inputs(self) -> None:
        bad = (
            b"",
            b"3,1,2,-;missing-newline",
            b"03,1,2,-;body\n",
            b"3,01,2,-;body\n",
            b"3,1,02,-;body\n",
            b"3,1,2,x;body\n",
            b"3,1,2,-body\n",
            b"3,1,2,-;body\x00\n",
            b"3,1,2,-;body\ninvalid-dictionary\n",
            b"3,1,2,-;bad\\q\n",
            b"3,1,2,-;bad\\x41\n",
            b"3,1,2,-;bad\\x5C\n",
            b"3,1,2,-;body\n\n",
            b"3,1,2,-;body\n \n",
            b"2048,1,2,-;body\n",
            b"3,18446744073709551616,2,-;body\n",
            b"4294967296,1,2,-;body\n",
            b"3,1,2,-;" + (b"x" * self.module.KMSG_RECORD_MAX),
        )
        for value in bad:
            with self.subTest(value=value[:40]):
                parsed, findings = self.module.parse_kmsg_record(value)
                self.assertIsNone(parsed)
                self.assertTrue(findings)

        valid = b"3,1,2,-;bad\\x5c\\x0a\\xff\n key=va\\x5clue\n\n"
        parsed, findings = self.module.parse_kmsg_record(valid)
        self.assertEqual(findings, [])
        self.assertEqual(parsed["priority"], 3)
        self.assertTrue(parsed["dictionaryPresent"])

    def test_dictionary_or_continuation_cannot_carry_mac_signature(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        variants = (
            self.record(1, self.module.TYPE0_ABSENT, flag="c"),
            self.record(
                1,
                self.module.TYPE0_ABSENT,
                dictionary=b" KEY=value\n",
            ),
            self.record(1, self.module.TYPE0_ABSENT, priority=11),
        )
        for record in variants:
            with self.subTest(record=record):
                raw = self.trace(qualified, [record])
                summary, findings = self.module.validate_trace(
                    raw, self.module.trace_expectation_from_qualified(qualified)
                )
                self.assertEqual(findings, [])
                self.assertEqual(summary["type0AbsentCount"], 0)

    def test_extended_text_grammar_matches_all_source_byte_classes(self) -> None:
        def source_escape(byte: int) -> bytes:
            if byte < 32 or byte >= 127 or byte == 92:
                return f"\\x{byte:02x}".encode()
            return bytes([byte])

        for byte in range(256):
            with self.subTest(kind="message", byte=byte):
                record = b"3,1,2,-;" + source_escape(byte) + b"\n"
                parsed, findings = self.module.parse_kmsg_record(record)
                self.assertEqual(findings, [])
                self.assertIsNotNone(parsed)
            with self.subTest(kind="dictionary", byte=byte):
                dictionary = (
                    b" \n\n"
                    if byte == 0
                    else b" " + source_escape(byte) + b"\n"
                )
                record = b"3,1,2,-;body\n" + dictionary
                parsed, findings = self.module.parse_kmsg_record(record)
                self.assertEqual(findings, [])
                self.assertIsNotNone(parsed)
            if 32 <= byte <= 126 and byte != 92:
                with self.subTest(kind="unnecessary-escape", byte=byte):
                    record = f"3,1,2,-;\\x{byte:02x}\n".encode()
                    parsed, findings = self.module.parse_kmsg_record(record)
                    self.assertIsNone(parsed)
                    self.assertTrue(findings)

    def test_sequence_gap_duplicate_regression_and_overflow_fail(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        variants = (
            (1, 3),
            (1, 1),
            (2, 1),
            (self.module.UINT64_MAX, 0),
        )
        for first, second in variants:
            with self.subTest(first=first, second=second):
                raw = self.trace(
                    qualified,
                    [self.record(first, "one"), self.record(second, "two")],
                )
                _summary, findings = self.module.validate_trace(
                    raw, self.module.trace_expectation_from_qualified(qualified)
                )
                self.assertIn("TRACE_SEQUENCE_MISMATCH", findings)

    def test_trace_header_frame_order_and_trailing_bytes_fail(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, "one")])
        variants = (
            b"X" + raw[1:],
            raw[:8] + b"\x00\x02" + raw[10:],
            raw + b"trailing",
            raw[:-1],
            self.module._trace_prefix()
            + self.module._frame(self.module.FRAME_RECORD, self.record(1, "one")),
        )
        for value in variants:
            with self.subTest(length=len(value)):
                summary, findings = self.module.validate_trace(
                    value, self.module.trace_expectation_from_qualified(qualified)
                )
                self.assertNotEqual(findings, [])
                self.assertEqual(summary["outcome"], "NO_PROOF_OBSERVER")

    def test_reported_fault_is_never_complete(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        fault = self.module.FAULT_PAYLOAD.pack(
            self.module.FAULT_EPIPE, 32, 0x8, self.module.UINT64_MAX
        )
        raw = self.trace(qualified, [], fault=fault)
        summary, findings = self.module.validate_trace(
            raw, self.module.trace_expectation_from_qualified(qualified)
        )
        self.assertIn("TRACE_REPORTED_FAULT", findings)
        self.assertEqual(summary["faultCount"], 1)
        self.assertEqual(summary["outcome"], "NO_PROOF_OBSERVER")

    def test_record_and_byte_caps_fail_closed(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        records = [self.record(1, "one"), self.record(2, "two")]
        raw = self.trace(qualified, records)
        small_count = copy.deepcopy(qualified)
        small_count["recordCountCap"] = 1
        _summary, findings = self.module.validate_trace(
            raw, self.module.trace_expectation_from_qualified(small_count)
        )
        self.assertIn("TRACE_ARM_BINDING_MISMATCH", findings)
        self.assertIn("TRACE_RECORD_COUNT_CAP_EXHAUSTED", findings)
        small_bytes = copy.deepcopy(qualified)
        small_bytes["recordByteCap"] = sum(map(len, records)) - 1
        _summary, findings = self.module.validate_trace(
            raw, self.module.trace_expectation_from_qualified(small_bytes)
        )
        self.assertIn("TRACE_RECORD_BYTE_CAP_EXHAUSTED", findings)

    def test_total_framed_trace_envelope_is_checked_before_parsing(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        expectation = self.module.trace_expectation_from_qualified(qualified)
        maximum = self.module.maximum_trace_bytes(expectation)
        self.assertIsInstance(maximum, int)
        raw = b"X" * (maximum + 1)
        summary, findings = self.module.validate_trace(raw, expectation)
        self.assertIn("TRACE_TOTAL_BYTE_CAP_EXHAUSTED", findings)
        self.assertEqual(summary["outcome"], "NO_PROOF_OBSERVER")

    def test_arm_and_end_bindings_are_exact(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, "one")])
        for key in (
            "runBindingSha256",
            "qualificationSha256",
            "observerBinarySha256",
            "driverInitEpochSha256",
            "captureCloseBindingSha256",
        ):
            forged = copy.deepcopy(qualified)
            forged[key] = sha(f"forged-{key}")
            _summary, findings = self.module.validate_trace(
                raw, self.module.trace_expectation_from_qualified(forged)
            )
            expected = (
                "TRACE_END_BINDING_MISMATCH"
                if key in ("driverInitEpochSha256", "captureCloseBindingSha256")
                else "TRACE_ARM_BINDING_MISMATCH"
            )
            self.assertIn(expected, findings)

    def test_qualified_expectation_rejects_cross_binding_and_bool_int(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        self.assertEqual(self.module.validate_qualified_expectation(qualified), [])
        variants = []
        value = copy.deepcopy(qualified)
        value["observerBinarySha256"] = sha("other-observer")
        variants.append(value)
        value = copy.deepcopy(qualified)
        value["runBindingSha256"] = sha("wrong-run")
        variants.append(value)
        value = copy.deepcopy(qualified)
        value["recordCountCap"] = True
        variants.append(value)
        value = copy.deepcopy(qualified)
        value["extra"] = False
        variants.append(value)
        value = copy.deepcopy(qualified)
        value["propertyExpectation"]["bindingProjection"]["target"] = b"bytes"
        variants.append(value)
        value = copy.deepcopy(qualified)
        value["propertyExpectation"]["bindingProjection"]["target"] = float("nan")
        variants.append(value)
        for value in variants:
            with self.subTest(value=value):
                self.assertNotEqual(
                    self.module.validate_qualified_expectation(value), []
                )

    def test_driver_outcome_receipt_is_exactly_cross_bound(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        receipt = self.driver_outcome_receipt(result, qualified)
        self.assertEqual(
            self.module.validate_driver_outcome_receipt(
                receipt, qualified, result
            ),
            [],
        )
        variants = []
        for key in (
            "bootIdSha256",
            "driverInitEpochSha256",
            "runBindingSha256",
        ):
            value = copy.deepcopy(receipt)
            value[key] = sha(f"forged-{key}")
            variants.append(value)
        value = copy.deepcopy(receipt)
        value["wlanOutcome"] = "MAC_INIT_FAILED_EXACT_SIGNATURE"
        variants.append(value)
        value = copy.deepcopy(receipt)
        value["bootIdSha256"] = False
        variants.append(value)
        value = copy.deepcopy(receipt)
        value["driverIdentityReceiptSha256"] = self.module.ZERO_SHA256
        variants.append(value)
        value = copy.deepcopy(receipt)
        value["interfaceOutcomeReceiptSha256"] = False
        variants.append(value)
        value = copy.deepcopy(receipt)
        value["wlanOutcome"] = []
        variants.append(value)
        value = copy.deepcopy(receipt)
        value["extra"] = True
        variants.append(value)
        for value in variants:
            with self.subTest(value=value):
                self.assertNotEqual(
                    self.module.validate_driver_outcome_receipt(
                        value, qualified, result
                    ),
                    [],
                )
        malformed_result = copy.deepcopy(result)
        malformed_result["deviceSafetyState"] = "BASELINE_HEALTHY"
        self.assertIn(
            "DRIVER_OUTCOME_RECEIPT_RESULT_REJECTED",
            self.module.validate_driver_outcome_receipt(
                receipt, qualified, malformed_result
            ),
        )

    def test_every_journal_prefix_is_no_replay(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        full = self.full_journal(raw, result, qualified)
        payloads = self.journal_payloads(full)
        for length in range(len(self.module.JOURNAL_EVENTS) + 1):
            with self.subTest(length=length):
                state, findings = self.module.validate_journal(
                    full[:length],
                    qualified["runBindingSha256"],
                    {
                        event: payloads[event]
                        for event in self.module.JOURNAL_EVENTS[:length]
                    },
                )
                self.assertEqual(findings, [])
                self.assertFalse(state["effectReplayAllowed"])
                self.assertEqual(state["effectConsumed"], length >= 2)
                if 2 <= length < len(self.module.JOURNAL_EVENTS):
                    self.assertEqual(
                        state["reconciliationMode"],
                        "OBSERVE_CLEANUP_RECOVERY_ONLY",
                    )
        state, findings = self.module.validate_journal(
            full, qualified["runBindingSha256"], payloads
        )
        self.assertEqual(findings, [])
        self.assertEqual(state["state"], "TERMINAL_BOUND")
        _state, findings = self.module.validate_journal([], False, payloads)
        self.assertIn("JOURNAL_RUN_BINDING_MISMATCH", findings)

        state, findings = self.module.validate_journal(
            full, qualified["runBindingSha256"]
        )
        self.assertIn("JOURNAL_PAYLOAD_EXPECTATION_MISMATCH", findings)
        self.assertNotEqual(state["state"], "TERMINAL_BOUND")

    def test_journal_order_chain_payload_and_type_mutations_fail(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        full = self.full_journal(raw, result, qualified)
        trace_summary, _ = self.module.validate_trace(
            raw, self.module.trace_expectation_from_qualified(qualified)
        )
        payloads = {
            "OBSERVER_ARMED": trace_summary["armReceiptSha256"],
            "EFFECT_INTENT": qualified["proofSubjectSha256"],
            "EFFECT_DISPATCHED": qualified["effectCommandSha256"],
            "DRIVER_OUTCOME_BOUND": hashlib.sha256(
                self.module._canonical_bytes(
                    self.driver_outcome_receipt(result, qualified)
                )
            ).hexdigest(),
            "CAPTURE_CLOSED": hashlib.sha256(raw).hexdigest(),
            "TERMINAL": hashlib.sha256(
                self.module._canonical_bytes(result)
            ).hexdigest(),
        }
        variants = []
        value = copy.deepcopy(full)
        value[2]["event"] = "DRIVER_OUTCOME_BOUND"
        variants.append(value)
        value = copy.deepcopy(full)
        value[1]["previousRecordSha256"] = sha("wrong-prev")
        variants.append(value)
        value = copy.deepcopy(full)
        value[4]["payloadSha256"] = sha("wrong-payload")
        variants.append(value)
        value = copy.deepcopy(full)
        value[0]["sequence"] = False
        variants.append(value)
        value = copy.deepcopy(full)
        value[0]["extra"] = 0
        variants.append(value)
        for value in variants:
            with self.subTest(value=value):
                _state, findings = self.module.validate_journal(
                    value,
                    qualified["runBindingSha256"],
                    payloads,
                )
                self.assertNotEqual(findings, [])

    def test_bound_false_result_requires_trace_and_full_journal(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(
            qualified,
            [
                self.record(10, self.module.TYPE0_ABSENT),
                self.record(11, "wlan0: link up", priority=6),
            ],
        )
        journal = self.full_journal(raw, result, qualified)
        receipt = self.driver_outcome_receipt(result, qualified)
        bound = self.module.build_bound_result(
            raw, result, qualified, receipt, journal
        )
        self.assertEqual(bound["findings"], [])
        self.assertEqual(
            bound["experimentProofOutcome"],
            "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
        )
        self.assertFalse(bound["generationPromotionEligible"])
        self.assertFalse(bound["authority"]["liveExecutionAuthorized"])
        self.assertEqual(
            self.module.validate_bound_result(
                bound, raw, result, qualified, receipt, journal
            ),
            [],
        )

    def test_bound_true_result_uses_unique_failure_signature(self) -> None:
        result = self.base_property_result("TRUE")
        qualified = self.qualified(result)
        raw = self.trace(
            qualified,
            [
                self.record(20, self.module.TYPE0_ABSENT),
                self.record(
                    21,
                    "wlan: [123:E:HDD] hdd_initialize_mac_address: 12245: "
                    + self.module.MAC_TRUE_FAILURE,
                ),
            ],
        )
        journal = self.full_journal(raw, result, qualified)
        bound = self.module.build_bound_result(
            raw,
            result,
            qualified,
            self.driver_outcome_receipt(result, qualified),
            journal,
        )
        self.assertEqual(bound["findings"], [])
        self.assertEqual(
            bound["experimentProofOutcome"],
            "MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
        )

    def test_missing_signature_or_incomplete_journal_is_no_proof(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, "wlan0: link up", priority=6)])
        journal = self.full_journal(raw, result, qualified)
        receipt = self.driver_outcome_receipt(result, qualified)
        bound = self.module.build_bound_result(
            raw, result, qualified, receipt, journal
        )
        self.assertIn("MAC_KMSG_SIGNATURE_MISMATCH", bound["findings"])
        self.assertEqual(bound["experimentProofOutcome"], "NO_PROOF_OBSERVER")
        self.assertEqual(bound["deviceSafetyState"], "RESIDENT_HEALTHY")
        self.assertEqual(bound["workflowState"], "TERMINAL")

        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        journal = self.full_journal(raw, result, qualified)
        bound = self.module.build_bound_result(
            raw, result, qualified, receipt, journal[:-1]
        )
        self.assertEqual(bound["experimentProofOutcome"], "NO_PROOF_OBSERVER")
        self.assertEqual(bound["journal"]["state"], "NO_PROOF_OBSERVER")
        self.assertEqual(bound["deviceSafetyState"], "RECOVERY_REQUIRED")
        self.assertEqual(bound["workflowState"], "RECOVERY_PARKED")

    def test_unbound_driver_receipt_cannot_publish_health(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        journal = self.full_journal(raw, result, qualified)
        receipt = self.driver_outcome_receipt(result, qualified)
        receipt["driverInitEpochSha256"] = sha("wrong-driver-epoch")
        bound = self.module.build_bound_result(
            raw, result, qualified, receipt, journal
        )
        self.assertEqual(bound["experimentProofOutcome"], "NO_PROOF_OBSERVER")
        self.assertEqual(bound["deviceSafetyState"], "RECOVERY_REQUIRED")
        self.assertEqual(bound["workflowState"], "RECOVERY_PARKED")

    def test_forged_bound_result_is_rederived_and_rejected(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        journal = self.full_journal(raw, result, qualified)
        receipt = self.driver_outcome_receipt(result, qualified)
        bound = self.module.build_bound_result(
            raw, result, qualified, receipt, journal
        )
        forged = copy.deepcopy(bound)
        forged["generationPromotionEligible"] = True
        self.assertEqual(
            self.module.validate_bound_result(
                forged, raw, result, qualified, receipt, journal
            ),
            ["BOUND_RESULT_MISMATCH"],
        )

    def test_malformed_types_do_not_escape_validators(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        raw = self.trace(qualified, [self.record(1, self.module.TYPE0_ABSENT)])
        mutations = []
        for key in self.module.TRACE_EXPECTATION_KEYS:
            value = copy.deepcopy(
                self.module.trace_expectation_from_qualified(qualified)
            )
            value[key] = []
            mutations.append(value)
        for value in mutations:
            with self.subTest(value=value):
                _summary, findings = self.module.validate_trace(raw, value)
                self.assertNotEqual(findings, [])
        malformed_journal = [
            {
                "schema": self.module.JOURNAL_RECORD_SCHEMA,
                "sequence": 0,
                "event": [],
                "runBindingSha256": qualified["runBindingSha256"],
                "previousRecordSha256": self.module.ZERO_SHA256,
                "payloadSha256": b"not-json",
            }
        ]
        _state, findings = self.module.validate_journal(
            malformed_journal,
            qualified["runBindingSha256"],
            self.journal_payloads(
                self.full_journal(raw, result, qualified)
            ),
        )
        self.assertNotEqual(findings, [])

    def test_arbitrary_binary_inputs_never_escape_trace_parser(self) -> None:
        result = self.base_property_result()
        qualified = self.qualified(result)
        expectation = self.module.trace_expectation_from_qualified(qualified)
        corpus = [
            bytes(((index * 73) + offset) & 0xFF for offset in range(index))
            for index in range(257)
        ]
        for raw in corpus:
            with self.subTest(length=len(raw)):
                summary, findings = self.module.validate_trace(raw, expectation)
                self.assertIsInstance(summary, dict)
                self.assertIsInstance(findings, list)
                self.assertNotEqual(findings, [])

    @unittest.skipUnless(shutil.which("gcc"), "host C compiler unavailable")
    def test_c_encoder_fixture_matches_python_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "kmsg-fixture"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-DA90_WP2_5B_KMSG_TEST_MAIN",
                    "-I",
                    str(HEADER.parent),
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            raw = subprocess.run([str(binary)], check=True, capture_output=True).stdout
            escaped_raw = subprocess.run(
                [str(binary), "escaped"], check=True, capture_output=True
            ).stdout
        expectation = {
            "runBindingSha256": "11" * 32,
            "qualificationSha256": "22" * 32,
            "observerBinarySha256": "33" * 32,
            "contractSha256": self.module.contract_sha256(),
            "driverInitEpochSha256": "44" * 32,
            "captureCloseBindingSha256": "55" * 32,
            "recordCountCap": 8,
            "recordByteCap": 16384,
        }
        summary, findings = self.module.validate_trace(raw, expectation)
        self.assertEqual(findings, [])
        self.assertEqual(summary["recordCount"], 2)
        self.assertEqual(summary["type0AbsentCount"], 1)
        escaped_summary, escaped_findings = self.module.validate_trace(
            escaped_raw, expectation
        )
        self.assertEqual(escaped_findings, [])
        self.assertEqual(escaped_summary["recordCount"], 1)

    @unittest.skipUnless(shutil.which("gcc"), "host C compiler unavailable")
    def test_c_encoder_fault_fixtures_are_explicit_no_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "kmsg-fixture"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-DA90_WP2_5B_KMSG_TEST_MAIN",
                    "-I",
                    str(HEADER.parent),
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            for mode, count_cap, byte_cap in (
                ("gap", 8, 16384),
                ("malformed", 8, 16384),
                ("raw-backslash", 8, 16384),
                ("blank-dict", 8, 16384),
                ("terminal-empty-dict", 8, 16384),
                ("priority-range", 8, 16384),
                ("short-flag-zero", 8, 16384),
                ("short-flag-one", 8, 16384),
                ("null", 8, 16384),
                ("count-cap", 1, 16384),
                ("byte-cap", 8, 8),
            ):
                with self.subTest(mode=mode):
                    raw = subprocess.run(
                        [str(binary), mode], check=True, capture_output=True
                    ).stdout
                    expectation = {
                        "runBindingSha256": "11" * 32,
                        "qualificationSha256": "22" * 32,
                        "observerBinarySha256": "33" * 32,
                        "contractSha256": self.module.contract_sha256(),
                        "driverInitEpochSha256": "44" * 32,
                        "captureCloseBindingSha256": "55" * 32,
                        "recordCountCap": count_cap,
                        "recordByteCap": byte_cap,
                    }
                    summary, findings = self.module.validate_trace(
                        raw, expectation
                    )
                    self.assertIn("TRACE_REPORTED_FAULT", findings)
                    self.assertEqual(summary["faultCount"], 1)
                    self.assertEqual(summary["outcome"], "NO_PROOF_OBSERVER")

    @unittest.skipUnless(
        shutil.which("aarch64-linux-gnu-gcc"), "AArch64 compiler unavailable"
    )
    def test_c_core_cross_compiles_as_aarch64_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "a90_wp2_5b_kmsg_stream.o"
            subprocess.run(
                [
                    "aarch64-linux-gnu-gcc",
                    "-std=gnu11",
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
                check=True,
            )
            description = subprocess.run(
                ["file", str(output)], check=True, capture_output=True, text=True
            ).stdout
        self.assertIn("ARM aarch64", description)

    @unittest.skipUnless(shutil.which("gcc"), "host C compiler unavailable")
    def test_c_short_and_null_records_are_ubsan_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / "kmsg-ubsan"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=all",
                    "-DA90_WP2_5B_KMSG_TEST_MAIN",
                    "-I",
                    str(HEADER.parent),
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            for mode in ("short-flag-zero", "short-flag-one", "null"):
                with self.subTest(mode=mode):
                    subprocess.run(
                        [str(binary), mode], check=True, capture_output=True
                    )

    def test_c_core_has_no_runtime_open_poll_or_effect_dispatch(self) -> None:
        text = SOURCE.read_text()
        for forbidden in (
            'open("/dev/kmsg"',
            'open("/proc/kmsg"',
            "poll(",
            "ioctl(",
            "system(",
            "execve(",
            "fork(",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("does not open /dev/kmsg", text)

    def test_public_docs_calibrate_partial_completion_and_open_gate(self) -> None:
        report = REPORT.read_text()
        requirement = REQUIREMENT_REPORT.read_text()
        proposal = PROPOSAL.read_text()
        hardening = HARDENING.read_text()
        context = CONTEXT.read_text()
        hardening_json = HARDENING_JSON.read_text()
        for text in (report, requirement, proposal, hardening, context, hardening_json):
            self.assertIn("WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT", text)
            self.assertIn("WP2_5B_KMSG_STREAM_COMPLETENESS", text)
        for text in (report, proposal, hardening, context, hardening_json):
            self.assertIn("WP2-5b.1", text)
        for claim in (
            "trace core complete H0; runtime observer and execution remain absent",
            "effectReplayAllowed` is always false",
            "generationPromotionEligible=false",
            "grants no candidate identity, D0, D1, F1",
            "one accidental S22+ public-source excerpt read",
        ):
            self.assertIn(claim, report)
        self.assertIn("runtime `WP2-5b` remain unimplemented and unauthorized", requirement)
        self.assertIn("durableWriterImplemented", CONTRACT.read_text())


if __name__ == "__main__":
    unittest.main()
