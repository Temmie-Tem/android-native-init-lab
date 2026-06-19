import json
import shutil
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_video_stream_v2874 as prepare_stream
import native_video_gray8_stream_live_handoff_v2893 as gray8_live


class NativeVideoMono1StreamV2896(unittest.TestCase):
    def test_prepare_stream_writes_mono1_manifest_and_header(self) -> None:
        out_dir = ROOT / "workspace/private/test-runs/v2896-mono1-unit"
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            result = prepare_stream.write_stream(
                out_dir=out_dir,
                width=16,
                height=8,
                stride=2,
                fps_num=30,
                fps_den=1,
                frames=2,
                pattern="checker",
                stream_format="mono1",
            )
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["video"]["format"], "mono1")
            self.assertEqual(manifest["video"]["visible_row_bytes"], 2)
            self.assertEqual(manifest["video"]["frame_bytes"], 16)
            self.assertEqual(result["frame_bytes"], 16)

            data = (out_dir / "frames.a90vstr").read_bytes()
            self.assertEqual(data[:8], prepare_stream.MAGIC)
            header = struct.unpack("<IIIIIIIII32s", data[8:76])
            self.assertEqual(header[0], 1)
            self.assertEqual(header[1], 16)
            self.assertEqual(header[2], 8)
            self.assertEqual(header[3], 2)
            self.assertEqual(header[4], prepare_stream.PIXEL_FORMAT_MONO1)
            self.assertEqual(header[8], 16)
            frame_index, payload_bytes, pts_ns = struct.unpack("<IIQ", data[76:92])
            self.assertEqual((frame_index, payload_bytes, pts_ns), (0, 16, 0))
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_stream_classifier_accepts_expected_mono1_marker(self) -> None:
        text = "\n".join([
            "video.stream.sha256_checked=1",
            "video.stream.sha256_match=1",
            "video.stream.requested_present=pageflip",
            "video.stream.present_mode=pageflip",
            "video.stream.presented=30",
            "video.stream.flip_events=30",
            "video.stream.flip_delta_count=29",
            "video.stream.flip_delta_min_us=16610",
            "video.stream.flip_delta_max_us=33245",
            "video.stream.flip_delta_avg_us=32659",
            "video.stream.flip_delta_target_us=33333",
            "video.stream.pixel_format=mono1",
            "video.stream.path=kms-dumb-buffer-pageflip",
        ])
        mono1 = gray8_live.classify_stream_output(text, expected_frames=30, expected_format="mono1")
        gray8 = gray8_live.classify_stream_output(text, expected_frames=30, expected_format="gray8")

        self.assertTrue(mono1["pass"])
        self.assertEqual(mono1["expected_pixel_format"], "mono1")
        self.assertFalse(gray8["pass"])


if __name__ == "__main__":
    unittest.main()
