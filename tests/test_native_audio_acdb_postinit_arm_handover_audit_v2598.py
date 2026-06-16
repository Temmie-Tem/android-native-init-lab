import unittest

import native_audio_acdb_postinit_arm_handover_audit_v2598 as v2598


class V2598PostinitArmHandoverAuditTest(unittest.TestCase):
    def test_payload_selects_existing_evidence_over_redundant_rerun(self) -> None:
        payload = v2598.make_payload()
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(
            payload["decision"],
            "v2598-postinit-arm-handover-superseded-by-existing-live-evidence",
        )
        conclusion = payload["conclusion"]
        self.assertTrue(conclusion["postinit_after_init_return_should_not_be_rerun"])
        self.assertTrue(conclusion["topology_payload_already_captured_by_v2563"])
        self.assertTrue(conclusion["current_frontier_is_per_device_direct_get_after_v2597"])
        self.assertIn("pure-read per-device GET", conclusion["recommended_next_unit"])

    def test_source_contract_has_required_arm_and_zero_buffer_guards(self) -> None:
        contract = v2598.source_contract()
        self.assertTrue(contract["v2562_postinit_manual_arm_implemented"], contract)
        self.assertTrue(contract["v2563_auto_arm_after_initialize_implemented"], contract)
        self.assertTrue(contract["tap_unarmed_path_no_dump_before_real"], contract)
        self.assertTrue(contract["tap_manual_arm_exported"], contract)
        self.assertTrue(contract["tap_zero_buffer_discriminator"], contract)

    def test_report_evidence_matches_known_live_results(self) -> None:
        evidence = v2598.report_evidence()
        self.assertTrue(all(evidence["reports_present"].values()), evidence)
        self.assertTrue(evidence["v2562_postinit_manual_arm_failed_before_arm"], evidence)
        self.assertTrue(evidence["v2576_postinit_manual_arm_repeat_failed_before_arm"], evidence)
        self.assertTrue(evidence["v2563_auto_arm_captured_topology"], evidence)
        self.assertTrue(evidence["v2577_common_topology_entry_arm_timed_out_without_acdbtap"], evidence)
        self.assertTrue(evidence["v2597_direct_preget_live"], evidence)


if __name__ == "__main__":
    unittest.main()
