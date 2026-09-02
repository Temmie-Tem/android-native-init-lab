from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P327StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load(
            "p327_runtime_build_test",
            REVALIDATION / "s22plus_fyg8_p327_framed_exec_runtime.py",
        )
        cls.artifact = load(
            "p327_artifact_build_test",
            REVALIDATION / "s22plus_fyg8_p327_artifact_identity.py",
        )
        cls.adapter = load(
            "p327_adapter_build_test",
            REVALIDATION / "s22plus_fyg8_p327_stock_process_v2_adapter.py",
        )
        cls.builder = load(
            "p327_builder_test",
            ANALYSIS / "s22plus_fyg8_p327_stock_candidate_build.py",
        )
        cls.result = cls.builder.audit_existing()

    def test_fresh_image_is_same_size_and_rejects_predecessor_ap(self) -> None:
        source = self.artifact.stable_bytes(
            self.artifact.P319_IMAGE,
            "P319 Image",
            64 << 20,
            self.artifact.P319_IMAGE_IDENTITY,
        )
        image, receipt = self.artifact.transform_image(source)
        self.assertEqual(len(image), len(source))
        self.assertEqual(
            receipt["target"]["run_id_hex"], self.runtime.P327_RUN_ID_HEX
        )
        self.assertEqual(
            self.artifact.validate_image(image)["run_id_hex"],
            self.runtime.P327_RUN_ID_HEX,
        )
        p326_ap = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p326/"
            "stock-candidate-build-v1-20260902-08/candidate-a/odin4/AP.tar.md5"
        )
        with self.assertRaises(self.artifact.ArtifactIdentityError):
            self.artifact.inspect_ap(p326_ap)

    def test_adapter_is_fresh_noncausal_and_rejects_p326(self) -> None:
        audit = self.adapter.audit()
        self.assertEqual(audit["run_id"], self.runtime.P327_RUN_ID_HEX)
        self.assertEqual(
            audit["predecessor_run_id"], self.artifact.P326_RUN_ID_HEX
        )
        self.assertFalse(audit["encoder_failure_is_success"])
        self.assertFalse(audit["encoder_failure_is_causal"])
        fixture = self.adapter.acceptance_fixture()
        checked = self.adapter.validate_acceptance_item(fixture)
        self.assertEqual(checked["run_id"], self.runtime.P327_RUN_ID_HEX)
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.decode_record(
                self.adapter.P326_RUN_ID,
                expected_run_id=self.adapter.P326_RUN_ID,
            )

    def test_builder_reopens_ab_boot_only_candidate(self) -> None:
        candidate = self.result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p326"])
        self.assertEqual(
            candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"]
        )
        self.assertNotEqual(
            candidate["a"]["ap_tar_md5"],
            self.result["lineage"]["predecessor_ap"],
        )
        for label in ("a", "b"):
            package = candidate[label]["package"]
            self.assertEqual(package["members"], ["boot.img.lz4"])
            self.assertEqual(
                package["schema"], "s22plus_fyg8_p327_boot_only_package_v1"
            )
            self.assertEqual(package["busybox"], self.builder.BUSYBOX_IDENTITY)

    def test_image_init_and_ap_join_one_fresh_run_id(self) -> None:
        candidate = self.result["phase2"]["candidate"]
        join = candidate["run_id_join"]
        self.assertTrue(join["joined"])
        self.assertEqual(join["run_id_hex"], self.runtime.P327_RUN_ID_HEX)
        for label in ("a", "b"):
            self.assertTrue(join[label]["joined"])
            self.assertTrue(join[label]["boot_only"])
            self.assertEqual(
                join[label]["image"]["run_id_hex"], self.runtime.P327_RUN_ID_HEX
            )
            self.assertEqual(
                join[label]["init"]["run_id_hex"], self.runtime.P327_RUN_ID_HEX
            )

    def test_runtime_source_delta_and_fixed_commands_are_bound(self) -> None:
        repair = self.result["lineage"]["runtime_repair"]
        self.assertEqual(
            repair["changed_anchors"],
            ["p326_console_helper", "p319_stock_publish"],
        )
        self.assertEqual(repair["command_policy"], "fixed_three_command_proof_v1")
        self.assertFalse(repair["caller_selected_command"])
        self.assertEqual(
            self.result["framed_exec"]["commands"],
            [self.builder.identity(item) for item in self.runtime.DEFAULT_COMMANDS],
        )
        self.assertFalse(self.result["framed_exec"]["interactive_pty"])

    def test_normalization_and_audit_are_idempotent(self) -> None:
        self.assertEqual(self.builder._normalize_result(self.result), self.result)
        self.assertEqual(self.builder.audit_existing(), self.result)

    def test_rollback_and_scope_remain_unchanged_host_only(self) -> None:
        self.assertTrue(self.result["phase2"]["rollback"]["untouched"])
        self.assertTrue(self.result["preservation"]["rollback_untouched"])
        self.assertEqual(self.result["scope"]["tier"], "H0")
        self.assertFalse(self.result["scope"]["device_contact"])
        self.assertEqual(self.result["scope"]["adb_commands"], 0)
        self.assertEqual(self.result["scope"]["odin_invocations"], 0)
        self.assertFalse(self.result["scope"]["live_authority_created"])


if __name__ == "__main__":
    unittest.main()
