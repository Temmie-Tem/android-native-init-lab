"""Tests for the V2779 native audio stage contract module split."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
QUERY_C = REPO / "workspace/public/src/native-init/a90_audio_query.c"
STAGE_H = REPO / "workspace/public/src/native-init/a90_audio_stage.h"
STAGE_C = REPO / "workspace/public/src/native-init/a90_audio_stage.c"
BUILDER = REPO / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2779_audio_stage_module.py"


class NativeAudioStageModuleV2779(unittest.TestCase):
    def test_stage_module_owns_stage_types_tokens_and_constants(self) -> None:
        header = STAGE_H.read_text(encoding="utf-8")

        self.assertIn("#define AUDIO_STAGE_CONTRACT_VERSION 1", header)
        self.assertIn("#define AUDIO_STAGE_CONTRACT_COUNT 14", header)
        self.assertIn('#define AUDIO_ADSP_BOOT_ONCE_TOKEN "AUD2_ONE_SHOT_ADSP_BOOT"', header)
        self.assertIn('#define AUDIO_SND_MATERIALIZE_TOKEN "AUD3_DEV_SND_MATERIALIZE_ONLY"', header)
        self.assertIn("#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH", header)
        self.assertIn("struct audio_stage_contract", header)
        self.assertIn("extern const struct audio_stage_contract AUDIO_STAGE_CONTRACTS", header)

    def test_stage_module_owns_canonical_stage_data(self) -> None:
        stage = STAGE_C.read_text(encoding="utf-8")

        self.assertIn("const struct audio_stage_contract AUDIO_STAGE_CONTRACTS[AUDIO_STAGE_CONTRACT_COUNT]", stage)
        for marker in [
            '.id = "preflight-v2321-health"',
            '.id = "adsp-boot-once"',
            '.id = "snd-materialize-once"',
            '.id = "write-global-app-type-config"',
            '.id = "verify-private-acdb-manifest"',
            '.id = "prepare-acdb-payload-bundle"',
            '.id = "load-acdb-payload-files"',
            '.id = "replay-acdb-setcal-sequence"',
            '.id = "apply-playback-speaker-route"',
            '.id = "plan-bounded-pcm-playback"',
            '.id = "bounded-pcm-playback"',
            '.id = "plan-audio-stop-cleanup"',
            '.id = "reset-playback-speaker-route"',
            '.id = "rollback-v2321"',
            '--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --verify --dry-run',
            '--manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --execute',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, stage)

    def test_command_file_uses_stage_module_instead_of_owning_stage_data(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")
        query = QUERY_C.read_text(encoding="utf-8")

        self.assertIn('#include "a90_audio_stage.h"', text)
        self.assertIn('#include "a90_audio_stage.h"', query)
        self.assertIn("return AUDIO_STAGE_CONTRACT_COUNT;", query)
        self.assertNotIn("static const struct audio_stage_contract AUDIO_STAGE_CONTRACTS", text)
        self.assertNotIn("struct audio_stage_contract {", text)
        self.assertNotIn("#define AUDIO_ADSP_BOOT_ONCE_TOKEN", text)
        self.assertNotIn("#define AUDIO_SND_MATERIALIZE_TOKEN", text)
        self.assertNotIn("#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH", text)

    def test_builder_records_v2779_stage_module_artifact(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")

        self.assertIn('CYCLE = "V2779"', text)
        self.assertIn('INIT_VERSION = "0.9.298"', text)
        self.assertIn('INIT_BUILD = "v2779-audio-stage-module"', text)
        self.assertIn("boot_linux_v2779_audio_stage_module.img", text)
        self.assertIn("NATIVE_INIT_V2779_AUDIO_STAGE_MODULE_SOURCE_BUILD_2026-06-19.md", text)


if __name__ == "__main__":
    unittest.main()
