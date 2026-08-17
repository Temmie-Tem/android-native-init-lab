import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_carrier_version_crosscheck.py"
)
SPEC = importlib.util.spec_from_file_location("p318_carrier_crosscheck_unbound", SOURCE)
assert SPEC is not None and SPEC.loader is not None
UNBOUND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UNBOUND)
AUDIT = UNBOUND.load_bound_auditor()


class CarrierVersionCrosscheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = AUDIT.build_receipt()

    def test_requested_three_match_v2_and_opposite_v1_is_zero(self):
        rows = {row["campaign"]: row for row in self.receipt["campaigns"]}
        for name, count in (("p310", 1), ("p314", 1), ("p317", 3)):
            with self.subTest(name=name):
                self.assertEqual(rows[name]["selected_carrier_version"], 2)
                self.assertEqual(rows[name]["actual_retained_carrier_version"], 2)
                self.assertEqual(rows[name]["selected_parser_record_count"], count)
                self.assertEqual(rows[name]["opposite_parser_record_count"], 0)
                self.assertIs(rows[name]["carrier_version_match"], True)
                self.assertIs(
                    rows[name]["frozen_consumer_execution_path"][
                        "classification_invokes_selected_decoder"
                    ],
                    True,
                )
        self.assertEqual(
            self.receipt["conclusion"][
                "carrier_version_mismatch_exemption_supported_for"
            ],
            ["p310", "p314", "p317"],
        )

    def test_p311_known_silent_mismatch_is_positive_control(self):
        row = next(row for row in self.receipt["campaigns"] if row["campaign"] == "p311")
        self.assertEqual(row["selected_carrier_version"], 1)
        self.assertEqual(row["actual_retained_carrier_version"], 2)
        self.assertEqual(row["selected_parser_record_count"], 0)
        self.assertEqual(row["opposite_parser_record_count"], 1)
        self.assertIs(row["carrier_version_match"], False)
        self.assertIs(self.receipt["controls"]["p311_known_mismatch_detected"], True)

    def test_v1_parser_positive_control_and_corruption(self):
        record = AUDIT.v1_positive_record()
        rows = AUDIT.scan_v1(b"prefix" + record + b"suffix")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["offset"], 6)
        corrupted = bytearray(record)
        corrupted[-1] ^= 1
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "Carrier-v1 slot"):
            AUDIT.scan_v1(bytes(corrupted))

        original_domain = AUDIT.V1_SLOT_CRC_DOMAIN
        AUDIT.V1_SLOT_CRC_DOMAIN = b"invented-self-consistent-domain\0"
        try:
            with self.assertRaisesRegex(AUDIT.CrosscheckError, "Carrier-v1 slot"):
                AUDIT.scan_v1(record)
        finally:
            AUDIT.V1_SLOT_CRC_DOMAIN = original_domain
        controls = self.receipt["controls"]
        self.assertIs(controls["local_v1_scanner_agrees_with_external_authority"], True)
        self.assertEqual(controls["p232_external_decoder_record_count"], 1)

    def test_frozen_consumer_selection_and_classification_mutations_reject(self):
        configs = {row["name"]: row for row in AUDIT.CAMPAIGNS}
        attacks = (
            (
                "p310-source-contract",
                "p310",
                b"return _selected_contract(source_contract_id, profile).decoder",
                b"return e1_latest_stage",
            ),
            (
                "p311-overlay-selection",
                "p311",
                b"return p311_decoder",
                b"return p310_decoder",
            ),
            (
                "p314-overlay-selection",
                "p314",
                b"selected = p314_decoder",
                b"selected = p311_decoder",
            ),
            (
                "p314-validator-return",
                "p314",
                b"return selected_decoder\n\n\ndef _validate_p301_overlay_contract",
                b"return source_decoder\n\n\ndef _validate_p301_overlay_contract",
            ),
            (
                "p317-classification-bypass",
                "p317",
                b"decoded = selected_decoder.classify_observation(",
                b"decoded = p310_decoder.classify_observation(",
            ),
        )
        for label, name, old, new in attacks:
            with self.subTest(label=label):
                config = configs[name]
                source = (
                    AUDIT.FROZEN_SOURCE_DIR / config["frozen_source_file"]
                ).read_bytes()
                self.assertIn(old, source)
                mutated = source.replace(old, new, 1)
                with self.assertRaisesRegex(
                    AUDIT.CrosscheckError,
                    "critical function|acceptance-to-classification|selected decoder",
                ):
                    AUDIT.audit_frozen_consumer_source(
                        mutated,
                        config,
                        enforce_identity=False,
                    )

    def test_live_classification_policy_profile_run_binding_mutations_reject(self):
        acceptance = {
            "policy_id": "policy",
            "profile": "E2",
            "run_id": "01" * 16,
        }
        base = {
            "long_record_count": 1,
            "family_count": 1,
            "exact_record_count": 1,
            **acceptance,
        }
        AUDIT.audit_classification_binding(
            base,
            acceptance,
            expected_count=1,
            label="fixture",
        )
        for key, value in (
            ("policy_id", "foreign"),
            ("profile", "E1"),
            ("run_id", "02" * 16),
            ("policy_id", 1),
        ):
            with self.subTest(key=key, value=value):
                mutated = {**base, key: value}
                with self.assertRaisesRegex(
                    AUDIT.CrosscheckError,
                    "frozen classification binding",
                ):
                    AUDIT.audit_classification_binding(
                        mutated,
                        acceptance,
                        expected_count=1,
                        label="fixture",
                    )

    def test_opposite_version_injection_rejects_semantic_exemption(self):
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "Carrier-version cross-check"):
            AUDIT.audit_version_relation(
                selected_version=2,
                v2_offsets=[10],
                v1_records=[{"offset": 20}],
                expected_count=1,
                expect_match=True,
                label="fixture",
            )
        control = AUDIT.audit_version_relation(
            selected_version=1,
            v2_offsets=[10],
            v1_records=[],
            expected_count=1,
            expect_match=False,
            label="p311-fixture",
        )
        self.assertIs(control["carrier_version_match"], False)

    def test_frozen_binding_identity_mutations_reject(self):
        parent = AUDIT.strict_json(AUDIT.PARENT.read_bytes(), "parent fixture")
        rows = AUDIT._parent_campaigns(parent)
        base = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p310")
        attacks = (
            ("decoder", {**base, "decoder": "foreign-decoder"}, "frozen Carrier selection"),
            ("manifest", {**base, "manifest": "foreign-manifest"}, "prepared identity"),
            (
                "typed-evidence",
                {**base, "typed_evidence": {"size": 1, "sha256": "0" * 64}},
                "frozen evidence source",
            ),
        )
        for label, config, error in attacks:
            with self.subTest(label=label):
                with self.assertRaisesRegex(AUDIT.CrosscheckError, error):
                    AUDIT.audit_campaign(config, rows["p310"])

    def test_parent_raw_path_and_record_offset_mutations_reject(self):
        parent = AUDIT.strict_json(AUDIT.PARENT.read_bytes(), "parent fixture")
        rows = AUDIT._parent_campaigns(parent)
        config = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p317")
        changed_path = json.loads(json.dumps(rows["p317"]))
        changed_path["final_observer_reads"][0]["path"] = "foreign.bin"
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "parent raw receipt"):
            AUDIT.audit_campaign(config, changed_path)
        changed_offset = json.loads(json.dumps(rows["p317"]))
        changed_offset["carrier_records"][0]["offset"] += 1
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "Carrier-v2 raw count"):
            AUDIT.audit_campaign(config, changed_offset)

    def test_strict_json_and_scope(self):
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "duplicate key"):
            AUDIT.strict_json(b'{"x":1,"x":2}', "fixture")
        with self.assertRaisesRegex(AUDIT.CrosscheckError, "NaN"):
            AUDIT.strict_json(b'{"x":NaN}', "fixture")
        scope = self.receipt["scope"]
        self.assertIs(scope["host_only"], True)
        self.assertIs(scope["device_contact"], False)
        self.assertEqual(scope["adb_commands"], 0)
        self.assertEqual(scope["usb_actions"], 0)
        self.assertEqual(scope["odin_invocations"], 0)
        self.assertEqual(scope["candidate_transfers"], 0)
        self.assertEqual(scope["rollback_transfers"], 0)
        self.assertIs(scope["replay"], False)
        self.assertIs(scope["live_authority_created"], False)

    def test_tracked_boundary_and_reviewed_ledger(self):
        report = (ROOT / (
            "docs/reports/"
            "S22PLUS_FYG8_P310_P314_P317_CARRIER_VERSION_CROSSCHECK_H0_2026-08-17.md"
        )).read_text()
        goal = (ROOT / "GOAL.md").read_text()
        ledger = (ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md").read_text()
        target = (ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md").read_text()
        self.assertIn(
            "PASS_GO_P318_CARRIER_VERSION_CROSSCHECK_H0_CAPABILITY_V2; "
            "H0 ONLY; NO LIVE AUTHORITY",
            report,
        )
        self.assertIn("P3.11 is the positive control", report)
        self.assertIn("opposite Carrier-v1 record count is zero", report)
        self.assertIn("mode-`0400`/link-count-one snapshot", report)
        self.assertIn("asks that authority to encode and decode", report)
        self.assertIn("That receipt is not current review authority", report)
        self.assertIn("13,488 bytes", report)
        self.assertIn("f3e152b484c3b5bf", report)
        self.assertIn("frozen-Carrier agreement is now host-audited", goal)
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertEqual(len(target.splitlines()), 260)
        pending = "h0-carrier-version-crosscheck-16"
        review = "h0-carrier-version-crosscheck-review-16"
        self.assertEqual(ledger.count(pending), 1)
        self.assertEqual(ledger.count(review), 1)
        self.assertIn(
            "P310_P314_P317_CARRIER_VERSION_CROSSCHECK_IMPLEMENTED_REVIEW_PENDING",
            ledger,
        )
        self.assertIn(
            "PASS_GO_P318_CARRIER_VERSION_CROSSCHECK_H0_CAPABILITY_V2",
            ledger,
        )

    def test_receipt_publication_and_mode(self):
        original_output = AUDIT.OUTPUT
        with tempfile.TemporaryDirectory() as directory:
            AUDIT.OUTPUT = Path(directory) / "receipt.json"
            previous = os.umask(0o777)
            try:
                AUDIT.write_receipt(self.receipt)
            finally:
                os.umask(previous)
            state = AUDIT.OUTPUT.lstat()
            self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
            self.assertEqual(state.st_nlink, 1)
            os.chmod(AUDIT.OUTPUT, 0o600)
            with self.assertRaisesRegex(AUDIT.CrosscheckError, "identity differs"):
                AUDIT.write_receipt(self.receipt)
        AUDIT.OUTPUT = original_output

    def test_preserved_receipt_is_exact_regeneration(self):
        expected = AUDIT.encode_receipt(self.receipt)
        actual = AUDIT.OUTPUT.read_bytes()
        state = AUDIT.OUTPUT.lstat()
        self.assertEqual(actual, expected)
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)
        decoded = json.loads(actual)
        self.assertEqual(decoded["schema"], AUDIT.SCHEMA)
        self.assertEqual(decoded["verdict"], AUDIT.VERDICT)


if __name__ == "__main__":
    unittest.main()
