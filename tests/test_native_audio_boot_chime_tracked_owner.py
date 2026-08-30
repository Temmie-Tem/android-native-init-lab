"""Static contract for serializing the boot chime with menu audio."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "workspace/public/src/native-init/a90_audio.c"
CHIME = ROOT / "workspace/public/src/native-init/a90_audio_chime.h"


class BootChimeTrackedOwnerTests(unittest.TestCase):
    def test_autoplay_defaults_to_pid1_tracked_worker_owner(self) -> None:
        header = CHIME.read_text(encoding="utf-8")
        self.assertIn(
            "#define A90_AUDIO_BOOT_CHIME_TRACKED_OWNER AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT",
            header,
        )

    def test_tracked_path_starts_chime_without_untracked_wrapper_fork(self) -> None:
        source = AUDIO.read_text(encoding="utf-8")
        start = source.index("#if A90_AUDIO_BOOT_CHIME_TRACKED_OWNER")
        end = source.index("#else\n    pid_t pid;", start)
        tracked = source[start:end]

        self.assertIn("rc = audio_chime_cmd(argv, argc);", tracked)
        self.assertIn("audio.boot_chime.owner=pid1-tracked-worker", tracked)
        self.assertIn("audio_play_async_worker_pid", tracked)
        self.assertNotIn("fork()", tracked)

    def test_menu_pre_stop_can_stop_the_same_tracked_worker(self) -> None:
        source = AUDIO.read_text(encoding="utf-8")
        stop_start = source.index("static int audio_stop_cmd")
        stop = source[stop_start : source.index("static int audio_open_control_device", stop_start)]
        tracked = stop.index("audio_play_stop_tracked_worker()")
        status = stop.index("audio_play_stop_status_worker", tracked)
        self.assertLess(tracked, status)

        status_start = source.index("static int audio_play_stop_status_worker")
        status_stop = source[status_start : source.index("static int audio_play_cmd", status_start)]
        self.assertIn("if (audio_play_async_worker_pid == pid)", status_stop)
        self.assertIn("if (kill(pid, SIGTERM) < 0)", status_stop)


if __name__ == "__main__":
    unittest.main()
