"""Regression tests for a90_kernel_v2251_tail_target_evidence_classifier."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2251 = load_revalidation("a90_kernel_v2251_tail_target_evidence_classifier")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def stack_line(sample: int, index: int, symbol: str) -> str:
    return (
        f"icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_{sample}."
        f"stack_{index}=[<0xffffff800810{index:04x}>] {symbol}+0x10/0x80"
    )


def helper_lines(include_full_stack=True):
    lines = [
        "post_fw_ready_boot_wlan_trigger.executed=1",
        "post_fw_ready_boot_wlan_trigger.write_rc=0",
        "post_fw_ready_boot_wlan_trigger.reason=unit",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.begin=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_count=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.seen_count=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.timed_out=0",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.label=cfg",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.firmware=wlan/qca_cld/WCNSS_qcom_cfg.ini",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.seen=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.fed=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.source_bytes=12345",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.data_rc=0",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.loading_done_rc=0",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.target=1",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.comm=kworker/u16:1",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.wchan=worker_thread",
    ]
    symbols = v2251.TARGET_SYMBOLS if include_full_stack else v2251.TARGET_SYMBOLS[:3]
    lines.extend(stack_line(0, index, symbol) for index, symbol in enumerate(symbols))
    lines.extend([
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_1.target=0",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_1.stack_0=[<0>] unrelated+0x0/0x4",
    ])
    return lines


def scorer_summary(hit_count=0, sample_count=835):
    return {
        "decision": "v2247-tail-pc-lr-scorer-pass",
        "pass": True,
        "target_count": len(v2251.TARGET_SYMBOLS),
        "scoring": {
            "sample_count": sample_count,
            "hit_count": hit_count,
        },
        "exact_slide": {
            "accepted_exact_codeword_slide": True,
            "accepted_symbolization_slide": False,
            "acceptance_reason": "unit",
            "slide_hex": "0x123000",
        },
    }


class BasicParsers(unittest.TestCase):
    def test_parse_int_accepts_int_strings_hex_empty_and_invalid(self):
        self.assertEqual(v2251.parse_int(7), 7)
        self.assertEqual(v2251.parse_int("15"), 15)
        self.assertEqual(v2251.parse_int("0x10"), 16)
        self.assertIsNone(v2251.parse_int(""))
        self.assertIsNone(v2251.parse_int(None))
        self.assertIsNone(v2251.parse_int("not-an-int"))

    def test_extract_stack_symbol_requires_kernel_stack_marker(self):
        self.assertEqual(
            v2251.extract_stack_symbol("[<0xffffff8008100000>] request_firmware+0x10/0x40"),
            "request_firmware",
        )
        self.assertIsNone(v2251.extract_stack_symbol("request_firmware+0x10/0x40"))
        self.assertIsNone(v2251.extract_stack_symbol("[<0>] +0x0/0x4"))

    def test_read_json_returns_empty_dict_for_missing_path(self):
        self.assertEqual(v2251.read_json(Path("/definitely/missing/v2251.json")), {})


class HelperAndSummaryParsing(unittest.TestCase):
    def test_parse_helper_groups_boot_feeder_stack_samples_and_target_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            helper = Path(tmp) / "helper.result.cmdv1.txt"
            helper.write_bytes(("\n".join(helper_lines()) + "\n").encode() + b"\0")

            parsed = v2251.parse_helper(helper)

        self.assertEqual(parsed["boot_wlan"]["executed"], "1")
        self.assertEqual(parsed["feeder"]["request_0.firmware"], "wlan/qca_cld/WCNSS_qcom_cfg.ini")
        self.assertEqual(len(parsed["stack_samples"]), 2)
        target_sample = parsed["stack_samples"][0]
        self.assertTrue(target_sample["target"])
        self.assertEqual(target_sample["comm"], "kworker/u16:1")
        self.assertEqual(target_sample["target_symbols_present"], v2251.TARGET_SYMBOLS)
        self.assertTrue(target_sample["all_targets_present"])
        self.assertEqual(target_sample["target_symbol_count"], len(v2251.TARGET_SYMBOLS))
        self.assertLessEqual(len(target_sample["public_stack_preview"]), 12)
        self.assertGreaterEqual(parsed["target_token_counts"]["request_firmware"], 1)

    def test_summarize_feeder_normalizes_request0_booleans_and_return_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            helper = Path(tmp) / "helper.result.cmdv1.txt"
            write_text(helper, "\n".join(helper_lines()) + "\n")
            feeder = v2251.parse_helper(helper)["feeder"]

        summary = v2251.summarize_feeder(feeder)

        self.assertTrue(summary["begin"])
        self.assertEqual(summary["request_count"], 1)
        self.assertFalse(summary["timed_out"])
        self.assertEqual(summary["request0_label"], "cfg")
        self.assertTrue(summary["request0_seen"])
        self.assertTrue(summary["request0_fed"])
        self.assertEqual(summary["request0_source_bytes"], 12345)
        self.assertEqual(summary["request0_data_rc"], 0)
        self.assertEqual(summary["request0_loading_done_rc"], 0)

    def test_summarize_scorer_reports_absent_and_present_summaries(self):
        self.assertEqual(v2251.summarize_scorer({}), {
            "present": False,
            "decision": None,
            "pass": None,
            "sample_count": None,
            "hit_count": None,
            "target_count": None,
            "accepted_exact_codeword_slide": None,
            "accepted_symbolization_slide": None,
            "acceptance_reason": None,
            "slide_hex": None,
        })

        present = v2251.summarize_scorer(scorer_summary(hit_count=2, sample_count=10))

        self.assertTrue(present["present"])
        self.assertEqual(present["hit_count"], 2)
        self.assertEqual(present["sample_count"], 10)
        self.assertTrue(present["accepted_exact_codeword_slide"])


class SummaryBuilder(unittest.TestCase):
    def make_args(self, root: Path, helper_payload, scorer_payload):
        run_dir = root / "run"
        write_text(run_dir / "helper.result.cmdv1.txt", "\n".join(helper_payload) + "\n")
        scorer_path = root / "score" / "summary.json"
        write_json(scorer_path, scorer_payload)
        return argparse.Namespace(
            label="unit-v2251",
            run_dir=run_dir,
            scorer_summary=scorer_path,
        )

    def test_build_summary_confirms_generic_sampler_miss_when_deterministic_tail_evidence_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            args = self.make_args(root, helper_lines(), scorer_summary(hit_count=0, sample_count=835))

            summary = v2251.build_summary(args, out_dir)
            evidence = json.loads((out_dir / "tail_target_evidence.json").read_text(encoding="utf-8"))

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2251-tail-target-evidence-generic-sampler-miss-confirmed")
        self.assertTrue(summary["boot_wlan_executed"])
        self.assertTrue(summary["feeder_confirmed"])
        self.assertTrue(summary["stack_confirmed"])
        self.assertTrue(summary["generic_sampler_zero_hits"])
        self.assertEqual(summary["full_target_stack_sample_count"], 1)
        self.assertFalse(summary["private_evidence"]["contains_raw_runtime_addresses"])
        self.assertFalse(summary["private_evidence"]["contains_private_helper_excerpt"])
        self.assertEqual(evidence["scorer"]["hit_count"], 0)
        self.assertEqual(evidence["stack_samples"][0]["target_symbols_present"], v2251.TARGET_SYMBOLS)

    def test_build_summary_requests_review_when_full_target_stack_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            args = self.make_args(
                root,
                helper_lines(include_full_stack=False),
                scorer_summary(hit_count=0, sample_count=835),
            )

            summary = v2251.build_summary(args, out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2251-tail-target-evidence-review-needed")
        self.assertTrue(summary["boot_wlan_executed"])
        self.assertTrue(summary["feeder_confirmed"])
        self.assertFalse(summary["stack_confirmed"])
        self.assertTrue(summary["generic_sampler_zero_hits"])
        self.assertEqual(summary["full_target_stack_sample_count"], 0)

    def test_build_summary_confirms_tail_path_without_generic_zero_label_when_scorer_has_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            args = self.make_args(root, helper_lines(), scorer_summary(hit_count=3, sample_count=835))

            summary = v2251.build_summary(args, out_dir)

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2251-tail-target-evidence-confirmed")
        self.assertFalse(summary["generic_sampler_zero_hits"])


if __name__ == "__main__":
    unittest.main()
