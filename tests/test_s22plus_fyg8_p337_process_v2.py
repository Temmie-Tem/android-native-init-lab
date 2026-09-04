from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p337_process_v2 as prepare  # noqa: E402
import s22plus_fyg8_p336_long_idle_acm_observer as p336_observer  # noqa: E402
import s22plus_fyg8_p337_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p337_d0_fresh_baseline as d0  # noqa: E402
import s22plus_fyg8_p337_d1_fresh_baseline as d1  # noqa: E402
import s22plus_fyg8_p337_open_read_diag_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p337_open_read_diag_runtime as runtime  # noqa: E402
import s22plus_fyg8_p337_process_v2_candidate_static as static  # noqa: E402
import s22plus_fyg8_p337_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p337_stock_process_v2_adapter as adapter  # noqa: E402


class P337ProcessV2Tests(unittest.TestCase):
    def test_first_open_diagnostic_decodes_without_causal_claim(self) -> None:
        frame = p336_observer.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            p336_observer.DIAGNOSTIC.pack(
                runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, -110
            ),
        )
        value = observer.parse_retained_open_read_diagnostic(
            runtime.DEVICE_BANNER + frame
        )
        self.assertEqual(value["classification"], "open-read-error")
        self.assertEqual(value["code"], -110)
        self.assertFalse(value["causal_result_allowed"])
        self.assertFalse(value["candidate_success"])

    def test_validation_reject_is_distinct_and_no_retry_is_added(self) -> None:
        frame = p336_observer.encode_frame(
            runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            p336_observer.DIAGNOSTIC.pack(
                runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT,
                runtime.OPEN_READ_VALIDATION_REJECTED,
            ),
        )
        value = observer.parse_open_read_diagnostic_frame(frame)
        self.assertEqual(value["classification"], "open-validation-rejected")
        self.assertFalse(runtime.audit_binding()["retry_added"])
        self.assertFalse(runtime.audit_binding()["timeout_changed"])

    def test_malformed_shared_receipt_uses_p337_error_boundary(self) -> None:
        self.assertIs(observer.AuthObserverError, observer.P337ObserverBindingError)
        malformed = {
            "first_open_failure_diagnostic": True,
            "open_read_diagnostic": None,
        }
        with (
            mock.patch.object(live, "_read_json", return_value=malformed),
            self.assertRaises(observer.P337ObserverBindingError),
        ):
            live._p337_validate_receipt(  # noqa: SLF001
                SimpleNamespace(), Path("/unused"), {}
            )

    def test_p337_arm_uses_retained_reopen_contract(self) -> None:
        class ReachedAuthKeyLoad(Exception):
            pass

        bundle = core.verify_bundle(ROOT, prepare.DEFAULT_MANIFEST)
        spec = bundle.manifest["observation"]["candidate_observer"]
        session = live._p337_candidate_observer_session(  # noqa: SLF001
            SimpleNamespace(),
            spec,
            lane_value={},
            lane_receipt={},
            usb_root=Path("/unused-usb"),
            typec_root=Path("/unused-typec"),
        )
        with (
            mock.patch.object(
                live,
                "_p328_read_auth_key",
                side_effect=ReachedAuthKeyLoad,
            ),
            self.assertRaises(ReachedAuthKeyLoad),
        ):
            session.__enter__()

    def test_adapter_and_observer_bind_only_fresh_identity(self) -> None:
        audit = adapter.audit()
        self.assertEqual(audit["run_id"], runtime.P337_RUN_ID_HEX)
        self.assertTrue(audit["first_open_failure_diagnostic"])
        self.assertEqual(audit["open_read_diagnostic_stage"], 3)
        self.assertIn(
            runtime.P336_PREDECESSOR_RUN_ID_HEX,
            audit["acceptance"]["predecessor_run_ids_rejected"],
        )
        self.assertEqual(observer.audit_binding()["run_id_hex"], runtime.P337_RUN_ID_HEX)

    def test_artifact_and_builder_reopen_final_boot_only_output(self) -> None:
        built = builder.audit_existing()
        candidate = built["phase2"]["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertNotEqual(
            candidate["a"]["ap_tar_md5"], artifact.P336_AP_IDENTITY
        )

    def test_static_and_ready_bundle_regenerate(self) -> None:
        value = static.build_result()
        self.assertEqual(value["run_id"], runtime.P337_RUN_ID_HEX)
        self.assertIsNone(value["action_runner"])
        self.assertFalse(value["later_action_authorized"])
        bundle = core.verify_bundle(ROOT, prepare.DEFAULT_MANIFEST)
        self.assertEqual(
            bundle.manifest["observation"]["acceptance"]["run_id"],
            runtime.P337_RUN_ID_HEX,
        )
        self.assertEqual(
            bundle.receipt["observation_contract"]["verification"]["schema"],
            "device_action_f1_p337_stock_offline_contract_v1",
        )

    def test_live_closure_uses_p337_sources_and_no_p336_action(self) -> None:
        bundle = core.verify_bundle(ROOT, prepare.DEFAULT_MANIFEST)
        closure = live._closure(ROOT, bundle)  # noqa: SLF001
        sources = closure["sources"]
        self.assertIn("p337_open_read_diag_runtime", sources)
        self.assertIn("p337_open_read_diag_acm_observer", sources)
        self.assertIn("p337_artifact_identity", sources)
        self.assertNotIn("p336_long_idle_action", sources)
        self.assertEqual(
            closure["p337_auth_exec_runtime_contract_id"], runtime.CONTRACT_ID
        )

    def test_predecessor_manifest_identity_is_rejected(self) -> None:
        bundle = core.verify_bundle(ROOT, prepare.DEFAULT_MANIFEST)
        value = json.loads(prepare.DEFAULT_MANIFEST.read_text())
        changed = copy.deepcopy(value)
        changed["observation"]["acceptance"]["run_id"] = (
            runtime.P336_PREDECESSOR_RUN_ID_HEX
        )
        with self.assertRaises(core.F1V2Error):
            core.validate_manifest(changed, bundle.profile)

    def test_d1_and_d0_host_fixtures_pass(self) -> None:
        self.assertEqual(d1.self_test()["reboot_count"], 1)
        self.assertTrue(d0.self_test()["clean_baseline"])


if __name__ == "__main__":
    unittest.main()
