import unittest

import build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674 as v2674


class V2674BuildContractTest(unittest.TestCase):
    def test_source_contract(self):
        state = v2674.source_state()
        self.assertTrue(state["required_ok"], state["required"])
        self.assertTrue(state["prohibited_ok"], state["prohibited"])
        self.assertEqual(state["v2674_contract"]["targets"][24], "0x000130da")
        self.assertEqual(state["v2674_contract"]["targets"][10], "0x00011394")
        self.assertEqual(state["v2674_contract"]["targets"][14], "0x00012e01")
        self.assertTrue(state["required"]["helper_does_not_arm_after_init"])
        self.assertTrue(state["required"]["helper_does_not_call_lower_after_init"])
        self.assertTrue(state["required"]["preload_arms_inside_common_hook"])
        self.assertTrue(state["required"]["preload_runs_lower_inside_common_hook"])
        self.assertTrue(state["required"]["preload_exits_after_inhook_lower"])

    def test_make_payload_without_private_build(self):
        args = v2674.parse_args([])
        payload = v2674.make_payload(args)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertIn("create_cal_node", payload["capture_contract"]["hidden_offsets"])
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [24, 10, 14])
        self.assertEqual(
            payload["capture_contract"]["call_order"],
            "acdb_loader_init_v3 -> init common skip hook -> patch initialized -> a90_arm_capture -> a90_run_lower_hidden_nodes -> exit_group(0)",
        )

    def test_patched_constants_restore(self):
        old_helper = v2674.v2659.HELPER_SOURCE_REL
        old_preinit = v2674.v2659.PREINIT_SOURCE_REL
        with v2674.patched_v2659_constants():
            self.assertEqual(v2674.v2659.HELPER_SOURCE_REL, v2674.HELPER_SOURCE_REL)
            self.assertEqual(v2674.v2659.PREINIT_SOURCE_REL, v2674.PREINIT_SOURCE_REL)
        self.assertEqual(v2674.v2659.HELPER_SOURCE_REL, old_helper)
        self.assertEqual(v2674.v2659.PREINIT_SOURCE_REL, old_preinit)


if __name__ == "__main__":
    unittest.main()
