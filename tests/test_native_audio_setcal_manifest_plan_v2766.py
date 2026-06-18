"""Tests for the V2766 native audio SET-cal manifest-plan API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalManifestPlanV2766(unittest.TestCase):
    def test_manifest_plan_struct_keeps_executor_inputs(self) -> None:
        text = source_text()

        for marker in [
            "struct audio_setcal_manifest_plan_entry",
            "char arg_path[PATH_MAX]",
            "char payload_path[PATH_MAX]",
            "long long arg_loaded",
            "long long payload_loaded",
            "struct audio_setcal_manifest_plan",
            "struct audio_setcal_manifest_plan_entry entries[AUDIO_PROFILE_ACDB_SET_COUNT]",
            "bool valid",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_verified_entries_are_materialized_only_after_file_checks(self) -> None:
        text = source_text()
        entry_start = text.index("static int audio_setcal_verify_manifest_entry")
        entry_end = text.index("static int audio_setcal_verify_manifest(", entry_start)
        entry_block = text[entry_start:entry_end]

        verify_arg = entry_block.index("audio_setcal_verify_regular_file(arg_prefix")
        verify_payload = entry_block.index("audio_setcal_verify_regular_file(payload_prefix")
        store = entry_block.index("audio_setcal_manifest_plan_store_entry")

        self.assertLess(verify_arg, store)
        self.assertLess(verify_payload, store)
        self.assertIn("if (rc == 0)", entry_block[verify_payload:store + 80])
        self.assertIn("arg_loaded", entry_block)
        self.assertIn("payload_loaded", entry_block)

    def test_manifest_headers_and_totals_are_stored_in_plan(self) -> None:
        text = source_text()
        verify_start = text.index("static int audio_setcal_verify_manifest")
        verify_end = text.index("static void audio_setcal_print_execute_plan", verify_start)
        verify_block = text[verify_start:verify_end]

        for marker in [
            "audio_setcal_manifest_plan_reset(plan)",
            "plan->version = manifest_version",
            "audio_copy_string(plan->profile",
            "plan->declared_entry_count = manifest_entry_count",
            "plan->totals = *totals",
            "plan->load_totals = *load_totals",
            "plan->valid = true",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, verify_block)

    def test_execute_plan_is_printed_from_materialized_manifest_plan(self) -> None:
        text = source_text()
        plan_start = text.index("static void audio_setcal_print_execute_plan")
        plan_end = text.index("static void audio_setcal_allocation_plan_build", plan_start)
        plan_block = text[plan_start:plan_end]

        for marker in [
            "const struct audio_setcal_manifest_plan *plan",
            "audio.setcal.execute.plan.manifest.valid",
            "audio.setcal.execute.plan.executor_input=manifest-plan-entries",
            "audio.setcal.execute.plan.entry.%d",
            "entry->arg_size",
            "entry->payload_size",
            "entry->arg_loaded",
            "entry->payload_loaded",
            "audio.setcal.execute.plan.devices_opened=0",
            "audio.setcal.execute.plan.ioctl_attempted=0",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, plan_block)
        self.assertNotIn("open(", plan_block)
        self.assertNotIn("ioctl(", plan_block)

    def test_setcal_cmd_allocates_and_frees_plan_around_manifest_actions(self) -> None:
        text = source_text()
        cmd_start = text.index("static int audio_setcal_cmd")
        cmd_end = text.index("static bool audio_parse_nonnegative_int", cmd_start)
        cmd_block = text[cmd_start:cmd_end]

        self.assertIn("struct audio_setcal_manifest_plan *manifest_plan = NULL", cmd_block)
        self.assertIn("manifest_plan = calloc(1, sizeof(*manifest_plan))", cmd_block)
        self.assertIn("manifest-plan-alloc-failed", cmd_block)
        self.assertIn("audio_setcal_verify_manifest(profile", cmd_block)
        self.assertIn("manifest_plan)", cmd_block)
        self.assertIn("audio_setcal_print_execute_plan(profile, manifest_plan)", cmd_block)
        self.assertRegex(
            cmd_block,
            re.compile(r"audio_setcal_execute_manifest_plan\(manifest_plan, &ioctl_count\).*?free\(manifest_plan\).*?return execute_rc;", re.DOTALL),
        )
        self.assertRegex(cmd_block, re.compile(r"free\(manifest_plan\).*?audio\.setcal\.dry_run_ok=1", re.DOTALL))


if __name__ == "__main__":
    unittest.main()
