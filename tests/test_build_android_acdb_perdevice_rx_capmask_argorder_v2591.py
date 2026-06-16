"""Host-only tests for the V2591 ACDB corrected send_audio_cal_v5 arg-order build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation

v2591 = load_revalidation("build_android_acdb_perdevice_rx_capmask_argorder_v2591")


class AcdbPerdeviceRxCapmaskArgorderBuildV2591(unittest.TestCase):
    def test_source_state_preserves_history_and_enables_fixed_stack_order(self) -> None:
        state = v2591.source_state()
        required = state["required"]

        self.assertTrue(state["required_ok"], state)
        self.assertTrue(state["prohibited_ok"], state)
        self.assertTrue(required["preinit_skips_real_common_topology_by_default"])
        self.assertTrue(required["preinit_calls_send_audio_cal_v5"])
        self.assertTrue(required["preinit_rx_path_default_zero"])
        self.assertTrue(required["preinit_rx_path_compile_override_guard"])
        self.assertTrue(required["preinit_fixed_stack_order_default_zero"])
        self.assertTrue(required["preinit_fixed_stack_order_compile_override_guard"])
        self.assertEqual(state["v2591_delta"]["send_audio_cal_v5_arg2"], 1)
        self.assertEqual(state["v2591_delta"]["send_audio_cal_v5_stack_args_5_6_7"], [0, 48000, 1])
        self.assertEqual(
            state["v2591_delta"]["compile_overrides"],
            ["-DA90_SPEAKER_RX_PATH=1", "-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1"],
        )

    def test_payload_contract_documents_corrected_arg_order_and_boundaries(self) -> None:
        class Args:
            build = False
            build_root = v2591.DEFAULT_BUILD_ROOT
            readelf = "readelf"
            file = "file"
            clang = v2591.v2572.TOOLCHAIN_ROOT / "bin/clang"
            lld = v2591.v2572.TOOLCHAIN_ROOT / "bin/ld.lld"

        payload = v2591.make_payload(Args())
        contract = payload["capture_contract"]
        boundary = payload["measurement_boundary"]

        self.assertEqual(
            contract["per_device_call"],
            "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        )
        self.assertIn("stack args", contract["delta_from_v2586"])
        self.assertTrue(boundary["no_live_default"])
        self.assertTrue(boundary["no_native_replay"])
        self.assertTrue(boundary["no_speaker_write"])
        self.assertEqual(boundary["fake_audio_cal_env"], "A90_ACDB_FAKE_ALLOCATE=1")


if __name__ == "__main__":
    unittest.main()
