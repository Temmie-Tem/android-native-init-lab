"""Host-only P3.45 real A/B artifact and builder audits."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for path in (ANALYSIS, REVALIDATION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import s22plus_fyg8_p345_stock_candidate_build as builder  # noqa: E402


class P345StockCandidateBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = builder.DEFAULT_OUTPUT_ROOT

    def test_existing_build_reopens_real_ab_join_and_shell_delta(self) -> None:
        result = builder.audit_existing(self.output)
        self.assertEqual(result["schema"], builder.SCHEMA)
        self.assertEqual(result["run_id_hex"], builder.P345_RUN_ID_HEX)
        self.assertEqual(result["scope"]["tier"], "H0")
        self.assertTrue(result["scope"]["host_only"])
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["live_authorized"])
        self.assertFalse(result["runtime_behavior_unchanged"])
        self.assertNotIn("default_runtime_behavior_unchanged", result)
        self.assertTrue(result["fixed_outer_id_nonce_commands_unchanged"])
        self.assertTrue(result["read_only_child_boundary"])
        self.assertTrue(result["authenticated_cancel"])
        self.assertFalse(result["catalog_unchanged"])
        self.assertNotIn("named_readonly_catalog_unchanged", result)
        self.assertTrue(result["middle_command_validator_widened"])
        self.assertFalse(result["f1_ready"])
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["ab_artifact_identity_equal"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], builder.P345_RUN_ID_HEX)
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertEqual(
            candidate["a"]["ap_tar_md5"],
            result["p345_ap_identity"],
        )
        self.assertEqual(
            candidate["run_id_join"]["image_run_id_hex"], builder.P345_RUN_ID_HEX
        )
        self.assertEqual(
            candidate["run_id_join"]["init_run_id_hex"], builder.P345_RUN_ID_HEX
        )
        self.assertTrue(result["read_only_child_boundary"])
        self.assertTrue(result["authenticated_cancel"])
        self.assertTrue(result["preservation"]["idle_listener_unchanged"])
        self.assertEqual(result["preservation"]["same_fd_session_count"], 5)
        self.assertEqual(result["preservation"]["idle_seconds"], 0)
        self.assertEqual(result["preservation"]["total_session_count"], 5)
        self.assertEqual(result["preservation"]["total_command_count"], 15)
        self.assertEqual(
            result["preservation"]["resident_lease_schema"],
            None,
        )
        self.assertFalse(result["preservation"]["later_action_lease_active"])
        self.assertNotIn(
            "default_runtime_behavior_unchanged", result["preservation"]
        )
        self.assertTrue(
            result["preservation"]["fixed_outer_id_nonce_commands_unchanged"]
        )
        self.assertEqual(
            result["qualification_observer"]["session_count"],
            builder.observer.SESSION_COUNT,
        )

    def test_p345_image_transform_is_same_length_and_40695_gzip(self) -> None:
        source = builder.P344_OUTPUT / "inputs/fixed-Image"
        original = source.read_bytes()
        transformed, receipt = builder.artifact.transform_image(original)
        self.assertEqual(len(transformed), len(original))
        self.assertEqual(builder.artifact.identity(transformed), builder.P345_IMAGE_IDENTITY)
        self.assertEqual(receipt["method"], "identity_only_post_link_v1")
        self.assertEqual(receipt["source"]["run_id_hex"], builder.P344_RUN_ID_HEX)
        self.assertEqual(receipt["target"]["run_id_hex"], builder.P345_RUN_ID_HEX)
        self.assertEqual(receipt["ikconfig"]["compressed_size"], 40_695)
        self.assertTrue(all(receipt["preserved"].values()))
        self.assertEqual(
            builder.artifact.validate_image(transformed)["run_id_hex"],
            builder.P345_RUN_ID_HEX,
        )
        self.assertNotIn(builder.P344_RUN_ID_HEX.encode("ascii"), transformed)

    def test_real_built_ab_joins_fresh_image_init_and_child(self) -> None:
        result = builder.audit_existing(self.output)
        image = (self.output / "inputs/fixed-Image").read_bytes()
        init = (self.output / "userspace-a/init").read_bytes()
        child_payload = (self.output / "userspace-a/s22-e1-child").read_bytes()
        expected_ap = result["p345_ap_identity"]
        for label in ("a", "b"):
            value = builder.artifact.inspect_ap(
                self.output / f"candidate-{label}/odin4/AP.tar.md5",
                expected_run_id=builder.P345_RUN_ID,
                expected_image=image,
                expected_init=init,
                expected_child=child_payload,
                expected_ap=expected_ap,
                label=f"P345 candidate {label} AP",
            )
            self.assertTrue(value["joined"])
            self.assertEqual(value["run_id_hex"], builder.P345_RUN_ID_HEX)

    def test_consumed_p344_ap_is_not_rollback_and_child_input_is_exact(self) -> None:
        result = builder.audit_existing(self.output)
        with self.assertRaises(builder.artifact.ArtifactIdentityError):
            builder.artifact.validate_rollback_ap(
                self.output / "candidate-a/odin4/AP.tar.md5",
                builder.P344_AP_IDENTITY,
            )
        child_input = (self.output / "inputs/p345-readonly-child.inc.c").read_bytes()
        self.assertEqual(builder.identity(child_input), builder.P345_CHILD_IDENTITY)
        self.assertEqual(
            result["inputs"]["p345-readonly-child.inc.c"],
            builder.P345_CHILD_IDENTITY,
        )
        self.assertEqual(
            result["inputs"]["p345-readonly-child.inc.c"]["sha256"],
            builder.child.SOURCE_IDENTITY["sha256"],
        )
        self.assertEqual(
            result["inputs"]["p345-artifact-identity.py"],
            builder.P345_ARTIFACT_IDENTITY,
        )
        self.assertEqual(
            result["inputs"]["p345-observer.py"],
            builder.P345_OBSERVER_IDENTITY,
        )
        self.assertEqual(
            result["inputs"]["p345-adapter.py"],
            builder.P345_ADAPTER_IDENTITY,
        )


if __name__ == "__main__":
    unittest.main()
