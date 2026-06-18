"""Tests for the V2790 native audio SET-cal replay executor."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
AUDIO_STAGE_C = REPO / "workspace/public/src/native-init/a90_audio_stage.c"
PROFILE_PY = REPO / "workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py"


def source_text() -> str:
    return "\n".join([
        AUDIO_C.read_text(encoding="utf-8"),
        AUDIO_STAGE_C.read_text(encoding="utf-8"),
        PROFILE_PY.read_text(encoding="utf-8"),
    ])


class NativeAudioSetcalExecuteNativeV2790(unittest.TestCase):
    def test_execute_support_is_enabled_and_refusal_removed(self) -> None:
        text = source_text()

        self.assertIn("audio.setcal.execute_supported=1", text)
        self.assertIn("audio.setcal.execute_native_replay_supported", text)
        self.assertIn("audio_setcal_execute_manifest_plan(manifest_plan, &ioctl_count)", text)
        self.assertNotIn("execute-not-implemented-native-setcal-ioctl", text)

    def test_executor_uses_scaffold_compatible_ion_dmabuf_flow(self) -> None:
        text = source_text()

        for marker in [
            "struct audio_ion_allocation_data",
            "AUDIO_ION_IOC_ALLOC",
            "AUDIO_ION_SYSTEM_HEAP_MASK",
            "AUDIO_ION_FLAG_CACHED",
            "mmap(NULL,",
            "PROT_READ | PROT_WRITE",
            "MAP_SHARED",
            "memcpy(state->mapped, state->payload, state->payload_len)",
            "msync(state->mapped, state->payload_len, MS_SYNC)",
            "munmap(state->mapped, state->payload_len)",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_executor_rejects_untrusted_zero_or_mismatched_inputs(self) -> None:
        text = source_text()

        for marker in [
            "audio_setcal_buffer_is_all_zero",
            "error=all-zero",
            "AUDIO_SETCAL_ARG_MAX_BYTES",
            "AUDIO_SETCAL_PAYLOAD_MAX_BYTES",
            "error=bad-arg-header",
            "error=payload-size-mismatch",
            "audio_setcal_payload_path_allowed(path)",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_executor_calls_allocate_set_and_reverse_deallocate(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")
        start = text.index("static int audio_setcal_execute_manifest_plan")
        end = text.index("static int audio_setcal_cmd", start)
        block = text[start:end]

        allocate = block.index("AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION")
        set_call = block.index("AUDIO_SETCAL_IOCTL_SET_CALIBRATION")
        reverse_loop = block.index("for (index = prepared_count; index > 0; --index)")
        deallocate = block.index("AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION")

        self.assertLess(allocate, set_call)
        self.assertLess(set_call, reverse_loop)
        self.assertLess(reverse_loop, deallocate)
        self.assertIn("states[index].allocated = true", block)
        self.assertIn("states[reverse_index].allocated = false", block)
        self.assertIn("audio.setcal.execute.set_count=%d", block)
        self.assertIn("audio.setcal.execute.deallocated_count=%d", block)

    def test_stage_contract_marks_replay_as_native_runtime_stage(self) -> None:
        text = source_text()

        self.assertIn('.id = "replay-acdb-setcal-sequence"', text)
        self.assertIn("replays the verified private ACDB SET sequence", text)
        self.assertRegex(
            text,
            re.compile(
                r'\.id = "replay-acdb-setcal-sequence".*?'
                r"\.native_implemented = true,.*?"
                r"\.writes_runtime_state = true,",
                re.DOTALL,
            ),
        )
        self.assertIn('stage_id="replay-acdb-setcal-sequence"', text)
        self.assertIn("native_implemented=True", text)


if __name__ == "__main__":
    unittest.main()
