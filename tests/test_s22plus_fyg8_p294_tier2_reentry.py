#!/usr/bin/env python3
"""Focused tests for the exact P2.94 Tier-2 re-entry."""

from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

import s22plus_fyg8_p294_build_repro_check as repro
import s22plus_fyg8_p294_tier2_reentry as reentry


ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p294_pre_lto/qualification.json"
)
BUILD_RESULT = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p294/"
    "full-lto-dd20b502-v1/repro-a/build-result.json"
)


class Tier2ReentryTests(unittest.TestCase):
    def test_full_checker_dispatches_through_reentry(self) -> None:
        repro._configure()  # noqa: SLF001
        self.assertIs(
            repro.base.base.verify_p286_qualification_file,
            repro.verify_p286_qualification_file,
        )
        self.assertIsNot(
            repro._INHERITED_VERIFY_QUALIFICATION,  # noqa: SLF001
            repro.verify_p286_qualification_file,
        )

    def test_actual_frozen_and_current_inputs_pass(self) -> None:
        result = reentry.check(ROOT, QUALIFICATION)
        self.assertEqual(result["verdict"], reentry.VERDICT)
        self.assertEqual(result["implementation_count"], 50)
        self.assertEqual(result["unique_implementation_count"], 49)
        self.assertEqual(
            result["changed_names"],
            [
                "observer",
                "linked_audit",
                "p294_linked_audit",
                "linked_audit_test",
                "observer_test",
                "process_v2_docs_test",
            ],
        )
        self.assertEqual(result["changed_count"], 6)
        self.assertEqual(result["gate_changed_count"], 3)
        self.assertEqual(result["evidence_changed_count"], 3)
        self.assertEqual(result["unchanged_gate_count"], 47)
        self.assertGreater(result["observer_test"]["test_count"], 0)
        self.assertGreater(result["process_v2_docs_test"]["test_count"], 0)

    def test_actual_full_lto_provenance_replays_through_formal_verifier(
        self,
    ) -> None:
        build_result = json.loads(BUILD_RESULT.read_text())
        provenance = build_result["provenance"][
            repro.P294_QUALIFICATION_PROVENANCE_KEY
        ]
        exact_contract = repro.candidate_contract.verify(
            ROOT,
            repro.candidate_contract.DEFAULT_SOURCE,
            repro.candidate_contract.DEFAULT_INTENT,
            repro.candidate_contract.DEFAULT_PATCH,
        )
        verified = repro.verify_p294_qualification_file(
            provenance,
            exact_contract,
            intent_path=repro.candidate_contract.DEFAULT_INTENT,
            patch_path=repro.candidate_contract.DEFAULT_PATCH,
            root=ROOT,
        )
        self.assertEqual(verified, provenance)

    def test_unrecognized_observer_delta_fails(self) -> None:
        frozen = reentry._git_blob(  # noqa: SLF001
            ROOT, reentry.FROZEN_COMMIT, reentry.OBSERVER_PATH
        )
        changed = reentry._expected_current_observer(frozen) + b"# drift\n"  # noqa: SLF001
        original = reentry._stable_read  # noqa: SLF001
        with mock.patch.object(
            reentry,
            "_stable_read",
        ) as stable_read:
            def replacement(path: Path, label: str, limit: int) -> bytes:
                if label == "P2.94 current observer":
                    return changed
                return original(path, label, limit)

            stable_read.side_effect = replacement
            with self.assertRaisesRegex(
                reentry.ReentryError, "current observer delta differs"
            ):
                reentry.check(ROOT, QUALIFICATION)

    def test_changed_frozen_gate_fails(self) -> None:
        qualification = json.loads(QUALIFICATION.read_text())
        frozen = qualification["gate_implementation"]["p294_decoder"]
        frozen["sha256"] = "00" * 32
        payload = json.dumps(qualification, sort_keys=True).encode("ascii")
        original = reentry._stable_read  # noqa: SLF001
        with mock.patch.object(
            reentry,
            "_stable_read",
        ) as stable_read:
            def replacement(path: Path, label: str, limit: int) -> bytes:
                if label == "P2.94 frozen qualification":
                    return payload
                return original(path, label, limit)

            stable_read.side_effect = replacement
            with self.assertRaisesRegex(
                reentry.ReentryError, "frozen qualification receipt differs"
            ):
                reentry.check(ROOT, QUALIFICATION)


if __name__ == "__main__":
    unittest.main()
