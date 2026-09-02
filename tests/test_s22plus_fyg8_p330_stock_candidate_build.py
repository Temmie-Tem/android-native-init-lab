from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"

import sys

if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

import s22plus_fyg8_p330_stock_candidate_build as builder  # noqa: E402


P329_RESULT = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p329/"
    "stock-candidate-build-v1-20260903-01/result.json"
)
PARTIAL_P330_AP = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}


class P330StockCandidateBuildTests(unittest.TestCase):
    def test_default_is_final_no_clobber_ordinal(self) -> None:
        self.assertEqual(
            builder.DEFAULT_OUTPUT_ROOT.name,
            "stock-candidate-build-v1-20260903-07",
        )
        payload = (builder.DEFAULT_OUTPUT_ROOT / "result.json").read_bytes()
        self.assertEqual(
            builder.identity(payload),
            {
                "size": 45_820,
                "sha256": "d2186404aaab0c1472d41d93a241c0ab32119561fe0a07ca231eb0b0ca3bacf1",
            },
        )

    def test_representative_raw_result_reaches_p330_normalizer(self) -> None:
        raw = P329_RESULT.read_bytes()
        self.assertEqual(builder.identity(raw), builder.P329_RESULT_IDENTITY)
        value = copy.deepcopy(json.loads(raw.decode("ascii")))
        value.update(
            schema=builder.SCHEMA,
            verdict=builder.VERDICT,
            status=builder.STATUS,
            target=builder.TARGET,
            run_id_hex=builder.P330_RUN_ID_HEX,
        )
        value["lineage"]["construction_base_run_id"] = (
            builder._P329.P328_RUN_ID_HEX
        )
        value["lineage"]["predecessor_run_id"] = builder.P329_RUN_ID_HEX
        value["lineage"]["fresh_run_id"] = builder.P330_RUN_ID_HEX
        for label in ("a", "b"):
            value["phase2"]["candidate"][label]["ap_tar_md5"] = dict(
                PARTIAL_P330_AP
            )
            value["phase2"]["candidate"][label]["package"].update(
                schema="s22plus_fyg8_p330_boot_only_package_v1",
                verdict="PASS_P330_DETERMINISTIC_BOOT_ONLY_DIAGNOSTIC_PACKAGE_H0",
            )
        value["phase2"]["candidate"]["differs_from_consumed_p329"] = True

        result = builder._normalize_result(value)

        self.assertEqual(result["schema"], builder.SCHEMA)
        self.assertEqual(result["verdict"], builder.VERDICT)
        self.assertEqual(result["run_id_hex"], builder.P330_RUN_ID_HEX)
        self.assertEqual(
            result["phase2"]["candidate"]["a"]["ap_tar_md5"],
            PARTIAL_P330_AP,
        )
        self.assertTrue(result["scope"]["host_only"])
        self.assertFalse(result["scope"]["device_contact"])
        repair = result["lineage"]["runtime_repair"]
        self.assertTrue(
            {
                "observer_contract",
                "preauth_diagnostic_frame",
                "rng_eagain_retry_limit",
                "diagnostics_non_authoritative",
            }.isdisjoint(repair)
        )


if __name__ == "__main__":
    unittest.main()
