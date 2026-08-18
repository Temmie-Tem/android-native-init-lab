import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
ANALYSIS = REVALIDATION / "s22plus_fyg8_p319_last_kmsg_retention_analysis.py"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_STAGE_A_PROBE_RESULT_2026-08-18.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def kernel_line(t, body, comm="kworker/u16:3", pid=245):
    return f"[{t:12.6f}] [0: {comm}: {pid}] {body}".encode()


class P319LastKmsgRetentionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(ANALYSIS, "p319_last_kmsg_retention")
        cls.report = REPORT.read_text(encoding="utf-8")

    def build(self, *, banner=True, start=0.0, count=200, userspace=True, xbl=True):
        lines = []
        if banner:
            lines.append(kernel_line(0.0, "Linux version 5.10.209-qgki-g0 (b@h)"))
        for index in range(count):
            body = "init: starting service" if userspace else "clk: probe ok"
            comm, pid = ("init", 1) if userspace else ("candidate", 1)
            lines.append(kernel_line(start + index * 0.01, body, comm, pid))
        if userspace:
            lines += [
                kernel_line(start + 5, "apexd: Marking APEXd as starting", "apexd", 1166)
            ] * 15
            lines.append(kernel_line(start + 6, "zygote preload", "zygote", 900))
        if xbl:
            lines.append(b"{ 1350174 }[ XBL ] Minidump      : ON")
            lines.append(b"{ 1350180 }[ XBL ] Exit EBS")
        return b"\n".join(lines)

    def test_pid1_traffic_names_a_stock_boot_not_the_filename(self):
        value = self.module.analyse(self.build())
        self.assertEqual(value["boot_kind"], "stock_android_boot")
        self.assertGreater(value["stock_userspace_markers"]["init:"], 100)
        self.assertGreater(value["stock_userspace_markers"]["apexd"], 10)

    def test_a_capture_without_pid1_traffic_is_not_a_stock_boot(self):
        # A native-init candidate replaces PID 1, so this is the shape its own
        # boot would have to take.
        value = self.module.analyse(self.build(userspace=False))
        self.assertEqual(value["boot_kind"], "no_stock_userspace")
        self.assertEqual(sum(value["stock_userspace_markers"].values()), 0)
        # PID 1 is the candidate, not init.  That is the whole discriminator.
        self.assertEqual(value["pid1_comms"], ["candidate"])

    def test_markers_are_scoped_to_the_message_not_the_comm_column(self):
        # Counting across the whole line also counts the comm field, which
        # inflates every process name; the first version of this analyser did.
        data = b"\n".join(
            kernel_line(1.0 + index * 0.01, "clk: probe ok", "apexd", 1166)
            for index in range(30)
        )
        value = self.module.analyse(data)
        self.assertEqual(value["stock_userspace_markers"]["apexd"], 0)

    def test_pid1_comm_settles_a_stock_boot_on_its_own(self):
        data = b"\n".join(
            kernel_line(1.0 + index * 0.01, "clk: probe ok", "init", 1)
            for index in range(5)
        )
        value = self.module.analyse(data)
        self.assertEqual(value["pid1_comms"], ["init"])
        self.assertEqual(value["boot_kind"], "stock_android_boot")

    def test_empty_kernel_log_is_named_rather_than_guessed(self):
        value = self.module.analyse(b"{ 1 }[ XBL ] only bootloader\n")
        self.assertEqual(value["boot_kind"], "no_kernel_log")
        self.assertEqual(value["kernel_lines"], 0)
        self.assertIsNone(value["span_seconds"])

    def test_missing_banner_with_forward_time_means_the_head_was_overwritten(self):
        wrapped = self.module.analyse(self.build(banner=False, start=3.45))
        self.assertFalse(wrapped["banner_present"])
        self.assertEqual(wrapped["backward_timestamp_steps"], 0)
        self.assertTrue(wrapped["head_overwritten"])
        intact = self.module.analyse(self.build(banner=True))
        self.assertTrue(intact["banner_present"])
        self.assertFalse(intact["head_overwritten"])

    def test_apexd_echo_is_not_counted_as_a_retained_panic(self):
        # The 2026-07-08 summary recorded panic_text_present true from a line
        # exactly like this one, and read it as a retained kernel panic record.
        echo = self.build() + b"\n" + kernel_line(
            6.379,
            'apexd: panic_message : "RWC":"0", PANIC:sysrq triggered crash PC:x',
        )
        value = self.module.analyse(echo)
        self.assertEqual(value["panic_lines"], 1)
        self.assertTrue(value["panic_is_userspace_echo_only"])

    def test_a_real_kernel_panic_line_is_not_written_off_as_an_echo(self):
        real = self.build() + b"\n" + kernel_line(9.0, "PANIC: kernel BUG at x")
        value = self.module.analyse(real)
        self.assertEqual(value["panic_lines"], 1)
        self.assertFalse(value["panic_is_userspace_echo_only"])

    def test_marker_search_counts_occurrences(self):
        data = self.build() + b"\nrun aa96a1cf run aa96a1cf\n"
        self.assertEqual(
            self.module.find_markers(data, ["aa96a1cf", "absent"]),
            {"aa96a1cf": 2, "absent": 0},
        )

    def test_bootloader_portion_is_located(self):
        value = self.module.analyse(self.build())
        self.assertEqual(value["xbl_lines"], 2)
        self.assertIsNotNone(value["first_xbl_line"])
        self.assertIsNone(self.module.analyse(self.build(xbl=False))["first_xbl_line"])

    def test_report_states_what_the_two_captures_actually_hold(self):
        for token in (
            "Neither capture holds a candidate boot",
            "`panic_text_present=true` was a false positive",
            "d6a7bc92",
            "4e706127",
            "stock_android_boot",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.report)

    def test_ledger_records_the_retention_analysis(self):
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if " h0-last-kmsg-retention-1 " in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("| H0 |", rows[0])
        self.assertIn("no device", rows[0])


if __name__ == "__main__":
    unittest.main()
