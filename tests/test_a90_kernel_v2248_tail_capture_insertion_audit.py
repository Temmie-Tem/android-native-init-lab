"""Regression tests for a90_kernel_v2248_tail_capture_insertion_audit."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2248 = load_revalidation("a90_kernel_v2248_tail_capture_insertion_audit")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def helper_source_text(ordered=True):
    lines = [
        "#define A90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_WAIT_MS 30000",
        "static int append_post_fw_ready_boot_wlan_trigger(struct buf *stdout_buf) {",
        "  return 0;",
        "}",
        "if (wlan_pd_post_fw_ready_fwclass_bridge) {",
        "  append_icnss_register_probe_stack_sampler(stdout_buf, \"after_boot_wlan_trigger\", 1000);",
    ]
    if ordered:
        lines.extend([
            "  append_post_fw_ready_boot_wlan_trigger(stdout_buf);",
            "  usleep(8000000);",
            "  append_qcacld_firmware_class_fallback_feeder(stdout_buf, \"after_boot_wlan_trigger\", 30000);",
        ])
    else:
        lines.extend([
            "  append_qcacld_firmware_class_fallback_feeder(stdout_buf, \"after_boot_wlan_trigger\", 30000);",
            "  usleep(8000000);",
            "  append_post_fw_ready_boot_wlan_trigger(stdout_buf);",
        ])
    lines.extend([
        "  append_icnss_register_probe_stack_sampler(stdout_buf, \"after_boot_wlan_long_window\", 1000);",
        "}",
    ])
    return "\n".join(lines) + "\n"


def build_v2237_text(has_env_flag=True):
    env_flag = (
        'SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = "A90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1"'
        if has_env_flag
        else 'SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = "A90_WIFI_TEST_BOOT_SERVICE_OBJECT_VISIBLE=1"'
    )
    return "\n".join([
        env_flag,
        'args += ["--helper-binary", "helper"]',
        'RAMDISK_CPIO = "ramdisk.cpio"',
        'args += ["--ramdisk-cpio", RAMDISK_CPIO]',
        '"--init-version": "0.9.268"',
    ]) + "\n"


def helper_v2216_text():
    return "\n".join([
        '#define A90_VERSION "a90_bpf_perf_regs_codeword_sample_ring v2216"',
        'usage("--duration-ms N --period-ns N --print-limit N");',
        'if (!allow_attach) die("--allow-attach required");',
        'printf("result=v2216-perf-regs-codeword-sample-ring-complete\\n");',
    ]) + "\n"


def runner_v2216_text():
    return "\n".join([
        'REMOTE_HELPER = "/cache/bin/a90_bpf_perf_regs_codeword_sample_ring"',
        'def install_helper(): pass',
        'cmd = [REMOTE_HELPER, "--allow-attach"]',
    ]) + "\n"


class PatchModulePaths:
    def __init__(self, root: Path, ordered=True, has_env_flag=True):
        self.root = root
        self.paths = {
            "HELPER_SOURCE": root / "a90_android_execns_probe.c",
            "BUILD_V2237": root / "build_native_init_boot_v2237_supplicant_terminate_poll.py",
            "RUNNER_V2216": root / "native_kernel_perf_regs_codeword_sample_ring_v2216.py",
            "HELPER_V2216": root / "a90_bpf_perf_regs_codeword_sample_ring.c",
        }
        write_text(self.paths["HELPER_SOURCE"], helper_source_text(ordered=ordered))
        write_text(self.paths["BUILD_V2237"], build_v2237_text(has_env_flag=has_env_flag))
        write_text(self.paths["RUNNER_V2216"], runner_v2216_text())
        write_text(self.paths["HELPER_V2216"], helper_v2216_text())
        self.old = {}

    def __enter__(self):
        for name, path in self.paths.items():
            self.old[name] = getattr(v2248, name)
            setattr(v2248, name, path)
        return self

    def __exit__(self, exc_type, exc, tb):
        for name, path in self.old.items():
            setattr(v2248, name, path)


class MatchHelpers(unittest.TestCase):
    def test_line_matches_returns_line_numbers_and_stripped_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.c"
            write_text(path, "alpha\n  beta  \ngamma beta\n")

            rows = v2248.line_matches(path, r"beta")

        self.assertEqual(rows, [{"line": 2, "text": "  beta"}, {"line": 3, "text": "gamma beta"}])

    def test_require_matches_raises_runtime_error_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.c"
            write_text(path, "alpha\n")

            with self.assertRaises(RuntimeError) as ctx:
                v2248.require_matches(path, "needle", r"beta")

        self.assertIn("missing needle", str(ctx.exception))

    def test_first_line_returns_first_or_minus_one(self):
        self.assertEqual(v2248.first_line([{"line": 9}, {"line": 10}]), 9)
        self.assertEqual(v2248.first_line([]), -1)


class AnchorReaders(unittest.TestCase):
    def test_helper_tail_anchors_extract_lines_and_ordered_window(self):
        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp), ordered=True):
            anchors = v2248.helper_tail_anchors()

        self.assertGreater(anchors["post_fw_ready_trigger_function_line"], 0)
        self.assertGreater(anchors["post_fw_ready_trigger_call_line"], 0)
        self.assertTrue(anchors["ordered_tail_window"])
        self.assertTrue(anchors["fw_ready_wait_macro_lines"])
        self.assertTrue(anchors["route_gate_lines"])

    def test_build_anchors_detects_bridge_flag_and_baseline_identity(self):
        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp), has_env_flag=True):
            anchors = v2248.build_anchors()

        self.assertTrue(anchors["service_object_fwclass_bridge_flag_present"])
        self.assertEqual(anchors["baseline_init_version"], "0.9.268")
        self.assertEqual(anchors["baseline_build"], "v2237-supplicant-terminate-poll")
        self.assertGreater(anchors["helper_binary_line"], 0)

    def test_v2216_sampler_anchors_capture_helper_and_runner_contract(self):
        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp)):
            anchors = v2248.v2216_sampler_anchors()

        self.assertEqual(anchors["remote_helper_path"], "/cache/bin/a90_bpf_perf_regs_codeword_sample_ring")
        self.assertEqual(anchors["default_duration_ms"], 1000)
        self.assertEqual(anchors["default_period_ns"], 1000000)
        self.assertTrue(anchors["supports_tail_window_duration"])
        self.assertGreater(anchors["runner_install_helper_line"], 0)


class SummaryBuilder(unittest.TestCase):
    def make_args(self):
        return argparse.Namespace(label="unit")

    def test_build_summary_passes_and_emits_tail_capture_contract(self):
        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp), ordered=True, has_env_flag=True):
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()

            summary = v2248.build_summary(self.make_args(), out_dir)
            summary_file = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2248-tail-capture-insertion-audit-pass")
        self.assertFalse(summary["analysis"]["host_after_boot_runner_sufficient"])
        self.assertTrue(summary["analysis"]["requires_embedded_concurrent_sampler"])
        self.assertEqual(summary["next_live_contract"]["next_cycle"], "V2249")
        self.assertIn("--allow-attach", summary["next_live_contract"]["required_helper_args"])
        self.assertEqual(summary_file["decision"], summary["decision"])

    def test_build_summary_fails_when_order_or_bridge_flag_is_wrong(self):
        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp), ordered=False, has_env_flag=True):
            out_dir = Path(tmp) / "out-order"
            out_dir.mkdir()
            bad_order = v2248.build_summary(self.make_args(), out_dir)

        with tempfile.TemporaryDirectory() as tmp, PatchModulePaths(Path(tmp), ordered=True, has_env_flag=False):
            out_dir = Path(tmp) / "out-flag"
            out_dir.mkdir()
            missing_flag = v2248.build_summary(self.make_args(), out_dir)

        self.assertFalse(bad_order["pass"])
        self.assertEqual(bad_order["decision"], "v2248-tail-capture-insertion-audit-failed")
        self.assertFalse(missing_flag["pass"])
        self.assertEqual(missing_flag["decision"], "v2248-tail-capture-insertion-audit-failed")


if __name__ == "__main__":
    unittest.main()
