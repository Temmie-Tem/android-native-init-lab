from __future__ import annotations

import importlib.util
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_candidate_qualification.py"
ADAPTER = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_stock_process_v2_adapter.py"
PHASE1 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-48"
PHASE2 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-49"
RUN = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-08"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STOCK_CANDIDATE_QUALIFICATION_H0_2026-08-21.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"
sys.path.insert(0, str(ADAPTER.parent))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P319CandidateQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualification = load(QUALIFICATION, "p319_candidate_qualification_test")
        cls.adapter = load(ADAPTER, "p319_stock_adapter_test")
        cls.phase1 = json.loads((PHASE1 / "result.json").read_bytes())
        cls.phase2 = json.loads((PHASE2 / "result.json").read_bytes())
        cls.qualification_result = json.loads((RUN / "qualification.json").read_bytes())
        cls.static = json.loads((RUN / "static-reconstruction.json").read_bytes())

    def test_final_private_outputs_are_durable_and_role_bound(self):
        for path in (PHASE1 / "result.json", PHASE2 / "result.json", RUN / "intent.json"):
            info = path.stat()
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
        candidate = self.phase2["phase2"]["candidate"]
        self.assertTrue(candidate["exact_one_member_generic_overlay"])
        self.assertEqual(candidate["vendor_layer_stock_modules"], 72)
        self.assertEqual(candidate["overlay_members"], ["lib/modules/s22plus_dwc3_event_latch.ko"])
        self.assertFalse("exact_stock_overlay" in candidate)
        self.assertFalse(self.phase2["scope"]["device_contact"])
        self.assertFalse(self.phase2["scope"]["live_authority_created"])

    def test_intent_binds_adapter_and_rootfs_transitive_sources(self):
        intent = json.loads((RUN / "intent.json").read_bytes())
        keys = self.qualification._source_keys()
        self.assertIn("adapter_carrier_model", keys)
        self.assertIn("adapter_telemetry_spec", keys)
        self.assertIn("rootfs_closure:s22plus_boot_verify.py", keys)
        self.assertIn("rootfs_closure:s22plus_o2_module_plan.py", keys)
        self.assertFalse("typed_evidence_source" in keys)
        self.assertFalse("f1_runner_source" in keys)
        self.assertFalse("f1_live_source" in keys)
        self.assertEqual(intent["module_plan"]["count"], 73)
        self.assertEqual(intent["module_plan"]["eud_index"], 38)
        self.assertEqual(intent["runtime"]["status_width"], 3)
        self.assertFalse(intent["scope"]["device_contact"])

    def test_qualify_consumes_declared_module_plan_authority(self):
        intent = json.loads((RUN / "intent.json").read_bytes())
        for field, bad_value in (
            ("count", 72),
            ("eud_index", 37),
            ("overlay_delta", ["foreign.ko"]),
        ):
            mutated = json.loads(json.dumps(intent))
            mutated["module_plan"][field] = bad_value
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification.qualify(
                    mutated,
                    self.phase1,
                    self.phase2,
                    self.static,
                    PHASE1,
                    PHASE2,
                )

    def test_stock_adapter_has_three_truthful_terminal_states(self):
        for state, classification, accepted in (
            ("COMPLETE", "P319_STOCK_WITNESS_COMPLETE", True),
            ("INCOMPLETE", "P319_STOCK_WITNESS_INCOMPLETE_NO_PROOF", False),
            ("AMBIGUOUS", "P319_STOCK_WITNESS_AMBIGUOUS_NO_PROOF", False),
        ):
            record = self.adapter.encode_fixture(state=state)
            raw = bytes(self.adapter.RAW_SIZE - len(record)) + record
            result = self.adapter.classify_observation(raw)
            self.assertEqual(result["classification"], classification)
            self.assertEqual(result["accepted"], accepted)
            self.assertEqual(result["long_record_count"], 1)
            self.assertEqual(result["exact_record_count"], 1)
            self.assertEqual(result["unsat_count"], 0)
            self.assertFalse(result["causal_result_allowed"])
            self.assertFalse(result["candidate_success"])
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.classify_observation(self.adapter.encode_fixture())

    def test_stock_adapter_rejects_mixed_unsat_legacy_and_duplicate_long(self):
        positive = self.adapter.encode_fixture()
        carrier = self.adapter.model
        for prefix in (
            carrier.unsat_record(self.adapter.PROFILE, self.adapter.STOCK_RUN_ID),
            carrier.LEGACY_FAMILIES[0] + b"legacy",
            positive,
        ):
            raw = prefix + bytes(self.adapter.RAW_SIZE - len(prefix) - len(positive)) + positive
            result = self.adapter.classify_observation(raw)
            self.assertEqual(result["classification"], "P319_STOCK_WITNESS_BASE_SHAPE_FAILURE")
            self.assertFalse(result["accepted"])

    def test_json_duplicate_nonfinite_and_noncanonical_fixtures_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="p319-qualification-json-") as directory:
            root = Path(directory)
            for name, payload in (
                ("duplicate.json", b'{"a":1,"a":2}\n'),
                ("nan.json", b'{"a":NaN}\n'),
                ("noncanonical.json", b'{"b":2,"a":1}\n'),
            ):
                path = root / name
                path.write_bytes(payload)
                path.chmod(0o400)
                with self.assertRaises(self.qualification.QualificationError):
                    self.qualification._json(path, require_canonical=True)

    def test_verify_intent_reopens_exact_disk_bytes_after_in_memory_load(self):
        original = json.loads((RUN / "intent.json").read_bytes())
        original["source_keys"] = self.qualification._source_keys()
        with tempfile.TemporaryDirectory(prefix="p319-qualification-intent-") as directory:
            path = Path(directory) / "intent.json"
            path.write_bytes(self.qualification._canonical(original) + b"\n")
            path.chmod(0o400)
            self.qualification.verify_intent(path, original)

            changed = dict(original)
            changed["candidate_window_sec"] = original["candidate_window_sec"] + 1
            path.unlink()
            path.write_bytes(self.qualification._canonical(changed) + b"\n")
            path.chmod(0o400)
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification.verify_intent(path, original)

    def test_verify_intent_rejects_noncanonical_and_duplicate_disk_json(self):
        original = json.loads((RUN / "intent.json").read_bytes())
        with tempfile.TemporaryDirectory(prefix="p319-qualification-intent-shape-") as directory:
            root = Path(directory)
            noncanonical = root / "noncanonical.json"
            noncanonical.write_bytes((json.dumps(original, sort_keys=True, indent=2) + "\n").encode())
            noncanonical.chmod(0o400)
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification.verify_intent(noncanonical, original)

            duplicate = root / "duplicate.json"
            duplicate.write_bytes(b'{"schema":"x","schema":"y"}\n')
            duplicate.chmod(0o400)
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification.verify_intent(duplicate, original)

    def test_exclusive_writer_overrides_hostile_umask(self):
        with tempfile.TemporaryDirectory(prefix="p319-qualification-umask-") as directory:
            path = Path(directory) / "receipt.json"
            previous = os.umask(0o777)
            try:
                self.qualification._write_exclusive(path, {"ok": True})
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            self.assertEqual(path.stat().st_nlink, 1)

    def test_extra_ready_file_is_rejected_by_exact_run_root_shape(self):
        with tempfile.TemporaryDirectory(prefix="p319-qualification-run-shape-") as directory:
            copy = Path(directory) / "run"
            shutil.copytree(RUN, copy)
            copy.chmod(0o700)
            (copy / "ready-manifest.json").write_bytes(b"{}"); (copy / "ready-manifest.json").chmod(0o400)
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification._require_complete_run_root(copy)
            with self.assertRaises(self.qualification.QualificationError):
                self.qualification.audit_existing(copy, PHASE1, PHASE2)

    def test_qualification_executes_adapter_audit_and_records_no_process_integration(self):
        adapter, source = self.qualification._load_adapter()
        audit = adapter.audit()
        self.assertTrue(audit["verified"])
        self.assertTrue(audit["full_record_required"])
        self.assertIn("adapter_audit", inspect.getsource(self.qualification.qualify))
        self.assertIn("process_v2_integration_created", inspect.getsource(self.qualification.qualify))
        self.assertGreater(len(source), 20_000)

    def test_final_bookkeeping_keeps_reviewed_h0_boundary(self):
        report = REPORT.read_text()
        ledger = LEDGER.read_text()
        goal = GOAL.read_text()
        self.assertIn("PASS_GO_P319_STOCK_CANDIDATE_QUALIFICATION_PLAN_BINDING_H0_CAPABILITY_V1", report)
        self.assertIn("No ready/run manifest", report)
        self.assertIn("h0-stock-candidate-qualification-plan-binding-review-26", ledger)
        self.assertIn("PASS_GO_P319_STOCK_CANDIDATE_QUALIFICATION_PLAN_BINDING_H0_CAPABILITY_V1", ledger)
        self.assertIn("current P3.19 `-48`/`-49`/`-08` is independently reviewed H0-only `PASS_GO`", goal)
        self.assertIn("Stage B has since run and read the mxim debug register dump 0x00-0x10", goal)
        self.assertIn("that dump does not contain CONTROL1", goal)
        self.assertIn("must not be cited as two candidate boots because the candidate observer was rejected", goal)

    def test_report_binds_current_canonical_source_keys_digest(self):
        intent = json.loads((RUN / "intent.json").read_bytes())
        canonical = json.dumps(
            intent["source_keys"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        report = REPORT.read_text()
        self.assertIn(f"SOURCE_KEYS digest: `{digest}` (436 keys).", report)


if __name__ == "__main__":
    unittest.main()
