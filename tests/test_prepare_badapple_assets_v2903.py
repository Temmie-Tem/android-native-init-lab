import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_badapple_assets_v2903 as assets


def args_for(input_video: Path, out_dir: Path, *, dry_run: bool = True) -> argparse.Namespace:
    return argparse.Namespace(
        input_video=input_video,
        out_dir=out_dir,
        dry_run=dry_run,
        width=1080,
        height=2400,
        fps_num=30,
        fps_den=1,
        max_frames=6501,
        threshold=128,
        audio_sample_rate=48000,
        audio_channels=2,
        audio_volume=0.15,
        skip_audio=False,
        asset_id="unit-badapple",
        ffmpeg_timeout=60.0,
        result_json=None,
        report_path=assets.DEFAULT_REPORT,
    )


class PrepareBadAppleAssetsV2903(unittest.TestCase):
    def test_video_filter_letterboxes_to_target_geometry(self) -> None:
        video_filter = assets.video_filter(1080, 2400, 30, 1)
        self.assertIn("fps=30", video_filter)
        self.assertIn("scale=w=1080:h=2400:force_original_aspect_ratio=decrease", video_filter)
        self.assertIn("pad=1080:2400:(ow-iw)/2:(oh-ih)/2:black", video_filter)
        self.assertTrue(video_filter.endswith("format=gray"))

    def test_frame_command_uses_private_pgm_pattern_and_max_frames(self) -> None:
        command = assets.frame_ffmpeg_command(
            "ffmpeg",
            ROOT / "workspace/private/demo-assets/input.mp4",
            ROOT / "workspace/private/demo-assets/frames/frame-%06d.pgm",
            width=1080,
            height=2400,
            fps_num=30,
            fps_den=1,
            max_frames=6501,
        )
        self.assertIn("-frames:v", command)
        self.assertEqual(command[command.index("-frames:v") + 1], "6501")
        self.assertIn("-f", command)
        self.assertEqual(command[command.index("-f") + 1], "image2")
        self.assertTrue(command[-1].endswith("frame-%06d.pgm"))

    def test_audio_command_outputs_bounded_48k_stereo_s16le(self) -> None:
        command = assets.audio_ffmpeg_command(
            "ffmpeg",
            ROOT / "workspace/private/demo-assets/input.mp4",
            ROOT / "workspace/private/demo-assets/audio/audio.s16le",
            sample_rate=48000,
            channels=2,
            volume=0.15,
        )
        self.assertEqual(command[command.index("-af") + 1], "volume=0.15")
        self.assertEqual(command[command.index("-ac") + 1], "2")
        self.assertEqual(command[command.index("-ar") + 1], "48000")
        self.assertEqual(command[command.index("-f") + 1], "s16le")

    def test_dry_run_plans_commands_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "workspace/private/test-runs") as temp:
            temp_root = Path(temp)
            input_video = temp_root / "source-placeholder.mp4"
            input_video.write_bytes(b"private placeholder")
            with mock.patch.object(assets, "ffmpeg_path", return_value=None):
                result = assets.run(args_for(input_video, temp_root / "out", dry_run=True))

            self.assertTrue(result["ok"])
            self.assertFalse(result["ffmpeg_available"])
            self.assertEqual(result["decision"], "v2903-badapple-assets-dry-run")
            self.assertIn("frames", result["commands"])
            self.assertIn("audio", result["commands"])
            self.assertEqual(result["validation"]["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
