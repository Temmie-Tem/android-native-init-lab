import tempfile
import unittest
from pathlib import Path

from workspace.public.src.scripts.revalidation import analyze_audio_acdb_core_topology_bridge_v2683 as v2683
from workspace.public.src.scripts.revalidation import analyze_audio_acdb_db_selected_topology_v2696 as v2696


class TestAnalyzeAudioAcdbDbSelectedTopologyV2696(unittest.TestCase):
    def test_embedded_fixed_record_detects_selected_topology(self):
        payload = v2683.fixed_payload_from_core([
            v2683.CoreRecord(0, 0, 0, 0x10005000, 0, ((0x10912, 0x10000), (0x10BFE, 0x10000))),
        ])
        words = v2683.u32_words(payload)

        record = v2696.embedded_fixed_candidate(words, 1)

        self.assertIsNotNone(record)
        self.assertEqual(record.topology_id, 0x10005000)
        self.assertEqual(record.module_count, 2)

    def test_embedded_core_record_detects_selected_topology(self):
        payload = v2683.pack_words([
            1,
            0,
            0x10004000,
            0,
            1,
            0x10719,
            0x10000,
        ])
        words = v2683.u32_words(payload)

        record = v2696.embedded_core_candidate(words, 2)

        self.assertIsNotNone(record)
        self.assertEqual(record.topology_id, 0x10004000)
        self.assertEqual(record.module_count, 1)

    def test_analyze_without_db_uses_payload_corpus(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        db_root = root / "db"
        db_root.mkdir()
        core = root / "core.bin"
        cal14 = root / "cal14.bin"
        cal24 = root / "cal24.bin"
        core.write_bytes(v2683.pack_words([
            3,
            0,
            0x10004000,
            0,
            1,
            0x10719,
            0x10000,
            0,
            0x10005000,
            0,
            1,
            0x10912,
            0x10000,
            0,
            0x1001025D,
            0,
            1,
            0x1025F,
            0x10000,
        ]))
        cal14.write_bytes(v2683.fixed_payload_from_core([
            v2683.CoreRecord(0, 0, 0, 0x10000018, 0, ((0x10719, 0x10000),)),
        ]))
        cal24.write_bytes(v2683.fixed_payload_from_core([
            v2683.CoreRecord(0, 0, 0, 0x1001025D, 0, ((0x1025F, 0x10000),)),
        ]))

        summary = v2696.analyze(db_roots=(db_root,), payload_files=(core, cal14, cal24))

        self.assertEqual(summary["decision"], "v2696-acdb-db-not-staged-core-has-selected-but-lower-selector-stale")
        self.assertFalse(summary["db_staged"])
        self.assertTrue(summary["core_has_selected_all"])
        self.assertFalse(summary["asm_selected_in_exact_lower_cal14"])
        self.assertTrue(summary["afe_selected_in_exact_lower_cal24"])
        by_cal = {item["cal_type"]: item for item in summary["target_summary"]}
        self.assertTrue(by_cal[10]["payload_parseable_record_found"])
        self.assertTrue(by_cal[14]["payload_parseable_record_found"])
        self.assertTrue(by_cal[24]["payload_parseable_record_found"])

    def test_analyze_with_db_records_promotes_selector_re(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        db_root = root / "db"
        db_root.mkdir()
        acdb = db_root / "synthetic.acdb"
        acdb.write_bytes(v2683.pack_words([
            3,
            0,
            0x10004000,
            0,
            1,
            0x10719,
            0x10000,
            0,
            0x10005000,
            0,
            1,
            0x10912,
            0x10000,
            0,
            0x1001025D,
            0,
            1,
            0x1025F,
            0x10000,
        ]))

        summary = v2696.analyze(db_roots=(db_root,), payload_files=())

        self.assertEqual(summary["decision"], "v2696-acdb-db-has-selected-records-selector-re-needed")
        self.assertTrue(summary["db_staged"])
        self.assertEqual(summary["db_file_count"], 1)
        self.assertTrue(all(item["db_parseable_record_found"] for item in summary["target_summary"]))

    def remove_tree(self, path: Path):
        import shutil

        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
