"""Roadmap step 4b: render the pinned upstream sources into one composite module.

The observer loads exactly one fixed module (g0q_ml030.ko) once. The composite links the gated ufshcd
core, ufshcd-pltfrm, ufs-qcom and the g0q QMP UFS PHY driver with the stage (g0q_handover.c). A module
has one init, so each upstream registration hook becomes a plain function the stage calls in order:
  ufshcd.c        module_init/module_exit(ufshcd_core_init/exit) -> g0q_ufshcd_core_init(); no exit
  ufs-qcom.c      module_platform_driver(ufs_qcom_pltform)       -> g0q_ufs_qcom_register()
  phy-qcom-qmp-ufs.c module_platform_driver(qmp_ufs_driver)     -> g0q_qmp_ufs_register()
The composite has no exit function, so it can never be unloaded. ufshcd-pltfrm.c has no hook.

Shutdown: upstream restart runs the W-LU shutdown (device power-off, link off) while the host clocks
are still on, but nothing proves the controller stopped before the SMMU stops translating. The render
adds the fixed stage's rule there, and again in a new ufs-qcom platform shutdown (after the W-LU,
before the SMMU) for a host whose W-LU never existed, after a runtime resume: stop both request lists, clear HCE and wait up to 1 s for it to read
0; otherwise assert the controller's own block reset (ufs-qcom core_reset) and park the restart forever,
so the attended physical Download is the recovery.
"""
from pathlib import Path
import gate_render
import phy_render

HERE = Path(__file__).resolve().parent


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("composite insertion point differs: " + old[:70])
    return text.replace(old, new, 1)


QUIESCE = (
    "/* g0q composite: prove the controller stopped before restart reaches the SMMU, or park. */\n"
    "void g0q_ufs_qcom_park(struct ufs_hba *hba);\n"
    "static bool g0q_quiesced;\n"
    "static void g0q_quiesce_or_park(struct ufs_hba *hba)\n{\n"
    "\tu64 until;\n\n"
    "\tufshcd_writel(hba, 0, REG_UTP_TRANSFER_REQ_LIST_RUN_STOP);\n"
    "\tufshcd_writel(hba, 0, REG_UTP_TASK_REQ_LIST_RUN_STOP);\n"
    "\tufshcd_writel(hba, CONTROLLER_DISABLE, REG_CONTROLLER_ENABLE);\n"
    "\tuntil = ktime_get_boottime_ns() + NSEC_PER_SEC;\n"
    "\twhile (ktime_get_boottime_ns() < until) {\n"
    "\t\tif (!(ufshcd_readl(hba, REG_CONTROLLER_ENABLE) & CONTROLLER_ENABLE)) {\n"
    "\t\t\tWRITE_ONCE(g0q_quiesced, true);\n"
    "\t\t\treturn;\n"
    "\t\t}\n"
    "\t\tudelay(100);\n"
    "\t}\n"
    "\tg0q_ufs_qcom_park(hba);\n"
    "}\n\n"
    "/* Platform shutdown (after the W-LU, before the SMMU): covers a host whose W-LU never existed.\n"
    " * Clocks may be runtime-suspended there, so resume first; a failed resume parks. */\n"
    "void g0q_ufshcd_shutdown_quiesce(struct ufs_hba *hba);\n"
    "void g0q_ufshcd_shutdown_quiesce(struct ufs_hba *hba)\n{\n"
    "\tif (READ_ONCE(g0q_quiesced))\n"
    "\t\treturn;\n"
    "\tif (pm_runtime_get_sync(hba->dev) < 0)\n"
    "\t\tg0q_ufs_qcom_park(hba);\n"
    "\tg0q_quiesce_or_park(hba);\n"
    "}\n\n")


def ufshcd(source):
    text = gate_render.render(source)
    text = _once(text, "static void ufshcd_wl_shutdown(struct scsi_device *sdev)\n{\n",
                 QUIESCE + "static void ufshcd_wl_shutdown(struct scsi_device *sdev)\n{\n")
    # After the W-LU power-off and link-off attempt (whatever its result), before ufshcd_suspend()
    # may turn the host clocks off: the registers are still accessible here.
    text = _once(text, "\t__ufshcd_wl_suspend(hba, UFS_SHUTDOWN_PM);\n\n\t/*\n\t * Next, turn off the UFS controller",
                 "\t__ufshcd_wl_suspend(hba, UFS_SHUTDOWN_PM);\n\tg0q_quiesce_or_park(hba);\n\n\t/*\n"
                 "\t * Next, turn off the UFS controller")
    text = _once(text, "static void __exit ufshcd_core_exit(void)",
                 "static void __exit __maybe_unused ufshcd_core_exit(void)")
    return _once(text, "module_init(ufshcd_core_init);\nmodule_exit(ufshcd_core_exit);\n",
                 "/* g0q composite: called once by the step-4b stage; never unloaded. */\n"
                 "int __init g0q_ufshcd_core_init(void);\n"
                 "int __init g0q_ufshcd_core_init(void)\n{\n\treturn ufshcd_core_init();\n}\n")


def _platform(text, driver, hook):
    return _once(text, f"module_platform_driver({driver});\n",
                 f"/* g0q composite: registered once by the step-4b stage; never unregistered. */\n"
                 f"int {hook}(void);\nint {hook}(void)\n{{\n\treturn platform_driver_register(&{driver});\n}}\n")


PARK = (
    "/* g0q composite: hold the controller's block reset and never return (restart parked). */\n"
    "void g0q_ufs_qcom_park(struct ufs_hba *hba);\n"
    "void g0q_ufs_qcom_park(struct ufs_hba *hba)\n{\n"
    "\tstruct ufs_qcom_host *host = ufshcd_get_variant(hba);\n\n"
    "\tif (host && host->core_reset)\n"
    "\t\treset_control_assert(host->core_reset);\n"
    "\tfor (;;)\n"
    "\t\tmdelay(1000);\n"
    "}\n\n")


SHUTDOWN = (
    "void g0q_ufshcd_shutdown_quiesce(struct ufs_hba *hba);\n"
    "static void g0q_ufs_qcom_shutdown(struct platform_device *pdev)\n{\n"
    "\tstruct ufs_hba *hba = platform_get_drvdata(pdev);\n\n"
    "\tif (hba)\n"
    "\t\tg0q_ufshcd_shutdown_quiesce(hba);\n"
    "}\n\n")


def ufs_qcom(source):
    text = _once(source, "static struct platform_driver ufs_qcom_pltform = {\n\t.probe\t= ufs_qcom_probe,\n"
                 "\t.remove = ufs_qcom_remove,\n",
                 PARK + SHUTDOWN + "static struct platform_driver ufs_qcom_pltform = {\n\t.probe\t= ufs_qcom_probe,\n"
                 "\t.remove = ufs_qcom_remove,\n\t.shutdown = g0q_ufs_qcom_shutdown,\n")
    return _platform(text, "ufs_qcom_pltform", "g0q_ufs_qcom_register")


def qmp_ufs(source):
    return _platform(phy_render.render(source), "qmp_ufs_driver", "g0q_qmp_ufs_register")
