from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_banner_result_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_banner_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 banner-result contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318BannerResultContractTest(unittest.TestCase):
    def inputs(self):
        return {
            "materialized_data": (ROOT / P318.DEFAULT_MATERIALIZED).read_bytes(),
            "p260_data": (ROOT / P318.DEFAULT_P260_RUNTIME).read_bytes(),
            "envelope_data": (ROOT / P318.DEFAULT_P317_ENVELOPE).read_bytes(),
            "base_envelope_data": (ROOT / P318.DEFAULT_BASE_ENVELOPE).read_bytes(),
            "dwc3_core_data": (ROOT / P318.DEFAULT_DWC3_CORE).read_bytes(),
            "dwc3_gadget_data": (ROOT / P318.DEFAULT_DWC3_GADGET).read_bytes(),
            "dwc3_ep0_data": (ROOT / P318.DEFAULT_DWC3_EP0).read_bytes(),
            "dwc3_trace_data": (ROOT / P318.DEFAULT_DWC3_TRACE).read_bytes(),
            "dwc3_trace_header_data": (
                ROOT / P318.DEFAULT_DWC3_TRACE_HEADER
            ).read_bytes(),
            "dwc3_makefile_data": (ROOT / P318.DEFAULT_DWC3_MAKEFILE).read_bytes(),
            "timekeeping_header_data": (
                ROOT / P318.DEFAULT_TIMEKEEPING_HEADER
            ).read_bytes(),
            "timekeeping_source_data": (
                ROOT / P318.DEFAULT_TIMEKEEPING_SOURCE
            ).read_bytes(),
            "kernel_config_data": (ROOT / P318.DEFAULT_KERNEL_CONFIG).read_bytes(),
            "extractor_data": SCRIPT.read_bytes(),
        }

    def test_current_blind_spot_and_successor_design_are_exact(self):
        result = P318.build_contract(**self.inputs())
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertTrue(result["current"]["terminal_before_banner"])
        self.assertTrue(result["current"]["banner_return_discarded"])
        self.assertFalse(result["current"]["terminal_can_retain_banner_result"])
        self.assertEqual(
            result["successor"]["status"],
            "CHANGES_REQUIRED_PRODUCER_AND_V4_NOT_IMPLEMENTED",
        )
        self.assertTrue(
            result["successor"]["schema"]["new_envelope_version_required"]
        )
        self.assertEqual(result["successor"]["schema"]["envelope_version"], 4)
        self.assertTrue(
            result["host_event_source_audit"]["setup_completion_source_bound"]
        )
        self.assertTrue(
            result["host_event_source_audit"]["module_only_producer_feasible"]
        )
        self.assertTrue(
            result["host_event_source_audit"][
                "dwc3_event_callback_proto_source_bound"
            ]
        )
        self.assertFalse(
            result["host_event_source_audit"]["producer_implementation_present"]
        )
        self.assertFalse(result["scope"]["p318_candidate_ready"])

    def test_terminal_banner_order_mutation_fails(self):
        values = self.inputs()
        terminal = b"s22_max77705_checkpoint_payload_terminal_position("
        banner = b"if (tty_fd >= 0) (void)p260_write_banner(tty_fd);"
        start = values["materialized_data"].index(
            b"static __attribute__((noreturn)) void p317_publish("
        )
        terminal_at = values["materialized_data"].index(terminal, start)
        banner_at = values["materialized_data"].index(banner, terminal_at)
        mutated = bytearray(values["materialized_data"])
        mutated[terminal_at : terminal_at + len(terminal)] = b"X" * len(terminal)
        mutated[banner_at : banner_at + len(banner)] = b"Y" * len(banner)
        values["materialized_data"] = bytes(mutated)
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_discarded_return_mutation_fails(self):
        values = self.inputs()
        old = b"if (tty_fd >= 0) (void)p260_write_banner(tty_fd);"
        new = b"if (tty_fd >= 0) p260_write_banner(tty_fd);".ljust(
            len(old), b" "
        )
        values["materialized_data"] = values["materialized_data"].replace(
            old, new, 1
        )
        with self.assertRaisesRegex(P318.BannerContractError, "discarded banner"):
            P318.build_contract(**values)

    def test_eagain_deadline_mutation_fails(self):
        values = self.inputs()
        values["p260_data"] = values["p260_data"].replace(
            b"if (rc == -EAGAIN && retry_eagain)",
            b"if (rc == -EAGAIN)                ",
            1,
        )
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_short_write_accounting_mutation_fails(self):
        values = self.inputs()
        values["p260_data"] = values["p260_data"].replace(
            b"written += (size_t)rc;", b"written = (size_t)rc; ", 1
        )
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_banner_length_source_mutation_fails(self):
        values = self.inputs()
        values["p260_data"] = values["p260_data"].replace(
            b"static char p260_banner[50];",
            b"static char p260_banner[51];",
            1,
        )
        with self.assertRaisesRegex(P318.BannerContractError, "banner length"):
            P318.build_contract(**values)

    def test_all_four_outcomes_have_boundary_preimages(self):
        successor = P318.successor_contract()
        preimages = successor["arming"]["positive_preimages"]
        self.assertEqual({item["outcome"] for item in preimages}, set(P318.OUTCOMES))
        self.assertEqual(
            sorted(
                {
                    item["bytes_written"]
                    for item in preimages
                    if item["outcome"] == "partial"
                }
            ),
            [1, 48],
        )
        self.assertEqual(successor["attempt"]["count"], 1)
        self.assertTrue(successor["attempt"]["retry_after_terminal_forbidden"])

    def test_banner_terminal_domain_is_total_and_zero_failures_are_classified(self):
        audit = P318.audit_banner_terminal_domain()
        self.assertEqual(audit["valid_terminal_row_count"], 344)
        self.assertEqual(audit["outcome_set"], sorted(P318.OUTCOMES))
        self.assertTrue(audit["zero_write_at_zero_is_failure"])
        self.assertTrue(audit["invalid_short_at_zero_is_failure"])
        self.assertTrue(audit["eagain_at_zero_is_timeout"])
        self.assertEqual(
            P318.classify_banner_terminal(
                bytes_written=1, error_class="invalid_short_write"
            ),
            "partial",
        )
        with self.assertRaises(P318.BannerContractError):
            P318.classify_banner_terminal(bytes_written=0, error_class="none")
        with self.assertRaises(P318.BannerContractError):
            P318.classify_banner_terminal(bytes_written=49, error_class="epipe")

    def test_successor_uses_one_absolute_deadline_for_every_retry_path(self):
        result = P318.build_contract(**self.inputs())
        self.assertTrue(result["current"]["p260_write_all_eintr_bypasses_deadline"])
        attempt = result["successor"]["attempt"]
        self.assertTrue(attempt["existing_p260_helper_is_not_sufficient"])
        self.assertTrue(attempt["deadline_covers_eintr"])
        self.assertTrue(attempt["deadline_covers_eagain"])
        self.assertTrue(attempt["deadline_covers_every_short_write_iteration"])
        self.assertTrue(attempt["deadline_never_reinitialized"])

    def test_v4_timing_banner_and_poll_budget_is_exact(self):
        budget = P318.validate_v4_budget()
        self.assertEqual(
            budget["metadata_size"]
            + budget["payload_size"]
            + budget["crc_size"],
            budget["envelope_size"],
        )
        self.assertEqual(budget["v4_prefix_size"], 25)
        self.assertEqual(budget["lossless_poll_capacity"], 51)
        self.assertEqual(budget["overflow_summary_size"], 44)
        self.assertEqual(budget["overflow_total_size"], 69)
        self.assertEqual(budget["overflow_spare_size"], 7)
        self.assertGreaterEqual(
            budget["signed_delta_us_max"], budget["process_v2_guard_us"]
        )

    def test_v4_budget_mutations_fail_closed(self):
        cases = (
            {"payload_size": 75},
            {"timing_prefix_size": 21},
            {"banner_prefix_size": 4},
            {"overflow_summary_size": 43},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(P318.BannerContractError):
                    P318.validate_v4_budget(**kwargs)

    def test_only_actual_host_caused_events_are_timing_anchors(self):
        timing = P318.successor_contract()["timing"]
        self.assertEqual(
            timing["first_host_event_kinds"],
            ["none", "reset", "connect_done", "setup"],
        )
        self.assertNotIn("gadget_ready", timing["first_host_event_kinds"])
        self.assertTrue(timing["gadget_ready_is_host_event_forbidden"])
        self.assertFalse(timing["cross_clock_synchronization_required"])
        self.assertEqual(
            timing["encoding"],
            "pre_is_zero_origin_plus_five_signed_int32_microsecond_deltas",
        )
        self.assertEqual(timing["causal_validity_masks"], [0x2F, 0x3F])
        self.assertIn("not observable", timing["legacy_0x0f_meaning"])
        self.assertEqual(
            timing["required_device_sample_order"],
            "pre <= write <= post1 < post2",
        )
        self.assertFalse(
            timing["guard_budget"]["design_value_is_execution_authority"]
        )
        self.assertTrue(
            timing["guard_budget"]["qualification_must_source_bind_actual_guard"]
        )

    def test_poll_boundary_and_overflow_remain_fail_closed(self):
        poll = P318.successor_contract()["poll_evidence"]
        self.assertEqual(poll["lossless_boundary_preimages"], [51, 52])
        self.assertEqual(poll["overflow_summary_size"], 44)
        self.assertFalse(poll["overflow_causal_result_allowed"])

    def test_host_event_source_dispatch_mutation_fails(self):
        values = self.inputs()
        values["dwc3_gadget_data"] = values["dwc3_gadget_data"].replace(
            b"case DWC3_DEVICE_EVENT_CONNECT_DONE:",
            b"case DWC3_DEVICE_EVENT_CONNECT_DONX:",
            1,
        )
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_tracepoint_export_and_clock_mutations_fail(self):
        cases = (
            (
                "dwc3_trace_data",
                b"EXPORT_TRACEPOINT_SYMBOL_GPL(dwc3_event);",
                b"EXPORT_TRACEPOINT_SYMBOL_GPL(dwc3_other);",
            ),
            (
                "timekeeping_source_data",
                b"EXPORT_SYMBOL_GPL(ktime_get);",
                b"EXPORT_SYMBOL_GPL(ktime_get_other);",
            ),
            (
                "kernel_config_data",
                b"CONFIG_TRACING=y",
                b"# CONFIG_TRACING is not set",
            ),
        )
        for field, old, new in cases:
            with self.subTest(field=field):
                values = self.inputs()
                values[field] = values[field].replace(old, new, 1)
                with self.assertRaises(P318.BannerContractError):
                    P318.build_contract(**values)

    def test_tracepoint_callback_abi_mutations_fail(self):
        cases = (
            (
                b"TP_PROTO(u32 event, struct dwc3 *dwc),",
                b"TP_PROTO(u32 event, void *dwc),       ",
            ),
            (
                b"__field(u32, ep0state)",
                b"__field(u32, otherstate)",
            ),
            (
                b"__entry->ep0state = dwc->ep0state;",
                b"__entry->ep0state = 0;             ",
            ),
        )
        for old, new in cases:
            with self.subTest(old=old):
                values = self.inputs()
                values["dwc3_trace_header_data"] = values[
                    "dwc3_trace_header_data"
                ].replace(old, new, 1)
                with self.assertRaisesRegex(
                    P318.BannerContractError, "callback ABI"
                ):
                    P318.build_contract(**values)

    def test_errno_classes_and_banner_u8_bound_are_explicit(self):
        successor = P318.successor_contract()
        mapping = successor["error_class_encoding"]["mapping"]
        self.assertEqual(
            len({mapping["eagain_deadline"], mapping["epipe"], mapping["enodev"]}),
            3,
        )
        self.assertEqual(successor["banner_length_contract"]["expected_bytes"], 49)
        retained = {
            item["error_class"] for item in successor["arming"]["positive_preimages"]
        }
        self.assertEqual(retained - {"none"}, set(P318.ERROR_CLASSES) - {"none"})
        self.assertTrue(
            successor["banner_length_contract"][
                "encoder_rejects_out_of_range_instead_of_saturating"
            ]
        )


if __name__ == "__main__":
    unittest.main()
