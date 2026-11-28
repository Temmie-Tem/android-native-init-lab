"""Roadmap step 4b: the V18 upstream-handover report, its decoder and the composite renders."""
import hashlib
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = ROOT / "workspace/public/src/mainline/s22plus_ufs_link_h0"
UP = ROOT / "workspace/public/src/mainline/s22plus_ufs_upstream_h0"
sys.path[:0] = [str(LINK), str(UP)]
import link_wire as w  # noqa: E402
import report_modes  # noqa: E402

KEY, ID, FIRST, SECOND, BOOT = (bytes([i]) * n for i, n in ((1, 32), (2, 32), (3, 32), (4, 32), (5, 16)))
WIT = w.frame(b"G030WIT1", 17, KEY, ID, FIRST, SECOND, BOOT, 2000, 63000, floor_ms=w.FLOOR_MS)
KERNEL = ROOT / "workspace/private/outputs/s22plus-ufs-route-h0-20261127-1/transport-build-floor/kernel-source"


def words(hexdigest):
    raw = bytes.fromhex(hexdigest)
    return [int.from_bytes(raw[i:i + 4], "big") for i in range(0, 32, 4)]


GATE_OK = [180, 2, 40, 6, 6, 0x1ff, 0x0f, 1, 1] + [0, 0, 0, 0, 0, 0, 0, 0] + \
          [(4 << 8) | 0x0a, (4 << 8) | 0x03, (7 << 8) | 0x04, (4 << 8) | 0x0d, (4 << 8) | 0x0d, (4 << 8) | 0x30, 0, 0]
GATE_OK[9 + 0x2a // 32] |= 1 << (0x2a % 32)          # one refused WRITE(10) attempt
GATE_OK[9 + 0x1b // 32] |= 1 << (0x1b % 32)          # one START STOP UNIT to a normal LU


def good(**overrides):
    v = [0, 8, report_modes.tag(18), 64200, 1840, 0, 0, 0, 0, 1, 0, 0, 0, 0,
         4, 4, 2, 2, 1, 1, 2, 0x310, 0x1ce, 5, 4096, 62305280, 0, *words(w.HANDOVER_GPT_SHA256),
         0, *words(w.STORAGE_PATTERN_SHA256), *GATE_OK]
    for index, value in overrides.items():
        v[int(index[1:])] = value
    return v


def record(values):
    line = (" ".join(map(str, values)) + "\n").encode()
    envelope = report_modes.ENVELOPE[18]
    raw = b"G030RES1" + WIT[8:w.HEADER.size] + struct.pack("<III", 0, 0, len(line)) + line.ljust(envelope, b"\0")
    return raw + w.tag(KEY, ID, 20, raw)


def decode(values):
    return w.result(record(values), WIT, KEY, ID, report_version=18)


class ReportFormat(unittest.TestCase):
    def test_producer_field_count_equals_the_declaration(self):
        text = (UP / "g0q_handover.c").read_text()
        head = re.search(r'n = scnprintf\(buf, PAGE_SIZE, "([^"]*)"', text).group(1)
        gate = int(re.search(r"#define G0Q_GATE_WORDS\s+(\d+)", text).group(1))
        self.assertEqual(head.count("%") + 8 + 1 + 8 + gate, report_modes.FIELDS[18])
        self.assertEqual(gate, int(re.search(r"#define G0Q_GATE_SNAPSHOT_WORDS (\d+)",
                                             (UP / "g0q_ufs_gate.h").read_text()).group(1)))
        self.assertIn(f"#define G0Q_HANDOVER_TAG\t0x{report_modes.tag(18):08x}U", text)

    def test_observer_header_declares_the_v18_envelope(self):
        header = (LINK / "link-report.h").read_text()
        block = header[header.index("#ifdef G0Q_UPSTREAM_HANDOVER"):header.index("#elif defined(G0Q_STORAGE_WRITE)")]
        self.assertIn(f"#define G0Q_REPORT_TAG 0x{report_modes.tag(18):08x}U", block)
        self.assertIn(f"#define G0Q_REPORT_FIELDS {report_modes.FIELDS[18]}", block)
        self.assertIn(f"#define G0Q_REPORT_BYTES {report_modes.ENVELOPE[18]}U", block)

    def test_worst_case_line_fits_the_envelope(self):
        widest = [-4095 if i in (0, 5, 6, 7, 8, 26, 35) else 2**32 - 1 for i in range(69)]
        self.assertLess(len(" ".join(map(str, widest))) + 1, report_modes.ENVELOPE[18])

    def test_v17_and_earlier_schemas_are_unchanged(self):
        self.assertEqual(report_modes.FIELDS[17], 57)
        self.assertEqual(report_modes.ENVELOPE[17], 512)
        self.assertEqual(report_modes.tag(17), 0xf0200000)


class Decoder(unittest.TestCase):
    def test_complete_handover_reads_gpt_and_pattern(self):
        facts = decode(good())
        self.assertEqual(facts["status"], "UFS_LINK_COMPLETED")
        self.assertTrue(facts["normal_return"] and facts["recovery_return"])
        self.assertTrue(facts["gpt_match"])
        self.assertEqual(facts["block"], "PATTERN")
        self.assertEqual(facts["hba_state"], "OPERATIONAL")
        self.assertEqual(facts["gate"]["refused_opcodes"], ["0x1b", "0x2a"])
        self.assertEqual(facts["gate"]["refused_queries"][0], dict(opcode=4, idn=0x0a))
        self.assertFalse(facts["gate"]["writes_possible"])

    def test_zero_block_still_completes_but_reports_zero(self):
        facts = decode(good(**{f"v{36 + i}": x for i, x in enumerate(words(hashlib.sha256(bytes(4096)).hexdigest()))}))
        self.assertEqual((facts["status"], facts["block"]), ("UFS_LINK_COMPLETED", "ZERO"))

    def test_other_gpt_is_not_completed(self):
        facts = decode(good(v27=0x12345678))
        self.assertEqual(facts["status"], "NO_PROOF")
        self.assertFalse(facts["gpt_match"])
        self.assertTrue(facts["recovery_return"])

    def test_probe_timeout_after_overlay(self):
        values = good(v0=-110, v1=3, v9=-1, v14=0, v15=0, v16=0, v17=0, v18=0, v19=0, v20=0, v21=0, v22=0,
                      v23=0, v24=0, v25=0, v26=-115, v35=-115, v4=120000)
        for i in list(range(27, 35)) + list(range(36, 44)):
            values[i] = 0
        values[44:69] = [0] * 25
        facts = decode(values)
        self.assertEqual((facts["status"], facts["step"], facts["operation_errno"]), ("NO_PROOF", "OVERLAY", 110))
        self.assertIsNone(facts["hba_state"])

    def test_registration_failure(self):
        values = [-19, 1, report_modes.tag(18), 64200, 0, -12, -125, -125, 0, -1] + [0] * 16 + [-115] + [0] * 8 + \
                 [-115] + [0] * 8 + [0] * 25
        facts = decode(values)
        self.assertEqual((facts["step"], facts["registration"]["core_errno"]), ("ADMITTED", 12))

    def test_producer_invariants_refuse_impossible_reports(self):
        for name, values in (
                ("tag", good(v2=report_modes.tag(17))),
                ("rc/step", good(v0=-5)),
                ("start before floor", good(v3=59999)),
                ("host not sampled", good(v9=-1)),
                ("gpt digest without read", good(v26=-5)),
                ("allowed opcode refused", good(v53=1)),
                ("query log beyond count", good(v48=1, v47=1)),
                ("caps gained", good(v50=0x200)),
                ("gate not applied", good(v51=0)),
                ("range", good(v10=-1))):
            with self.subTest(name), self.assertRaises(ValueError):
                decode(values)

    def test_wrong_field_count_is_refused(self):
        with self.assertRaises(ValueError):
            decode(good()[:-1])


@unittest.skipUnless((KERNEL / "drivers/ufs/core/ufshcd.c").exists(), "pinned private kernel source required")
class CompositeRender(unittest.TestCase):
    def test_each_registration_hook_replaces_its_module_init(self):
        import combine_render
        core = combine_render.ufshcd((KERNEL / "drivers/ufs/core/ufshcd.c").read_text())
        qcom = combine_render.ufs_qcom((KERNEL / "drivers/ufs/host/ufs-qcom.c").read_text())
        qmp = combine_render.qmp_ufs((KERNEL / "drivers/phy/qualcomm/phy-qcom-qmp-ufs.c").read_text())
        for text, hook in ((core, "int __init g0q_ufshcd_core_init(void)\n{"),
                           (qcom, "int g0q_ufs_qcom_register(void)\n{"), (qmp, "int g0q_qmp_ufs_register(void)\n{")):
            self.assertEqual(text.count(hook), 1)
            self.assertNotIn("module_init(", text)
            self.assertNotIn("module_exit(", text)
            self.assertNotIn("module_platform_driver(", text)
        self.assertIn("if (!g0q_gate_scsi(hba, cmd))", core)
        self.assertIn("QSERDES_V5_RX_GM_CAL, 0x0f", qmp)

    def test_stage_never_opens_the_private_arena_or_writes(self):
        text = (UP / "g0q_handover.c").read_text()
        for banned in ("g0q_rpmh_begin", "g0q_rpmh_", "kernel_write", "BLK_OPEN_WRITE", "submit_bio",
                       "scsi_execute_cmd", "vfs_write"):
            self.assertNotIn(banned, text)
        self.assertIn("BLK_OPEN_READ", text)


if __name__ == "__main__":
    unittest.main()
