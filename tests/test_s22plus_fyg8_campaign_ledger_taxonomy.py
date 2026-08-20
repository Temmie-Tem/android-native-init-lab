from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_campaign_ledger_taxonomy.py"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
REPORT = ROOT / (
    "docs/reports/S22PLUS_FYG8_CAMPAIGN_LEDGER_TAXONOMY_H0_2026-08-15.md"
)
RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/"
    "ledger-taxonomy-20260817-p318-correction-v3.json"
)
V2_PREDECESSOR_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/"
    "ledger-taxonomy-20260815-01.json"
)
V1_PREDECESSOR_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/"
    "ledger-taxonomy-20260815-01-v1-approved.json"
)
PREDECESSOR_MARKER = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P318_LEDGER_TAXONOMY_V1_PREDECESSOR_PROVENANCE.json"
)


def load_auditor():
    spec = importlib.util.spec_from_file_location("p318_ledger_taxonomy", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load taxonomy auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(data: bytes, old: bytes, new: bytes) -> bytes:
    if data.count(old) != 1:
        raise AssertionError(f"mutation source count is {data.count(old)}, expected 1")
    return data.replace(old, new, 1)


class CampaignLedgerTaxonomyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auditor = load_auditor()
        cls.ledger_data = LEDGER.read_bytes()
        cls.script_data = SCRIPT.read_bytes()
        cls.receipt_data = RECEIPT.read_bytes()
        cls.receipt = json.loads(cls.receipt_data)

    def test_private_receipt_is_exact_deterministic_regeneration(self):
        regenerated = self.auditor.build_receipt(LEDGER)
        self.assertEqual(self.auditor.encode_receipt(regenerated), self.receipt_data)
        self.assertEqual(
            hashlib.sha256(self.receipt_data).hexdigest(),
            "a3ff5130179e7a0713d29d0f5200f7b49b1160f7a2ba647f4ca8ec65ab4c4166",
        )
        self.assertEqual(len(self.receipt_data), 28383)
        self.assertEqual(
            self.receipt["verdict"],
            "PASS_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_V3",
        )
        self.assertEqual(
            self.receipt["schema"], "s22plus-fyg8-campaign-ledger-taxonomy-v3"
        )
        self.assertEqual(self.receipt["derivation_version"], 3)
        self.assertEqual(self.receipt["status"], "IMPLEMENTED_REVIEW_PENDING")

    def test_approved_v1_predecessor_receipt_and_marker_are_preserved(self):
        predecessor = V1_PREDECESSOR_RECEIPT.read_bytes()
        self.assertEqual(len(predecessor), 10118)
        self.assertEqual(
            hashlib.sha256(predecessor).hexdigest(),
            "4214ea5393ed2ec9f1bdef2357e711494050d483cf39b18c46fc9324bf94a153",
        )
        marker = json.loads(PREDECESSOR_MARKER.read_bytes())
        self.assertEqual(
            marker["status"], "HISTORICAL_APPROVED_PREDECESSOR_NOT_CURRENT"
        )
        self.assertTrue(marker["predecessor"]["receipt"]["bytes_preserved"])
        self.assertFalse(marker["predecessor"]["auditor"]["bytes_preserved"])
        self.assertFalse(
            marker["reproducibility"][
                "predecessor_reproducible_from_current_header_and_auditor"
            ]
        )
        self.assertEqual(
            marker["current_successor"]["receipt"]["sha256"],
            hashlib.sha256(V2_PREDECESSOR_RECEIPT.read_bytes()).hexdigest(),
        )

    def test_approved_v2_predecessor_receipt_is_preserved(self):
        predecessor = V2_PREDECESSOR_RECEIPT.read_bytes()
        self.assertEqual(len(predecessor), 23314)
        self.assertEqual(
            hashlib.sha256(predecessor).hexdigest(),
            "6541ed535aec06337094cae98f9b07a91c37e13528a619bdeb4811fc870da026",
        )

    def test_historical_prefix_is_byte_pinned(self):
        authority = self.receipt["authority"]["historical_log_prefix"]
        self.assertEqual(
            authority,
            {
                "row_count": 181,
                "size": 103274,
                "sha256": (
                    "3c0cca0feea9259a0107cc9c9bfa021579707595afa15b6bf9371529f1fe06e1"
                ),
            },
        )
        mutated = replace_once(
            self.ledger_data,
            b"nested-bytes JSON serialization incident",
            b"nested-byte JSON serialization incident",
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "historical append-only log bytes changed"
        ):
            self.auditor.audit_ledger_bytes(mutated, self.script_data)

    def test_only_campaign_proof_corrections_change_metrics(self):
        corrections = self.receipt["correction_registry"]
        self.assertEqual(len(corrections), 3)
        self.assertEqual(corrections[0]["scope"], "CAMPAIGN_PROOF")
        self.assertEqual(corrections[0]["metric_effect"], "APPLY_TO_METRICS")
        self.assertEqual(corrections[1]["scope"], "SUBRESULT_ONLY")
        self.assertEqual(
            corrections[1]["metric_effect"], "EXCLUDE_FROM_CAMPAIGN_METRICS"
        )
        self.assertEqual(corrections[2]["scope"], "CAMPAIGN_PROOF")
        self.assertEqual(corrections[2]["original_campaign"], "s22plus-fyg8-p318")
        self.assertEqual(corrections[2]["metric_effect"], "APPLY_TO_METRICS")
        mutated = replace_once(
            self.ledger_data,
            (
                b"h0-design-1 | CAMPAIGN_PROOF | experiment | "
                b"NO_PROOF_EXPERIMENT_PRECONDITION | APPLY_TO_METRICS"
            ),
            (
                b"h0-design-1 | SUBRESULT_ONLY | experiment | "
                b"NO_PROOF_EXPERIMENT_PRECONDITION | "
                b"EXCLUDE_FROM_CAMPAIGN_METRICS"
            ),
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "correction registry differs"
        ):
            self.auditor.audit_ledger_bytes(mutated, self.script_data)

    def test_p317_endpoint_subresult_cannot_reclassify_campaign(self):
        mutated = replace_once(
            self.ledger_data,
            (
                b"h0-endpoint-topology-correction-2 | SUBRESULT_ONLY | "
                b"endpoint-selection | NO_PROOF_EXPERIMENT_PRECONDITION | "
                b"EXCLUDE_FROM_CAMPAIGN_METRICS"
            ),
            (
                b"h0-endpoint-topology-correction-2 | CAMPAIGN_PROOF | "
                b"endpoint-selection | NO_PROOF_EXPERIMENT_PRECONDITION | "
                b"APPLY_TO_METRICS"
            ),
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "correction registry differs"
        ):
            self.auditor.audit_ledger_bytes(mutated, self.script_data)

    def test_p310_through_p318_effective_attempt_accounting(self):
        attempts = self.receipt["attempts"]
        self.assertEqual(len(attempts), 9)
        self.assertEqual(
            [item["campaign"] for item in attempts],
            [f"s22plus-fyg8-p{number}" for number in range(310, 319)],
        )
        by_campaign = {item["campaign"]: item for item in attempts}
        self.assertEqual(
            by_campaign["s22plus-fyg8-p316"]["raw_experiment_proof"],
            "NO_PROOF_OBSERVER",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p316"]["effective_experiment_proof"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p317"]["effective_experiment_proof"],
            "NO_PROOF_OBSERVER",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p317"]["terminal_ordinal"],
            "1-recovery-close",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p318"]["raw_experiment_proof"],
            "NO_PROOF_OBSERVER",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p318"]["effective_experiment_proof"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )
        self.assertEqual(
            by_campaign["s22plus-fyg8-p318"]["campaign_correction"],
            "s22plus-fyg8-p318/h0-postlive-eud-index-14",
        )
        self.assertEqual(
            self.receipt["cohorts"]["p310_through_p316"]["effective_class_counts"],
            {
                "PROVED": 0,
                "REFUTED": 2,
                "NO_PROOF_EXPERIMENT_PRECONDITION": 1,
                "NO_PROOF_OBSERVER": 4,
            },
        )
        self.assertEqual(
            self.receipt["cohorts"]["p310_through_p317"]["effective_class_counts"],
            {
                "PROVED": 0,
                "REFUTED": 2,
                "NO_PROOF_EXPERIMENT_PRECONDITION": 1,
                "NO_PROOF_OBSERVER": 5,
            },
        )
        self.assertEqual(
            self.receipt["cohorts"]["p310_through_p318"]["effective_class_counts"],
            {
                "PROVED": 0,
                "REFUTED": 2,
                "NO_PROOF_EXPERIMENT_PRECONDITION": 2,
                "NO_PROOF_OBSERVER": 5,
            },
        )

    def test_presession_and_park_rows_do_not_add_attempts(self):
        marker = self.auditor.MARKER
        scoped = self.ledger_data.split(marker, 1)[1].splitlines(keepends=True)
        taxonomy_index = next(
            index
            for index, line in enumerate(scoped)
            if self.auditor.TAXONOMY_ACTION.encode() in line
        )
        rows, _, _ = self.auditor.parse_log_rows(scoped[: taxonomy_index + 1])
        presession = next(
            row for row in rows if row["action"] == "PRE_CANDIDATE_DOWNLOAD_PRESENT"
        )
        parked = next(
            row for row in rows if row["action"] == "ROLLBACK_ENDPOINT_AMBIGUITY_PARK"
        )
        self.assertEqual(
            self.auditor.row_kind(presession),
            "PRESESSION_OR_ZERO_TRANSFER_F1_STOP",
        )
        self.assertEqual(
            self.auditor.row_kind(parked),
            "INTERMEDIATE_DEVICE_ATTEMPT_OR_RECOVERY",
        )

    def test_observer_localization_audit_includes_both_p313_layers(self):
        rows = self.receipt["localization_audit"]
        p313_actions = [
            item["action"]
            for item in rows
            if item["campaign"] == "s22plus-fyg8-p313"
        ]
        self.assertEqual(
            p313_actions,
            [
                "INTERMEDIATE_CONTRADICTION_DECODER_RECOVERY",
                "STOP_MULTIPLICITY_SOURCE_TRIGGER_LOCALIZED",
            ],
        )

    def test_missing_transfer_exception_set_is_closed(self):
        self.assertEqual(len(self.receipt["legacy_missing_transfer_rows"]), 4)
        mutated = replace_once(
            self.ledger_data,
            (
                b"s22plus-fyg8-p310 | 1 | F1 | CAMPAIGN_CLOSED | HEALTHY | "
                b"NO_PROOF_OBSERVER | 1/1 |"
            ),
            (
                b"s22plus-fyg8-p310 | 1 | F1 | CAMPAIGN_CLOSED | HEALTHY | "
                b"NO_PROOF_OBSERVER |"
            ),
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "missing transfer accounting"
        ):
            self.auditor.audit_ledger_bytes(mutated, self.script_data)

    def test_legacy_evidence_exception_set_is_closed(self):
        self.assertEqual(len(self.receipt["legacy_evidence_rows"]), 4)
        self.assertEqual(
            {
                item["raw_evidence_outcome"]
                for item in self.receipt["legacy_evidence_rows"]
            },
            {"NO_PROOF", "NO_PROOF_SUBTYPE", "NO_PROOF_LOG_BASELINE"},
        )

    def test_valid_post_scope_review_is_validated_without_changing_receipt(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | PROVED | 0/0 | Synthetic valid post-scope review row.\n"
        )
        baseline = self.auditor.audit_ledger_bytes(
            self.ledger_data, self.script_data
        )
        with_tail = self.auditor.audit_ledger_bytes(appended, self.script_data)
        self.assertEqual(with_tail, baseline)

    def test_malformed_post_scope_row_is_rejected(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | PROVED | Missing transfer field.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "missing transfer accounting"
        ):
            self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_post_scope_row_cannot_reuse_legacy_proof_spelling(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | NO_PROOF | 0/0 | Invalid legacy spelling reuse.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "reuses a legacy evidence outcome"
        ):
            self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_post_scope_timestamp_requires_real_utc_calendar_time(self):
        invalid_timestamps = (
            "2026-13-01T00:00:00Z",
            "2026-02-30T00:00:00Z",
            "2026-08-16T24:00:00Z",
            "2026-08-16T00:60:00Z",
            "2026-08-16T00:00:60Z",
        )
        for timestamp in invalid_timestamps:
            with self.subTest(timestamp=timestamp):
                appended = self.ledger_data + (
                    f"{timestamp} | s22plus-fyg8-p319 | "
                    "h0-synthetic-review-1 | H0 | "
                    "PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
                    "HEALTHY | PROVED | 0/0 | Invalid calendar timestamp.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(
                    self.auditor.TaxonomyError,
                    "invalid UTC calendar timestamp",
                ):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_post_scope_tier_and_transfer_cross_product_is_closed(self):
        attacks = (
            (
                "H0",
                "CAMPAIGN_CLOSED",
                "PROVED",
                "0/0",
                "assigns CAMPAIGN_CLOSED outside F1",
            ),
            (
                "H0",
                "H0_INVALID_TRANSFER",
                "PROVED",
                "1/0",
                "boot transfer to non-F1",
            ),
            (
                "D0",
                "D0_INVALID_ROLLBACK",
                "PROVED",
                "0/1",
                "boot transfer to non-F1",
            ),
            (
                "F1",
                "CAMPAIGN_CLOSED",
                "NO_PROOF_OBSERVER",
                "2/1",
                "violates one-shot F1 transfer accounting",
            ),
            (
                "F1",
                "CAMPAIGN_CLOSED",
                "NO_PROOF_OBSERVER",
                "0/1",
                "records rollback without candidate transfer",
            ),
        )
        for tier, action, proof, transfers, error in attacks:
            with self.subTest(tier=tier, action=action, transfers=transfers):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | 1 | "
                    f"{tier} | {action} | HEALTHY | {proof} | {transfers} | "
                    "Invalid tier and transfer combination.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(self.auditor.TaxonomyError, error):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_campaign_close_health_and_rollback_cross_product_is_closed(self):
        attacks = (
            ("HEALTHY", "1/0", "claims healthy close without exact rollback"),
            ("HEALTH_PENDING", "1/0", "nonterminal health state"),
            ("HOST_OBSERVER_FAILURE", "1/1", "nonterminal health state"),
            ("RECOVERY_PENDING_PARKED", "1/0", "nonterminal health state"),
        )
        for health, transfers, error in attacks:
            with self.subTest(health=health, transfers=transfers):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | 1 | F1 | "
                    f"CAMPAIGN_CLOSED | {health} | NO_PROOF_OBSERVER | "
                    f"{transfers} | Invalid campaign close state.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(self.auditor.TaxonomyError, error):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

        recovery_required = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | 1 | F1 | "
            b"CAMPAIGN_CLOSED | RECOVERY_REQUIRED | NO_PROOF_OBSERVER | 1/0 | "
            b"Recovery exhausted after one candidate transfer.\n"
        )
        baseline = self.auditor.audit_ledger_bytes(
            self.ledger_data, self.script_data
        )
        self.assertEqual(
            self.auditor.audit_ledger_bytes(recovery_required, self.script_data),
            baseline,
        )

    def test_post_scope_action_key_is_unique(self):
        row = (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | PROVED | 0/0 | Duplicate-key attack row.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "duplicates one ledger action"
        ):
            self.auditor.audit_ledger_bytes(
                self.ledger_data + row + row, self.script_data
            )

    def test_post_scope_timestamp_is_nondecreasing_with_ties_allowed(self):
        regressed = self.ledger_data + (
            b"2026-08-14T00:00:00Z | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | PROVED | 0/0 | Backdated append attack.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "regresses UTC ordering"
        ):
            self.auditor.audit_ledger_bytes(regressed, self.script_data)

        last_timestamp = (
            self.ledger_data.rstrip(b"\n").rsplit(b"\n", 1)[-1].split(b" | ", 1)[0]
        )
        tied = self.ledger_data + (
            last_timestamp
            + b" | s22plus-fyg8-p319 | "
            b"h0-synthetic-review-1 | H0 | "
            b"PASS_GO_P319_SYNTHETIC_TAXONOMY_H0_CAPABILITY_V1 | "
            b"HEALTHY | PROVED | 0/0 | Valid equal-time append.\n"
        )
        baseline = self.auditor.audit_ledger_bytes(
            self.ledger_data, self.script_data
        )
        self.assertEqual(
            self.auditor.audit_ledger_bytes(tied, self.script_data), baseline
        )

    def test_review_state_labels_are_reserved_to_h0(self):
        attacks = (
            ("F1", "PASS_GO_EXAMPLE", "NO_PROOF_OBSERVER"),
            ("D0", "EXAMPLE_REVIEW_PENDING", "PROVED"),
        )
        for tier, action, proof in attacks:
            with self.subTest(tier=tier, action=action):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | review-1 | "
                    f"{tier} | {action} | HEALTHY | {proof} | 0/0 | "
                    "Review-label tier attack.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(
                    self.auditor.TaxonomyError, "H0 review label outside H0"
                ):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_s22_campaign_ordinal_and_action_tokens_are_closed(self):
        attacks = (
            ("a90-h24", "h0-1", "VALID_ACTION", "invalid S22 campaign token"),
            (" ", "h0-1", "VALID_ACTION", "invalid S22 campaign token"),
            ("s22plus-fyg8-p319", " ", "VALID_ACTION", "invalid ordinal token"),
            ("s22plus-fyg8-p319", "h0-1", "bad-action", "invalid action token"),
        )
        for campaign, ordinal, action, error in attacks:
            with self.subTest(campaign=campaign, ordinal=ordinal, action=action):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | "
                    f"{campaign} | {ordinal} | H0 | {action} | HEALTHY | "
                    "PROVED | 0/0 | Invalid token attack.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(self.auditor.TaxonomyError, error):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_candidate_bearing_f1_ordinal_is_positive_and_canonical(self):
        for ordinal in ("banana", "0", "00", "01"):
            with self.subTest(ordinal=ordinal):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
                    f"{ordinal} | F1 | ROLLBACK_DOWNLOAD_WAIT | "
                    "RECOVERY_PENDING_PARKED | NO_PROOF_OBSERVER | 1/0 | "
                    "Invalid candidate-bearing attempt ordinal.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(
                    self.auditor.TaxonomyError,
                    "noncanonical F1 attempt ordinal",
                ):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_normalized_f1_attempt_state_is_monotonic_and_terminal_once(self):
        attacks = (
            (
                (
                    "1 | F1 | CAMPAIGN_CLOSED | HEALTHY | "
                    "NO_PROOF_OBSERVER | 1/1 | First terminal.\n"
                ),
                (
                    "1-recovery-close | F1 | CAMPAIGN_CLOSED | HEALTHY | "
                    "NO_PROOF_OBSERVER | 1/1 | Duplicate terminal.\n"
                ),
                "second terminal",
            ),
            (
                (
                    "1 | F1 | POST_ROLLBACK_OBSERVATION | "
                    "HOST_OBSERVER_FAILURE | NO_PROOF_OBSERVER | 1/1 | "
                    "Both transfers consumed.\n"
                ),
                (
                    "1-recovery-close | F1 | ROLLBACK_DOWNLOAD_WAIT | "
                    "RECOVERY_PENDING_PARKED | NO_PROOF_OBSERVER | 1/0 | "
                    "Rollback count regression.\n"
                ),
                "regresses one F1 attempt's transfer accounting",
            ),
            (
                (
                    "1 | F1 | ROLLBACK_DOWNLOAD_WAIT | "
                    "RECOVERY_PENDING_PARKED | NO_PROOF_OBSERVER | 1/0 | "
                    "Candidate consumed.\n"
                ),
                (
                    "1 | F1 | RECOVERY_OBSERVATION | HOST_OBSERVER_FAILURE | "
                    "NO_PROOF_OBSERVER | 0/0 | Candidate count regression.\n"
                ),
                "regresses one F1 attempt's transfer accounting",
            ),
            (
                (
                    "1 | F1 | CAMPAIGN_CLOSED | HEALTHY | "
                    "NO_PROOF_OBSERVER | 1/1 | Terminal.\n"
                ),
                (
                    "1-recovery-close | F1 | POST_CLOSE_OBSERVATION | "
                    "HOST_OBSERVER_FAILURE | NO_PROOF_OBSERVER | 1/1 | "
                    "Closed-attempt replay.\n"
                ),
                "resumes a closed F1 attempt",
            ),
        )
        prefix = "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
        for first, second, error in attacks:
            with self.subTest(error=error):
                appended = self.ledger_data + (prefix + first + prefix + second).encode(
                    "ascii"
                )
                with self.assertRaisesRegex(self.auditor.TaxonomyError, error):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_recovery_close_may_advance_one_existing_attempt(self):
        prefix = "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
        appended = self.ledger_data + (
            prefix
            + "1 | F1 | ROLLBACK_DOWNLOAD_WAIT | RECOVERY_PENDING_PARKED | "
            "NO_PROOF_OBSERVER | 1/0 | Candidate consumed; rollback pending.\n"
            + prefix
            + "1-recovery-close | F1 | CAMPAIGN_CLOSED | HEALTHY | "
            "NO_PROOF_OBSERVER | 1/1 | Exact recovery closed the attempt.\n"
        ).encode("ascii")
        baseline = self.auditor.audit_ledger_bytes(
            self.ledger_data, self.script_data
        )
        self.assertEqual(
            self.auditor.audit_ledger_bytes(appended, self.script_data), baseline
        )

    def test_recovery_close_requires_prior_attempt_state(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
            b"1-recovery-close | F1 | CAMPAIGN_CLOSED | HEALTHY | "
            b"NO_PROOF_OBSERVER | 1/1 | Orphan recovery close.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "recovery close without prior attempt state"
        ):
            self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_capability_review_state_is_independent_and_fail_closed(self):
        classify = self.auditor.capability_review_state
        self.assertEqual(classify("H0", "PASS_GO_EXAMPLE"), "PASS_GO")
        self.assertEqual(
            classify("H0", "EXAMPLE_IMPLEMENTED_REVIEW_PENDING"),
            "IMPLEMENTED_REVIEW_PENDING",
        )
        self.assertEqual(
            classify("H0", "EXAMPLE_READY_PENDING_REVIEW"),
            "IMPLEMENTED_REVIEW_PENDING",
        )
        self.assertEqual(
            classify("H0", "FOCUSED_INDEPENDENT_REVIEW"),
            "LEGACY_UNSCOPED_REVIEW_LABEL",
        )
        self.assertEqual(classify("F1", "PASS_GO_EXAMPLE"), "NOT_APPLICABLE")
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "cannot be PASS_GO and REVIEW_PENDING"
        ):
            classify("H0", "PASS_GO_EXAMPLE_REVIEW_PENDING")

    def test_review_label_counts_are_not_unresolved_review_debt(self):
        marker = self.auditor.MARKER
        all_lines = self.ledger_data.split(marker, 1)[1].splitlines(keepends=True)
        all_rows, _, _ = self.auditor.parse_log_rows(all_lines)
        current = self.auditor.audit_review_obligations(all_rows)
        # The single absolute pin on live obligation state.  A new pending row
        # moves this triple and the three relative expectations below by one.
        self.assertEqual(
            (current["total"], current["resolved_count"], current["unresolved_count"]),
            (40, 26, 14),
        )
        self.assertEqual(
            sorted(item["review_topic"] for item in current["unresolved"]),
            [
                "acm-control-requalification",
                "auditor-stale-bytecode",
                "boundary-failclosed",
                "evidence-crosscheck",
                "guard-fixture-invalidation",
                "last-kmsg-retention",
                "log-harvest-runner",
                "mux-module-chain",
                "raw-first-observer",
                "stage-b-rederivation",
                "stage-b-reg-runner",
                "stock-choreography",
                "usb-role-state-runner",
                "usblog-parse",
            ],
        )
        self.assertEqual(
            sorted(item["pending_ordinal"] for item in current["unresolved"]),
            [
                "h0-acm-control-requalification-1",
                "h0-auditor-stale-bytecode-1",
                "h0-boundary-failclosed-1",
                "h0-evidence-crosscheck-1",
                "h0-guard-fixture-invalidation-1",
                "h0-last-kmsg-retention-1",
                "h0-log-harvest-runner-1",
                "h0-mux-module-chain-1",
                "h0-raw-first-observer-2",
                "h0-stage-b-rederivation-1",
                "h0-stage-b-reg-runner-1",
                "h0-stock-choreography-1",
                "h0-usb-role-state-runner-1",
                "h0-usblog-parse-1",
            ],
        )
        self.assertEqual(
            current["resolved"][-1],
            {
                "campaign": "s22plus-fyg8-p319",
                "review_topic": "candidate-witness-transport",
                "pending_ordinal": "h0-candidate-witness-transport-7",
                "pending_action": (
                    "P319_CANDIDATE_WITNESS_TRANSPORT_"
                    "IMPLEMENTED_REVIEW_PENDING"
                ),
                "resolution_ordinal": (
                    "h0-candidate-witness-transport-review-7"
                ),
                "resolution_action": (
                    "PASS_GO_P319_CANDIDATE_WITNESS_CARRIER_V5_"
                    "H0_CAPABILITY_V1"
                ),
            },
        )
        scoped = self.receipt["scoped_review_obligations"]
        self.assertEqual(
            (scoped["total"], scoped["resolved_count"], scoped["unresolved_count"]),
            (18, 17, 1),
        )
        self.assertEqual(
            scoped["unresolved"],
            [
                {
                    "campaign": "s22plus-fyg8-p318",
                    "review_topic": "postlive-eud-index",
                    "pending_ordinal": "h0-postlive-eud-index-14",
                    "pending_action": (
                        "P318_POSTLIVE_EUD_INDEX_RECOVERY_"
                        "IMPLEMENTED_REVIEW_PENDING"
                    ),
                }
            ],
        )
        self.assertEqual(current["pass_go_resolving_no_obligation_count"], 10)
        self.assertEqual(scoped["pass_go_resolving_no_obligation_count"], 10)
        self.assertEqual(
            [item["campaign"] for item in scoped["pass_go_resolving_no_obligation"]],
            [
                "s22plus-fyg8-p309",
                "s22plus-fyg8-p311",
                "s22plus-fyg8-p312",
                "s22plus-fyg8-p313",
                "s22plus-fyg8-p314",
                "s22plus-fyg8-p314",
                "s22plus-fyg8-p315",
                "s22plus-fyg8-p316",
                "s22plus-fyg8-p318",
                "s22plus-fyg8-p318",
            ],
        )

    def test_one_topic_cannot_open_two_review_obligations(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | h0-pending-1 | H0 | "
            b"FIRST_IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | 0/0 | "
            b"First synthetic obligation.\n"
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | h0-pending-2 | H0 | "
            b"SECOND_IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | 0/0 | "
            b"Second synthetic obligation before review.\n"
        )
        with self.assertRaisesRegex(
            self.auditor.TaxonomyError, "opens a second pending review obligation"
        ):
            self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_pending_review_ordinal_grammar_is_closed(self):
        for ordinal in (
            "h0-review-1",
            "h0-topic-0",
            "h0-topic-01",
            "h0-topic--9",
            "h0--topic-9",
            "h0-topic--followup-9",
        ):
            with self.subTest(ordinal=ordinal):
                appended = self.ledger_data + (
                    "2099-12-31T23:59:59Z | s22plus-fyg8-p319 | "
                    f"{ordinal} | H0 | SYNTHETIC_IMPLEMENTED_REVIEW_PENDING | "
                    "HEALTHY | PROVED | 0/0 | Invalid pending ordinal.\n"
                ).encode("ascii")
                with self.assertRaisesRegex(
                    self.auditor.TaxonomyError,
                    "pending review ordinal has no closed topic key",
                ):
                    self.auditor.audit_ledger_bytes(appended, self.script_data)

    def test_review_obligation_axis_describes_topic_keyed_resolution(self):
        self.assertEqual(
            self.receipt["axes"]["review_obligation_state"],
            (
                "pending keyed by campaign and review topic; only same-topic "
                "PASS_GO resolves it, with six exact legacy mappings"
            ),
        )

    def live_obligations(self):
        """Obligation state of the real ledger.

        These cases are about the synthetic topic they append, not about how
        many obligations the live ledger happens to carry.  Measuring the
        baseline keeps the assertions exact while a new pending row stops
        rewriting three unrelated expectations.
        """

        marker = self.auditor.MARKER
        rows, _, _ = self.auditor.parse_log_rows(
            self.ledger_data.split(marker, 1)[1].splitlines(keepends=True)
        )
        value = self.auditor.audit_review_obligations(rows)
        return value, {item["review_topic"] for item in value["unresolved"]}

    def test_unrelated_pending_topics_can_coexist(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p318 | h0-unrelated-9 | H0 | "
            b"UNRELATED_IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | 0/0 | "
            b"Independent pending topic.\n"
        )
        marker = self.auditor.MARKER
        rows, _, _ = self.auditor.parse_log_rows(
            appended.split(marker, 1)[1].splitlines(keepends=True)
        )
        obligations = self.auditor.audit_review_obligations(rows)
        live, live_topics = self.live_obligations()
        self.assertNotIn("unrelated", live_topics)
        self.assertEqual(
            obligations["unresolved_count"], live["unresolved_count"] + 1
        )
        self.assertEqual(
            {item["review_topic"] for item in obligations["unresolved"]},
            live_topics | {"unrelated"},
        )
        baseline = self.auditor.audit_ledger_bytes(
            self.ledger_data, self.script_data
        )
        self.assertEqual(
            self.auditor.audit_ledger_bytes(appended, self.script_data), baseline
        )

    def test_unrelated_pass_go_cannot_resolve_open_topic(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p318 | "
            b"h0-taxonomy-guard-9 | H0 | "
            b"TAXONOMY_GUARD_IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | "
            b"0/0 | Synthetic open topic.\n"
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p318 | "
            b"h0-unrelated-implementation-ready-9 | H0 | "
            b"PASS_GO_P318_UNRELATED_OFFLINE_READY_CAPABILITY_V1 | HEALTHY | "
            b"PROVED | 0/0 | Unrelated PASS must not resolve taxonomy.\n"
        )
        marker = self.auditor.MARKER
        rows, _, _ = self.auditor.parse_log_rows(
            appended.split(marker, 1)[1].splitlines(keepends=True)
        )
        obligations = self.auditor.audit_review_obligations(rows)
        live, live_topics = self.live_obligations()
        self.assertNotIn("taxonomy-guard", live_topics)
        self.assertEqual(
            obligations["unresolved_count"], live["unresolved_count"] + 1
        )
        self.assertEqual(
            {item["review_topic"] for item in obligations["unresolved"]},
            live_topics | {"taxonomy-guard"},
        )
        self.assertEqual(
            obligations["pass_go_resolving_no_obligation_count"], 11
        )

    def test_matching_review_resolves_only_its_topic(self):
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p318 | h0-unrelated-9 | H0 | "
            b"UNRELATED_IMPLEMENTED_REVIEW_PENDING | HEALTHY | PROVED | 0/0 | "
            b"Independent pending topic.\n"
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p318 | "
            b"h0-unrelated-review-9 | H0 | "
            b"PASS_GO_P318_UNRELATED_H0_CAPABILITY_V1 | HEALTHY | PROVED | "
            b"0/0 | Exact unrelated-topic review.\n"
        )
        marker = self.auditor.MARKER
        rows, _, _ = self.auditor.parse_log_rows(
            appended.split(marker, 1)[1].splitlines(keepends=True)
        )
        obligations = self.auditor.audit_review_obligations(rows)
        live, live_topics = self.live_obligations()
        self.assertEqual(
            obligations["resolved_count"], live["resolved_count"] + 1
        )
        self.assertEqual(
            obligations["unresolved_count"], live["unresolved_count"]
        )
        self.assertEqual(
            {item["review_topic"] for item in obligations["unresolved"]},
            live_topics,
        )

    def test_candidate_bearing_open_attempt_enters_inventory(self):
        marker = self.auditor.MARKER
        appended = self.ledger_data + (
            b"2099-12-31T23:59:59Z | s22plus-fyg8-p319 | 1 | F1 | "
            b"ROLLBACK_DOWNLOAD_WAIT | RECOVERY_PENDING_PARKED | "
            b"NO_PROOF_OBSERVER | 1/0 | Synthetic open attempt.\n"
        )
        lines = appended.split(marker, 1)[1].splitlines(keepends=True)
        rows, _, _ = self.auditor.parse_log_rows(lines)
        inventory = self.auditor.audit_attempt_inventory(rows)
        open_item = next(
            item for item in inventory if item["campaign"] == "s22plus-fyg8-p319"
        )
        self.assertEqual(open_item["attempt_state"], "ATTEMPT_OPEN")
        self.assertEqual(open_item["candidate_transfers"], 1)
        self.assertEqual(open_item["terminal_ordinal"], None)
        header = appended.split(marker, 1)[0].decode("utf-8")
        corrections = self.auditor.parse_corrections(header, rows)
        outcomes = self.auditor.derive_attempt_outcomes(rows, corrections)
        open_cohort = self.auditor.cohort(outcomes, ["s22plus-fyg8-p319"])
        self.assertEqual(open_cohort["attempt_count"], 1)
        self.assertEqual(
            open_cohort["attempt_state_counts"],
            {"CLOSED": 0, "ATTEMPT_OPEN": 1},
        )
        self.assertEqual(
            open_cohort["conclusive_information_yield"],
            {"numerator": 0, "denominator": 1},
        )
        self.assertEqual(
            self.receipt["attempt_inventory"]["state_counts"], {"CLOSED": 20}
        )

    def test_h0_row_kind_does_not_consume_review_state(self):
        marker = self.auditor.MARKER
        lines = self.ledger_data.split(marker, 1)[1].splitlines(keepends=True)
        taxonomy_index = next(
            index
            for index, line in enumerate(lines)
            if self.auditor.TAXONOMY_ACTION.encode() in line
        )
        rows, _, _ = self.auditor.parse_log_rows(lines[: taxonomy_index + 1])
        pairs = {
            (
                self.auditor.capability_review_state(row["tier"], row["action"]),
                self.auditor.row_kind(row),
            )
            for row in rows
            if row["tier"] == "H0"
        }
        self.assertIn(("PASS_GO", "H0_HOST_ONLY_NONCORRECTION"), pairs)
        self.assertIn(
            ("IMPLEMENTED_REVIEW_PENDING", "H0_HOST_ONLY_NONCORRECTION"), pairs
        )
        self.assertIn(("NOT_APPLICABLE", "H0_HOST_ONLY_NONCORRECTION"), pairs)
        correction_rows = [
            row
            for row in rows
            if self.auditor.row_kind(row) == "H0_ANALYSIS_OR_CORRECTION"
        ]
        self.assertEqual(len(correction_rows), 2)
        p309 = next(
            row
            for row in rows
            if row["action"] == "PASS_GO_TRACEFS_ABI_CORRECTION_PREREQUISITE"
        )
        self.assertEqual(
            self.auditor.row_kind(p309), "H0_HOST_ONLY_NONCORRECTION"
        )

    def test_candidate_replay_identity_is_explicitly_outside_taxonomy(self):
        safety = self.receipt["safety"]
        self.assertFalse(safety["candidate_artifact_identity_present_in_ledger"])
        self.assertFalse(safety["candidate_identity_replay_audited"])

    def test_append_only_implementation_row_follows_prior_p318_review(self):
        ledger = self.ledger_data.decode("utf-8")
        prior = (
            "s22plus-fyg8-p318 | h0-cdc-acm-qemu-e2e-review-6 | H0 | "
            "PASS_GO_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0_CAPABILITY_V1"
        )
        taxonomy = (
            "s22plus-fyg8-p318 | h0-ledger-taxonomy-7 | H0 | "
            "P318_CAMPAIGN_LEDGER_TAXONOMY_IMPLEMENTED_REVIEW_PENDING"
        )
        review = (
            "s22plus-fyg8-p318 | h0-ledger-taxonomy-review-7 | H0 | "
            "PASS_GO_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_CAPABILITY_V1"
        )
        followup = (
            "s22plus-fyg8-p318 | h0-ledger-taxonomy-followup-8 | H0 | "
            "P318_CAMPAIGN_LEDGER_TAXONOMY_DERIVATION_FOLLOWUP_"
            "IMPLEMENTED_REVIEW_PENDING"
        )
        followup_review = (
            "s22plus-fyg8-p318 | h0-ledger-taxonomy-review-8 | H0 | "
            "PASS_GO_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_CAPABILITY_V2"
        )
        self.assertEqual(ledger.count(prior), 1)
        self.assertEqual(ledger.count(taxonomy), 1)
        self.assertEqual(ledger.count(review), 1)
        self.assertEqual(ledger.count(followup), 1)
        self.assertEqual(ledger.count(followup_review), 1)
        self.assertLess(ledger.index(prior), ledger.index(taxonomy))
        self.assertLess(ledger.index(taxonomy), ledger.index(review))
        self.assertLess(ledger.index(review), ledger.index(followup))
        self.assertLess(ledger.index(followup), ledger.index(followup_review))

    def test_report_binds_receipt_and_denies_live_authority(self):
        report = " ".join(REPORT.read_text(encoding="utf-8").split())
        required = (
            "PASS_GO_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_CAPABILITY_V2; H0 ONLY; NO LIVE AUTHORITY",
            "five observer no-proofs, one precondition no-proof, and two conclusive results",
            "SUBRESULT_ONLY",
            "LEGACY_UNSCOPED_REVIEW_LABEL",
            "3c0cca0feea9259a0107cc9c9bfa021579707595afa15b6bf9371529f1fe06e1",
            "6541ed535aec06337094cae98f9b07a91c37e13528a619bdeb4811fc870da026",
            "grants no D0, D1, F1, recovery, replay, or live authority",
            "all eleven historical obligations were therefore resolved",
            "ATTEMPT_OPEN",
            "does not audit candidate artifact identity or cross-ordinal replay",
            "pass_go_resolving_no_obligation",
            "S22PLUS_FYG8_P318_LEDGER_TAXONOMY_V1_PREDECESSOR_PROVENANCE.json",
            "The read-only review independently regenerated",
        )
        for clause in required:
            self.assertIn(clause, report)
        self.assertEqual(self.receipt["safety"]["device_actions"], 0)
        self.assertFalse(self.receipt["safety"]["live_authority_created"])

    def test_receipt_publication_is_complete_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "receipt.json"
            self.auditor.publish_exclusive(target, b"exact receipt\n")
            self.assertEqual(target.read_bytes(), b"exact receipt\n")
            with self.assertRaises(FileExistsError):
                self.auditor.publish_exclusive(target, b"replacement\n")
            self.assertEqual(target.read_bytes(), b"exact receipt\n")


if __name__ == "__main__":
    unittest.main()
