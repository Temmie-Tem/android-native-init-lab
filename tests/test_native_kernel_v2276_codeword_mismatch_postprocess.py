"""Regression tests for native_kernel_v2276_codeword_mismatch_postprocess."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2276 = load_revalidation("native_kernel_v2276_codeword_mismatch_postprocess")


SLIDE = 0x100000
TARGET_STATIC = 0x1000
NON_TARGET_STATIC = 0x2000
LR_STATIC = 0x3000


def insn(base, *, reg=3, base_reg=4):
    return base | reg | (base_reg << 5)


def sample(*, pc_static=TARGET_STATIC, lr_static=LR_STATIC, live_pc=None, stock_pc=None):
    stock_pc = stock_pc if stock_pc is not None else insn(v2276.STR_POST_VALUE)
    live_pc = live_pc if live_pc is not None else insn(v2276.STTR_VALUE)
    return {
        "seq": 7,
        "comm": "kworker/u16:1",
        "pid": 10,
        "tgid": 20,
        "ctx_pc": SLIDE + pc_static,
        "ctx_pc_insn": live_pc,
        "ctx_lr": SLIDE + lr_static,
        "ctx_lr_prev_insn": 0x94000001,
        "ctx_lr_insn": 0xd503201f,
        "_stock_pc": stock_pc,
    }


def patch_codeword_io(samples):
    stock_by_static = {}
    for row in samples:
        stock_by_static[row["ctx_pc"] - SLIDE] = row["_stock_pc"]
        lr_static = row["ctx_lr"] - SLIDE
        stock_by_static[lr_static - 4] = row["ctx_lr_prev_insn"]
        stock_by_static[lr_static] = row["ctx_lr_insn"]

    def read_stock_u32(_raw, _base, static_addr):
        return stock_by_static.get(static_addr)

    return mock.patch.multiple(
        v2276.codeword_v2216,
        load_kernel_raw=mock.Mock(return_value=b"raw"),
        load_synthetic_base=mock.Mock(return_value=0),
        load_text_symbols=mock.Mock(return_value=[
            (TARGET_STATIC, "request_firmware_work_func"),
            (NON_TARGET_STATIC, "non_target_symbol"),
            (LR_STATIC, "lr_site"),
            (0x4000, "end"),
        ]),
        read_stock_u32=mock.Mock(side_effect=read_stock_u32),
    )


def write_run(root: Path, *, workqueue_text="", codeword_text="codeword\n"):
    device = root / "device"
    device.mkdir(parents=True, exist_ok=True)
    (device / "codeword_log.cmdv1.txt").write_text(codeword_text, encoding="utf-8")
    (device / "workqueue_log.cmdv1.txt").write_text(workqueue_text, encoding="utf-8")
    return root


def workqueue_log(*, result="v2273-workqueue-func-sample-ring-complete", target=True, total=1, stored=1):
    static = TARGET_STATIC if target else NON_TARGET_STATIC
    return (
        f"result={result}\n"
        f"stats total={total} stored={stored}\n"
        f"sample index=0 kind=delayed function=0x{SLIDE + static:x} pid=10 tgid=20\n"
    )


def patch_workqueue_symbols():
    addrs = [TARGET_STATIC, NON_TARGET_STATIC, 0x4000]
    names = ["request_firmware_work_func", "non_target_symbol", "end"]
    index = dict(zip(names, addrs))
    return mock.patch.object(v2276.workqueue_v2275, "load_symbol_map", return_value=(addrs, names, index))


class ScalarInstructionHelpers(unittest.TestCase):
    def test_int_and_hex_helpers_accept_expected_forms(self):
        self.assertEqual(v2276.as_int("0x20"), 32)
        self.assertEqual(v2276.as_int(7), 7)
        self.assertEqual(v2276.hex64(0x20), "0x0000000000000020")
        self.assertEqual(v2276.hex32(0x20), "0x00000020")
        self.assertIsNone(v2276.hex64(None))
        self.assertIsNone(v2276.hex32(None))

    def test_instruction_register_extractors_and_mask_helpers(self):
        pair = insn(v2276.STP_POST_VALUE, reg=5, base_reg=9)
        single = insn(v2276.STR_POST_VALUE, reg=6, base_reg=10)
        unpriv = insn(v2276.STTR_VALUE, reg=6, base_reg=10)

        self.assertTrue(v2276.is_pair_post(pair, v2276.STP_POST_VALUE))
        self.assertTrue(v2276.is_single_post(single, v2276.STR_POST_VALUE))
        self.assertTrue(v2276.is_unpriv(unpriv, v2276.STTR_VALUE))
        self.assertEqual(v2276.rt(single), 6)
        self.assertEqual(v2276.rn(single), 10)

    def test_classify_uao_runtime_patch_requires_same_registers(self):
        str_stock = insn(v2276.STR_POST_VALUE, reg=1, base_reg=2)
        sttr_live = insn(v2276.STTR_VALUE, reg=1, base_reg=2)
        ldr_stock = insn(v2276.LDR_POST_VALUE, reg=3, base_reg=4)
        ldtr_live = insn(v2276.LDTR_VALUE, reg=3, base_reg=4)
        stp_stock = insn(v2276.STP_POST_VALUE, reg=5, base_reg=6)
        ldp_stock = insn(v2276.LDP_POST_VALUE, reg=7, base_reg=8)

        self.assertEqual(v2276.classify_uao_runtime_patch(str_stock, sttr_live), "uao_user_alternative_str_to_sttr")
        self.assertEqual(v2276.classify_uao_runtime_patch(ldr_stock, ldtr_live), "uao_user_alternative_ldr_to_ldtr")
        self.assertEqual(v2276.classify_uao_runtime_patch(stp_stock, insn(v2276.STTR_VALUE, reg=5, base_reg=6)), "uao_stp_first_lane_to_sttr")
        self.assertEqual(v2276.classify_uao_runtime_patch(ldp_stock, insn(v2276.LDTR_VALUE, reg=7, base_reg=8)), "uao_ldp_first_lane_to_ldtr")
        self.assertIsNone(v2276.classify_uao_runtime_patch(str_stock, insn(v2276.STTR_VALUE, reg=9, base_reg=2)))
        self.assertIsNone(v2276.classify_uao_runtime_patch(None, sttr_live))


class MismatchRows(unittest.TestCase):
    def test_symbol_resolver_returns_containing_symbol(self):
        resolve = v2276.symbol_resolver([(0x1000, "first"), (0x2000, "second"), (0x3000, "third")])

        self.assertEqual(resolve(0x2100), {"symbol": "second", "offset": 0x100, "symbol_addr": 0x2000})
        self.assertEqual(resolve(0x500), {"symbol": None, "offset": None, "symbol_addr": None})

    def test_mismatch_rows_classifies_uao_patch_and_counts_lr_matches(self):
        rows_in = [sample()]
        probe = {"samples": rows_in}
        with patch_codeword_io(rows_in):
            rows, counts = v2276.mismatch_rows(probe, SLIDE)

        self.assertEqual(counts["pc_readable"], 1)
        self.assertEqual(counts["pc_match"], 0)
        self.assertEqual(counts["lr_prev_match"], 1)
        self.assertEqual(counts["lr_match"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pc_symbol"], "request_firmware_work_func")
        self.assertEqual(rows[0]["uao_patch_class"], "uao_user_alternative_str_to_sttr")
        self.assertTrue(rows[0]["lr_prev_match"])
        self.assertTrue(rows[0]["lr_match"])

    def test_mismatch_rows_suppresses_matching_pc_rows(self):
        row = sample(live_pc=insn(v2276.STR_POST_VALUE), stock_pc=insn(v2276.STR_POST_VALUE))
        with patch_codeword_io([row]):
            rows, counts = v2276.mismatch_rows({"samples": [row]}, SLIDE)

        self.assertEqual(rows, [])
        self.assertEqual(counts["pc_match"], 1)


class WorkqueueAndAnalyze(unittest.TestCase):
    def test_classify_workqueue_with_slide_reports_target_and_no_hit(self):
        with tempfile.TemporaryDirectory() as tmp, patch_workqueue_symbols():
            target_dir = write_run(Path(tmp) / "target", workqueue_text=workqueue_log(target=True))
            no_hit_dir = write_run(Path(tmp) / "no-hit", workqueue_text=workqueue_log(target=False))

            target = v2276.classify_workqueue_with_slide(target_dir, SLIDE)
            no_hit = v2276.classify_workqueue_with_slide(no_hit_dir, SLIDE)

        self.assertEqual(target["classification"], "workqueue-target-hit")
        self.assertEqual(target["target_hit_count"], 1)
        self.assertEqual(target["target_hits"][0]["symbol"], "request_firmware_work_func")
        self.assertEqual(target["symbol_counts_top"][0], ("request_firmware_work_func", 1))
        self.assertEqual(no_hit["classification"], "workqueue-no-target-hit")
        self.assertEqual(no_hit["target_hit_count"], 0)

    def test_classify_workqueue_with_slide_reports_incomplete_and_no_activity(self):
        with tempfile.TemporaryDirectory() as tmp, patch_workqueue_symbols():
            incomplete_dir = write_run(Path(tmp) / "incomplete", workqueue_text=workqueue_log(result="still-running"))
            no_activity_dir = write_run(Path(tmp) / "no-activity", workqueue_text=workqueue_log(total=0, stored=0))

            incomplete = v2276.classify_workqueue_with_slide(incomplete_dir, SLIDE)
            no_activity = v2276.classify_workqueue_with_slide(no_activity_dir, SLIDE)

        self.assertEqual(incomplete["classification"], "workqueue-sampler-incomplete")
        self.assertEqual(no_activity["classification"], "workqueue-no-activity")

    def patch_analysis_inputs(self, *, mismatches, counts, workqueue):
        return mock.patch.multiple(
            v2276,
            mismatch_rows=mock.Mock(return_value=(mismatches, counts)),
            classify_workqueue_with_slide=mock.Mock(return_value=workqueue),
        )

    def patch_codeword_analysis(self):
        return mock.patch.multiple(
            v2276.codeword_v2216,
            parse_helper_stdout=mock.Mock(return_value={"samples": [{"seq": 1}]}),
            analyze_probe=mock.Mock(return_value={
                "codeword": {
                    "accepted_symbolization_slide": False,
                    "acceptance_reason": "pc mismatch",
                    "best": {"slide": f"0x{SLIDE:x}", "slide_hex": f"0x{SLIDE:x}"},
                }
            }),
        )

    def test_analyze_accepts_uao_patch_and_branches_on_workqueue_result(self):
        mismatch = {"uao_patch_class": "uao_user_alternative_str_to_sttr"}
        counts = {
            "pc_readable": 2,
            "pc_match": 1,
            "lr_prev_readable": 2,
            "lr_prev_match": 2,
            "lr_readable": 2,
            "lr_match": 2,
        }
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = write_run(Path(tmp), workqueue_text=workqueue_log(target=False))
            with self.patch_codeword_analysis(), self.patch_analysis_inputs(
                mismatches=[mismatch],
                counts=counts,
                workqueue={"classification": "workqueue-no-target-hit", "target_hit_count": 0},
            ):
                no_hit = v2276.analyze(run_dir)
            with self.patch_codeword_analysis(), self.patch_analysis_inputs(
                mismatches=[mismatch],
                counts=counts,
                workqueue={"classification": "workqueue-target-hit", "target_hit_count": 1},
            ):
                target = v2276.analyze(run_dir)

        self.assertTrue(no_hit["patch_aware_accepted"])
        self.assertEqual(no_hit["decision"], "v2276-codeword-uao-patch-aware-accepted-workqueue-no-target-hit")
        self.assertEqual(target["decision"], "v2276-codeword-uao-patch-aware-accepted-workqueue-target-hit")
        self.assertEqual(no_hit["codeword"]["pc_match"], "1/2")
        self.assertEqual(no_hit["codeword"]["mismatch_classes"], ["uao_user_alternative_str_to_sttr"])

    def test_analyze_rejects_when_lr_is_not_exact(self):
        counts = {
            "pc_readable": 1,
            "pc_match": 0,
            "lr_prev_readable": 1,
            "lr_prev_match": 0,
            "lr_readable": 1,
            "lr_match": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = write_run(Path(tmp), workqueue_text=workqueue_log())
            with self.patch_codeword_analysis(), self.patch_analysis_inputs(
                mismatches=[{"uao_patch_class": "uao_user_alternative_str_to_sttr"}],
                counts=counts,
                workqueue={"classification": "workqueue-target-hit", "target_hit_count": 1},
            ):
                result = v2276.analyze(run_dir)

        self.assertFalse(result["patch_aware_accepted"])
        self.assertEqual(result["decision"], "v2276-codeword-mismatch-not-accepted")
        self.assertIsNone(result["workqueue"])


if __name__ == "__main__":
    unittest.main()
