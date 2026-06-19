"""Tests for the V2801 V2798 readiness replay runner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2798_audio_msm_audio_cal_devnode.py"
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_v2798_readiness_replay_live_handoff_v2801.py"


def load_live_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2801_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioV2798ReadinessReplayV2801(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_live_module()

    def test_sound_control_wait_matches_prior_device_settle_budget(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("AUDIO_PLAY_ASYNC_STATUS_PATH", text)
        self.assertIn("audio_play_start_worker", text)
        self.assertIn("audio.play.execute.async_worker=1", text)
        self.assertIn(
            "audio_setcal_path_has_prefix(path, AUDIO_SETCAL_LEGACY_REPLAY_PREFIX)",
            text,
        )
        self.assertIn("audio.play.integrated.setcal.verify_load_files=0", text)
        self.assertIn("audio_setcal_verify_manifest(profile, manifest_path, &totals, false, NULL, &plan)", text)
        self.assertIn('strcmp(argv[1], "play-status") == 0', text)
        self.assertIn("a90_console_redirect_child_to_file(AUDIO_PLAY_ASYNC_LOG_PATH)", text)
        self.assertIn(
            'audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )
        self.assertNotIn(
            'audio_wait_for_audio_condition("sound_control", 20000, 250, audio_condition_sound_control_ready, profile)',
            text,
        )

    def test_ion_devnode_is_materialized_before_ion_open(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn('#define AUDIO_SETCAL_SYSFS_ION_DEV "/sys/class/misc/ion/dev"', text)
        self.assertIn("static int audio_materialize_ion_devnode_once(void);", text)
        self.assertIn("static int audio_materialize_ion_devnode_once(void) {", text)
        self.assertIn("read_trimmed_text_file(AUDIO_SETCAL_SYSFS_ION_DEV", text)
        self.assertIn("parse_dev_numbers(dev_info, &major_num, &minor_num)", text)
        self.assertIn("mknod(AUDIO_SETCAL_DEV_ION, S_IFCHR | 0600, wanted)", text)
        self.assertIn("audio.ion_materialize.created=1", text)
        self.assertIn("audio_materialize_ion_devnode_once() < 0", text)
        self.assertLess(
            text.index("audio_materialize_ion_devnode_once() < 0"),
            text.index("open(AUDIO_SETCAL_DEV_ION, O_RDONLY | O_CLOEXEC)"),
        )

    def test_dmabuf_msync_failure_is_nonfatal(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn("audio.setcal.execute.entry.%d.msync_ok=0 errno=%d", text)
        self.assertIn("audio.setcal.execute.entry.%d.msync_nonfatal=1", text)
        self.assertIn("audio.setcal.execute.entry.%d.payload_copied=1", text)
        self.assertNotIn("return -saved_errno;\n    }\n    a90_console_printf(\"audio.setcal.execute.entry.%d.mmap_ok=1", text)


    def test_msm_audio_cal_devnode_is_materialized_before_open(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")

        self.assertIn('#define AUDIO_SETCAL_SYSFS_MSM_AUDIO_CAL_DEV "/sys/class/misc/msm_audio_cal/dev"', text)
        self.assertIn('#define AUDIO_PROC_MISC "/proc/misc"', text)
        self.assertIn('#define AUDIO_MISC_MAJOR 10U', text)
        self.assertIn("static int audio_materialize_msm_audio_cal_devnode_once(void);", text)
        self.assertIn("static int audio_materialize_msm_audio_cal_devnode_once(void) {", text)
        self.assertIn('audio_read_misc_minor_by_name("msm_audio_cal", &minor_num)', text)
        self.assertIn("audio.msm_audio_cal_materialize.version=1", text)
        self.assertIn("audio.msm_audio_cal_materialize.source=proc_misc", text)
        self.assertIn("audio.msm_audio_cal_materialize.created=1", text)
        self.assertIn("mknod(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, S_IFCHR | 0600, wanted)", text)
        self.assertIn("audio_materialize_msm_audio_cal_devnode_once();", text)
        self.assertLess(
            text.index("audio_materialize_msm_audio_cal_devnode_once();"),
            text.index("open(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, O_RDWR | O_CLOEXEC)"),
        )

    def test_builder_uses_v2798_patch_artifact_identity(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2798"', text)
        self.assertIn('INIT_VERSION = "0.9.311"', text)
        self.assertIn('INIT_BUILD = "v2798-audio-msm-audio-cal-devnode"', text)
        self.assertIn('boot_linux_v2798_audio_msm_audio_cal_devnode.img', text)
        self.assertIn('NATIVE_INIT_V2798_AUDIO_MSM_AUDIO_CAL_DEVNODE_SOURCE_BUILD_2026-06-19.md', text)
        self.assertIn('"sound_control_wait_timeout_ms": 70000', text)
        self.assertIn('"play_worker_executor_compiled": True', text)
        self.assertIn('"ion_devnode_materialization_compiled": True', text)
        self.assertIn('"msm_audio_cal_sysfs_dev_path": "/sys/class/misc/msm_audio_cal/dev"', text)
        self.assertIn('"msm_audio_cal_proc_misc_fallback": True', text)
        self.assertIn('"msm_audio_cal_runtime_devnode": "/dev/msm_audio_cal"', text)
        self.assertIn('"dmabuf_msync_nonfatal_compiled": True', text)
        self.assertIn('"v2797_blocker": "audio.setcal.execute.open.msm_audio_cal.open_ok=0 errno=2"', text)
        self.assertIn('"/sys/class/misc/ion/dev"', text)
        self.assertIn('"/dev/ion"', text)

    def test_live_runner_targets_v2798_and_allowed_manifest_path(self) -> None:
        module = self.live
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)

        self.assertEqual(module.CYCLE, "V2801")
        self.assertEqual(module.CANDIDATE_VERSION, "0.9.311")
        self.assertIn("boot_linux_v2798_audio_msm_audio_cal_devnode.img", str(module.CANDIDATE_IMAGE))
        self.assertIn("NATIVE_INIT_V2801_AUDIO_V2798_READINESS_REPLAY_LIVE_2026-06-19.md", str(module.REPORT_PATH))
        self.assertEqual(
            module.REMOTE_NATIVE_MANIFEST,
            "/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest",
        )
        self.assertIn(module.REMOTE_NATIVE_MANIFEST, payload["commands"]["play"])
        self.assertEqual(payload["commands"]["play"][-1], "--execute")
        self.assertEqual(payload["commands"]["play_status"], ["audio", "play-status"])
        self.assertEqual(payload["commands"]["play_worker_log"], ["run", "/bin/busybox", "cat", module.REMOTE_PLAY_LOG])

    def test_live_runner_captures_adsp_snd_and_dmesg_diagnostics(self) -> None:
        text = LIVE.read_text(encoding="utf-8")

        self.assertIn("candidate-audio-adsp-status-before-play", text)
        self.assertIn("candidate-audio-snd-status-before-play", text)
        self.assertIn("candidate-audio-adsp-status-after-play", text)
        self.assertIn("candidate-audio-snd-status-after-play", text)
        self.assertIn("candidate-dmesg-audio-tail", text)
        self.assertIn('"audio", "adsp-status"', text)
        self.assertIn('"audio", "snd-status"', text)
        self.assertIn('"dmesg | tail -n 240"', text)
        self.assertIn("## Diagnostic Captures", text)

    def test_worker_output_classification_requires_worker_markers(self) -> None:
        module = self.live
        summary = module.classify_play_output(
            "\n".join([
                "audio.play.worker.started=1",
                "audio.play.worker.done=1 rc=0",
                "A90_LISTEN_WINDOW_BEGIN",
                "A90_LISTEN_WINDOW_END",
                "audio.play.integrated.done=1 rc=0",
                "audio.ion_materialize.version=1",
                "audio.ion_materialize.created=1 major=10 minor=94",
                "audio.setcal.execute.ion.alloc_ok=1 dmabuf_fd=5",
                "audio.msm_audio_cal_materialize.version=1",
                "audio.msm_audio_cal_materialize.created=1 major=10 minor=54",
                "audio.setcal.execute.open.msm_audio_cal.open_ok=1",
                "audio.setcal.execute.ioctl.0.request=0xc00861c8",
                "audio.setcal.execute.ioctl.1.request=0xc00861cb",
                "audio.setcal.execute.entry.0.msync_nonfatal=1",
                "audio.setcal.execute.prepared_count=11",
                "audio.setcal.execute.hold_active=1",
                "audio.setcal.execute.set_count=11",
                "audio.setcal.execute.deallocated_count=4",
                "audio.play.integrated.route_apply.rc=0",
                "audio.play.integrated.route_reset.rc=0",
                "audio.play.execute.pcm_write_attempted=1",
                "audio.play.execute.done=1",
                "audio.play.safety.amplitude_within_cap=1",
                "audio.play.safety.duration_within_cap=1",
            ])
        )

        self.assertTrue(summary["ion_materialize_seen"], summary)
        self.assertTrue(summary["ion_materialize_ok"], summary)
        self.assertTrue(summary["ion_alloc_ok"], summary)
        self.assertTrue(summary["msm_audio_cal_materialize_seen"], summary)
        self.assertTrue(summary["msm_audio_cal_materialize_ok"], summary)
        self.assertTrue(summary["msm_audio_cal_open_ok"], summary)
        self.assertTrue(summary["setcal_allocate_request_native"], summary)
        self.assertTrue(summary["setcal_set_request_native"], summary)
        self.assertFalse(summary["setcal_first_ioctl_efault"], summary)
        self.assertFalse(summary["setcal_allocate_efault"], summary)
        self.assertTrue(summary["dmabuf_msync_nonfatal"], summary)
        self.assertTrue(summary["setcal_prepared_all"], summary)
        self.assertFalse(summary["msm_audio_cal_missing"], summary)
        self.assertTrue(module.play_output_pass(summary), summary)

    def test_worker_output_classifies_v2798_efault_frontier(self) -> None:
        module = self.live
        summary = module.classify_play_output(
            "\n".join([
                "audio.play.worker.started=1",
                "audio.ion_materialize.version=1",
                "audio.ion_materialize.created=1 major=10 minor=94",
                "audio.setcal.execute.ion.alloc_ok=1 dmabuf_fd=5",
                "audio.msm_audio_cal_materialize.version=1",
                "audio.msm_audio_cal_materialize.created=1 major=10 minor=54",
                "audio.setcal.execute.open.msm_audio_cal.open_ok=1",
                "audio.setcal.execute.ioctl.0.request=0xc00461c8",
                "audio.setcal.execute.ioctl.0.rc=-1 errno=14",
                "audio.setcal.execute.allocate_failed.index=0 errno=14",
                "audio.setcal.execute.entry.0.msync_nonfatal=1",
                "audio.setcal.execute.prepared_count=11",
            ])
        )

        self.assertTrue(summary["msm_audio_cal_materialize_ok"], summary)
        self.assertTrue(summary["msm_audio_cal_open_ok"], summary)
        self.assertFalse(summary["setcal_allocate_request_native"], summary)
        self.assertFalse(summary["setcal_set_request_native"], summary)
        self.assertTrue(summary["setcal_first_ioctl_efault"], summary)
        self.assertTrue(summary["setcal_allocate_efault"], summary)
        self.assertTrue(summary["setcal_prepared_all"], summary)
        self.assertFalse(module.play_output_pass(summary), summary)

    def test_worker_output_classifies_sound_control_timeout_before_ioctl(self) -> None:
        module = self.live
        summary = module.classify_play_output(
            "\n".join([
                "audio.play.worker.started=1",
                "audio.play.integrated.stage=adsp",
                "audio.adsp_boot_once.write=accepted",
                "audio.play.integrated.adsp.rc=0",
                "audio.play.integrated.wait.sound_control.ready=0 elapsed_ms=70250",
                "audio.play.integrated.setcal_ioctl_count=0",
                "audio.play.integrated.done=0 rc=-110",
            ])
        )

        self.assertTrue(summary["worker_started"], summary)
        self.assertTrue(summary["sound_control_wait_timeout"], summary)
        self.assertFalse(summary["sound_control_wait_ready"], summary)
        self.assertFalse(summary["ion_materialize_seen"], summary)
        self.assertFalse(summary["setcal_allocate_request_native"], summary)
        self.assertFalse(module.play_output_pass(summary), summary)


if __name__ == "__main__":
    unittest.main()
