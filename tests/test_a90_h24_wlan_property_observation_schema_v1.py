"""Validate the host-only A90 WP2-4 property observation contract."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "a90_h24_wlan_property_observation_schema_v1.py"
)
SCHEMA = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "schema/a90-h24-wlan-property-observation-schema-v1.json"
)
PROPOSAL = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "proposals/wlan-vendor-property-ablation.md"
)
HARDENING = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "hardening.md"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_wp2_4_schema", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load WP2-4 schema generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class A90H24WlanPropertyObservationSchemaV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_generator()
        cls.data = json.loads(SCHEMA.read_text())

    def base_result(self, terminal: str) -> dict:
        roles = ["cnss_daemon"]
        events = []
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
            "schema": self.module.RESULT_SCHEMA,
            "terminal": terminal,
            "bindings": {
                "target": "Samsung Galaxy A90 5G",
                "residentBuild": "future-exact-resident",
                "candidateSha256": sha("candidate"),
                "parentGenerationSha256": sha("parent"),
                "componentManifestSha256": sha("manifest"),
                "bootIdSha256": sha("boot"),
                "runNonce": "future-run-nonce",
                "observerSha256": sha("observer"),
                "observationBudgetSha256": "",
                "qualificationSha256": sha("qualified-generation"),
                "traceSha256": self.module._event_digest(events),
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
                for phase in self.module.PHASES
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
                "traceBytes": len(self.module._event_bytes(events)),
                "traceByteCap": 65536,
            },
            "seedEntries": [],
            "seedFilesystem": {
                "state": "ABSENT",
                "rootPath": None,
                "rootReadOnly": None,
                "memberNames": [],
                "memberSetSha256": self.module._member_digest([]),
                "unexpectedMembers": [],
                "symlinkCount": 0,
                "hardlinkAliasCount": 0,
                "specialFileCount": 0,
                "generationMatches": True,
                "digestStable": True,
            },
            "macProvisioningEffect": {
                "sameBoot": False,
                "sameRun": False,
                "sourceIdentityBound": False,
                "driverIdentityBound": False,
                "debugfsIdentityBound": False,
                "readComplete": False,
                "cnssUtilsMacState": "UNREADABLE_OR_MALFORMED",
                "wlanOutcome": "OTHER_OR_UNPROVED",
                "decision": "NO_PROOF_OBSERVER",
            },
            "deviceSafetyState": "RESIDENT_HEALTHY",
            "experimentProof": "PROVED",
            "workflowState": "TERMINAL",
        }
        result["bindings"]["observationBudgetSha256"] = (
            self.module._observation_budget_digest(
                result["trace"]["eventCountCap"],
                result["trace"]["traceByteCap"],
            )
        )
        return result

    def qualified_expectation(self, result: dict) -> dict:
        return {
            "bindingProjection": {
                key: copy.deepcopy(result["bindings"][key])
                for key in self.module.QUALIFIED_BINDING_KEYS
            },
            "expectedRoles": copy.deepcopy(result["expectedRoles"]),
            "coldRelaunchRoles": copy.deepcopy(result["coldRelaunchRoles"]),
            "persistentAcrossRelaunchRoles": copy.deepcopy(
                result["persistentAcrossRelaunchRoles"]
            ),
            "eventCountCap": result["trace"]["eventCountCap"],
            "seedContractSha256": self.module._seed_contract_digest(result),
            "traceByteCap": result["trace"]["traceByteCap"],
        }

    def validate_absent(self, result: dict, expected_from: dict | None = None) -> list[str]:
        return self.module.validate_property_absent_result(
            result, self.qualified_expectation(expected_from or result)
        )

    def validate_finite(self, result: dict, expected_from: dict | None = None) -> list[str]:
        return self.module.validate_property_finite_seed_result(
            result, self.qualified_expectation(expected_from or result)
        )

    def bind_events(self, result: dict, events: list[dict]) -> None:
        result["events"] = events
        result["bindings"]["traceSha256"] = self.module._event_digest(events)
        result["trace"].update(
            declaredEventCount=len(events),
            firstSequence=0 if events else -1,
            lastSequence=len(events) - 1,
            fabricatedDefaultEvents=sum(
                isinstance(event, dict) and event.get("returnedDefault") is True
                for event in events
            ),
            traceBytes=len(self.module._event_bytes(events)),
        )

    def add_persistent_wifi_helper(self, result: dict) -> None:
        result["expectedRoles"] = ["cnss_daemon", "wifi-helper"]
        result["persistentAcrossRelaunchRoles"] = ["wifi-helper"]
        result["processInstances"].append(
            {
                "instanceId": "wifi-helper-initial",
                "role": "wifi-helper",
                "launchEpoch": "INITIAL",
                "pid": 200,
                "starttime": 2000,
                "executableSha256": sha("wifi-helper-executable"),
                "identitySha256": sha("wifi-helper-identity"),
                "launchReceiptSha256": sha("wifi-helper-launch"),
                "exitReceiptSha256": sha("wifi-helper-exit"),
                "lifecycleClosure": "EXITED_REAPED_BOUND",
            }
        )
        result["coverage"].extend(
            {
                "role": "wifi-helper",
                "phase": phase,
                "state": "RUNNING_OBSERVED",
                "observerComplete": True,
                "startBoundaryProved": True,
                "endBoundaryProved": True,
                "eventLossCount": 0,
                "processInstanceIds": ["wifi-helper-initial"],
            }
            for phase in self.module.PHASES
        )

    def finite_result(self) -> dict:
        result = self.base_result("PROPERTY_FINITE_SEED_PROVED")
        entry = {
            "seedId": "seed-01",
            "key": "ro.vendor.example",
            "context": "u:object_r:vendor_default_prop:s0",
            "valueBytes": 7,
            "valueSha256": sha("enabled"),
            "sourcePath": "/run/a90-property-seed/seed-01",
            "sourceBytes": 96,
            "sourceSha256": sha("seed-file"),
            "sourceMode": "0444",
            "sourceUid": 1000,
            "sourceGid": 1000,
            "sourceNlink": 1,
            "sourceKind": "REGULAR",
            "sourceReadOnlyLifetime": "BEFORE_FIRST_READER_THROUGH_FINAL_READER",
            "readers": ["cnss_daemon"],
        }
        event = {
            "sequence": 0,
            "role": "cnss_daemon",
            "phase": "CLEAN_LAUNCH",
            "processInstanceId": "cnss-daemon-initial",
            "operation": "READ",
            "requestId": "request-0001",
            "key": entry["key"],
            "context": entry["context"],
            "sourceId": entry["seedId"],
            "result": "SUCCESS",
            "errno": 0,
            "returnedDefault": False,
            "valueBytes": entry["valueBytes"],
            "valueSha256": entry["valueSha256"],
        }
        result["events"] = [event]
        result["bindings"]["traceSha256"] = self.module._event_digest([event])
        result["trace"].update(
            declaredEventCount=1,
            firstSequence=0,
            lastSequence=0,
            traceBytes=len(self.module._event_bytes([event])),
        )
        result["seedEntries"] = [entry]
        names = ["seed-01"]
        result["seedFilesystem"] = {
            "state": "PRESENT_EXACT",
            "rootPath": "/run/a90-property-seed",
            "rootReadOnly": True,
            "memberNames": names,
            "memberSetSha256": self.module._member_digest(names),
            "unexpectedMembers": [],
            "symlinkCount": 0,
            "hardlinkAliasCount": 0,
            "specialFileCount": 0,
            "generationMatches": True,
            "digestStable": True,
        }
        return result

    def test_generated_schema_is_canonical_current_and_valid(self) -> None:
        self.assertEqual(SCHEMA.read_text(), self.module.canonical_text())
        self.assertEqual(self.module.validate_schema(self.data), [])
        self.assertEqual(len(self.data["sourcePins"]), 5)
        for pin in self.data["sourcePins"]:
            raw = (ROOT / pin["path"]).read_bytes()
            self.assertEqual(len(raw), pin["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), pin["sha256"])

    def test_wp2_4_is_h0_only_and_retires_no_gate(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key != "tier":
                self.assertIs(value, False, key)
        status = self.data["status"]
        self.assertEqual(
            status["wp2_4"],
            "COMPLETE_H0_PROPERTY_OBSERVATION_SCHEMA_AND_TERMINAL_VALIDATORS_ONLY",
        )
        self.assertEqual(status["runtimeObserverImplementation"], "ABSENT")
        self.assertEqual(status["byteDerivedConsumer"], "ABSENT")
        self.assertEqual(status["h0d04"], "UNPROVED")
        self.assertEqual(status["h0d10"], "UNPROVED")
        self.assertEqual(status["dependencyGatesRetired"], [])
        self.assertEqual(status["optionC"], "BLOCKED_RESEARCH_ONLY")

    def test_phase_and_role_coverage_is_cartesian_and_fail_closed(self) -> None:
        self.assertEqual(len(self.data["observationPhases"]), 8)
        self.assertEqual(
            self.data["scope"]["parentRoleVocabulary"],
            [
                "servicemanager",
                "hwservicemanager",
                "qrtr_ns",
                "pd_mapper",
                "rmt_storage",
                "tftp_server",
                "vndservicemanager",
                "pm_proxy_helper",
                "per_mgr",
                "cnss_diag",
                "cnss_daemon",
                "property-service-shim",
                "modem-holder",
                "wifi-helper",
            ],
        )
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"].pop()
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        for row in value["coverage"]:
            row["state"] = "PROVED_NOT_RUNNING"
            row["processInstanceIds"] = []
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["processInstances"].pop()
        self.assertIn(
            "PROCESS_IDENTITY_MISMATCH",
            self.validate_absent(value),
        )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["processInstances"].reverse()
        self.assertIn("PROCESS_IDENTITY_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"].reverse()
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

    def test_relaunch_lifecycle_partition_is_exact_and_supports_persistent_supervisor(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        self.add_persistent_wifi_helper(value)
        self.assertEqual(self.validate_absent(value), [])

        changed = copy.deepcopy(value)
        changed["persistentAcrossRelaunchRoles"] = []
        self.assertIn(
            "PROCESS_IDENTITY_MISMATCH",
            self.validate_absent(changed),
        )

        changed = copy.deepcopy(value)
        changed["processInstances"][-1]["pid"] = changed["processInstances"][0]["pid"]
        changed["processInstances"][-1]["starttime"] = changed["processInstances"][0]["starttime"]
        self.assertIn(
            "PROCESS_IDENTITY_MISMATCH",
            self.validate_absent(changed),
        )

    def test_result_cannot_self_nominate_a_generation_or_role_vocabulary(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        self.assertIn(
            "QUALIFIED_EXPECTATION_MISSING",
            self.module.validate_property_absent_result(value),
        )

        expected = self.qualified_expectation(value)
        value["expectedRoles"] = ["forged-role"]
        value["coldRelaunchRoles"] = ["forged-role"]
        for instance in value["processInstances"]:
            instance["role"] = "forged-role"
        for row in value["coverage"]:
            row["role"] = "forged-role"
        findings = self.module.validate_property_absent_result(value, expected)
        self.assertIn("QUALIFIED_EXPECTATION_MISMATCH", findings)
        self.assertIn("ROLE_VOCABULARY_MISMATCH", findings)

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        expected = self.qualified_expectation(value)
        value["trace"]["eventCountCap"] += 1
        self.assertIn(
            "QUALIFIED_EXPECTATION_MISMATCH",
            self.module.validate_property_absent_result(value, expected),
        )

    def test_budget_digest_is_derived_from_exact_qualified_caps(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        self.assertEqual(self.validate_absent(value), [])

        value["bindings"]["observationBudgetSha256"] = sha("forged-budget")
        self.assertIn(
            "QUALIFIED_EXPECTATION_MISMATCH",
            self.validate_absent(value),
        )

    def test_integer_fields_reject_boolean_substitution(self) -> None:
        mutations = []

        value = self.finite_result()
        value["events"][0]["sequence"] = False
        value["trace"]["firstSequence"] = False
        value["trace"]["lastSequence"] = False
        value["trace"]["declaredEventCount"] = True
        value["bindings"]["traceSha256"] = self.module._event_digest(value["events"])
        mutations.append((value, self.validate_finite, "EVENT_SCHEMA_MISMATCH"))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"][0]["eventLossCount"] = False
        mutations.append((value, self.validate_absent, "COVERAGE_MISMATCH"))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["trace"]["droppedEvents"] = False
        value["trace"]["fabricatedDefaultEvents"] = False
        value["trace"]["traceBytes"] = False
        mutations.append((value, self.validate_absent, "OBSERVER_INCOMPLETE"))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["seedFilesystem"]["symlinkCount"] = False
        mutations.append((value, self.validate_absent, "SEED_SCHEMA_MISMATCH"))

        for value, validator, expected in mutations:
            with self.subTest(expected=expected):
                self.assertIn(expected, validator(value))

    def test_unhashable_process_instance_ids_are_rejected_without_exception(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"][0]["processInstanceIds"] = [{}]
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

    def test_unhashable_nested_identity_fields_are_rejected_without_exception(self) -> None:
        mutations = []

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["processInstances"][0]["launchEpoch"] = {}
        mutations.append((value, self.validate_absent, "PROCESS_IDENTITY_MISMATCH"))

        for key in ("processInstanceId", "sourceId", "result"):
            value = self.finite_result()
            value["events"][0][key] = {}
            mutations.append((value, self.validate_finite, "EVENT_SCHEMA_MISMATCH"))

        for value, validator, expected in mutations:
            with self.subTest(expected=expected):
                self.assertIn(expected, validator(value))

    def test_every_declared_launch_epoch_is_observed_running(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        for row in value["coverage"]:
            if row["phase"] != "COLD_RELAUNCH":
                row["state"] = "PROVED_NOT_RUNNING"
                row["processInstanceIds"] = []
        self.assertIn("PROCESS_IDENTITY_MISMATCH", self.validate_absent(value))

    def test_mac_binding_fields_require_exact_booleans(self) -> None:
        boolean_keys = (
            "sameBoot",
            "sameRun",
            "sourceIdentityBound",
            "driverIdentityBound",
            "debugfsIdentityBound",
            "readComplete",
        )
        for key in boolean_keys:
            value = self.base_result("PROPERTY_ABSENT_PROVED")
            value["macProvisioningEffect"][key] = 0
            with self.subTest(key=key):
                self.assertIn("MAC_EFFECT_MISMATCH", self.validate_absent(value))

    def test_absent_terminal_accepts_only_complete_zero_read_evidence(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        self.assertEqual(self.validate_absent(value), [])

        read = self.finite_result()["events"][0]
        value["events"] = [read]
        value["bindings"]["traceSha256"] = self.module._event_digest([read])
        value["trace"].update(declaredEventCount=1, firstSequence=0, lastSequence=0)
        value["trace"]["traceBytes"] = len(self.module._event_bytes([read]))
        self.assertIn(
            "SUCCESSFUL_READ_PRESENT",
            self.validate_absent(value),
        )

    def test_finite_seed_terminal_maps_every_read_and_uses_every_entry(self) -> None:
        value = self.finite_result()
        self.assertEqual(self.validate_finite(value), [])

        changed = copy.deepcopy(value)
        changed["events"][0]["valueSha256"] = sha("drift")
        changed["bindings"]["traceSha256"] = self.module._event_digest(changed["events"])
        self.assertIn(
            "SEED_READ_MAPPING_MISMATCH",
            self.validate_finite(changed),
        )

        changed = self.finite_result()
        self.add_persistent_wifi_helper(changed)
        changed["seedEntries"][0]["readers"].append("wifi-helper")
        self.assertIn(
            "SEED_READ_MAPPING_MISMATCH",
            self.validate_finite(changed),
        )

        changed = copy.deepcopy(value)
        extra = copy.deepcopy(changed["seedEntries"][0])
        extra.update(
            seedId="seed-02",
            key="ro.vendor.unused",
            sourcePath="/run/a90-property-seed/seed-02",
        )
        changed["seedEntries"].append(extra)
        names = ["seed-01", "seed-02"]
        changed["seedFilesystem"]["memberNames"] = names
        changed["seedFilesystem"]["memberSetSha256"] = self.module._member_digest(names)
        self.assertIn(
            "SEED_READ_MAPPING_MISMATCH",
            self.validate_finite(changed),
        )

    def test_seed_filesystem_rejects_writable_links_specials_and_extras(self) -> None:
        mutations = (
            ("sourceMode", "0644"),
            ("sourceNlink", 2),
            ("sourceNlink", True),
            ("sourceBytes", 0),
            ("sourceUid", -1),
            ("sourcePath", "/run/a90-property-seed/./seed-01"),
        )
        for key, bad in mutations:
            with self.subTest(key=key):
                value = self.finite_result()
                value["seedEntries"][0][key] = bad
                self.assertIn(
                    "SEED_SCHEMA_MISMATCH",
                    self.validate_finite(value),
                )
        for key in ("symlinkCount", "hardlinkAliasCount", "specialFileCount"):
            with self.subTest(key=key):
                value = self.finite_result()
                value["seedFilesystem"][key] = 1
                self.assertIn(
                    "SEED_SCHEMA_MISMATCH",
                    self.validate_finite(value),
                )
        value = self.finite_result()
        value["seedFilesystem"]["unexpectedMembers"] = ["extra"]
        self.assertIn(
            "SEED_SCHEMA_MISMATCH",
            self.validate_finite(value),
        )

        value = self.finite_result()
        value["seedFilesystem"]["rootPath"] = "/run/./a90-property-seed"
        self.assertIn("SEED_SCHEMA_MISMATCH", self.validate_finite(value))

        value = self.finite_result()
        expected = self.qualified_expectation(value)
        value["seedEntries"][0]["sourceSha256"] = sha("changed-seed-file")
        self.assertIn(
            "QUALIFIED_EXPECTATION_MISMATCH",
            self.module.validate_property_finite_seed_result(value, expected),
        )

    def test_observer_failure_never_becomes_absence(self) -> None:
        for mutate in (
            lambda value: value["trace"].update(droppedEvents=1),
            lambda value: value["trace"].update(fabricatedDefaultEvents=1),
            lambda value: value["trace"].update(mixedRun=True),
            lambda value: value["trace"].update(truncated=True),
        ):
            value = self.base_result("PROPERTY_ABSENT_PROVED")
            mutate(value)
            self.assertIn(
                "OBSERVER_INCOMPLETE",
                self.validate_absent(value),
            )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        event = self.finite_result()["events"][0]
        event.update(result="MISSING", errno=2, returnedDefault=True)
        value["events"] = [event]
        value["bindings"]["traceSha256"] = self.module._event_digest([event])
        value["trace"].update(
            declaredEventCount=1,
            firstSequence=0,
            lastSequence=0,
            fabricatedDefaultEvents=1,
            traceBytes=len(self.module._event_bytes([event])),
        )
        self.assertIn(
            "OBSERVER_INCOMPLETE",
            self.validate_absent(value),
        )

    def test_read_error_or_denial_never_becomes_a_property_terminal(self) -> None:
        for result, errno in (("ERROR", 5), ("DENIED", 13)):
            with self.subTest(result=result):
                value = self.base_result("PROPERTY_ABSENT_PROVED")
                event = copy.deepcopy(self.finite_result()["events"][0])
                event.update(
                    result=result,
                    errno=errno,
                    valueBytes=0,
                    valueSha256=sha(""),
                )
                self.bind_events(value, [event])
                self.assertIn("READ_OUTCOME_INCOMPLETE", self.validate_absent(value))

                event["valueBytes"] = 1
                event["valueSha256"] = sha("x")
                self.bind_events(value, [event])
                self.assertIn("EVENT_SCHEMA_MISMATCH", self.validate_absent(value))

        value = self.finite_result()
        event = copy.deepcopy(value["events"][0])
        event.update(
            sequence=1,
            requestId="request-error",
            result="ERROR",
            errno=5,
            valueBytes=0,
            valueSha256=sha(""),
        )
        self.bind_events(value, [value["events"][0], event])
        self.assertIn("READ_OUTCOME_INCOMPLETE", self.validate_finite(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        event = copy.deepcopy(self.finite_result()["events"][0])
        event.update(result="MISSING", errno=2, valueBytes=0, valueSha256=sha(""))
        self.bind_events(value, [event])
        self.assertEqual(self.validate_absent(value), [])

    def test_event_phases_are_monotonic(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        late = copy.deepcopy(self.finite_result()["events"][0])
        late.update(
            sequence=0,
            phase="COLD_RELAUNCH",
            processInstanceId="cnss-daemon-cold_relaunch",
            requestId="missing-late",
            result="MISSING",
            errno=2,
            valueBytes=0,
            valueSha256=sha(""),
        )
        early = copy.deepcopy(late)
        early.update(
            sequence=1,
            phase="CLEAN_LAUNCH",
            processInstanceId="cnss-daemon-initial",
            requestId="missing-early",
        )
        self.bind_events(value, [late, early])
        self.assertIn("EVENT_PHASE_ORDER_MISMATCH", self.validate_absent(value))

    def test_event_and_coverage_semantics_reject_internal_contradictions(self) -> None:
        value = self.finite_result()
        value["events"][0]["errno"] = 5
        value["bindings"]["traceSha256"] = self.module._event_digest(value["events"])
        self.assertIn(
            "EVENT_SCHEMA_MISMATCH",
            self.validate_finite(value),
        )

        value = self.finite_result()
        value["coverage"][0]["state"] = "PROVED_NOT_RUNNING"
        self.assertIn(
            "COVERAGE_MISMATCH",
            self.validate_finite(value),
        )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"] = None
        self.assertIn(
            "COVERAGE_MISMATCH",
            self.validate_absent(value),
        )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        self.bind_events(value, [None])
        self.assertIn("EVENT_SCHEMA_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        event = copy.deepcopy(self.finite_result()["events"][0])
        event["requestId"] = []
        self.bind_events(value, [event])
        self.assertIn("EVENT_SCHEMA_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["expectedRoles"] = [{}]
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"][0]["role"] = []
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["coverage"][0]["state"] = []
        self.assertIn("COVERAGE_MISMATCH", self.validate_absent(value))

        value = self.finite_result()
        value["seedEntries"][0]["readers"] = [{}]
        self.assertIn("SEED_SCHEMA_MISMATCH", self.validate_finite(value))

        value = self.finite_result()
        value["seedEntries"][0]["sourceMode"] = []
        self.assertIn("SEED_SCHEMA_MISMATCH", self.validate_finite(value))

    def test_write_ack_pairs_are_exact_and_never_become_read_proof(self) -> None:
        value = self.base_result("PROPERTY_ABSENT_PROVED")
        common = {
            "role": "cnss_daemon",
            "phase": "CLEAN_LAUNCH",
            "processInstanceId": "cnss-daemon-initial",
            "requestId": "write-0001",
            "key": "ctl.stop",
            "context": "u:object_r:ctl_default_prop:s0",
            "sourceId": "write-only-compat",
            "result": "SUCCESS",
            "errno": 0,
            "returnedDefault": False,
            "valueBytes": 18,
            "valueSha256": sha("vendor.rmt_storage"),
        }
        write = {"sequence": 0, "operation": "WRITE", **common}
        ack = {"sequence": 1, "operation": "ACK", **common}
        value["events"] = [write, ack]
        value["bindings"]["traceSha256"] = self.module._event_digest(value["events"])
        value["trace"].update(
            declaredEventCount=2,
            firstSequence=0,
            lastSequence=1,
            traceBytes=len(self.module._event_bytes(value["events"])),
        )
        self.assertEqual(self.validate_absent(value), [])

        missing = copy.deepcopy(value)
        missing["events"].pop()
        missing["bindings"]["traceSha256"] = self.module._event_digest(missing["events"])
        missing["trace"].update(
            declaredEventCount=1,
            lastSequence=0,
            traceBytes=len(self.module._event_bytes(missing["events"])),
        )
        self.assertIn(
            "WRITE_ACK_MISMATCH",
            self.validate_absent(missing),
        )

        drifted = copy.deepcopy(value)
        drifted["events"][1]["valueSha256"] = sha("different")
        drifted["bindings"]["traceSha256"] = self.module._event_digest(drifted["events"])
        drifted["trace"]["traceBytes"] = len(self.module._event_bytes(drifted["events"]))
        self.assertIn(
            "WRITE_ACK_MISMATCH",
            self.validate_absent(drifted),
        )

        cross_lifecycle = copy.deepcopy(value)
        cross_lifecycle["events"][1].update(
            phase="COLD_RELAUNCH",
            processInstanceId="cnss-daemon-cold_relaunch",
        )
        self.bind_events(cross_lifecycle, cross_lifecycle["events"])
        self.assertIn(
            "WRITE_ACK_MISMATCH",
            self.validate_absent(cross_lifecycle),
        )

        cross_identity = self.base_result("PROPERTY_ABSENT_PROVED")
        self.add_persistent_wifi_helper(cross_identity)
        write = copy.deepcopy(value["events"][0])
        ack = copy.deepcopy(value["events"][1])
        write.update(
            phase="COLD_RELAUNCH",
            processInstanceId="cnss-daemon-cold_relaunch",
        )
        ack.update(
            phase="COLD_RELAUNCH",
            role="wifi-helper",
            processInstanceId="wifi-helper-initial",
        )
        self.bind_events(cross_identity, [write, ack])
        self.assertIn(
            "WRITE_ACK_MISMATCH",
            self.validate_absent(cross_identity),
        )

    def test_property_terminal_requires_exact_final_resident_health(self) -> None:
        for key, bad in (
            ("deviceSafetyState", "RECOVERY_REQUIRED"),
            ("experimentProof", "NO_PROOF_OBSERVER"),
            ("workflowState", "RECOVERY_PARKED"),
        ):
            with self.subTest(key=key):
                value = self.base_result("PROPERTY_ABSENT_PROVED")
                value[key] = bad
                self.assertIn(
                    "SAFETY_PROOF_MISMATCH",
                    self.validate_absent(value),
                )

    def test_mac_effect_table_is_total_and_scoped_to_one_exact_run(self) -> None:
        table = self.data["macProvisioningEffectObservation"]["decisionTable"]
        self.assertEqual(len(table), 18)
        self.assertEqual(
            self.module.classify_mac_effect(
                "ABSENT_PARSED", "WLAN0_UP_EXACT_DRIVER", True
            ),
            "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
        )
        self.assertEqual(
            self.module.classify_mac_effect(
                "ABSENT_PARSED", "MAC_INIT_FAILED_EXACT_SIGNATURE", True
            ),
            "MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
        )
        self.assertEqual(
            self.module.classify_mac_effect(
                "PRESENT_VALID", "WLAN0_UP_EXACT_DRIVER", True
            ),
            "MAC_PROVISION_VALUE_UNRESOLVED",
        )
        self.assertEqual(
            self.module.classify_mac_effect(
                "ABSENT_PARSED", "WLAN0_UP_EXACT_DRIVER", False
            ),
            "NO_PROOF_OBSERVER",
        )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["macProvisioningEffect"].update(
            cnssUtilsMacState="ABSENT_PARSED",
            wlanOutcome="WLAN0_UP_EXACT_DRIVER",
            decision="MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
        )
        self.assertIn(
            "MAC_EFFECT_MISMATCH",
            self.validate_absent(value),
        )

        value = self.base_result("PROPERTY_ABSENT_PROVED")
        value["macProvisioningEffect"]["cnssUtilsMacState"] = "UNKNOWN"
        self.assertIn(
            "MAC_EFFECT_MISMATCH",
            self.validate_absent(value),
        )

    def test_finite_seed_reader_and_root_are_exactly_bounded(self) -> None:
        value = self.finite_result()
        value["seedEntries"][0]["readers"].append("unknown-role")
        self.assertIn(
            "SEED_SCHEMA_MISMATCH",
            self.validate_finite(value),
        )

        value = self.finite_result()
        value["seedEntries"][0]["sourcePath"] = "/other-root/seed-01"
        self.assertIn(
            "SEED_SCHEMA_MISMATCH",
            self.validate_finite(value),
        )

    def test_global_kernel_objects_require_individual_controls(self) -> None:
        rule = self.data["globalKernelObjectRule"]
        self.assertEqual(rule["unknownScope"], "NO_GO")
        self.assertIn("never evidence", rule["default"])
        self.assertEqual(len(rule["cases"]), 3)
        text = json.dumps(rule, sort_keys=True)
        for token in (
            "AF_QIPCRTR",
            "compat socketcall",
            "Non-relaxable coupled invariant",
            "SELinux",
            "proc magic links",
            "Fresh nested PID namespace",
        ):
            self.assertIn(token, text)

    def test_schema_mutations_fail_closed_without_smuggling_authority(self) -> None:
        mutations = []

        value = copy.deepcopy(self.data)
        value["authority"]["liveExecutionAuthorized"] = True
        mutations.append((value, "AUTHORITY_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["status"]["dependencyGatesRetired"] = ["H0D04"]
        mutations.append((value, "STATUS_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["globalKernelObjectRule"]["unknownScope"] = "ASSUME_NAMESPACE_PRIVATE"
        mutations.append((value, "PINNED_SEMANTIC_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["extra"] = True
        mutations.append((value, "TOP_LEVEL_SCHEMA_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["status"] = []
        mutations.append((value, "STATUS_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["macProvisioningEffectObservation"] = []
        mutations.append((value, "MAC_DECISION_TABLE_MISMATCH"))

        for value, expected in mutations:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.module.validate_schema(value))

    def test_public_docs_bind_wp2_4_without_live_authority(self) -> None:
        proposal = PROPOSAL.read_text()
        hardening = HARDENING.read_text()
        for text in (proposal, hardening):
            self.assertIn("a90-h24-wlan-property-observation-schema-v1.json", text)
            self.assertIn("Namespace membership is never", text)
            self.assertIn("AF_QIPCRTR", text)
            self.assertIn("NO_PROOF_OBSERVER", text)
            self.assertIn("no D0", text)
            self.assertIn("H0D04", text)
            self.assertIn("H0D10", text)
            self.assertIn("separately qualified", text)
            self.assertIn("READ `ERROR`", text)


if __name__ == "__main__":
    unittest.main()
