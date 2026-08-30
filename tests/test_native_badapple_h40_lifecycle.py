"""Host-only source contract for the H40 Bad Apple demo lifecycle."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
VIDEO = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
AUDIO = ROOT / "workspace/public/src/native-init/a90_audio.c"
AUDIO_H = ROOT / "workspace/public/src/native-init/a90_audio.h"
MAIN = ROOT / "workspace/public/src/native-init/v724/90_main.inc.c"


class H40BadAppleLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        menu = MENU.read_text(encoding="utf-8")
        self.block = menu[
            menu.index("case SCREEN_MENU_DEMO_BADAPPLE:") :
            menu.index("case SCREEN_MENU_DEMO_NYAN:")
        ]
        self.video = VIDEO.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_selection_acknowledges_before_blocking_work(self) -> None:
        starting = self.block.index("STARTING - PRESS ANY HARDWARE KEY TO CANCEL")
        release = self.block.index("a90_input_close(ctx)")
        pre_stop = self.block.index('auto_hud_stop_demo_audio("badapple", "pre")')
        self.assertLess(starting, release)
        self.assertLess(release, pre_stop)
        self.assertIn('a90_kms_present("demo-transition", false)', MENU.read_text(encoding="utf-8"))

    def test_audio_status_is_bound_to_spawned_worker(self) -> None:
        self.assertIn('"--sync-audio-pid", audio_pid_text', self.block)
        self.assertIn("a90_audio_current_worker_pid()", self.block)
        self.assertIn("audio_pid <= 1", self.block)
        self.assertIn("audio.play.worker.pid", self.video)
        self.assertIn("status_pid != sync->expected_pid", self.video)
        self.assertIn("pid_t a90_audio_current_worker_pid(void)", AUDIO_H.read_text(encoding="utf-8"))
        self.assertIn("return audio_play_async_worker_pid", AUDIO.read_text(encoding="utf-8"))

        status = self.video[
            self.video.index("static int video_audio_sync_read_status") :
            self.video.index("static int video_audio_sync_wait_ready")
        ]
        pid_check = status.index("status_pid != sync->expected_pid")
        done_check = status.index('strstr(status, "audio.play.worker.done=1")')
        self.assertLess(pid_check, done_check)

    def test_readiness_is_bounded_fail_fast_and_physically_cancellable(self) -> None:
        self.assertIn('"--sync-wait-ms", "10000"', self.block)
        self.assertNotIn('"--sync-wait-ms", "60000"', self.block)
        wait = self.video[
            self.video.index("static int video_audio_sync_wait_ready") :
            self.video.index("struct video_stream_physical_exit {")
        ]
        self.assertIn("status_rc < 0", wait)
        self.assertIn("video_stream_physical_exit_poll(physical_exit)", wait)
        self.assertIn("cancelled_by_physical_input=1", wait)
        self.assertIn("worker_done_before_ready=1", self.video)

    def test_worker_bound_demo_requires_physical_exit_input(self) -> None:
        play = self.video[
            self.video.index("static int video_stream_play") :
            self.video.index("static const char *video_cache_preset_sha256")
        ]
        open_call = play.index("rc = video_stream_physical_exit_open(&physical_exit)")
        required = play.index("audio_sync->expected_pid > 0 && rc < 0", open_call)
        sync_wait = play.index("video_audio_sync_wait_ready", required)
        self.assertLess(open_call, required)
        self.assertLess(required, sync_wait)
        self.assertIn("video.stream.physical_exit.required=1 open_rc=%d", play)
        failure = play[required:sync_wait]
        self.assertIn("free(decode_buffer)", failure)
        self.assertIn("free(frame_buffer)", failure)
        self.assertIn("close(fd)", failure)

    def test_input_and_audio_are_closed_on_every_return(self) -> None:
        video_call = self.block.index("cmd_video_demo(")
        post_stop = self.block.index('auto_hud_stop_demo_audio("badapple", "post")')
        reopen = self.block.index('a90_input_open(ctx, "autohud")')
        menu = self.block.index("auto_hud_show_menu(state, false)")
        self.assertLess(video_call, post_stop)
        self.assertLess(post_stop, reopen)
        self.assertLess(reopen, menu)
        self.assertIn("FAILED RC=%d - RETURNING TO MENU", self.block)

    def test_cold_boot_replays_only_the_h37_sibling_sequence(self) -> None:
        helper = self.main[
            self.main.index("static int v641_run_badapple_sibling_ssctl_once") :
            self.main.index("int main(void)")
        ]
        for subsystem in ("adsp", "cdsp", "slpi"):
            self.assertIn(f'{{ "{subsystem}", "/sys/kernel/boot_{subsystem}/boot" }}', helper)
        self.assertIn("A90_BADAPPLE_BOOT_EXPLICIT_SIBLING_SSCTL", self.main)
        self.assertIn("audio.boot_prereq.sibling_ssctl.cache_flag_required=0", self.main)

    def test_boot_prerequisites_and_chime_precede_interactive_hud_fork(self) -> None:
        cold_boot = self.main[
            self.main.index("v724_run_qrtr_servloc_boot_once();") :
            self.main.index("}  /* end !a90_reloaded live-service re-init guard */")
        ]
        mounts = cold_boot.index("v641_prepare_firmware_mounts()")
        siblings = cold_boot.index("v641_run_badapple_sibling_ssctl_once()", mounts)
        chime = cold_boot.index("a90_audio_boot_chime_start_once()", siblings)
        hud = cold_boot.index("start_auto_hud(BOOT_HUD_REFRESH_SECONDS", chime)
        self.assertLess(mounts, siblings)
        self.assertLess(siblings, chime)
        self.assertLess(chime, hud)
        self.assertEqual(cold_boot.count("a90_audio_boot_chime_start_once()"), 1)
        self.assertIn("inherited tracked-worker", cold_boot)


if __name__ == "__main__":
    unittest.main()
