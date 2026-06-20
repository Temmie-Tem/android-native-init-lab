"""Tests for the V2755 native audio core route writer contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
ROUTE_C = REPO / "workspace/public/src/native-init/a90_audio_route.c"
ROUTE_H = REPO / "workspace/public/src/native-init/a90_audio_route.h"


def source_text() -> str:
    return "\n".join([
        AUDIO_C.read_text(encoding="utf-8"),
        ROUTE_C.read_text(encoding="utf-8"),
        ROUTE_H.read_text(encoding="utf-8"),
    ])


class NativeAudioRouteCoreWriterV2755(unittest.TestCase):
    def test_only_core_and_playback_layers_are_write_allowed(self) -> None:
        text = source_text()

        self.assertIn('bool a90_audio_route_layer_write_allowed(const char *layer)', text)
        self.assertIn('strcmp(layer, AUDIO_ROUTE_LAYER_CORE) == 0', text)
        self.assertIn('strcmp(layer, AUDIO_ROUTE_LAYER_PLAYBACK) == 0', text)
        self.assertIn('write_mode && !a90_audio_route_layer_write_allowed(layer)', text)
        self.assertIn('audio.route.refused=write-mode-blocked-non-core-layer', text)
        self.assertIn('audio.route.refused=write-mode-blocked-smart-amp-boost-review', text)

    def test_core_writer_uses_existing_alsa_control_resolution_and_elem_write(self) -> None:
        text = source_text()

        self.assertIn('static int audio_route_write_selected_controls', text)
        self.assertIn('audio_open_control_device(profile->card)', text)
        self.assertIn('audio_resolve_control_by_name(fd, control->name, &id)', text)
        self.assertIn('SNDRV_CTL_IOCTL_ELEM_INFO', text)
        self.assertIn('SNDRV_CTL_IOCTL_ELEM_WRITE', text)
        self.assertIn('audio.route.write_attempted=1', text)
        self.assertIn('audio.route.write_done count=%d layer=%s mode=%s', text)

    def test_core_writer_supports_numeric_boolean_and_enum_controls(self) -> None:
        text = source_text()

        self.assertIn('static int audio_route_validate_numeric_control', text)
        self.assertIn('static int audio_route_find_enum_item', text)
        self.assertIn('SNDRV_CTL_ELEM_TYPE_INTEGER', text)
        self.assertIn('SNDRV_CTL_ELEM_TYPE_BOOLEAN', text)
        self.assertIn('SNDRV_CTL_ELEM_TYPE_ENUMERATED', text)
        self.assertIn('expected=numeric', text)
        self.assertIn('value->value.integer.value[index] = route_value->ints[index];', text)
        self.assertIn('value->value.enumerated.item[0] = item;', text)

    def test_writer_iterates_apply_forward_and_reset_reverse(self) -> None:
        text = source_text()

        self.assertRegex(
            text,
            re.compile(
                r'if \(reset_mode\).*?for \(index = a90_audio_route_control_count\(\) - 1; index >= 0; --index\)',
                re.DOTALL,
            ),
        )
        self.assertRegex(
            text,
            re.compile(
                r'else \{\s*for \(index = 0; index < a90_audio_route_control_count\(\); \+\+index\)',
                re.DOTALL,
            ),
        )

    def test_non_core_layers_remain_blocked_before_any_write_attempt(self) -> None:
        text = source_text()

        refusal = text.index('if (write_mode && !a90_audio_route_layer_write_allowed(layer))')
        write_call = text.index('return audio_route_write_selected_controls(profile, layer, reset_mode);')
        self.assertLess(refusal, write_call)
        self.assertIn('audio.route.write_attempted=0', text[refusal:write_call])
        self.assertIn('return -EPERM;', text[refusal:write_call])


if __name__ == "__main__":
    unittest.main()
