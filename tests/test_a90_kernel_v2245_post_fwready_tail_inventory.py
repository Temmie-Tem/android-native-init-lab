"""Regression tests for a90_kernel_v2245_post_fwready_tail_inventory."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2245 = load_revalidation("a90_kernel_v2245_post_fwready_tail_inventory")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_run(root: Path, name: str, helper_lines: list[str], summary_lines: list[str]):
    run_dir = root / name
    write_text(run_dir / "device/helper_result.txt", "\n".join(helper_lines) + "\n")
    write_text(run_dir / "device/summary.txt", "\n".join(summary_lines) + "\n")
    return run_dir


def complete_tail_lines():
    return [
        "post_fw_ready_boot_wlan_trigger.begin=1",
        "post_fw_ready_boot_wlan_trigger.executed=1",
        "post_fw_ready_boot_wlan_trigger.write_rc=0",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.firmware=WCNSS_qcom_cfg.ini",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.fed=1",
        "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.source_bytes=12345",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.register_driver.processed=1",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.cfg_req=1",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.cfg_resp=1",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.mode_req=2",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.mode_resp=2",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.ini_req=1",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.ini_resp=1",
        "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.state.hex=0xd85",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.target=1",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.comm=kworker",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.wchan=worker_thread",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.stack_0=icnss_register_driver",
        "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.stack_1=process_one_work",
    ]


class BasicParsers(unittest.TestCase):
    def test_read_key_values_is_lossy_and_last_value_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kv.txt"
            path.write_bytes(b"a=1\0ignored\nb=2\na=3\nnoequals\n")

            values = v2245.read_key_values(path)

        self.assertEqual(values, {"a": "3", "b": "2"})
        self.assertEqual(v2245.read_key_values(Path("/no/such/file")), {})

    def test_as_int_and_value_is_one_cover_empty_hex_and_invalid_values(self):
        self.assertEqual(v2245.as_int("0x10"), 16)
        self.assertEqual(v2245.as_int(""), None)
        self.assertEqual(v2245.as_int(None), None)
        self.assertEqual(v2245.as_int("bad"), None)
        self.assertTrue(v2245.value_is_one({"x": "1"}, "x"))
        self.assertFalse(v2245.value_is_one({"x": "01"}, "x"))

    def test_infer_run_id_strips_suffix_when_present(self):
        self.assertEqual(v2245.infer_run_id(Path("/tmp/v2233-live")), "v2233")
        self.assertEqual(v2245.infer_run_id(Path("/tmp/custom")), "custom")

    def test_count_tail_keys_counts_known_prefix_groups_only(self):
        counts = v2245.count_tail_keys({
            "post_fw_ready_boot_wlan_trigger.begin": "1",
            "post_fw_ready_boot_wlan_trigger.executed": "1",
            "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count": "1",
            "unrelated": "1",
        })

        self.assertEqual(counts["post_fw_ready_boot_wlan_trigger"], 2)
        self.assertEqual(counts["qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger"], 1)
        self.assertNotIn("unrelated", counts)


class StageAndStackClassification(unittest.TestCase):
    def test_collect_target_stacks_keeps_only_target_samples_and_stack_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            helper = Path(tmp) / "helper_result.txt"
            write_text(
                helper,
                "\n".join([
                    "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.target=1",
                    "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.comm=kworker",
                    "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.wchan=worker_thread",
                    "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_0.stack_0=icnss_register_driver",
                    "icnss_register_probe_stack_sampler.after_boot_wlan_trigger.sample_1.stack_0=ignored_without_target",
                ]),
            )

            stacks = v2245.collect_target_stacks(helper)

        self.assertEqual(len(stacks), 1)
        self.assertEqual(stacks[0]["sample"], "sample_0")
        self.assertEqual(stacks[0]["comm"], "kworker")
        self.assertEqual(stacks[0]["stack_depth"], 1)
        self.assertEqual(stacks[0]["stack_functions"], ["icnss_register_driver"])

    def test_classify_stage_covers_absent_blocked_failure_partial_and_complete(self):
        self.assertEqual(v2245.classify_stage({}, {}), "tail_absent")
        self.assertEqual(
            v2245.classify_stage({"post_fw_ready_boot_wlan_trigger.begin": "1"}, {}),
            "boot_wlan_not_executed",
        )
        self.assertEqual(
            v2245.classify_stage({
                "post_fw_ready_boot_wlan_trigger.begin": "1",
                "post_fw_ready_boot_wlan_trigger.executed": "1",
                "post_fw_ready_boot_wlan_trigger.write_rc": "-1",
            }, {}),
            "boot_wlan_write_failed",
        )
        self.assertEqual(
            v2245.classify_stage({
                "post_fw_ready_boot_wlan_trigger.begin": "1",
                "post_fw_ready_boot_wlan_trigger.executed": "1",
                "post_fw_ready_boot_wlan_trigger.write_rc": "0",
            }, {}),
            "boot_wlan_executed_no_fwclass_feed",
        )
        partial = {
            "post_fw_ready_boot_wlan_trigger.begin": "1",
            "post_fw_ready_boot_wlan_trigger.executed": "1",
            "post_fw_ready_boot_wlan_trigger.write_rc": "0",
            "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count": "1",
            "wlan_pd_icnss_ipc_snapshot.after_boot_wlan_long_window.icnss_stats.event.register_driver.processed": "1",
        }
        self.assertEqual(v2245.classify_stage(partial, {}), "driver_probe_tail_partial")

        complete = dict(line.split("=", 1) for line in complete_tail_lines() if "=" in line)
        self.assertEqual(v2245.classify_stage(complete, {"wlan0_present": "1"}), "tail_complete_wlan0_ready")

    def test_summarize_run_returns_selected_public_signals_and_target_stack_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = write_run(Path(tmp), "v2233-live", complete_tail_lines(), ["wlan0_present=1"])

            summary = v2245.summarize_run(run_dir)

        self.assertEqual(summary["run_id"], "v2233")
        self.assertTrue(summary["helper_result_present"])
        self.assertEqual(summary["tail_stage"], "tail_complete_wlan0_ready")
        self.assertEqual(summary["target_stack_sample_count"], 1)
        self.assertEqual(
            summary["signals"]["qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.firmware"],
            "WCNSS_qcom_cfg.ini",
        )


class SummaryBuilder(unittest.TestCase):
    def make_args(self, root: Path, run_dirs, v2244_payload):
        v2244_path = root / "v2244.json"
        write_json(v2244_path, v2244_payload)
        return argparse.Namespace(
            label="unit",
            run_dir=run_dirs,
            v2244_summary=v2244_path,
        )

    def test_compare_runs_marks_tail_as_success_delta_only_when_semantic_order_is_identical(self):
        runs = {
            "v1": {"tail_stage": "tail_absent"},
            "v2": {"tail_stage": "tail_complete_wlan0_ready"},
        }
        v2244 = {
            "comparison": {
                "edge_sets_identical_across_runs": True,
                "semantic_signatures_identical_across_runs": True,
            }
        }

        comparison = v2245.compare_runs(runs, v2244)

        self.assertTrue(comparison["post_fwready_tail_explains_success_delta"])
        self.assertEqual(comparison["tail_complete_runs"], ["v2"])
        self.assertEqual(comparison["tail_absent_runs"], ["v1"])

    def test_build_summary_passes_for_absent_absent_complete_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            no_tail_a = write_run(root, "v2229-live", [], ["wlan0_present=0"])
            no_tail_b = write_run(root, "v2231-live", [], ["wlan0_present=0"])
            complete = write_run(root, "v2233-live", complete_tail_lines(), ["wlan0_present=1"])
            args = self.make_args(
                root,
                [no_tail_a, no_tail_b, complete],
                {
                    "comparison": {
                        "edge_sets_identical_across_runs": True,
                        "semantic_signatures_identical_across_runs": True,
                    }
                },
            )
            out_dir = root / "out"
            out_dir.mkdir()

            summary = v2245.build_summary(args, out_dir)
            inventory = json.loads((root / summary["inventory"]["path"]).read_text(encoding="utf-8"))

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2245-post-fwready-tail-inventory-pass")
        self.assertEqual(summary["tail_stage_counts"], {"tail_absent": 2, "tail_complete_wlan0_ready": 1})
        self.assertTrue(summary["comparison"]["post_fwready_tail_explains_success_delta"])
        self.assertFalse(summary["inventory"]["raw_helper_result_published"])
        self.assertIn("runs", inventory)

    def test_build_summary_requests_review_when_wlfw_semantics_are_not_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            no_tail = write_run(root, "v2229-live", [], ["wlan0_present=0"])
            complete = write_run(root, "v2233-live", complete_tail_lines(), ["wlan0_present=1"])
            args = self.make_args(
                root,
                [no_tail, complete],
                {
                    "comparison": {
                        "edge_sets_identical_across_runs": True,
                        "semantic_signatures_identical_across_runs": False,
                    }
                },
            )
            out_dir = root / "out"
            out_dir.mkdir()

            summary = v2245.build_summary(args, out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2245-post-fwready-tail-inventory-review-needed")
        self.assertFalse(summary["comparison"]["post_fwready_tail_explains_success_delta"])


if __name__ == "__main__":
    unittest.main()
