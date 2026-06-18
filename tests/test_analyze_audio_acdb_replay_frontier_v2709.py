import unittest

import analyze_audio_acdb_replay_frontier_v2709 as v2709


class TestV2709ReplayFrontier(unittest.TestCase):
    def test_parse_setcal_log_targets(self):
        text = """
A90_ACDB_SETCAL_ALLOCATE_OK index=1 cal_type=24 size=1180
A90_ACDB_SETCAL_SET_OK index=1 cal_type=24 kind=1 has_payload=1
A90_ACDB_SETCAL_DEALLOCATE_OK index=1 cal_type=24
A90_ACDB_SETCAL_ALLOCATE_OK index=2 cal_type=10 size=16076
A90_ACDB_SETCAL_SET_OK index=2 cal_type=10 kind=1 has_payload=1
A90_ACDB_SETCAL_DEALLOCATE_OK index=2 cal_type=10
A90_ACDB_SETCAL_ALLOCATE_OK index=3 cal_type=14 size=2356
A90_ACDB_SETCAL_SET_OK index=3 cal_type=14 kind=1 has_payload=1
A90_ACDB_SETCAL_DEALLOCATE_OK index=3 cal_type=14
"""
        parsed = v2709.parse_setcal_log(text)
        self.assertEqual(parsed[24]["allocated_size"], 1180)
        self.assertTrue(parsed[10]["set_ok"])
        self.assertTrue(parsed[14]["deallocated"])

    def test_dmesg_markers(self):
        markers = v2709.dmesg_markers("""
q6asm_callback: cmd = 0x10dbe returned error = 0x2
send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]
msm_pcm_open: Could not allocate memory
SM8150 Media1: ASoC: failed to start FE -12
""")
        self.assertTrue(markers["q6asm_error_0x2"])
        self.assertTrue(markers["asm_custom_topology_ebadparam"])
        self.assertTrue(markers["pcm_open_enomem"])
        self.assertTrue(markers["frontend_failed_minus12"])

    def test_classify_get_payload_exhausted(self):
        v2704 = {cal_type: {"success": True, "raw_ok": True} for cal_type in v2709.TARGET_CAL_TYPES}
        manifest = {cal_type: {"basic_payload": True} for cal_type in v2709.TARGET_CAL_TYPES}
        replay = {cal_type: {"set_ok": True, "deallocated": True} for cal_type in v2709.TARGET_CAL_TYPES}
        markers = {"asm_custom_topology_ebadparam": True}
        result = {"playback_attempted": True}
        classified = v2709.classify(v2704, manifest, replay, markers, result)
        self.assertEqual(classified["decision"], "v2709-get-payload-replay-exhausted-need-byte-exact-topology-set-capture")
        self.assertTrue(classified["same_manifest_rerun_low_value"])

    def test_missing_evidence_detects_absent_marker(self):
        v2704 = {24: {"success": True}, 10: {"success": True}, 14: {"success": True}}
        manifest = {24: {}, 10: {}, 14: {}}
        replay = {24: {"set_ok": True}, 10: {"set_ok": True}, 14: {"set_ok": True}}
        missing = v2709.missing_evidence(v2704, manifest, replay, {"asm_custom_topology_ebadparam": False})
        self.assertIn("V2708 dmesg ASM ADSP_EBADPARAM marker", missing)


if __name__ == "__main__":
    unittest.main()
