"""Tests for the V2769 audio SET-cal ION request-plan boundary."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalIonRequestPlanV2769(unittest.TestCase):
    def test_ion_request_constants_match_scaffold_contract(self) -> None:
        text = source_text()

        for marker in [
            "AUDIO_ION_FLAG_CACHED 1U",
            "AUDIO_ION_SYSTEM_HEAP_ID 25U",
            "AUDIO_ION_SYSTEM_HEAP_MASK (1U << AUDIO_ION_SYSTEM_HEAP_ID)",
            "#include <stdint.h>",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_ion_request_plan_struct_tracks_unallocated_metadata(self) -> None:
        text = source_text()

        for marker in [
            "struct audio_setcal_ion_request_slot",
            "uint64_t len",
            "uint32_t heap_id_mask",
            "uint32_t flags",
            "int dmabuf_fd",
            "int mem_handle",
            "struct audio_setcal_ion_request_plan",
            "int request_count",
            "uint64_t total_len",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_ion_request_plan_builds_from_positive_allocation_slots_only(self) -> None:
        text = source_text()
        build_start = text.index("static void audio_setcal_ion_request_plan_build")
        build_end = text.index("static void audio_setcal_print_ion_request_plan", build_start)
        build_block = text[build_start:build_end]

        for marker in [
            "request_plan->heap_id_mask = AUDIO_ION_SYSTEM_HEAP_MASK",
            "request_plan->flags = AUDIO_ION_FLAG_CACHED",
            "if (!slot->active || slot->payload_size <= 0)",
            "request = &request_plan->requests[request_plan->request_count]",
            "request->len = (uint64_t)slot->payload_size",
            "request->dmabuf_fd = -1",
            "request->mem_handle = -1",
            "request_plan->request_count += 1",
            "request_plan->total_len += request->len",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, build_block)
        self.assertNotIn("open(", build_block)
        self.assertNotIn("ioctl(", build_block)

    def test_ion_request_plan_output_declares_no_alloc_attempt(self) -> None:
        text = source_text()
        print_start = text.index("static void audio_setcal_print_ion_request_plan")
        print_end = text.index("static int32_t audio_setcal_read_le_i32", print_start)
        print_block = text[print_start:print_end]

        for marker in [
            "audio.setcal.execute.ion.plan.version=1",
            "audio.setcal.execute.ion.plan.request.count",
            "audio.setcal.execute.ion.plan.total_len",
            "audio.setcal.execute.ion.plan.heap_id_mask",
            "audio.setcal.execute.ion.plan.flags",
            "audio.setcal.execute.ion.plan.alloc_attempted=0",
            "audio.setcal.execute.ion.plan.ioctl_attempted=0",
            "audio.setcal.execute.ion.plan.request.%d",
            "request->dmabuf_fd",
            "request->mem_handle",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, print_block)
        self.assertNotIn("ioctl(", print_block)

    def test_execute_orders_ion_request_plan_before_native_replay(self) -> None:
        text = source_text()
        cmd_start = text.index("static int audio_setcal_cmd")
        cmd_end = text.index("static bool audio_parse_nonnegative_int", cmd_start)
        cmd_block = text[cmd_start:cmd_end]

        allocation = cmd_block.index("audio_setcal_print_allocation_plan(&allocation_plan)")
        build = cmd_block.index("audio_setcal_ion_request_plan_build(&allocation_plan, &ion_request_plan)")
        print_plan = cmd_block.index("audio_setcal_print_ion_request_plan(&ion_request_plan)")
        execute = cmd_block.index("audio_setcal_execute_manifest_plan(manifest_plan, &ioctl_count)")

        self.assertLess(allocation, build)
        self.assertLess(build, print_plan)
        self.assertLess(print_plan, execute)
        self.assertIn("struct audio_setcal_ion_request_plan ion_request_plan", cmd_block)
        self.assertIn("memset(&ion_request_plan, 0, sizeof(ion_request_plan))", cmd_block)
        self.assertIn("audio.setcal.ioctl_attempted=0", cmd_block)


if __name__ == "__main__":
    unittest.main()
