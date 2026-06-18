import json
import tempfile
import unittest
from pathlib import Path

import analyze_audio_acdb_selected_payload_frontier_v2712 as v2712


def fixed_payload(topology_ids: list[int]) -> bytes:
    import struct

    words: list[int] = [len(topology_ids)]
    for topology_id in topology_ids:
        record = [0] * 98
        record[0] = topology_id
        record[1] = 1
        record[2] = 0x10001000
        record[3] = 0
        words.extend(record)
    return struct.pack("<" + "I" * len(words), *words)


class TestV2712SelectedPayloadFrontier(unittest.TestCase):
    def setUp(self):
        self.old_payloads = v2712.DEFAULT_PAYLOADS

    def tearDown(self):
        v2712.DEFAULT_PAYLOADS = self.old_payloads

    def make_fixture(self, root: Path, v2689_ok: bool = True, v2711_ok: bool = True):
        core = root / "core.bin"
        cal10 = root / "cal10.bin"
        cal14 = root / "cal14.bin"
        cal24 = root / "cal24.bin"
        cand10 = root / "cand10.bin"
        cand14 = root / "cand14.bin"
        core.write_bytes(fixed_payload([0x10004000, 0x10005000, 0x1001025D]))
        cal10.write_bytes(fixed_payload([0x1301033B]))
        cal14.write_bytes(fixed_payload([0x1000FFFF, 0x10000018]))
        cal24.write_bytes(fixed_payload([0x1001025D]))
        cand10.write_bytes(fixed_payload([0x10004000]))
        cand14.write_bytes(fixed_payload([0x10005000]))

        v2712.DEFAULT_PAYLOADS = {
            10: {"role": "ADM_CUST_TOPOLOGY", "selected_topology": 0x10004000, "observed_payload": cal10},
            14: {"role": "ASM_CUST_TOPOLOGY", "selected_topology": 0x10005000, "observed_payload": cal14},
            24: {"role": "AFE_CUST_TOPOLOGY", "selected_topology": 0x1001025D, "observed_payload": cal24},
        }

        plan = root / "plan.json"
        plan.write_text(
            json.dumps(
                {
                    "basic_payloads": [
                        {"cal_type": 10, "payload_remote": "/remote/cand10.bin"},
                        {"cal_type": 14, "payload_remote": "/remote/cand14.bin"},
                    ],
                    "files": [
                        {"remote_path": "/remote/cand10.bin", "local": {"local_path_private": str(cand10)}},
                        {"remote_path": "/remote/cand14.bin", "local": {"local_path_private": str(cand14)}},
                    ],
                }
            ),
            encoding="utf-8",
        )
        v2689 = root / "v2689.md"
        v2689.write_text(
            "v2689-defined-module-topology-replay-still-adsp-ebadparam\nsend_asm_custom_topology\n" if v2689_ok else "no failure marker\n",
            encoding="utf-8",
        )
        v2711 = root / "v2711.md"
        v2711.write_text(
            "v2711-setarg-geometry-exhausted-selector-payload-frontier\n" if v2711_ok else "geometry unknown\n",
            encoding="utf-8",
        )
        return core, plan, v2689, v2711

    def test_classifies_existing_candidates_exhausted(self):
        with tempfile.TemporaryDirectory() as temp:
            core, plan, v2689, v2711_report = self.make_fixture(Path(temp))
            args = type("Args", (), {"core_payload": core, "v2688_plan": plan, "v2689_report": v2689, "v2711_report": v2711_report})
            summary = v2712.build_summary(args)

        self.assertEqual(summary["classification"]["decision"], "v2712-existing-payload-corpus-exhausted-need-new-selector-model")
        self.assertFalse(summary["classification"]["cal10_observed_payload_selected_present"])
        self.assertFalse(summary["classification"]["cal14_observed_payload_selected_present"])
        self.assertTrue(summary["classification"]["cal24_observed_payload_selected_present"])
        self.assertEqual(summary["rows"][1]["frontier"], "selected-candidate-already-failed-existing-lower-payload-stale")

    def test_missing_v2689_marker_keeps_frontier_open(self):
        with tempfile.TemporaryDirectory() as temp:
            core, plan, v2689, v2711_report = self.make_fixture(Path(temp), v2689_ok=False)
            args = type("Args", (), {"core_payload": core, "v2688_plan": plan, "v2689_report": v2689, "v2711_report": v2711_report})
            summary = v2712.build_summary(args)

        self.assertEqual(summary["classification"]["decision"], "v2712-selected-payload-frontier-open")
        self.assertFalse(summary["classification"]["existing_candidates_exhausted"])

    def test_selected_present_uses_word_hits_and_parser_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = Path(temp) / "payload.bin"
            payload.write_bytes(fixed_payload([0x10005000]))
            scan = v2712.scan_private_payload(payload, 0x10005000)

        self.assertTrue(scan["selected_present"])
        self.assertEqual(scan["parser"], "fixed")


if __name__ == "__main__":
    unittest.main()
