"""Roadmap step 4b: render the pinned upstream sources into one composite module.

The observer loads exactly one fixed module (g0q_ml030.ko) once. The composite links the gated ufshcd
core, ufshcd-pltfrm, ufs-qcom and the g0q QMP UFS PHY driver with the stage (g0q_handover.c). A module
has one init, so each upstream registration hook becomes a plain function the stage calls in order:
  ufshcd.c        module_init/module_exit(ufshcd_core_init/exit) -> g0q_ufshcd_core_init(); no exit
  ufs-qcom.c      module_platform_driver(ufs_qcom_pltform)       -> g0q_ufs_qcom_register()
  phy-qcom-qmp-ufs.c module_platform_driver(qmp_ufs_driver)     -> g0q_qmp_ufs_register()
The composite has no exit function, so it can never be unloaded. ufshcd-pltfrm.c has no hook.
"""
from pathlib import Path
import gate_render
import phy_render

HERE = Path(__file__).resolve().parent


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("composite insertion point differs: " + old[:70])
    return text.replace(old, new, 1)


def ufshcd(source):
    text = gate_render.render(source)
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


def ufs_qcom(source):
    return _platform(source, "ufs_qcom_pltform", "g0q_ufs_qcom_register")


def qmp_ufs(source):
    return _platform(phy_render.render(source), "qmp_ufs_driver", "g0q_qmp_ufs_register")
