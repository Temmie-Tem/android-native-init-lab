from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p320_stock_candidate_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p320_stock_candidate_build", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.20 stock candidate builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.output = cls.module.DEFAULT_OUTPUT_ROOT
        if cls.output.exists():
            cls.result = cls.module.audit_existing(cls.output)
        else:
            cls.result = cls.module.build_result(cls.output)

    def test_result_is_h0_envelope_only_and_run_id_is_new(self) -> None:
        self.assertEqual(self.result["schema"], "s22plus-fyg8-p320-stock-candidate-build-v1")
        self.assertEqual(self.result["verdict"], "PASS_P320_STOCK_CANDIDATE_BUILD_H0_ENVELOPE_ONLY")
        self.assertEqual(self.result["status"], "IMPLEMENTED_REVIEW_PENDING")
        self.assertEqual(self.result["run_id_hex"], self.module.P320_RUN_ID.hex())
        self.assertNotEqual(self.result["run_id_hex"], self.module.P319_RUN_ID.hex())
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertEqual(self.result["scope"]["adb_commands"], 0)
        self.assertEqual(self.result["scope"]["odin_invocations"], 0)
        self.assertFalse(self.result["scope"]["live_authority_created"])

    def test_live_p319_lineage_and_helpers_are_pinned(self) -> None:
        lineage = self.result["lineage"]
        self.assertEqual(lineage["p319_result"], self.module.P319_RESULT_IDENTITY)
        self.assertEqual(lineage["p319_consumed_ap"], self.module.P319_AP_IDENTITY)
        self.assertEqual(lineage["p319_runtime"], self.module.P319_RUNTIME_IDENTITY)
        self.assertEqual(lineage["p319_rollback"], self.module.P319_ROLLBACK_IDENTITY)
        self.assertEqual(lineage["p319_candidate_reproductions"], 2)
        self.assertEqual(self.result["helper_sources"]["p319-stock-candidate-build.py"], self.module.P319_STOCK_BUILDER_IDENTITY)
        self.assertEqual(self.result["helper_sources"]["s22plus_o2_loader_core.h"], self.module.O2_LOADER_CORE_IDENTITY)
        self.assertEqual(self.result["inputs"]["p320-kmsg-witness-wiring.py"], self.module.P320_WIRING_IDENTITY)
        self.assertEqual(self.result["inputs"]["p319-kmsg-record-envelope.py"], self.module.P319_ENVELOPE_IDENTITY)
        self.assertEqual(
            self.result["module_bytes"],
            {"s22plus_dwc3_event_latch.ko": self.module.P319_MODULE_LATCH_IDENTITY},
        )
        packager, _ = self.module._load_bound_module(
            self.module.P319_STOCK_BUILDER,
            self.module.P319_STOCK_BUILDER_IDENTITY,
            "p320_test_packager_tools",
        )
        packager._ACTIVE_TOOLS = None
        packager._bind_tools()
        self.assertEqual(
            self.result["tools"],
            {
                name: dict(packager.TOOL_IDENTITIES[name])
                for name in sorted(self.result["tools"])
            },
        )

    def test_runtime_transform_changes_only_declared_record_seam(self) -> None:
        transform = self.result["runtime_transform"]
        self.assertTrue(transform["changed_only_injected_envelope_and_record_seam"])
        self.assertTrue(transform["human_message_only"])
        self.assertTrue(transform["dictionary_lines_excluded"])
        self.assertTrue(transform["header_extensions_excluded"])
        self.assertTrue(transform["fragment_flag_metadata_excluded"])
        self.assertFalse(transform["fragment_reassembly"])
        self.assertTrue(transform["existing_p319_detail_namespace_reused"])
        self.assertFalse(transform["new_detail_namespace"])
        self.assertTrue(transform["fail_closed_on_envelope_error"])
        self.assertTrue(transform["stock_payload_carrier_decoder_semantics_preserved"])
        runtime = (self.output / "stock-sources" / self.module.RUNTIME_INCLUDE_NAME).read_bytes()
        self.assertGreaterEqual(runtime.count(b"P320_KMSG_ENVELOPE_MAX_RECORD"), 2)
        self.assertEqual(runtime.count(b"p320_kmsg_witness_observe_v2"), 2)
        self.assertEqual(runtime.count(b"p319_witness_observe_v2(view.message, view.message_length)"), 1)
        self.assertNotIn(b"p319_witness_observe_v2(record", runtime)
        self.assertNotIn(b"P320_DETAIL_", runtime)
        self.assertNotIn(b"P320_CARRIER_", runtime)

    def test_all_unmodified_stock_sources_remain_byte_identical(self) -> None:
        for name, expected in self.module.P319_SOURCE_IDENTITIES.items():
            output = self.output / "stock-sources" / name
            self.assertEqual(self.module.identity(output.read_bytes()), self.result["source_closure"][name])
            if name != self.module.RUNTIME_INCLUDE_NAME:
                self.assertEqual(output.read_bytes(), (self.module.P319_SOURCE_ROOT / name).read_bytes())

    def test_phase2_has_static_aarch64_ab_identity_and_boot_only_ap(self) -> None:
        phase2 = self.result["phase2"]
        self.assertTrue(phase2["built"])
        self.assertTrue(phase2["static_aarch64"])
        self.assertEqual(phase2["boot_builds"], 2)
        self.assertEqual(phase2["ap_builds"], 2)
        self.assertTrue(phase2["userspace"]["byte_identical"])
        self.assertTrue(phase2["candidate"]["byte_identical"])
        self.assertTrue(phase2["candidate"]["fixed_image"])
        self.assertTrue(phase2["candidate"]["one_boot_img_lz4_member"])
        self.assertEqual(phase2["candidate"]["overlay_members"], ["lib/modules/s22plus_dwc3_event_latch.ko"])
        self.assertTrue(phase2["candidate"]["inherited_modules_not_copied"])
        self.assertTrue(phase2["candidate"]["ap_differs_from_consumed_p319"])
        self.assertNotEqual(phase2["candidate"]["a"]["ap_tar_md5"], self.module.P319_AP_IDENTITY)
        self.assertEqual(phase2["candidate"]["a"], phase2["candidate"]["b"])
        self.assertEqual(phase2["userspace"]["a"], phase2["userspace"]["b"])
        init = (self.output / "userspace-a/init").read_bytes()
        self.assertEqual(init.count(self.module.P320_RUN_ID), 1)
        self.assertNotIn(self.module.P319_RUN_ID, init)

    def test_rollback_is_read_only_and_result_is_audit_reopenable(self) -> None:
        rollback = self.module.stable_bytes(
            self.module.P319_ROLLBACK_AP,
            "test rollback",
            64 << 20,
            self.module.P319_ROLLBACK_IDENTITY,
        )
        self.assertEqual(self.module.identity(rollback), self.module.P319_ROLLBACK_IDENTITY)
        self.assertTrue(self.result["phase2"]["rollback"]["untouched"])
        self.assertEqual(self.result["phase2"]["rollback"]["identity"], self.module.P319_ROLLBACK_IDENTITY)
        self.assertEqual(self.module.audit_existing(self.output), self.result)

    def test_result_json_is_strict_and_no_device_or_final_ready_claim(self) -> None:
        payload = (self.output / "result.json").read_bytes()
        self.assertEqual(json.loads(payload.decode("ascii")), self.result)
        self.assertTrue(any("0x6020" in item for item in self.result["limitations"]))
        self.assertTrue(any("live-ready promotion" in item for item in self.result["limitations"]))
        self.assertTrue(self.result["preservation"]["exact_rollback_untouched"])
        self.assertFalse(self.result["preservation"]["new_p320_carrier_or_detail_abi"])

    def test_runtime_transform_has_composable_post_envelope_seam(self) -> None:
        self.assertEqual(
            self.module.compose_runtime_transforms(
                b"seed", (lambda value: value + b"-observer-contract",)
            ),
            b"seed-observer-contract",
        )
        with self.assertRaises(self.module.AuditError):
            self.module.compose_runtime_transforms(
                b"seed", (lambda value: "not-bytes",)
            )


if __name__ == "__main__":
    unittest.main()
