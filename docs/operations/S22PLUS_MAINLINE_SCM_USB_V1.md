# S22+ one attended SCM binding observation

Status: **REVIEW_GATED_CAPABILITY**

Ordinary cue status: **REVIEW_GATED_CAPABILITY**

For the SM-S906N / g0q / FYG8 observation, the existing mainline RAM owner uses one Android-origin operation with its existing physical attendance, effect-time identity, health, fixed observation window, manual Download, original-A return and no-replay conditions. The selected board artifact is the [qualified moduleless Debian RAM candidate](../reports/S22PLUS_MAINLINE_SCM_BOARD_ARTIFACT_H0_2026-11-22.md). Its exact qualification pins one AP, key commitment, decoder and loader-produced FDT. The [Image review](../reports/S22PLUS_MAINLINE_SCM_USB_H0_2026-11-22.md) identifies the kernel's own SCM initialization effects. MPSS, UFS and SD controllers are disabled.

## Kernel effects for the exact candidate

The boot package has SHA-256 `c7dd8fa726fee413a0d9cddc37b58cbf16f05b5695ef84469c261e6396bb83d9`. Its built-in SCM driver and the fixed device tree determine the following reachable effects during boot. The userspace observer only samples binding state.

- The platform probe can acquire its interconnect and clock resources, register the wait-queue IRQ and initialize the TrustZone memory allocator. If the IRQ fires, the driver can query pending wait contexts repeatedly while firmware reports more pending work.
- The driver queries shared-memory bridge support and can request bridge enablement. Its kernel memory pool starts empty and can allocate up to 256 KiB on demand. Modem VMID 15 assignment is outside this experiment.
- The selected default dump mode permits a read and conditional NODUMP field update and a request to disable watchdog debugging and SDI. A kernel shutdown that reaches the SCM callback may request NODUMP again. Firmware persistence of the SDI setting is unverified. Physical Download and restoration of original A are independent of a successful USB observation.
- The kernel can issue the fixed zero-length QTEE support query and conditionally register its platform device. Its Gunyah watchdog helper can register a platform device when the platform conditions match. The selected kernel configuration omits the Gunyah watchdog driver.

The enabled SM8450 SMMU can proceed with normal platform initialization once SCM is available. Its register, context and cache setup are kernel platform effects. MPSS remains disabled. The USB observation supplies no return value for any individual firmware request and makes no IRQ-registration claim. The 120-second evidence window bounds host observation. Kernel initialization and IRQ activity can precede that window or continue until the physical reset.

## Observation and return

A single NCM challenge samples the first binding of the identified SCM device. The original transfer window, endpoint continuity, authenticated request, sealed response and exact loader FDT apply. A valid bound or unbound sample records the observed state. A valid indeterminate sample retains the authenticated boot evidence and the indeterminate value. Missing or rejected evidence leaves SCM unproved. An observation error follows the existing physical recovery path. Final Android return and health must be established independently before terminal closure. Physical recovery requires the same original owner and original A.

The foreground preapproval `ready` operation uses the mainline RAM policy’s existing fixed Android transcript. The exact source-bound SCM review, qualified package, current target and recovery bindings, and the existing one-operation attended grant are required by the [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md). One operation authorizes one boot-only N transfer and at most one original-A return on the same owner. The operator must be present and able to enter physical Download. The owner rechecks the original A and final rooted Android health. Consumed candidates and uncertain transfers remain consumed.

## Ordinary USB attach cue

The S22+ target contract's SCM observation may use the existing bounded
phone-end attach procedure on its ordinary `mainline-evidence` step. The
new task must bind the dedicated [SCM ordinary-cue source review](../../workspace/public/src/device-action/bindings/s22plus_mainline_scm_ordinary_cue_v21_review.json)
and meet the existing SCM qualification, finite approval, attendance and
rollback requirements. Earlier SCM tasks retain their original review and
operation records. The qualification named above was consumed in the
[SCM USB run](../reports/S22PLUS_MAINLINE_SCM_USB_RUN_2026-11-22.md). A
subsequent run requires its own reviewed qualification, fresh exact task and
finite attended approval.

Use the fixed cue caller. It checks raw-complete N and the active original
120-second observation window with more than 60 seconds remaining, the latest
sealed census showing USB2 absence with no related children, and the absence
of endpoint selection, a request, a stop or a return. Only a durable cue
eligible for display permits the operator to detach the phone end once for
about three seconds and then reconnect with the same cable, host port and
orientation, without pressing buttons. The operator records one actual
completion or cancellation. A cable or enumeration race retains the one-shot
request and stop rules. The cue cannot extend the observation window.
Recording the operator's statement may wait up to one second to acquire the
operation lock. The local wait gives no additional time to the observation.

The ordinary observation rederives the authenticated result with an
operation-bound cue closure at or after the sealed response. With a pending
cue, the owner cannot request a physical Download return or start a new
original-A recovery. After a stop, further cue issuance is closed for the
original owner. A late actual completion or cancellation can settle that
owner's recovery interlock without renewing the observation or grant. An
existing A intent follows its original raw-completion and health-only rules.
Independently proved A and final health can support H0 terminal repair when
the observation closure is unavailable.

This adopts the physical attach condition within the existing SCM observation
and return scope. Replugging supplies no proof of the cause of USB absence.
The separate physical Download, exact A, final Android health and no-replay
conditions continue to apply.
