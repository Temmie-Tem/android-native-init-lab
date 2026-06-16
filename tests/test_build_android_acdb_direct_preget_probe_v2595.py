"""Tests for the V2595 ACDB direct pre-GET build gate."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2595 = load_revalidation("build_android_acdb_direct_preget_probe_v2595")


class AcdbDirectPregetProbeV2595(unittest.TestCase):
    def test_source_state_requires_direct_query_and_rejects_send_route(self) -> None:
        state = v2595.source_state()

        self.assertTrue(state["required"]["preget_cmd_0x1122e"])
        self.assertTrue(state["required"]["preget_app_id_0x11135"])
        self.assertTrue(state["required"]["preget_geometry_4_4"])
        self.assertTrue(state["required"]["preget_direct_acdb_ioctl_call"])
        self.assertTrue(state["required"]["preget_exits_before_init_tail"])
        self.assertFalse(state["prohibited"]["preget_calls_send_audio_cal"])
        self.assertFalse(state["prohibited"]["preget_opens_msm_audio_cal"])
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])

    def test_make_payload_without_build_is_host_only_and_boundary_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                build=False,
                build_root=Path(tmp) / "build",
                clang=v2595.TOOLCHAIN_ROOT / "bin/clang",
                lld=v2595.TOOLCHAIN_ROOT / "bin/ld.lld",
                readelf="readelf",
                file="file",
            )

            payload = v2595.make_payload(args)

        self.assertTrue(payload["host_only_build"])
        self.assertTrue(payload["measurement_boundary"]["no_live_default"])
        self.assertTrue(payload["measurement_boundary"]["no_native_replay"])
        self.assertTrue(payload["measurement_boundary"]["no_speaker_write"])
        self.assertTrue(payload["capture_contract"]["skips_send_audio_cal_v5"])
        self.assertEqual(
            payload["capture_contract"]["direct_query"],
            "acdb_ioctl(0x1122e, &0x11135, 4, &out_word, 4)",
        )
        self.assertEqual(payload["build"]["reason"], "pass --build to materialize private ARM32 artifacts")


if __name__ == "__main__":
    unittest.main()
