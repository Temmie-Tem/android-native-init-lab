"""Render the pinned Linux 7.2.11 drivers/ufs/core/ufshcd.c with the S22+ step-4 write gate (g0q_ufs_gate.h).

Each insertion must match exactly once; any upstream drift refuses. The rendering:
  1. includes g0q_ufs_gate.h after the local core headers;
  2. ufshcd_queuecommand(): refuses a SCSI command outside the policy with CHECK CONDITION,
     ILLEGAL REQUEST / INVALID COMMAND OPERATION CODE (no retry), before any state handling;
  3. ufshcd_issue_dev_cmd(): refuses a composed device-management UPIU outside the policy with
     -EACCES before execution (covers NOP, query and raw BSG/RPMB UPIUs: all three callers);
  4. ufshcd_hba_init(): clears the low-power, WriteBooster, crypto and TX EQ capabilities right
     after the variant (ufs-qcom) init that sets them;
  5. ufshcd_init(): disables auto-hibernate (ahit = 0) after the core's 150 ms default;
  6. ufshcd_wl_probe(): no pm_runtime_allow(), so the device W-LU keeps the SCSI default
     (runtime PM forbidden) and the device and link stay active until shutdown.
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINNED_SHA256 = "a99c7260652e6e40ced80685af95027ca5f857d2bd68be48a059233b00485fd6"
GATE_HEADER = HERE / "g0q_ufs_gate.h"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("insertion point differs: " + old[:70])
    return text.replace(old, new, 1)


def _within(text, signature, old, new):
    if text.count(signature) != 1:
        raise ValueError("function differs: " + signature)
    start = text.index(signature)
    end = text.index("\n}\n", start) + 3
    return text[:start] + _once(text[start:end], old, new) + text[end:]


def render(source):
    if digest(source) != PINNED_SHA256:
        raise ValueError("ufshcd.c is not the pinned 7.2.11 source")
    text = _once(source, '#include "ufshcd-crypto.h"\n',
                 '#include "ufshcd-crypto.h"\n#include "g0q_ufs_gate.h"\n')
    text = _within(text, "static enum scsi_qc_status ufshcd_queuecommand(struct Scsi_Host *host,",
                   "\tswitch (hba->ufshcd_state) {\n",
                   "\tif (!g0q_gate_scsi(hba, cmd)) {\n"
                   "\t\t/* g0q gate: INVALID COMMAND OPERATION CODE, completed without retry. */\n"
                   "\t\tscsi_build_sense(cmd, 0, ILLEGAL_REQUEST, 0x20, 0);\n"
                   "\t\tscsi_done(cmd);\n"
                   "\t\treturn 0;\n"
                   "\t}\n\n"
                   "\tswitch (hba->ufshcd_state) {\n")
    text = _within(text, "static int ufshcd_issue_dev_cmd(struct ufs_hba *hba, struct scsi_cmnd *cmd,",
                   "\trq->timeout = timeout;\n",
                   "\tif (!g0q_gate_devman((const u8 *)lrbp->ucd_req_ptr))\n"
                   "\t\treturn -EACCES;\n\n"
                   "\trq->timeout = timeout;\n")
    text = _within(text, "static int ufshcd_hba_init(struct ufs_hba *hba)",
                   "\terr = ufshcd_variant_hba_init(hba);\n\tif (err)\n\t\tgoto out_disable_vreg;\n",
                   "\terr = ufshcd_variant_hba_init(hba);\n\tif (err)\n\t\tgoto out_disable_vreg;\n"
                   "\tg0q_gate_caps(hba);\n")
    text = _within(text, "int ufshcd_init(struct ufs_hba *hba, void __iomem *mmio_base, unsigned int irq)",
                   "\t\t\t    FIELD_PREP(UFSHCI_AHIBERN8_SCALE_MASK, 3);\n\t}\n",
                   "\t\t\t    FIELD_PREP(UFSHCI_AHIBERN8_SCALE_MASK, 3);\n\t}\n"
                   "\t/* g0q gate: no auto-hibernate; the link stays active while idle. */\n"
                   "\thba->ahit = 0;\n\tg0q_gate.ahit_disabled = 1;\n")
    text = _within(text, "static int ufshcd_wl_probe(struct scsi_device *sdev)",
                   "\tpm_runtime_set_autosuspend_delay(dev, 0);\n\tpm_runtime_allow(dev);\n",
                   "\t/* g0q gate: runtime PM stays forbidden (SCSI default); device and link stay active. */\n"
                   "\tg0q_gate.wlun_rpm_kept = 1;\n")
    return text


if __name__ == "__main__":
    import sys
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    rendered = render(src.read_text())
    out.write_text(rendered)
    print(digest(rendered))
