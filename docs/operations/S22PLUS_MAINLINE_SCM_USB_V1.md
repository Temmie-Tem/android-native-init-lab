# S22+ one attended SCM binding observation

Status: **DRAFT_H0**

For the proposed SM-S906N / g0q / FYG8 observation, the existing mainline RAM owner would use one Android-origin operation with its existing physical attendance, effect-time identity, health, fixed observation window, manual Download, original-A return and no-replay conditions. The selected board artifact is the [qualified moduleless Debian RAM candidate](../reports/S22PLUS_MAINLINE_SCM_BOARD_ARTIFACT_H0_2026-11-22.md). Its exact qualification pins one AP, key commitment, decoder and loader-produced FDT. The [Image review](../reports/S22PLUS_MAINLINE_SCM_USB_H0_2026-11-22.md) identifies the kernel's own SCM initialization effects. MPSS, UFS and SD controllers are disabled.

A single NCM challenge samples the first binding of the identified SCM device. The original transfer window, endpoint continuity, authenticated request, sealed response and exact loader FDT apply. A valid bound or unbound sample records the observed state. A valid indeterminate sample retains the authenticated boot evidence and the indeterminate value. Missing or rejected evidence leaves SCM unproved. An observation error follows the existing physical recovery path. Final Android return and health must be established independently before terminal closure. Physical recovery requires the same original owner and original A.

This scope is prepared in an isolated checkout. Execution requires independent review of the affecting owner closure, explicit target adoption and the exact finite attended run grant under the [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md).
