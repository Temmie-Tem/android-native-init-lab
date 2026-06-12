"""Regression tests for native_kernel_workqueue_fwclass_oracle_plan_v2272."""

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2272 = load_revalidation("native_kernel_workqueue_fwclass_oracle_plan_v2272")


WORKQUEUE_TRACE_TEXT = """
TRACE_EVENT(workqueue_queue_work,
    TP_STRUCT__entry(
        __field( void *, function)
    ),
    TP_fast_assign(
        __entry->function = work->func;
    )
);

TRACE_EVENT(workqueue_execute_start,
    TP_STRUCT__entry(
        __field( void *, function)
    ),
    TP_fast_assign(
        __entry->function = work->func;
    )
);
"""

FIRMWARE_CLASS_TEXT = """
static void request_firmware_work_func(struct work_struct *work)
{
    _request_firmware();
}

void fw_schedule(void)
{
    INIT_WORK(&fw_work->work, request_firmware_work_func);
    schedule_work(&fw_work->work);
}
"""

V2216_TEXT = """
Decision: `v2216-codeword-slide-exact`
Codeword exact slide accepted: `true`
"""

V2253_TEXT = """
Decision: `target-stack-visible-before-feed`
This also documents a sampler-miss artifact.
"""


def write_fixture(root: Path, *, firmware_trace=False, v2253_text=V2253_TEXT):
    source_root = root / "source"
    trace_root = source_root / "include" / "trace" / "events"
    trace_root.mkdir(parents=True)
    workqueue = trace_root / "workqueue.h"
    firmware_class = source_root / "drivers" / "base" / "firmware_class.c"
    firmware_class.parent.mkdir(parents=True)
    workqueue.write_text(WORKQUEUE_TRACE_TEXT, encoding="utf-8")
    firmware_class.write_text(FIRMWARE_CLASS_TEXT, encoding="utf-8")
    if firmware_trace:
        (trace_root / "firmware.h").write_text("TRACE_SYSTEM(firmware)\n", encoding="utf-8")
    v2216 = root / "reports" / "v2216.md"
    v2253 = root / "reports" / "v2253.md"
    v2216.parent.mkdir()
    v2216.write_text(V2216_TEXT, encoding="utf-8")
    v2253.write_text(v2253_text, encoding="utf-8")
    return source_root, workqueue, firmware_class, v2216, v2253


class PatchedV2272:
    def __init__(self, *, firmware_trace=False, v2253_text=V2253_TEXT):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (
            self.source_root,
            self.workqueue,
            self.firmware_class,
            self.v2216,
            self.v2253,
        ) = write_fixture(self.root, firmware_trace=firmware_trace, v2253_text=v2253_text)
        self.old_values = {}

    def __enter__(self):
        for name, value in {
            "REPO_ROOT": self.root,
            "SOURCE_ROOT": self.source_root,
            "WORKQUEUE_TRACE": self.workqueue,
            "FIRMWARE_CLASS": self.firmware_class,
            "V2216_REPORT": self.v2216,
            "V2253_REPORT": self.v2253,
        }.items():
            self.old_values[name] = getattr(v2272, name)
            setattr(v2272, name, value)
        return self

    def __exit__(self, exc_type, exc, tb):
        for name, value in self.old_values.items():
            setattr(v2272, name, value)
        self.tmp.cleanup()


class BasicHelpers(unittest.TestCase):
    def test_read_text_rel_and_regex_present_are_safe_for_missing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "sub" / "data.txt"
            file_path.parent.mkdir()
            file_path.write_text("TRACE_EVENT(workqueue_queue_work)\n", encoding="utf-8")
            old_root = v2272.REPO_ROOT
            try:
                v2272.REPO_ROOT = root

                self.assertEqual(v2272.read_text(file_path), "TRACE_EVENT(workqueue_queue_work)\n")
                self.assertEqual(v2272.read_text(root / "missing.txt"), "")
                self.assertEqual(v2272.rel(file_path), "sub/data.txt")
                self.assertTrue(v2272.regex_present("a\nb\nc", r"a.*c"))
                self.assertFalse(v2272.regex_present("abc", r"z+"))
            finally:
                v2272.REPO_ROOT = old_root

    def test_firmware_tracepoint_source_absent_handles_missing_absent_and_present(self):
        old_source_root = v2272.SOURCE_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                v2272.SOURCE_ROOT = root / "missing-source"
                self.assertFalse(v2272.firmware_tracepoint_source_absent())

                trace_root = root / "source" / "include" / "trace" / "events"
                trace_root.mkdir(parents=True)
                (trace_root / "workqueue.h").write_text("TRACE_SYSTEM(workqueue)\n", encoding="utf-8")
                v2272.SOURCE_ROOT = root / "source"
                self.assertTrue(v2272.firmware_tracepoint_source_absent())

                (trace_root / "firmware.h").write_text("TRACE_SYSTEM(firmware)\n", encoding="utf-8")
                self.assertFalse(v2272.firmware_tracepoint_source_absent())
        finally:
            v2272.SOURCE_ROOT = old_source_root


class PlanBuilder(unittest.TestCase):
    def test_build_plan_ready_requires_workqueue_firmware_and_prior_reports(self):
        with PatchedV2272() as fixture:
            plan = v2272.build_plan()

        candidate = plan["candidates"][0]
        self.assertEqual(plan["decision"], "v2272-workqueue-fwclass-oracle-defined")
        self.assertTrue(all(plan["checks"].values()))
        self.assertEqual(candidate["id"], "t1-workqueue-fwclass-function-pointer-oracle")
        self.assertEqual(candidate["track"], "T1")
        self.assertEqual(candidate["status"], "ready_for_next_v_iteration")
        self.assertTrue(candidate["safe_actionable_now"])
        self.assertIn("workqueue_queue_work", candidate["next_runner_contract"][0])
        self.assertIn("request_firmware_work_func", candidate["expected_discriminator"]["positive"])
        self.assertEqual(plan["source_paths"]["workqueue_trace"], "source/include/trace/events/workqueue.h")
        self.assertEqual(plan["source_paths"]["v2253_report"], "reports/v2253.md")
        self.assertTrue(plan["generated_at"])

    def test_build_plan_blocks_when_prior_boundary_evidence_or_absence_check_fails(self):
        with PatchedV2272(v2253_text="target-stack-visible-before-feed only"):
            missing_v2253 = v2272.build_plan()
        with PatchedV2272(firmware_trace=True):
            has_firmware_trace = v2272.build_plan()

        self.assertEqual(missing_v2253["decision"], "v2272-workqueue-fwclass-oracle-not-ready")
        self.assertFalse(missing_v2253["checks"]["v2253_fwclass_boundary_closed"])
        self.assertFalse(missing_v2253["candidates"][0]["safe_actionable_now"])
        self.assertEqual(missing_v2253["candidates"][0]["status"], "blocked_by_missing_evidence")

        self.assertFalse(has_firmware_trace["checks"]["firmware_tracepoint_source_absent"])
        self.assertEqual(has_firmware_trace["decision"], "v2272-workqueue-fwclass-oracle-not-ready")

    def test_render_text_outputs_decision_candidate_status_and_check_lines(self):
        with PatchedV2272():
            plan = v2272.build_plan()

        rendered = v2272.render_text(plan)

        self.assertIn("decision=v2272-workqueue-fwclass-oracle-defined", rendered)
        self.assertIn("candidate=t1-workqueue-fwclass-function-pointer-oracle", rendered)
        self.assertIn("status=ready_for_next_v_iteration", rendered)
        self.assertIn("safe_actionable_now=True", rendered)
        self.assertIn("check.workqueue_queue_work_has_function_field=True", rendered)
        self.assertIn("check.v2216_exact_codeword_slide_reported=True", rendered)


if __name__ == "__main__":
    unittest.main()
