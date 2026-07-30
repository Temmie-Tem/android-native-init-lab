"""Regression and fault tests for the V3404 D3 owner-timeout successor."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3404_d3_resolved_owner_timeout")
model = load_revalidation("a90_d3_resolved_owner_timeout_v3404")

SERVER_DISTRO = Path("workspace/public/src/native-init/a90_server_distro.c")


class BuildNativeInitBootV3404D3ResolvedOwnerTimeoutTests(unittest.TestCase):
    def test_builder_identity_and_required_marker(self) -> None:
        self.assertEqual(builder.CYCLE, "V3404")
        self.assertEqual(builder.INIT_VERSION, "0.11.160")
        self.assertEqual(builder.INIT_BUILD, "v3404-d3-resolved-owner-timeout")
        required = b"\n".join(builder.REQUIRED_STRINGS)
        self.assertIn(b"owner_timeouts=%u resolved_by_zero_owner_scan=1", required)

    def test_rewrite_updates_v3403_identity(self) -> None:
        text = builder._rewrite_v3404_text(
            "V3403 0.11.159 v3403-d3-immutable-handoff "
            "a90-doomgeneric-v3403"
        )
        self.assertIn("V3404", text)
        self.assertIn("0.11.160", text)
        self.assertIn("v3404-d3-resolved-owner-timeout", text)
        self.assertIn("a90-doomgeneric-v3404", text)
        self.assertNotIn("v3403", text)
        self.assertNotIn("0.11.159", text)

    def test_boot_audit_binds_narrow_timeout_resolution(self) -> None:
        audit = builder._boot_audit_manifest()["d3_immutable_handoff"]
        self.assertTrue(audit["final_zero_owner_scan_resolves_owner_timeout"])
        self.assertTrue(audit["service_scan_and_signal_errors_remain_fatal"])
        self.assertTrue(audit["nonzero_final_owner_count_remains_fatal"])
        self.assertIn("a90_d3_resolved_owner_timeout_v3404.py", audit["source_contract"])

    def test_active_c_source_matches_versioned_contract(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        self.assertEqual(model.validate_source_contract(source), ())

    def test_per_owner_timeout_is_resolved_only_by_successful_zero_scan(self) -> None:
        outcome = model.evaluate_display_cleanup(
            owner_rcs=(0, model.EBUSY, 0),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, 0)
        self.assertEqual(outcome.owner_timeouts, 1)
        self.assertEqual(outcome.resolved_owner_timeouts, 1)

    def test_nonzero_final_owner_count_remains_fatal(self) -> None:
        outcome = model.evaluate_display_cleanup(
            owner_rcs=(model.EBUSY,),
            final_scan_rc=0,
            remaining_owners=1,
        )
        self.assertEqual(outcome.rc, model.EBUSY)
        self.assertEqual(outcome.resolved_owner_timeouts, 0)

    def test_service_failure_is_not_cleared_by_zero_scan(self) -> None:
        outcome = model.evaluate_display_cleanup(
            service_rcs=(-5,),
            owner_rcs=(model.EBUSY,),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, -5)
        self.assertEqual(outcome.resolved_owner_timeouts, 1)

    def test_service_ebusy_is_not_confused_with_owner_timeout(self) -> None:
        outcome = model.evaluate_display_cleanup(
            service_rcs=(model.EBUSY,),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, model.EBUSY)
        self.assertEqual(outcome.owner_timeouts, 0)

    def test_preserving_handoff_does_not_defer_owner_timeout(self) -> None:
        outcome = model.evaluate_display_cleanup(
            strict_mode=False,
            owner_rcs=(model.EBUSY,),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, model.EBUSY)
        self.assertEqual(outcome.owner_timeouts, 0)

    def test_scan_failure_is_not_cleared(self) -> None:
        outcome = model.evaluate_display_cleanup(
            owner_rcs=(model.EBUSY,),
            final_scan_rc=-5,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, -5)
        self.assertEqual(outcome.resolved_owner_timeouts, 0)

    def test_non_timeout_owner_failure_is_not_cleared(self) -> None:
        outcome = model.evaluate_display_cleanup(
            owner_rcs=(-1,),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, -1)
        self.assertEqual(outcome.owner_timeouts, 0)

    def test_non_timeout_owner_failure_survives_resolved_timeout(self) -> None:
        outcome = model.evaluate_display_cleanup(
            owner_rcs=(model.EBUSY, -1),
            final_scan_rc=0,
            remaining_owners=0,
        )
        self.assertEqual(outcome.rc, -1)
        self.assertEqual(outcome.owner_timeouts, 1)
        self.assertEqual(outcome.resolved_owner_timeouts, 1)

    def test_source_gate_rejects_writing_timeout_into_final_rc(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        mutated = source.replace(
            "owner_timeouts++;",
            "final_rc = rc;",
            1,
        )
        issues = model.validate_source_contract(mutated)
        self.assertTrue(any("owner_timeouts++" in issue for issue in issues))
        self.assertTrue(any("per-owner EBUSY" in issue for issue in issues))

    def test_source_gate_rejects_broad_non_strict_timeout_resolution(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        mutated = source.replace(
            "if (!preserve_dpublic && rc == -EBUSY) {",
            "if (rc == -EBUSY) {",
            1,
        )
        issues = model.validate_source_contract(mutated)
        self.assertTrue(any("!preserve_dpublic" in issue for issue in issues))

    def test_source_gate_rejects_clearing_unrelated_error_after_zero_scan(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        mutated = source.replace(
            "} else if (owner_timeouts != 0U) {",
            "} else if (owner_timeouts != 0U) {\n        final_rc = 0;",
            1,
        )
        issues = model.validate_source_contract(mutated)
        self.assertTrue(any("unrelated final_rc" in issue for issue in issues))

    def test_source_gate_rejects_final_owner_scan_removal(self) -> None:
        source = SERVER_DISTRO.read_text(encoding="utf-8")
        mutated = source.replace(
            "scan_rc = d_handoff_count_display_owners(preserve_dpublic, &remaining);",
            "scan_rc = 0;",
            1,
        )
        issues = model.validate_source_contract(mutated)
        self.assertTrue(any("d_handoff_count_display_owners" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
