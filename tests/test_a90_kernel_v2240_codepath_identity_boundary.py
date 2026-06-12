"""Regression tests for a90_kernel_v2240_codepath_identity_boundary."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2240 = load_revalidation("a90_kernel_v2240_codepath_identity_boundary")


def timeline_item(group, event, address, ts=1.0, surface="uprobe"):
    return {
        "group": group,
        "event": event,
        "surface": surface,
        "ts": ts,
        "line": f"task-1 [000] .... {ts:.6f}: {group}:{event}: ({address})",
    }


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class AddressAndSampleParsing(unittest.TestCase):
    def test_classify_domain_separates_kernel_user_library_pie_low_and_unknown(self):
        cases = [
            (0xFFFFFF8000000000, "kernel_canonical"),
            (0x0000007F12345000, "user_shared_library"),
            (0x0000005512345000, "user_pie_executable"),
            (0x1234, "user_or_low_va"),
            (0x0000008000000000, "unknown_noncanonical"),
        ]

        for address, expected in cases:
            with self.subTest(address=hex(address)):
                self.assertEqual(v2240.classify_domain(address), expected)

    def test_extract_samples_filters_a90_groups_deduplicates_and_parses_addresses(self):
        timeline = [
            timeline_item("a90cnss", "wlfw_start", "0x7f10001000", ts=3.0),
            timeline_item("a90cnss", "wlfw_start", "0x7f10009999", ts=4.0),
            timeline_item("a90libqmi", "libqmi_loop_client_init_ret", "0x7f20002000", ts=5.0),
            timeline_item("a90cnss", "_surface_nonlog", "0x7f30003000", ts=6.0),
            timeline_item("other", "wlfw_start", "0x7f40004000", ts=7.0),
            {"group": "a90pmsrv", "event": "pm_event", "line": "no address", "ts": 8.0},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v9100-live/parser/summary.json"
            write_json(path, {"timeline": timeline})
            samples = v2240.extract_samples(path)

        self.assertEqual([sample.event for sample in samples], [
            "wlfw_start",
            "libqmi_loop_client_init_ret",
        ])
        self.assertEqual(samples[0].run_id, "v9100")
        self.assertEqual(samples[0].address_hex, "0x7f10001000")
        self.assertEqual(samples[0].domain, "user_shared_library")
        self.assertEqual(samples[0].low12_hex, "0x0")

    def test_extract_samples_rejects_empty_timeline_or_no_addresses(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "v9101-live/parser/summary.json"
            no_address = Path(tmp) / "v9102-live/parser/summary.json"
            write_json(empty, {"timeline": []})
            write_json(no_address, {"timeline": [{"group": "a90cnss", "event": "wlfw_start"}]})

            with self.assertRaisesRegex(ValueError, "missing timeline"):
                v2240.extract_samples(empty)
            with self.assertRaisesRegex(ValueError, "no a90 probe samples"):
                v2240.extract_samples(no_address)


class SignatureSummaries(unittest.TestCase):
    def make_cnss_samples(self):
        return [
            v2240.ProbeSample("v1", "wlfw_start", "a90cnss", "uprobe", 1.0, 0x7F10001000, "0x7f10001000", "user_shared_library", "0x0", ""),
            v2240.ProbeSample("v1", "wlfw_service_request", "a90cnss", "uprobe", 2.0, 0x7F10001110, "0x7f10001110", "user_shared_library", "0x110", ""),
            v2240.ProbeSample("v1", "wlfw_cap_qmi", "a90cnss", "uprobe", 3.0, 0x7F10001220, "0x7f10001220", "user_shared_library", "0x220", ""),
            v2240.ProbeSample("v2", "wlfw_start", "a90cnss", "uprobe", 1.0, 0x7F20001000, "0x7f20001000", "user_shared_library", "0x0", ""),
            v2240.ProbeSample("v2", "wlfw_service_request", "a90cnss", "uprobe", 2.0, 0x7F20001110, "0x7f20001110", "user_shared_library", "0x110", ""),
            v2240.ProbeSample("v2", "wlfw_cap_qmi", "a90cnss", "uprobe", 3.0, 0x7F20001230, "0x7f20001230", "user_shared_library", "0x230", ""),
        ]

    def test_build_relative_signature_tracks_stable_delta_and_low12_separately(self):
        signature = v2240.build_a90cnss_relative_signature(self.make_cnss_samples())

        service = signature["stability"]["wlfw_service_request"]
        cap = signature["stability"]["wlfw_cap_qmi"]

        self.assertEqual(signature["per_run"]["v1"]["anchor_address"], "0x7f10001000")
        self.assertTrue(service["stable_delta"])
        self.assertEqual(service["delta_hex"], "0x110")
        self.assertTrue(service["stable_low12"])
        self.assertEqual(service["low12"], "0x110")
        self.assertFalse(cap["stable_delta"])
        self.assertFalse(cap["stable_low12"])

    def test_build_relative_signature_marks_runs_without_anchor(self):
        samples = [
            v2240.ProbeSample("v3", "wlfw_cap_qmi", "a90cnss", "uprobe", 1.0, 0x7F1, "0x7f1", "user_or_low_va", "0x7f1", ""),
        ]

        signature = v2240.build_a90cnss_relative_signature(samples)

        self.assertFalse(signature["per_run"]["v3"]["anchor_present"])
        self.assertEqual(signature["per_run"]["v3"]["events"], {})

    def test_summarize_low12_by_event_groups_by_group_and_event(self):
        samples = self.make_cnss_samples() + [
            v2240.ProbeSample("v1", "libqmi_loop_client_init_ret", "a90libqmi", "uprobe", 1.0, 0x5512345000, "0x5512345000", "user_pie_executable", "0x0", ""),
        ]

        summary = v2240.summarize_low12_by_event(samples)

        self.assertEqual(summary["a90cnss:wlfw_service_request"]["observed_runs"], 2)
        self.assertTrue(summary["a90cnss:wlfw_service_request"]["stable_low12"])
        self.assertEqual(summary["a90libqmi:libqmi_loop_client_init_ret"]["domains"], ["user_pie_executable"])


class SummaryBuilder(unittest.TestCase):
    def write_parser(self, root: Path, name: str, base: int, kernel: bool = False):
        address = "0xffffff8009a42334" if kernel else hex(base)
        timeline = [
            timeline_item("a90cnss", "wlfw_start", address, ts=1.0),
            timeline_item("a90cnss", "wlfw_service_request", hex(base + 0x110), ts=2.0),
            timeline_item("a90cnss", "wlfw_cap_qmi", hex(base + 0x220), ts=3.0),
            timeline_item("a90cnss", "wlfw_bdf_entry", hex(base + 0x330), ts=4.0),
            timeline_item("a90cnss", "wlfw_bdf_send_ret", hex(base + 0x440), ts=5.0),
            timeline_item("a90cnss", "wlfw_bdf_result_log", hex(base + 0x550), ts=6.0),
            timeline_item("a90cnss", "wlfw_worker_done_signal", hex(base + 0x660), ts=7.0),
            timeline_item("a90cnss", "wlfw_worker_post_done_wait", hex(base + 0x770), ts=8.0),
            timeline_item("a90libqmi", "libqmi_loop_client_init_ret", hex(base + 0x880), ts=9.0),
        ]
        path = root / f"{name}/parser/summary.json"
        write_json(path, {"timeline": timeline})
        return path

    def test_build_summary_passes_for_user_probe_ips_and_records_identity_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parser_paths = [
                self.write_parser(root, "v9103-live", 0x7F10001000),
                self.write_parser(root, "v9104-live", 0x7F20001000),
            ]
            exact = root / "exact.json"
            v2239_path = root / "v2239.json"
            write_json(exact, {"exact_slide_hex": "0x123000", "decision": "exact"})
            write_json(v2239_path, {"decision": "v2239-pass"})

            summary = v2240.build_summary(parser_paths, exact, v2239_path, root / "out", "unit")

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2240-codepath-identity-boundary-pass")
        self.assertEqual(summary["kernel_exact_slide"]["slide_hex"], "0x123000")
        self.assertIn("user_shared_library", summary["a90_probe_ip_domain_counts"])
        self.assertEqual(
            summary["identity_contract"]["a90_user_uprobe_side"],
            "Use event names plus stable intra-binary relative offset signatures; do not subtract the kernel KASLR slide from user-space __probe_ip values.",
        )
        self.assertIn("wlfw_service_request", summary["stable_a90cnss_signature_events"])

    def test_build_summary_flags_unexpected_kernel_canonical_a90_probe_ip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parser_paths = [self.write_parser(root, "v9105-live", 0x7F10001000, kernel=True)]
            exact = root / "exact.json"
            v2239_path = root / "v2239.json"
            write_json(exact, {"exact_slide_hex": "0x123000", "decision": "exact"})
            write_json(v2239_path, {"decision": "v2239-pass"})

            summary = v2240.build_summary(parser_paths, exact, v2239_path, root / "out", "unit")

        self.assertFalse(summary["pass"])
        self.assertEqual(
            summary["decision"],
            "v2240-codepath-identity-boundary-unexpected-kernel-a90-probe-ip",
        )
        self.assertEqual(summary["a90_kernel_canonical_probe_ips"][0]["event"], "wlfw_start")


if __name__ == "__main__":
    unittest.main()
