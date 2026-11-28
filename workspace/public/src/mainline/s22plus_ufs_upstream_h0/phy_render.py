"""Render the pinned Linux 7.2.11 phy-qcom-qmp-ufs.c with the g0q board values (roadmap step 4a).

Upstream sm8450_ufsphy_cfg reuses the sm8350 tables. Against the FYG8 Waipio tables that the fixed module
proved on this phone (rate A + 2nd lane, G4), the final register maps agree on 121 of 128 registers.
This rendering adopts the stock values for the three that differ on both lanes:
  TX RES_CODE_LANE_OFFSET_TX 0x09 -> 0x03, TX RES_CODE_LANE_OFFSET_RX 0x09 -> 0x06, RX GM_CAL (absent) -> 0x0f.
The remaining module-only write, PCS POWER_DOWN_CONTROL = 1, is done by the upstream power-on path itself.
Only the sm8350/sm8450 tables change; on g0q only the sm8450 config can match.
"""
import hashlib
from pathlib import Path

PINNED_SHA256 = "47e941f37fcf28b5a311087bebc48dc68ef3cb329183f0c1d62afb1fa2897bad"


def _section(text, name):
    start = text.index("static const struct qmp_phy_init_tbl " + name + "[] = {\n")
    return start, text.index("\n};\n", start)


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("table line differs: " + old)
    return text.replace(old, new, 1)


def render(source):
    if hashlib.sha256(source.encode()).hexdigest() != PINNED_SHA256:
        raise ValueError("phy-qcom-qmp-ufs.c is not the pinned 7.2.11 source")
    start, end = _section(source, "sm8350_ufsphy_tx")
    tx = source[start:end]
    tx = _once(tx, "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_TX, 0x09),",
               "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_TX, 0x03),\t/* g0q FYG8 */")
    tx = _once(tx, "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_RX, 0x09),",
               "QMP_PHY_INIT_CFG(QSERDES_V5_TX_RES_CODE_LANE_OFFSET_RX, 0x06),\t/* g0q FYG8 */")
    text = source[:start] + tx + source[end:]
    start, end = _section(text, "sm8350_ufsphy_rx")
    if "QSERDES_V5_RX_GM_CAL" in text[start:end]:
        raise ValueError("rx table already writes GM_CAL")
    return text[:end] + "\n\tQMP_PHY_INIT_CFG(QSERDES_V5_RX_GM_CAL, 0x0f),\t/* g0q FYG8 */" + text[end:]


if __name__ == "__main__":
    import sys
    out = render(Path(sys.argv[1]).read_text())
    Path(sys.argv[2]).write_text(out)
    print(hashlib.sha256(out.encode()).hexdigest())
