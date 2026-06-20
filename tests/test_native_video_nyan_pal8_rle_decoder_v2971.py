import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"


class NativeVideoNyanPal8RleDecoderV2971(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_a90vstr2_constants_and_header_are_present(self) -> None:
        self.assertIn("#define VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE 4U", self.text)
        self.assertIn("#define VIDEO_STREAM_VERSION_A90VSTR2 2U", self.text)
        self.assertIn("#define VIDEO_STREAM_PAL8_RAW_MODE 1U", self.text)
        self.assertIn("#define VIDEO_STREAM_PAL8_RLE_MODE 2U", self.text)
        self.assertIn("struct video_stream_header_v2", self.text)
        self.assertIn("struct video_stream_frame_record_v2", self.text)
        self.assertIn('memcmp(header->magic, "A90VSTR2", 8)', self.text)

    def test_manifest_parser_accepts_pal8_rle_without_v1_stride_fields(self) -> None:
        self.assertIn('strcmp(manifest->format, "pal8-rle") == 0', self.text)
        self.assertIn("manifest->stream_version = VIDEO_STREAM_VERSION_A90VSTR2", self.text)
        self.assertIn('"stream_version"', self.text)
        self.assertIn('"palette_count"', self.text)
        self.assertIn('"max_payload_bytes"', self.text)
        self.assertIn("manifest->frame_bytes = manifest->max_payload_bytes", self.text)

    def test_player_hud_keeps_badapple_mono1_and_adds_nyan_pal8(self) -> None:
        self.assertIn("manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_MONO1 &&", self.text)
        self.assertIn("manifest->pixel_format != VIDEO_STREAM_PIXEL_FORMAT_PAL8_RLE", self.text)
        self.assertIn('"DEMO / NYAN CAT"', self.text)
        self.assertIn("video_render_pal8_player_hud_region", self.text)
        self.assertIn("video_expand_mono1_frame_scaled", self.text)
        self.assertIn("video.stream.error=pal8-rle-layout-unsupported", self.text)

    def test_pal8_decoder_validates_rle_rows_and_palette_indices(self) -> None:
        self.assertIn("video_decode_pal8_rle_frame", self.text)
        self.assertIn("source_offset == payload_bytes ? 0 : -EINVAL", self.text)
        self.assertIn("palette_index >= palette_count", self.text)
        self.assertIn("record_v2.payload_bytes > manifest->max_payload_bytes", self.text)
        self.assertIn("record_v2.mode != VIDEO_STREAM_PAL8_RAW_MODE", self.text)
        self.assertIn("record_v2.mode != VIDEO_STREAM_PAL8_RLE_MODE", self.text)

    def test_v2_does_not_reuse_badapple_beat_flash_metadata(self) -> None:
        self.assertIn("beat_flash_enabled = manifest != NULL && manifest->pixel_format == VIDEO_STREAM_PIXEL_FORMAT_MONO1", self.text)
        self.assertIn('beat_enabled ? A90_BADAPPLE_BEAT_SOURCE_ID : "none"', self.text)
        self.assertIn("manifest->stream_version == VIDEO_STREAM_VERSION_A90VSTR2", self.text)
        self.assertIn("return 0;", self.text)


if __name__ == "__main__":
    unittest.main()
