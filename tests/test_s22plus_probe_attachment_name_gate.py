from __future__ import annotations

import re
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p280_contract_spec as p280  # noqa: E402
import s22plus_fyg8_p282_contract_spec as p282  # noqa: E402
import s22plus_fyg8_p284_stock_outer_d1_spec as d1_spec  # noqa: E402
import s22plus_probe_attachment_name_gate as gate  # noqa: E402


def _kernel_readback(events):
    lines = []
    for event in events:
        prefix = "r16" if event.probe_kind == "return" else "p"
        symbol = event.symbol
        if event.offset is not None:
            symbol = f"{symbol}+{event.offset}"
        target = f"{event.module}:{symbol}" if event.module else symbol
        lines.append(
            f"{prefix}:{d1_spec.TRACE_GROUP}/{event.name} "
            f"{target}{event.fetch}"
        )
    return "\n".join(lines) + "\n"


class ProbeAttachmentNameGateTests(unittest.TestCase):
    def test_p280_descriptors_match_their_actual_attachments(self):
        gate.require_clean(
            p280.TRACE_EVENTS,
            post_call_offsets=(0x34, 0x450),
        )

    def test_frozen_p282_mismatch_is_exactly_the_two_worker_labels(self):
        issues = gate.audit_events(
            p282.TRACE_EVENTS,
            post_call_offsets=(0x34, 0x450),
        )
        self.assertEqual(
            tuple(
                (issue.code, issue.event_name, issue.attached_symbol)
                for issue in issues
            ),
            (
                (
                    "descriptor-semantic-mismatch",
                    "worker_in",
                    "dwc3_otg_start_peripheral",
                ),
                (
                    "descriptor-semantic-mismatch",
                    "worker_out",
                    "dwc3_otg_start_peripheral",
                ),
            ),
        )

    def test_precise_stop_peripheral_labels_clear_the_historical_issue(self):
        corrected = tuple(
            replace(
                event,
                name=(
                    event.name.replace("worker_", "stop_peripheral_", 1)
                    if event.phase == p282.PHASE_CYCLE
                    and event.name.startswith("worker_")
                    else event.name
                ),
            )
            for event in p282.TRACE_EVENTS
        )
        gate.require_clean(
            corrected,
            post_call_offsets=(0x34, 0x450),
        )

    def test_actual_outer_work_labels_require_actual_outer_work_symbol(self):
        worker_events = tuple(
            replace(
                event,
                name=event.name.replace("worker_", "outer_sm_work_", 1),
                symbol="dwc3_otg_sm_work",
            )
            for event in p282.TRACE_EVENTS
            if event.phase == p282.PHASE_CYCLE
            and event.name.startswith("worker_")
        )
        gate.require_clean(worker_events)

    def test_stock_d1_descriptors_match_every_actual_attachment(self):
        gate.require_clean(d1_spec.TRACE_EVENTS)

    def test_kernel_normalized_kretprobe_maxactive_readback_is_accepted(self):
        readback = _kernel_readback(d1_spec.TRACE_EVENTS)
        gate.require_tracefs_readback_clean(
            readback,
            d1_spec.TRACE_EVENTS,
            group=d1_spec.TRACE_GROUP,
        )
        legacy_count = sum(
            bool(re.match(r"^[pr]:p284stock/", line))
            for line in readback.splitlines()
        )
        self.assertEqual(legacy_count, 19)
        self.assertEqual(len(d1_spec.TRACE_EVENTS), 27)

    def test_missing_kernel_normalized_return_probe_fails_readback_gate(self):
        readback = _kernel_readback(d1_spec.TRACE_EVENTS)
        lines = readback.splitlines()
        missing = next(
            line for line in lines
            if line.startswith("r16:p284stock/parent_suspend_out ")
        )
        issues = gate.audit_tracefs_readback(
            "\n".join(line for line in lines if line != missing) + "\n",
            d1_spec.TRACE_EVENTS,
            group=d1_spec.TRACE_GROUP,
        )
        self.assertEqual(
            tuple(
                (issue.code, issue.event_name)
                for issue in issues
            ),
            (("readback-event-missing", "parent_suspend_out"),),
        )

    def test_mode_store_writer_identity_label_is_symbol_exact(self):
        entry = next(
            event for event in d1_spec.TRACE_EVENTS
            if event.name == "mode_store_in"
        )
        self.assertEqual(
            entry.definition(),
            "p:p284stock/mode_store_in dwc3_msm:mode_store\n",
        )
        gate.require_clean((entry,))

    def test_semantic_writer_alias_does_not_hide_mode_store_attachment(self):
        entry = next(
            event for event in d1_spec.TRACE_EVENTS
            if event.name == "mode_store_in"
        )
        misleading = replace(entry, name="android_writer_in")
        with self.assertRaisesRegex(
            gate.ProbeNameGateError,
            "descriptor-semantic-mismatch",
        ):
            gate.require_clean((misleading,))

    def test_generic_worker_label_is_rejected_for_both_possible_symbols(self):
        current = next(
            event for event in p282.TRACE_EVENTS
            if event.name == "worker_in"
        )
        outer = replace(current, symbol="dwc3_otg_sm_work")
        for event in (current, outer):
            with self.subTest(symbol=event.symbol):
                with self.assertRaisesRegex(
                    gate.ProbeNameGateError,
                    "descriptor-semantic-mismatch",
                ):
                    gate.require_clean((event,))

    def test_unreviewed_attachment_symbol_fails_closed(self):
        current = next(
            event for event in p282.TRACE_EVENTS
            if event.name == "worker_in"
        )
        unknown = replace(
            current,
            name="mystery_in",
            symbol="unknown_function",
        )
        issues = gate.audit_events((unknown,))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "unknown-attached-symbol")

    def test_invalid_declared_probe_kind_fails_closed(self):
        current = next(
            event for event in p282.TRACE_EVENTS
            if event.name == "worker_in"
        )
        invalid = replace(
            current,
            name="stop_peripheral_in",
            probe_kind="ambiguous",
        )
        issues = gate.audit_events((invalid,))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "declared-probe-kind-invalid")


if __name__ == "__main__":
    unittest.main()
