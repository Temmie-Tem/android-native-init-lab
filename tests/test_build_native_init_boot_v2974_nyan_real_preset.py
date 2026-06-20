import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_native_init_boot_v2974_nyan_real_preset as build_v2974


class BuildNativeInitBootV2974NyanRealPreset(unittest.TestCase):
    def test_version_axes_are_distinct(self) -> None:
        self.assertEqual(build_v2974.CYCLE, "V2974")
        self.assertEqual(build_v2974.INIT_VERSION, "0.10.59")
        self.assertEqual(build_v2974.INIT_BUILD, "v2974-nyan-real-preset")
        self.assertTrue(str(build_v2974.BOOT_IMAGE).endswith("boot_linux_v2974_nyan_real_preset.img"))

    def test_required_markers_capture_real_nyan_surface(self) -> None:
        markers = {marker.decode("ascii") for marker in build_v2974.REQUIRED_STRINGS}
        self.assertIn("video.status.version=9", markers)
        self.assertIn("video cache preset [badapple|badapple-scale|nyan]", markers)
        self.assertIn("video demo [badapple|badapple-scale|nyan]", markers)
        self.assertIn("nyancat-v2973-pal8-rle-preview", markers)
        self.assertIn("9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573", markers)
        self.assertIn("menu.demo.nyan.action=play-av-preview", markers)
        self.assertIn("menu.demo.nyan.audio_pcm=/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le", markers)
        self.assertIn("A90VSTR2", markers)
        self.assertIn("pal8-rle", markers)

    def test_report_names_deferred_live_validation_and_private_media_policy(self) -> None:
        manifest = {
            "decision": build_v2974.DECISION,
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2974_nyan_real_preset.img",
            "boot_sha256": "0" * 64,
            "init_version": build_v2974.INIT_VERSION,
            "init_build": build_v2974.INIT_BUILD,
            "v2974_marker_strings": ["video.status.version=9"],
            "audio_bundled_setcal": {},
        }
        report = build_v2974.render_report(manifest, ("-DHELPER",), ("-DINIT",))
        self.assertIn("deferred to V2975", report)
        self.assertIn("Media bytes remain private/untracked", report)
        self.assertIn("No device action was performed", report)
        self.assertIn("nyan-real-preset-candidate", report)


if __name__ == "__main__":
    unittest.main()
