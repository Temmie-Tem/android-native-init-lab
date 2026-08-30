"""Host-only ordering contract for the H39 Bad Apple audio prerequisite."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workspace/public/src/native-init/v724/90_main.inc.c"


class AudioBootPrereqFirmwareMountTests(unittest.TestCase):
    def test_feature_defaults_off_and_is_explicitly_gated(self) -> None:
        source = MAIN.read_text(encoding="utf-8")
        self.assertIn("#define A90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS 0", source)
        self.assertIn("#if A90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS", source)

    def test_firmware_mount_precedes_tracked_boot_chime(self) -> None:
        source = MAIN.read_text(encoding="utf-8")
        block = source[
            source.index("#if A90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS") :
            source.index("(void)a90_audio_boot_chime_start_once();") + 42
        ]
        self.assertLess(
            block.index("v641_prepare_firmware_mounts()"),
            block.index("a90_audio_boot_chime_start_once()"),
        )
        self.assertIn("audio.boot_prereq.firmware_mounts.cache_flag_required=0", block)
        self.assertIn("audio.boot_prereq.firmware_mounts.rc=%d", block)


if __name__ == "__main__":
    unittest.main()
