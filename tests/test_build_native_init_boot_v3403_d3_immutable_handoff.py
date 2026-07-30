"""Regression and fault tests for the V3403 immutable D3 handoff."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3403_d3_immutable_handoff")
model = load_revalidation("a90_d3_immutable_handoff_v3403")

SERVER_DISTRO = Path("workspace/public/src/native-init/a90_server_distro.c")


class BuildNativeInitBootV3403D3ImmutableHandoffTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3403")
        self.assertEqual(builder.INIT_VERSION, "0.11.159")
        self.assertEqual(builder.INIT_BUILD, "v3403-d3-immutable-handoff")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3403-d3-immutable-handoff",
            b"0.11.159",
            b"A90D3H0",
            b"handoff_display strict=1 preserve_dpublic=0",
            b"required_nonpreserved_owner_count=0 observed=%u",
            b"source_sha phase=%s sha=%s expected_sha_match=1",
            b"work_copy=ready source=%s work=%s",
            b"d3-handoff-work.img",
            b"source_unchanged_after_failure=1",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3402_identity(self) -> None:
        text = builder._rewrite_v3403_text(
            "V3402 0.11.158 v3402-dpublic-hud-presenter-restart-policy "
            "a90-doomgeneric-v3402"
        )
        self.assertIn("V3403", text)
        self.assertIn("0.11.159", text)
        self.assertIn("v3403-d3-immutable-handoff", text)
        self.assertIn("a90-doomgeneric-v3403", text)
        self.assertNotIn("v3402", text)
        self.assertNotIn("0.11.158", text)

    def test_boot_audit_records_immutable_source_contract(self) -> None:
        audit = builder._boot_audit_manifest()["d3_immutable_handoff"]

        self.assertTrue(audit["display_cleanup_before_storage"])
        self.assertTrue(audit["source_recheck_after_display_cleanup"])
        self.assertTrue(audit["work_copy_mounted_rw"])
        self.assertTrue(audit["preexisting_work_copy_refused"])
        self.assertTrue(audit["source_sha_recheck_after_failure"])
        self.assertIn("a90_d3_immutable_handoff_v3403.py", audit["source_contract"])
        self.assertEqual(audit["private_doom_source_pin"], builder.doom_source.PINNED_COMMIT)
        self.assertEqual(
            audit["legacy_v535_manifest_sha256"],
            "e848fafcfe3070a3a37ea389542c4ececdb7db60a8fe511821b847c29c6f647c",
        )

    def test_builder_uses_a_fresh_pinned_private_doom_checkout(self) -> None:
        self.assertTrue(str(builder.PRIVATE_DOOM_SOURCE_ROOT).endswith("doomgeneric-v3403"))
        self.assertEqual(
            builder.doom_source.PINNED_COMMIT,
            "dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284",
        )

    def test_builder_routes_legacy_v535_to_recovered_exact_input(self) -> None:
        self.assertTrue(str(builder.RECOVERED_V535_MANIFEST).endswith(
            "source-v2321-commit/tmp/wifi/"
            "v535-rmt-storage-private-property-runtime/manifest.json"
        ))

    def test_active_c_source_matches_versioned_order_contract(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        self.assertEqual(model.validate_source_contract(source), ())

    def test_source_contract_rejects_mounting_manifest_source(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        mutated = source.replace(
            "d3_attach_loop(A90_D3_WORK_IMAGE, &loop_attached)",
            "d3_attach_loop(image, &loop_attached)",
            1,
        )
        issues = model.validate_source_contract(mutated)
        self.assertTrue(any("d3_attach_loop(A90_D3_WORK_IMAGE" in issue for issue in issues))

    def test_each_pre_switch_failure_preserves_source_and_cleans_work_state(self) -> None:
        for fail_step in model.PRE_SWITCH_STEPS:
            with self.subTest(fail_step=fail_step):
                state = model.simulate_handoff(
                    owners=(101, 202, 303),
                    fail_step=fail_step,
                )
                self.assertTrue(state.source_unchanged)
                self.assertFalse(state.work_exists)
                self.assertFalse(state.loop_attached)
                self.assertFalse(state.root_mounted)
                self.assertFalse(state.mounts_moved)
                self.assertFalse(state.exec_reached)
                self.assertIn("verify_source_after_failure", state.history)

    def test_multiple_drm_owners_are_all_stopped_before_storage(self) -> None:
        state = model.simulate_handoff(owners=(101, 202, 303, 404))

        self.assertEqual(state.owners, [])
        self.assertTrue(state.exec_reached)
        self.assertLess(state.history.index("stop_drm_owner:404"), state.history.index("copy_work"))
        self.assertLess(state.history.index("verify_zero_owners"), state.history.index("attach_loop"))
        self.assertLess(state.history.index("rehash_source"), state.history.index("mount_rw"))

    def test_ebusy_owner_fails_before_copy_loop_or_mount(self) -> None:
        state = model.simulate_handoff(
            owners=(101, 202, 303),
            busy_owner=202,
        )

        self.assertEqual(state.rc, -16)
        self.assertTrue(state.source_unchanged)
        self.assertFalse(state.work_exists)
        self.assertFalse(state.loop_attached)
        self.assertFalse(state.root_mounted)
        self.assertNotIn("copy_work", state.history)
        self.assertNotIn("attach_loop", state.history)
        self.assertNotIn("mount_rw", state.history)


if __name__ == "__main__":
    unittest.main()
