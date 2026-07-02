from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


pair = load_script(
    "workspace/public/src/scripts/revalidation/a90_repl_current_kernel_time64_pair.py"
)
repl = pair.a90_repl

REPO_ROOT = Path(__file__).resolve().parents[1]
C2B_PADDING_MAP_PATH = (
    REPO_ROOT / "workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map"
)
PAIR_IMAGE_PATH = (
    REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_call_pair.img"
)
KERNEL_SOURCE_ROOT = (
    REPO_ROOT / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel"
)


class FakePairTransport:
    def __init__(self, slide: int) -> None:
        self.slide = slide
        self.pairs = [
            (repl.ADR_SELF_LINK_VADDR + slide, 0),
            (0x69000000, 0x11111111),
            (0x69000000, 0x01020304),
            (0x69000001, 0x02030405),
            (0x69000001, 0x22222222),
        ]
        self.op_count = 0

    def run_serial_command(self, argv, **_kwargs):
        shell = argv[-1]
        if repl.NODE in shell:
            if self.op_count >= len(self.pairs):
                raise AssertionError("unexpected extra pair op")
            x0, x1 = self.pairs[self.op_count]
            self.op_count += 1
            return {"ok": True, "rc": 0, "stdout": f"[ 1.0] R{x0:x}:{x1:x}\n"}
        return {"ok": True, "rc": 0, "stdout": ""}


class A90ReplCurrentKernelTime64PairTests(unittest.TestCase):
    def test_parse_pair_values(self) -> None:
        self.assertEqual(
            pair.parse_pair_values("noise R1234:abcd\nR0:1"),
            [(0x1234, 0xABCD), (0, 1)],
        )

    def test_current_kernel_time64_pair_fake_transport_passes(self) -> None:
        if not C2B_PADDING_MAP_PATH.is_file() or not PAIR_IMAGE_PATH.is_file() or not KERNEL_SOURCE_ROOT.is_dir():
            self.skipTest("promoted map, call-pair image, or kernel source tree not present")

        symbols = repl.load_system_map(C2B_PADDING_MAP_PATH)
        image = repl.load_static_image(PAIR_IMAGE_PATH)
        fake = FakePairTransport(0x130000)
        orig_run = repl.transport.run_serial_command
        orig_hide = pair.a90ctl.bridge_exchange
        repl.transport.run_serial_command = fake.run_serial_command
        pair.a90ctl.bridge_exchange = lambda *args, **kwargs: {"ok": True}
        self.addCleanup(lambda: setattr(repl.transport, "run_serial_command", orig_run))
        self.addCleanup(lambda: setattr(pair.a90ctl, "bridge_exchange", orig_hide))
        session = pair.PairReplSession(pair.PairReplConfig(settle_sec=0.0, retry_delay_sec=0.0))

        summary, private = pair.run_pair_proof(
            session,
            symbols,
            image,
            source_root=KERNEL_SOURCE_ROOT,
        )

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(
            summary["decision"],
            "a90-repl-live-call-proof-current_kernel_time64-return-pair-pass",
        )
        self.assertEqual(
            summary["proof_status"],
            "trusted-under-timespec64-x0-x1-return-pair-contract",
        )
        self.assertEqual(summary["source_evidence"]["signature"], "struct timespec64 current_kernel_time64(void)")
        self.assertEqual(summary["source_evidence"]["aggregate_return_lanes"], "arm64-small-struct-x0-x1")
        self.assertEqual(summary["observed_first_tv_sec_x0"], "0x69000000")
        self.assertEqual(summary["observed_first_tv_nsec_x1"], "0x1020304")
        self.assertTrue(summary["all_tv_nsec_in_range"])
        self.assertTrue(summary["all_tv_sec_within_anchor_range"])
        self.assertTrue(summary["raw_runtime_values_redacted"])
        self.assertNotIn("current_kernel_time64_runtime", summary)
        self.assertIn("current_kernel_time64_runtime", private)
        self.assertEqual(fake.op_count, 5)


if __name__ == "__main__":
    unittest.main()
