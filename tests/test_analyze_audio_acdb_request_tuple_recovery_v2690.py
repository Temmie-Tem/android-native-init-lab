import json
import tempfile
import unittest
from pathlib import Path

from workspace.public.src.scripts.revalidation import analyze_audio_acdb_request_tuple_recovery_v2690 as v2690


class AnalyzeAudioAcdbRequestTupleRecoveryV2690Test(unittest.TestCase):
    def test_parse_tap_records_decodes_signed_ret_and_size(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        tap = root / "acdbtap"
        tap.mkdir()
        (tap / "acdbtap-00000002-cmd-00011394-len-00000004.bin").write_bytes(b"\x00\x00\x00\x00")
        rows = [
            {"event": "acdb_ioctl_call", "seq": "0x00000002", "cmd": "0x00011394", "in_word0": "0x1000", "in_word1": "0xe9382000", "phase": "enter"},
            {"seq": "0x00000002", "cmd": "0x00011394", "buffer": "in", "sha256": "in-sha"},
            {"seq": "0x00000002", "cmd": "0x00011394", "buffer": "out", "ret": "0xfffffff4", "sha256": "out-sha", "raw_path": "/data/local/tmp/a90-acdb-tap/acdbtap-00000002-cmd-00011394-len-00000004.bin", "all_zero": True},
        ]
        (tap / "acdbtap-events.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

        records = v2690.parse_tap_records(tap)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].cal_type, 10)
        self.assertEqual(records[0].output_ret, -12)
        self.assertEqual(records[0].output_size, 0)
        self.assertEqual(records[0].input_words, [0x1000, 0xE9382000])

    def test_analysis_classifies_v2675_v2689_frontier(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        run = root / "run"
        artifacts = run / "ownget-device-artifacts"
        tap = artifacts / "acdbtap"
        tap.mkdir(parents=True)
        lower_lines = []
        for cal, code, value in ((24, 0, 0x49C), (10, -12, 0), (14, 0, 0x934)):
            lower_lines.extend(
                [
                    f'{{"event":"v2672_lower_hidden","stage":"create_cal_node_return","code":0,"cal_type":{cal},"value":0x1,"pid":1,"tid":1}}',
                    f'{{"event":"v2672_lower_hidden","stage":"allocate_cal_block_return","code":0,"cal_type":{cal},"value":0x2,"pid":1,"tid":1}}',
                    f'{{"event":"v2672_lower_hidden","stage":"acdb_ioctl_get_return","code":{code},"cal_type":{cal},"value":0x{value:08x},"pid":1,"tid":1}}',
                ]
            )
        (artifacts / "acdb-v2674-lower-hidden-inhook-events.jsonl").write_text("\n".join(lower_lines), encoding="utf-8")
        set_rows = [
            {"event": "setcal_capture", "sequence": 1, "cal_type": 24, "data_size": 32, "cal_size": 1180, "mem_handle": 35, "set_arg": {"sha256": "arg24"}, "dmabuf": {"sha256": "pay24", "status": "ok"}},
            {"event": "setcal_capture", "sequence": 2, "cal_type": 14, "data_size": 32, "cal_size": 2356, "mem_handle": 37, "set_arg": {"sha256": "arg14"}, "dmabuf": {"sha256": "pay14", "status": "ok"}},
        ]
        (artifacts / "setcal-events.jsonl").write_text("\n".join(json.dumps(row) for row in set_rows), encoding="utf-8")
        tap_rows = []
        for seq, cal, cmd, word1, ret, size in (
            (1, 24, 0x130DA, 0xE9383000, 0, 1180),
            (2, 10, 0x11394, 0xE9382000, 0xFFFFFFF4, 0),
            (3, 14, 0x12E01, 0xE9381000, 0, 2356),
        ):
            out_name = f"acdbtap-{seq:08x}-cmd-{cmd:08x}-len-00000004.bin"
            (tap / out_name).write_bytes(size.to_bytes(4, "little"))
            tap_rows.extend(
                [
                    {"event": "acdb_ioctl_call", "seq": f"0x{seq:08x}", "cmd": f"0x{cmd:08x}", "in_word0": "0x00001000", "in_word1": f"0x{word1:08x}", "phase": "enter"},
                    {"seq": f"0x{seq:08x}", "cmd": f"0x{cmd:08x}", "buffer": "in", "sha256": f"in{cal}"},
                    {"seq": f"0x{seq:08x}", "cmd": f"0x{cmd:08x}", "buffer": "out", "ret": f"0x{ret:08x}", "sha256": f"out{cal}", "raw_path": f"/data/local/tmp/a90-acdb-tap/{out_name}", "all_zero": size == 0},
                ]
            )
        (tap / "acdbtap-events.jsonl").write_text("\n".join(json.dumps(row) for row in tap_rows), encoding="utf-8")
        report = root / "v2689.md"
        report.write_text("v2689-defined-module-topology-replay-still-adsp-ebadparam\nADSP_EBADPARAM\n", encoding="utf-8")

        analysis = v2690.analyze(run, report)

        self.assertTrue(analysis.ok)
        self.assertEqual(analysis.failed_get_cal_types, [10])
        self.assertEqual(analysis.captured_custom_cal_types, [14, 24])
        self.assertEqual([audit.verdict for audit in analysis.tuple_audits], ["captured-real-set-payload", "get-failed-before-set", "captured-real-set-payload"])

    def remove_tree(self, path: Path):
        import shutil

        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
