"""Host-only checks for the fixed P339 post-transfer health resumption."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_fyg8_p339_health_resume as resume


class P339HealthResumeTests(unittest.TestCase):
    def test_historical_input_changes_only_document_and_restores_function(self):
        current_doc = (ROOT / resume.DOCUMENT).read_bytes()
        original = resume.tiers.tier3_materials
        sentinel = {"direct:process_v2_contract": current_doc, "other-source": b"unchanged"}
        with mock.patch.object(resume.tiers, "tier3_materials", return_value=sentinel) as source:
            with resume.original_document_input():
                values = resume.tiers.tier3_materials(ROOT)
                self.assertEqual(resume.identity(values["direct:process_v2_contract"]), resume.DOCUMENT_IDENTITY)
                self.assertEqual(values["other-source"], b"unchanged")
                self.assertEqual(sentinel["direct:process_v2_contract"], current_doc)
            self.assertIs(resume.tiers.tier3_materials, source)
        self.assertIs(resume.tiers.tier3_materials, original)
        self.assertEqual((ROOT / resume.DOCUMENT).read_bytes(), current_doc)

    def test_backend_cannot_transfer_or_request_download(self):
        backend = object.__new__(resume.HealthOnlyBackend)
        with self.assertRaisesRegex(resume.live.F1LiveError, "cannot transfer"):
            backend.transfer()
        with self.assertRaisesRegex(resume.live.F1LiveError, "cannot request Download"):
            backend.request_download()

    def test_pre_rollback_state_stops_before_backend_or_recovery(self):
        prepared = SimpleNamespace(binding_sha256="0" * 64)
        journal = SimpleNamespace(state=lambda: "OBSERVED")
        with (
            mock.patch.object(resume, "original_document_input", return_value=nullcontext()),
            mock.patch.object(resume.live, "load_prepared", return_value=prepared),
            mock.patch.object(resume.live.core, "Journal", return_value=journal),
            mock.patch.object(resume, "HealthOnlyBackend") as backend,
            mock.patch.object(resume.live, "recover_prepared") as recover,
        ):
            with self.assertRaisesRegex(resume.live.F1LiveError, "not in post-transfer"):
                resume.run(recover=True)
            backend.assert_not_called()
            recover.assert_not_called()

    def test_final_validator_changes_only_fixed_read_location(self):
        prepared = resume.live.PreparedRun(
            ROOT, resume.RUN, object(),
            {"manifest_id": "s22plus-fyg8-p339-process-v2-ready-2"}, {},
        )
        state = {"example": "unchanged"}
        with mock.patch.object(resume.live, "_validate_final_observer") as original:
            with resume.final_capture_location():
                resume.live._validate_final_observer(prepared, state)
            changed, actual_state = original.call_args.args
            self.assertEqual(changed.run_dir, resume.FINAL_ROOT)
            self.assertIs(changed.bundle, prepared.bundle)
            self.assertIs(changed.prepared, prepared.prepared)
            self.assertIs(actual_state, state)
            self.assertEqual(prepared.run_dir, resume.RUN)

    def test_wrong_health_destination_stops_before_directory_creation(self):
        backend = object.__new__(resume.HealthOnlyBackend)
        with self.assertRaisesRegex(resume.live.F1LiveError, "destination differs"):
            backend.verify_final(SimpleNamespace(run_dir=resume.RUN), None, None, ROOT)

    def test_retained_backend_has_no_device_or_endpoint_path(self):
        backend = resume.RetainedBackend()
        for name in ("transfer", "request_download", "wait_download"):
            with self.subTest(name=name), self.assertRaises(resume.live.F1LiveError):
                getattr(backend, name)()
        with backend.endpoint_session(resume.RUN / "odin-endpoints") as lease:
            self.assertIsNone(lease)
        with self.assertRaises(resume.live.F1LiveError):
            backend.endpoint_session(ROOT)

    def test_projection_fix_is_one_additional_p339_exclusion_and_restores(self):
        original = resume.live._finish_rollback
        with resume.p339_final_projection():
            repaired = resume.live._finish_rollback
            self.assertIsNot(repaired, original)
            self.assertEqual(repaired.__code__.co_names, original.__code__.co_names)
            self.assertEqual(repaired.__code__.co_consts, original.__code__.co_consts)
            # P339 already has its own projection earlier in the same function;
            # only the P328-only fallback acquires one additional predicate.
            import dis
            count = lambda fn: sum(i.opname == "LOAD_GLOBAL" and i.argval == "_p339_bundle" for i in dis.get_instructions(fn))
            self.assertEqual(count(repaired), count(original) + 1)
        self.assertIs(resume.live._finish_rollback, original)

    def test_retained_owner_rejects_before_any_capture_read(self):
        with mock.patch.object(resume.live.raw_capture, "load_handle") as read:
            with self.assertRaisesRegex(resume.live.F1LiveError, "owner differs"):
                resume.retained_final(SimpleNamespace(run_dir=ROOT))
            read.assert_not_called()

    def test_real_recover_entry_rebinds_final_validator_exactly_once(self):
        prepared = resume.live.PreparedRun(ROOT, resume.RUN, object(), {
            "manifest_id": "s22plus-fyg8-p339-process-v2-ready-2",
            "approval_binding_sha256": "0" * 64,
        }, {})
        current = {f"{kind}_{key}": value for kind in ("candidate", "rollback")
                   for key, value in (("completed", True), ("classification", "odin_transfer_completed"))}

        def retained(value):
            resume.live._validate_final_observer(value, {})
            return {"rederived": True}

        def recover(value, backend):
            return backend.verify_final(value, None, None, resume.RUN)

        with (
            mock.patch.object(resume, "original_document_input", return_value=nullcontext()),
            mock.patch.object(resume.live, "load_prepared", return_value=prepared),
            mock.patch.object(resume.live.core, "Journal", return_value=SimpleNamespace(state=lambda: "ROLLBACK_FLASHED")),
            mock.patch.object(resume.live, "_state", return_value=current),
            mock.patch.object(resume.live, "_validate_transfer_result", return_value={"classification": "odin_transfer_completed"}),
            mock.patch.object(resume, "retained_final", side_effect=retained),
            mock.patch.object(resume.live, "recover_prepared", side_effect=recover),
            mock.patch.object(resume.live, "_validate_final_observer") as validator,
        ):
            self.assertEqual(resume.run(recover=True), {"rederived": True})
            validator.assert_called_once()
            self.assertEqual(validator.call_args.args[0].run_dir, resume.FINAL_ROOT)


if __name__ == "__main__":
    unittest.main()
