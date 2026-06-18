"""Tests for the V2768 audio SET-cal allocation work-list boundary."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalAllocationPlanV2768(unittest.TestCase):
    def test_allocation_plan_struct_models_dmabuf_slots(self) -> None:
        text = source_text()

        for marker in [
            "struct audio_setcal_allocation_slot",
            "bool active",
            "int sequence",
            "int cal_type",
            "long long payload_size",
            "long long payload_loaded",
            "struct audio_setcal_allocation_plan",
            "int slot_count",
            "long long total_payload_bytes",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_allocation_plan_builds_only_dmabuf_expected_manifest_entries(self) -> None:
        text = source_text()
        build_start = text.index("static void audio_setcal_allocation_plan_build")
        build_end = text.index("static void audio_setcal_print_allocation_plan", build_start)
        build_block = text[build_start:build_end]

        for marker in [
            "if (manifest_plan == NULL || !manifest_plan->valid)",
            "if (!entry->present || !entry->dmabuf_expected)",
            "slot = &allocation_plan->slots[allocation_plan->slot_count]",
            "slot->sequence = entry->sequence",
            "slot->cal_type = entry->cal_type",
            "slot->payload_size = entry->payload_size",
            "slot->payload_loaded = entry->payload_loaded",
            "allocation_plan->slot_count += 1",
            "allocation_plan->total_payload_bytes += entry->payload_size",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, build_block)
        self.assertNotIn("open(", build_block)
        self.assertNotIn("ioctl(", build_block)

    def test_allocation_plan_output_declares_no_allocate_attempt(self) -> None:
        text = source_text()
        print_start = text.index("static void audio_setcal_print_allocation_plan")
        print_end = text.index("static void audio_setcal_ion_request_plan_build", print_start)
        print_block = text[print_start:print_end]

        for marker in [
            "audio.setcal.execute.allocate.plan.version=1",
            "audio.setcal.execute.allocate.plan.slot.count",
            "audio.setcal.execute.allocate.plan.total_payload_bytes",
            "audio.setcal.execute.allocate.plan.ioctl.allocate",
            "audio.setcal.execute.allocate.plan.ioctl.deallocate",
            "audio.setcal.execute.allocate.plan.allocate_attempted=0",
            "audio.setcal.execute.allocate.plan.ioctl_attempted=0",
            "audio.setcal.execute.allocate.plan.slot.%d",
            "slot->payload_size",
            "slot->payload_loaded",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, print_block)
        self.assertNotIn("ioctl(", print_block)

    def test_execute_inserts_allocation_plan_before_native_replay(self) -> None:
        text = source_text()
        cmd_start = text.index("static int audio_setcal_cmd")
        cmd_end = text.index("static bool audio_parse_nonnegative_int", cmd_start)
        cmd_block = text[cmd_start:cmd_end]

        build_call = cmd_block.index("audio_setcal_allocation_plan_build(manifest_plan, &allocation_plan)")
        print_call = cmd_block.index("audio_setcal_print_allocation_plan(&allocation_plan)")
        execute_call = cmd_block.index("audio_setcal_execute_manifest_plan(manifest_plan, &ioctl_count)")

        self.assertLess(build_call, print_call)
        self.assertLess(print_call, execute_call)
        self.assertIn("struct audio_setcal_allocation_plan allocation_plan", cmd_block)
        self.assertIn("memset(&allocation_plan, 0, sizeof(allocation_plan))", cmd_block)
        self.assertNotIn("execute-not-implemented-native-setcal-ioctl", cmd_block)


if __name__ == "__main__":
    unittest.main()
