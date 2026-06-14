"""Host-only tests for the V2386 PCM write diagnostic probe builder."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation

v2386 = load_revalidation("build_audio_pcm_write_probe_v2386")


class AudioPcmWriteProbeBuilder(unittest.TestCase):
    def test_metadata_points_to_pinned_tinyalsa_and_private_build(self) -> None:
        self.assertEqual(v2386.RUN_ID, "V2386")
        self.assertEqual(v2386.BUILD_TAG, "v2386-audio-pcm-write-probe")
        self.assertEqual(v2386.TOOL_NAME, "a90_pcm_write_probe_v2386")
        self.assertIn("workspace/private/builds/audio", str(v2386.DEFAULT_BUILD_ROOT))
        self.assertEqual(v2386.tiny.TINYALSA_COMMIT, "e14bf1479ebaaabf60bc4472ce8d304f72f03c32")
        self.assertIn("-static", v2386.CFLAGS)

    def test_probe_source_has_error_markers_and_no_route_mutation(self) -> None:
        source = (v2386.tiny.ROOT / v2386.SOURCE_REL).read_text(encoding="utf-8")

        self.assertIn("A90_PCM_PROBE_WRITE_ERROR", source)
        self.assertIn("pcm_get_error", source)
        self.assertIn("errno", source)
        self.assertIn("pcm_write", source)
        self.assertNotIn("tinymix", source)
        self.assertNotIn("mixer", source.lower())
        self.assertNotIn("/dev/block", source)

    def test_existing_manifest_describes_static_aarch64_probe_when_built(self) -> None:
        manifest = v2386.DEFAULT_MANIFEST
        if not manifest.exists():
            self.skipTest("private V2386 probe manifest has not been built")
        data = __import__("json").loads(manifest.read_text(encoding="utf-8"))
        tool = data["build"]["tools"][v2386.TOOL_NAME]
        self.assertTrue((v2386.tiny.ROOT / tool["path"]).exists())
        self.assertIn("ARM aarch64", tool["file"])
        self.assertIn("statically linked", tool["file"])
        self.assertTrue(data["diagnostic_contract"]["reports_pcm_get_error"])
        self.assertTrue(data["diagnostic_contract"]["reports_errno"])


if __name__ == "__main__":
    unittest.main()
