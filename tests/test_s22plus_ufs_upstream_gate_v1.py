"""Roadmap step 4a: the deny-by-default UFS write gate (policy table, ufshcd.c rendering) and the upstream overlay."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "workspace/public/src/mainline/s22plus_ufs_upstream_h0"
sys.path.insert(0, str(CODE))
import gate_render  # noqa: E402

KERNEL_UFSHCD = ROOT / ("workspace/private/outputs/s22plus-ufs-route-h0-20261127-1/"
                        "transport-build-floor/kernel-source/drivers/ufs/core/ufshcd.c")
LUNS = (0x00, 0x01, 0x1f, 0x81, 0xb0, 0xc4, 0xd0)

FIXTURE = r"""
#include <stdio.h>
#include "g0q_ufs_gate.h"
static const unsigned char luns[] = {0x00, 0x01, 0x1f, 0x81, 0xb0, 0xc4, 0xd0};
int main(void)
{
	unsigned char cdb[16] = {0}, upiu[32] = {0};
	for (int op = 0; op < 256; op++)
		for (int sa = 0; sa < 32; sa++)
			for (unsigned l = 0; l < sizeof(luns); l++) {
				cdb[0] = op; cdb[1] = 0xe0 | sa;
				printf("S %d %d %d %d\n", op, sa, luns[l], g0q_gate_scsi_allowed(cdb, 16, luns[l]));
			}
	cdb[0] = 0x9e; cdb[1] = 0x10;
	printf("SHORT %d\n", g0q_gate_scsi_allowed(cdb, 1, 0));
	for (int type = 0; type < 64; type++)
		for (int opc = 0; opc < 16; opc++)
			for (int idn = 0; idn < 0x40; idn++) {
				upiu[0] = type; upiu[12] = opc; upiu[13] = idn;
				printf("D %d %d %d %d\n", type, opc, idn, g0q_gate_devman_allowed(upiu));
			}
	return 0;
}
"""

READ_ONLY = {0x00, 0x03, 0x12, 0xA0, 0x25, 0x1A, 0x5A, 0x08, 0x28, 0x88, 0x35, 0x91}
WRITES = {0x0A, 0x2A, 0x8A, 0xAA, 0x2E, 0x8E, 0x41, 0x93, 0x42, 0x04, 0x3B, 0x15, 0x55, 0xB5, 0x07,
          0x48, 0x9F, 0x3F, 0x9D, 0xA4, 0x8C, 0x2F, 0x94}


def expected_scsi(op, sa, lun):
    if op in READ_ONLY:
        return 1
    if op == 0x9E:
        return int(sa == 0x10)
    if op == 0x1B:
        return int(lun == 0xD0)
    return 0


def expected_devman(type_, opc, idn):
    if type_ == 0x00:
        return 1
    if type_ != 0x16:
        return 0
    return int(opc in (1, 3, 5) or (opc == 6 and idn == 1))


@unittest.skipUnless(shutil.which("cc"), "host C compiler required")
class GatePolicyTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "fixture.c"
            exe = Path(tmp) / "fixture"
            src.write_text(FIXTURE)
            subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", "-I", str(CODE), str(src), "-o", str(exe)],
                           check=True)
            cls.lines = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.splitlines()

    def test_every_scsi_opcode_service_action_and_lun(self):
        rows = [l.split() for l in self.lines if l.startswith("S ")]
        self.assertEqual(len(rows), 256 * 32 * len(LUNS))
        for _, op, sa, lun, got in rows:
            self.assertEqual(int(got), expected_scsi(int(op), int(sa), int(lun)), (op, sa, lun))

    def test_no_write_like_opcode_is_allowed_anywhere(self):
        allowed = {int(l.split()[1]) for l in self.lines if l.startswith("S ") and l.endswith(" 1")}
        self.assertFalse(allowed & WRITES)
        self.assertNotIn(0x1B, {int(l.split()[1]) for l in self.lines
                                if l.startswith("S ") and l.endswith(" 1") and l.split()[3] != str(0xD0)})

    def test_short_service_action_cdb_is_refused(self):
        self.assertIn("SHORT 0", self.lines)

    def test_every_devman_type_query_opcode_and_idn(self):
        rows = [l.split() for l in self.lines if l.startswith("D ")]
        self.assertEqual(len(rows), 64 * 16 * 0x40)
        for _, type_, opc, idn, got in rows:
            self.assertEqual(int(got), expected_devman(int(type_), int(opc), int(idn)), (type_, opc, idn))

    def test_query_writes_upstream_issues_are_refused(self):
        # (opcode, idn): bRefClkFreq, bActiveICCLevel, bMaxNumOfRTT, qTimestamp, dSecondsPassed,
        # wExceptionEventControl, fBackgroundOpsEn set/clear, WriteBooster enable, TX EQ settings.
        for opc, idn in ((4, 0x0A), (4, 0x03), (4, 0x2B), (4, 0x30), (4, 0x34), (4, 0x0D), (6, 0x04),
                         (7, 0x04), (6, 0x0E), (7, 0x0E), (8, 0x01), (2, 0x01), (7, 0x01)):
            self.assertIn(f"D 22 {opc} {idn} 0", self.lines)


@unittest.skipUnless(KERNEL_UFSHCD.exists(), "pinned private kernel source required")
class GateRendering(unittest.TestCase):
    def setUp(self):
        self.source = KERNEL_UFSHCD.read_text()
        self.text = gate_render.render(self.source)

    def test_each_hook_is_inserted_once(self):
        for needle in ('#include "g0q_ufs_gate.h"', "if (!g0q_gate_scsi(hba, cmd))",
                       "if (!g0q_gate_devman((const u8 *)lrbp->ucd_req_ptr))", "\tg0q_gate_caps(hba);\n",
                       "\thba->ahit = 0;\n", "g0q_gate.wlun_rpm_kept = 1;"):
            self.assertEqual(self.text.count(needle), 1, needle)

    def test_scsi_gate_precedes_every_issue_path_in_queuecommand(self):
        start = self.text.index("static enum scsi_qc_status ufshcd_queuecommand(")
        body = self.text[start:self.text.index("\n}\n", start)]
        self.assertLess(body.index("g0q_gate_scsi"), body.index("switch (hba->ufshcd_state)"))
        self.assertLess(body.index("g0q_gate_scsi"), body.index("ufshcd_send_command"))

    def test_devman_gate_precedes_execution(self):
        start = self.text.index("static int ufshcd_issue_dev_cmd(")
        body = self.text[start:self.text.index("\n}\n", start)]
        self.assertLess(body.index("g0q_gate_devman"), body.index("blk_execute_rq"))
        # Every device-management execution goes through ufshcd_issue_dev_cmd: one blk_execute_rq,
        # and each of the three reserved-command users (query/NOP, raw UPIU, advanced RPMB) calls it.
        self.assertEqual(self.text.count("blk_execute_rq("), 1)
        users = [i for i in range(len(self.text)) if self.text.startswith("ufshcd_get_dev_mgmt_cmd(hba);", i)]
        self.assertEqual(len(users), 3)
        for at in users:
            body = self.text[at:self.text.index("\n}\n", at)]
            self.assertIn("ufshcd_issue_dev_cmd(hba, cmd, tag,", body)
        start = self.text.index("static enum scsi_qc_status ufshcd_queue_reserved_command(")
        self.assertNotIn("scsi_get_internal_cmd", self.text[self.text.index("\n}\n", 3 + self.text.index(
            "return scsi_get_internal_cmd(")):])
        self.assertGreater(start, 0)

    def test_runtime_pm_is_never_allowed(self):
        self.assertNotIn("pm_runtime_allow(", self.text)

    def test_drifted_source_is_refused(self):
        with self.assertRaises(ValueError):
            gate_render.render(self.source.replace("pm_runtime_allow(dev);", "pm_runtime_allow(dev); "))


if __name__ == "__main__":
    unittest.main()


import upstream_overlay  # noqa: E402


@unittest.skipUnless(upstream_overlay.ROUTE_DTB.exists() and shutil.which("fdtoverlay"), "route DT + dtc required")
class UpstreamOverlay(unittest.TestCase):
    def test_overlay_enables_only_the_upstream_nodes_with_fixed_rails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = upstream_overlay.build(Path(tmp) / "out")
        self.assertEqual(result["status"], "PASS_H0_G0Q_UPSTREAM_UFS_OVERLAY")
        self.assertEqual(result["rails"], {"smps12": 1256000, "ldo6": 1200000, "ldo7": 2504000, "ldo9": 1200000})
        self.assertFalse(result["reset_gpio"])

    def test_overlay_text_has_no_reset_gpio_bob_parent_or_ice_change(self):
        text = upstream_overlay.source()
        for banned in ("reset-gpios", "vdd-l2-l7-supply", "qcom,ice", "tlmm", "pinctrl"):
            self.assertNotIn(banned, text)


import phy_render  # noqa: E402

KERNEL_QMP = KERNEL_UFSHCD.parents[2] / "phy/qualcomm/phy-qcom-qmp-ufs.c"


@unittest.skipUnless(KERNEL_QMP.exists(), "pinned private kernel source required")
class PhyRendering(unittest.TestCase):
    def test_only_the_three_board_values_change(self):
        source = KERNEL_QMP.read_text()
        text = phy_render.render(source)
        removed = [l for l in source.splitlines() if l not in text.splitlines()]
        added = [l for l in text.splitlines() if l not in source.splitlines()]
        self.assertEqual(len(removed), 2)
        self.assertEqual(sorted(a.split("\t/*")[0].strip() for a in added), [
            "QMP_PHY_INIT_CFG(QSERDES_V5_RX_GM_CAL, 0x0f),",
            "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_RX, 0x06),",
            "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_TX, 0x03),"])

    def test_drifted_source_is_refused(self):
        with self.assertRaises(ValueError):
            phy_render.render(KERNEL_QMP.read_text() + "\n")
