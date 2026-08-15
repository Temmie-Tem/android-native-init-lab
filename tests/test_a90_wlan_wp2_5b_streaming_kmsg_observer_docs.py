"""Pin the host-only A90 WP2-5b streaming-kmsg observer requirement."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272"
KERNEL = PACKAGE / "Kernel"
DEFCONFIG = KERNEL / "arch/arm64/configs/r3q_kor_single_defconfig"
PRINTK = KERNEL / "kernel/printk/printk.c"
PRINTK_H = KERNEL / "include/linux/printk.h"
PROC_KMSG = KERNEL / "fs/proc/kmsg.c"
V724 = ROOT / "workspace/public/src/native-init/v724/90_main.inc.c"
REPORT = ROOT / "docs/reports/A90_WLAN_WP2_5B_STREAMING_KMSG_OBSERVER_H0_2026-08-16.md"
PORTFOLIO = ROOT / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
PROPOSAL = PORTFOLIO / "proposals/wlan-vendor-property-ablation.md"
HARDENING = PORTFOLIO / "hardening.md"
CONTEXT = PORTFOLIO / "context.md"
HARDENING_JSON = PORTFOLIO / "hardening.json"
GOAL = ROOT / "GOAL_A90.md"


def config_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"(CONFIG_[A-Z0-9_]+)=(.+)", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


class A90WlanWp25bStreamingKmsgObserverDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.source_staged = KERNEL.is_dir()

    def require_source(self) -> None:
        if not self.source_staged:
            self.skipTest(f"operator-staged A90 kernel source is absent: {KERNEL}")

    def test_static_minimum_is_not_mislabeled_as_the_final_ring(self) -> None:
        self.require_source()
        config = config_values(DEFCONFIG.read_text(errors="replace"))
        self.assertEqual(config["CONFIG_SMP"], "y")
        self.assertEqual(config["CONFIG_NR_CPUS"], "8")
        self.assertEqual(config["CONFIG_LOG_BUF_SHIFT"], "17")
        self.assertEqual(config["CONFIG_LOG_CPU_MAX_BUF_SHIFT"], "17")
        self.assertEqual(config["CONFIG_MESSAGE_LOGLEVEL_DEFAULT"], "4")
        self.assertIn(
            "# CONFIG_SEC_DEBUG_MSG_LOG is not set",
            DEFCONFIG.read_text(errors="replace"),
        )

        source = PRINTK.read_text(errors="replace")
        for token in (
            "#define __LOG_BUF_LEN (1 << CONFIG_LOG_BUF_SHIFT)",
            "cpu_extra = (num_possible_cpus() - 1) * __LOG_CPU_MAX_BUF_LEN;",
            "log_buf_len_update(cpu_extra + __LOG_BUF_LEN);",
            'early_param("log_buf_len", log_buf_len_setup);',
        ):
            self.assertIn(token, source)

        static_minimum = 1 << int(config["CONFIG_LOG_BUF_SHIFT"])
        cpu_extra = (int(config["CONFIG_NR_CPUS"]) - 1) * (
            1 << int(config["CONFIG_LOG_CPU_MAX_BUF_SHIFT"])
        )
        source_default = 1 << (static_minimum + cpu_extra - 1).bit_length()
        self.assertEqual(static_minimum, 128 * 1024)
        self.assertEqual(source_default, 1024 * 1024)
        for claim in (
            "static 128 KiB buffer",
            "source-default calculation is\n1 MiB",
            "actual ring size remains **unproved**",
        ):
            self.assertIn(claim, self.report)

    def test_devkmsg_supplies_per_reader_sequence_and_overrun_detection(self) -> None:
        self.require_source()
        source = PRINTK.read_text(errors="replace")
        header = PRINTK_H.read_text(errors="replace")
        for token in (
            "struct devkmsg_user {",
            "u64 seq;",
            "u32 idx;",
            "if (user->seq < log_first_seq)",
            "ret = -EPIPE;",
            "case SEEK_END:",
            "user->seq = log_next_seq;",
            "Reading /dev/kmsg itself\n\t\t * changes no global state",
        ):
            self.assertIn(token, source)
        self.assertIn("#define CONSOLE_EXT_LOG_MAX\t8192", header)
        for claim in (
            "per-open `seq` and `idx` state",
            "returns `-EPIPE`",
            "buffer at least that\nlarge",
            "WP2_5B_KMSG_STREAM_COMPLETENESS",
        ):
            self.assertIn(claim, self.report)

    def test_proc_kmsg_global_cursor_is_not_an_automatic_fallback(self) -> None:
        self.require_source()
        proc = PROC_KMSG.read_text(errors="replace")
        printk = PRINTK.read_text(errors="replace")
        self.assertIn(
            "return do_syslog(SYSLOG_ACTION_READ, buf, count, SYSLOG_FROM_PROC);",
            proc,
        )
        for token in (
            "static u64 syslog_seq;",
            "static u32 syslog_idx;",
            "static size_t syslog_partial;",
            "syslog_seq++;",
        ):
            self.assertIn(token, printk)
        self.assertIn("`/proc/kmsg` is not an acceptable automatic fallback", self.report)
        self.assertIn("advances the one global", self.report)

    def test_current_v724_watcher_is_only_source_precedent(self) -> None:
        source = V724.read_text(encoding="utf-8")
        for token in (
            'open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC)',
            "(void)lseek(fd, 0, SEEK_END);",
            'open("/proc/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC)',
            "char line[768];",
            "usleep(20000);",
        ):
            self.assertIn(token, source)
        self.assertIn("precedent, not an implementation", self.report)
        self.assertIn("not a reusable or qualified WP2-5b observer", self.report)

    def test_portfolio_and_goal_bind_the_same_open_gate(self) -> None:
        texts = (
            PROPOSAL.read_text(encoding="utf-8"),
            HARDENING.read_text(encoding="utf-8"),
            CONTEXT.read_text(encoding="utf-8"),
            GOAL.read_text(encoding="utf-8"),
            json.dumps(json.loads(HARDENING_JSON.read_text()), sort_keys=True),
        )
        for text in texts:
            self.assertIn("WP2_5B_KMSG_STREAM_COMPLETENESS", text)
            self.assertIn("WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT", text)
            self.assertIn("/dev/kmsg", text)
            self.assertIn("/proc/kmsg", text)
        self.assertIn("`WP2-5b` remains absent and unauthorized", HARDENING.read_text())
        self.assertIn("implementation, journal/observer encoders", PROPOSAL.read_text())

    def test_design_stops_before_intent_and_never_replays_after_loss(self) -> None:
        for claim in (
            "publishes a bounded\n   `OBSERVER_ARMED` receipt before durable effect intent",
            "Open, identity, seek, buffer,\n   parser-selftest",
            "consume no live ordinal",
            "Any loss detected after effect intent becomes\n   `NO_PROOF_OBSERVER`",
            "the effect is never replayed",
            "exact byte and record caps",
            "remain unset",
        ):
            self.assertIn(claim, self.report)

    def test_report_grants_no_authority(self) -> None:
        for claim in (
            "This report is H0 only",
            "creates no observer binary",
            "D0, D1, F1",
            "remain unimplemented and unauthorized",
        ):
            self.assertIn(claim, self.report)


if __name__ == "__main__":
    unittest.main()
