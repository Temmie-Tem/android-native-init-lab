import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import analyze_audio_acdb_setarg_geometry_frontier_v2711 as v2711


def write_words(path: Path, words: list[int]) -> None:
    import struct

    path.write_bytes(struct.pack("<" + "i" * len(words), *words))


class TestV2711SetargGeometryFrontier(unittest.TestCase):
    def test_basic_equivalence_ignores_mem_handle_only(self):
        exact = [32, 0, 14, 16, 0, 0, 2356, 37]
        basic = v2711.basic_set_words(14, 2356, mem_handle=0)
        self.assertTrue(v2711.words_equivalent_mod_mem_handle(exact, basic))

    def test_basic_equivalence_rejects_shape_difference(self):
        exact = [48, 0, 14, 32, 0, 0, 2356, 37, 1, 2, 3, 4]
        basic = v2711.basic_set_words(14, 2356, mem_handle=0)
        self.assertFalse(v2711.words_equivalent_mod_mem_handle(exact, basic))

    def test_classifies_geometry_exhausted_when_14_24_match(self):
        rows = [
            {"cal_type": 24, "lower_exact_arg_equivalent_mod_mem_handle": True, "lower_exact_payload_matches_v2704": True, "lower_exact_record_count": 1},
            {"cal_type": 10, "lower_exact_arg_equivalent_mod_mem_handle": False, "lower_exact_payload_matches_v2704": False, "lower_exact_record_count": 0},
            {"cal_type": 14, "lower_exact_arg_equivalent_mod_mem_handle": True, "lower_exact_payload_matches_v2704": True, "lower_exact_record_count": 1},
        ]
        c = v2711.classify(rows)
        self.assertEqual(c["decision"], "v2711-setarg-geometry-exhausted-selector-payload-frontier")
        self.assertTrue(c["v2708_failure_not_explained_by_cal14_setarg_geometry"])

    def test_build_summary_from_synthetic_private_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payload24 = b"afe-payload"
            payload14 = b"asm-payload"
            v2704 = root / "v2704-result.json"
            v2704.write_text(
                json.dumps(
                    {
                        "large_get_summary": {
                            "target_rows": [
                                {
                                    "target_cal_type": 24,
                                    "out_len": len(payload24),
                                    "sha256": hashlib.sha256(payload24).hexdigest(),
                                    "ret": 0,
                                    "raw_status": {"exists": True, "nonzero": True, "sha_ok": True, "size_ok": True},
                                },
                                {
                                    "target_cal_type": 10,
                                    "out_len": 16076,
                                    "sha256": "admsha",
                                    "ret": 0,
                                    "raw_status": {"exists": True, "nonzero": True, "sha_ok": True, "size_ok": True},
                                },
                                {
                                    "target_cal_type": 14,
                                    "out_len": len(payload14),
                                    "sha256": hashlib.sha256(payload14).hexdigest(),
                                    "ret": 0,
                                    "raw_status": {"exists": True, "nonzero": True, "sha_ok": True, "size_ok": True},
                                },
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            lower = root / "lower"
            lower.mkdir()
            write_words(lower / "setcal-arg-p00000001-s00000001-cal00000018-len00000020.bin", [32, 0, 24, 16, 0, 0, len(payload24), 35])
            (lower / "setcal-dmabuf-p00000001-s00000001-cal00000018-len0000000b.bin").write_bytes(payload24)
            write_words(lower / "setcal-arg-p00000001-s00000002-cal0000000e-len00000020.bin", [32, 0, 14, 16, 0, 0, len(payload14), 37])
            (lower / "setcal-dmabuf-p00000001-s00000002-cal0000000e-len0000000b.bin").write_bytes(payload14)

            args = type("Args", (), {"v2704_result": v2704, "lower_dir": [str(lower)]})
            summary = v2711.build_summary(args)

        self.assertEqual(summary["classification"]["decision"], "v2711-setarg-geometry-exhausted-selector-payload-frontier")
        self.assertTrue(summary["rows"][0]["lower_exact_arg_equivalent_mod_mem_handle"])
        self.assertEqual(summary["rows"][1]["lower_exact_record_count"], 0)
        self.assertTrue(summary["rows"][2]["lower_exact_payload_matches_v2704"])


if __name__ == "__main__":
    unittest.main()
