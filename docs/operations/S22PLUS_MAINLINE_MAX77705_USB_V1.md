# S22+ one attended MAX77705 USB switch observation

Status: **REVIEW_GATED_CAPABILITY**

For the SM-S906N / g0q / FYG8 observation, the existing mainline RAM owner runs one Android-origin operation. Every condition of that owner applies unchanged:
- physical attendance;
- effect-time identity and health;
- the fixed observation window;
- the attach cue and its resolution interlock, extended to this image's ordinary evidence route. The [cue tool](../../workspace/public/src/scripts/host_tools/s22plus_mainline_attach_cue_v1.py) accepts the image while its `mainline-evidence` step is active. After the response, the owner closes issuance with the same `close_issuance` rule as the UFS route. An issued cue must carry the operator's resolution before the window ends, or the observation is not accepted;
- manual Download;
- original-A return;
- no replay.

The selected board artifact is the [qualified moduleless Debian RAM candidate with the read-only MAX77705 observer](../reports/S22PLUS_MAINLINE_MAX77705_OBSERVER_H0_2026-11-22.md#board-package-h0). Its exact qualification pins one AP, a key commitment, a self-contained decoder and the loader-produced FDT. The candidate differs from the reviewed ML053 inputs in three places:
- `I2C_QCOM_GENI=y`;
- SE5 and its QUP wrapper enabled, with the SE5 pinctrl removed;
- the observer.

MPSS, UFS, SD and every remote processor stay disabled. TLMM and `gpi_dma0` stay disabled.

**Bus effects.** The only register values the observer writes are the two USBC mailbox bytes for one `CONTROL1_R` command: `0x05 → 0x21` and `0x00 → 0x41` on `0x25`. There are at most 32 such commands. Each read also sends its register address in write direction, to the PMIC, USBC and FSA4480 alike. No register value is written to the PMIC or FSA4480, and `CONTROL1_W` is never sent. Reads clear the volatile `UIC_INT` and `CC_INT` latches. The [SE5 sharing review](../reports/S22PLUS_MAINLINE_MAX77705_OBSERVER_H0_2026-11-22.md#se5-sharing-review) lists what the mainline driver writes to the serial engine for each handoff state.

**Kernel effects for the exact candidate.** The boot package has SHA-256 `3b4f30394111891b268bcdd62cfce47c191c7ec98c54b8ae3bd295c9342d2c86`. Its kernel was built from the same source tree as the adopted SCM candidate (`s22plus-mainline-ml035-bcm-alias-h0-20261110-1/transport-build-1/kernel-source`), with `CONFIG_QCOM_SCM=y`, `CONFIG_QCOM_TZMEM_MODE_SHMBRIDGE=y`, `CONFIG_QCOM_QSEECOM` and `CONFIG_GUNYAH_WATCHDOG` not set, and no download-mode default, so `download_mode` is 0 (off). The loader-produced FDT keeps the same enabled `/firmware/scm` node as the SCM candidate (`qcom,scm-sm8450`, `qcom,dload-mode = <TCSR 0x13000>`, its interconnects). These SCM effects are reachable during boot, before the observer runs, and are the same as those listed in the [SCM policy](S22PLUS_MAINLINE_SCM_USB_V1.md#kernel-effects-for-the-exact-candidate):
- the platform probe can acquire its interconnect and clock resources, initialize the TrustZone memory allocator and register the wait-queue IRQ that firmware reports. If the IRQ fires, the driver can query pending wait contexts repeatedly while firmware reports more pending work;
- the driver queries shared-memory bridge support and can request bridge enablement. Its kernel memory pool starts empty and can allocate up to 256 KiB on demand. Modem VMID 15 assignment is outside this experiment;
- with download mode off, the probe performs a read and conditional NODUMP update of the TCSR download-mode field and requests that watchdog debugging and SDI be disabled. A kernel shutdown that reaches the SCM callback may request NODUMP again. Firmware persistence of the SDI setting is unverified. Physical Download and restoration of original A are independent of a successful USB observation;
- the kernel can issue the fixed zero-length QTEE support query and conditionally register its platform device. Its Gunyah watchdog helper can register a platform device when the platform conditions match; the selected configuration omits the Gunyah watchdog driver.

The enabled SM8450 SMMU can proceed with normal platform initialization once SCM is available. SE5, its QUP wrapper and the I2C GENI driver add the serial-engine effects in the SE5 sharing review. MPSS remains disabled. The USB observation supplies no return value for any individual firmware request and makes no IRQ-registration claim. Kernel initialization and IRQ activity can precede the evidence window or continue until the physical reset.

**Observation and outcomes.** A single NCM challenge returns the record, which spans boot to request. The existing transfer window, endpoint continuity, authenticated request, sealed response and exact loader FDT apply.

| Evidence | Outcome |
|---|---|
| Valid sample with a switch verdict (`INITIAL_COM_USB`, `OTHER_INITIAL_CONTROL1`, `OPEN_NO_ATTACH_SEEN`, `OPEN_BOOT_ATTACH_ONLY`, `OPEN_NO_READ_AFTER_ATTACH`, `OPEN_THEN_COM_USB_AFTER_ATTACH`, `OPEN_UNCHANGED_AFTER_ATTACH` or `OPEN_THEN_OTHER_AFTER_ATTACH`) and a valid cue closure | The verdict is recorded, together with the decoder's own verdict. |
| `OPEN_INITIAL_LATCH_UNREAD`: the decoder said `OPEN_NO_ATTACH_SEEN`, but the boot-time UIC latch was not read | MAX77705 stays unproved. |
| `EVENTS_DROPPED`: more than 48 events occurred, so the producer overwrote the middle of the event list | MAX77705 stays unproved. Only a first-read verdict (`INITIAL_COM_USB`, `OTHER_INITIAL_CONTROL1`) whose first successful read lies in the kept, complete prefix of 24 events is kept. |
| Valid `NO_PROOF_*` sample (adapter absent, identity mismatch, no CONTROL1 read) | The authenticated boot evidence and the reason are retained. The switch stays unproved. |
| Missing or rejected evidence, a record the observer cannot produce, or a missing or unresolved cue closure | MAX77705 stays unproved. |
| Observation error | The existing physical recovery path is followed. |

Final Android return and health must be established independently before terminal closure. Physical recovery requires the same original owner and the original A.

**Scope of the result.** A verdict describes this one record and is not causal. Interpreting it is the [root-cause plan](../reports/S22PLUS_MAINLINE_REPLUG_DEPENDENCY_ROOT_CAUSE_H0_2026-11-22.md)'s task. A `CONTROL1_W` profile (Stage 2) is out of scope.

**Target adoption (2026-11-22).** The [target contract](targets/S22PLUS_FYG8_TARGET_CONTRACT.md) adopts this scope as a **REVIEW_GATED_CAPABILITY**. Each run requires:
- the selected MAX77705 review at `PASS_GO` for the exact owner closure, checked before candidate code is imported;
- the exact board qualification named by the binding module;
- current target identity and a usable original-A recovery path;
- the existing fixed foreground preapproval D0 on a fresh task;
- one new finite attended mainline RAM grant under the [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md);
- the operator's attendance for the cued replug and its explicit resolution.

It grants no `CONTROL1_W`, Linux storage, installed-root, reset, automatic-recovery, retry or replay capability. Preparing a task is H0.

**No-attach refinement (independent review, 2026-11-22).** The pinned board decoder derives `OPEN_NO_ATTACH_SEEN` from the event array only. The producer, however, saves the boot-time UIC latch before its first CONTROL1 command, and the phone normally boots with the cable in. The binding module refines that one verdict from the decoded latch, without changing the qualified decoder or the board artifact:
- an unread latch gives `OPEN_INITIAL_LATCH_UNREAD`, which is inconclusive;
- a VBUSDetI or CHGTypI latch gives `OPEN_BOOT_ATTACH_ONLY`, an attach before the first read only;
- otherwise the verdict stays `OPEN_NO_ATTACH_SEEN`.

A later attach event, such as the cued replug, keeps the decoder's after-attach verdict. When more than 48 events occurred, the dropped middle may hold the first successful read, an attach or a later read, so every switch verdict becomes `EVENTS_DROPPED`, except a first-read verdict whose first successful read lies in the kept prefix (re-review findings, 2026-11-22).

**Re-application on the adopted shared cue (2026-11-22).** The shared
ordinary-route cue, the SCM selection and the three shared-interlock fixes
listed in the first draft were adopted into `main` in `a2f0e74eb8`. This
version keeps the cue tool unchanged and adds only:
- the `MX_*` constants, `max77705_board()`, and a MAX77705 branch in
  `ordinary_cue(adapter, request)`. The cue opens only when the task binds
  this scope's own review ([`s22plus_mainline_max77705_usb_v2_review.json`](../../workspace/public/src/device-action/bindings/s22plus_mainline_max77705_usb_v2_review.json)).
  There is no MAX77705 scope without the cue;
- the wire and image-binding dispatch;
- a `rederive` branch. It checks the review closure before importing
  candidate code and joins the attach closure, which must not precede the
  sealed response. Malformed retained records surface as `ValueError`;
- `validate_result`, `terminal` (with `attach_closure`), and the task
  source closure, review selection, recovery skip of the candidate module,
  and target adoption check.

These shared modules are pinned by the review set adopted in `a2f0e74eb8`:
gateway v57, loader timing-v3 cue, and SCM ordinary cue v2. Adopting this
change therefore needs a successor review set and one more cutover, run
under the same checker and locks. The MAX77705 module still drops the
observation when the cue closure is missing, even though the sealed response
survives.

## Successor reviews and adoption

The H0 branch staged four records under
`workspace/public/src/device-action/bindings/`.

- `s22plus_approved_terminal_persistent_v58_review.json`
- `s22plus_loader_android_timing_v3_cue_v2_review.json`
- `s22plus_mainline_scm_ordinary_cue_v3_review.json`
- `s22plus_mainline_max77705_usb_v1_review.json`

After independent review of the exact closure, publish the approved set in
one squash commit on the operating HEAD. Include all four `PASS_GO`
receipts, the task selectors, and the gateway selector pin for the final
approved v58 receipt. Keep the prior receipts and task evidence. Use the
[shared cutover procedure](../reports/S22PLUS_MAINLINE_ORDINARY_CUE_H0_2026-11-22.md#integration-hold-and-atomic-adoption)
with the existing admission lock and target session lease. Close old owners
and tasks with the old reviews, and resolve staged approvals before the
switch. Run the read-only checker against the exact proposed commit while
the old checkout is still in place.

These four records were adopted in `9a697cb415`. The target adoption edits
this policy and the target contract, which those records pin, so it is
published with its own successor review set (see the section below). The exact board
qualification and separate finite attended approval apply to any later run.

## Successor reviews for target adoption

The target-adoption branch selects four pending records under
`workspace/public/src/device-action/bindings/`.

- `s22plus_approved_terminal_persistent_v59_review.json`
- `s22plus_loader_android_timing_v3_cue_v3_review.json`
- `s22plus_mainline_scm_ordinary_cue_v4_review.json`
- `s22plus_mainline_max77705_usb_v2_review.json`

After independent review of the exact bytes, publish the target adoption,
all four `PASS_GO` records, the task selectors, and the gateway selector pin
for the approved v59 receipt in one squash on the operating HEAD. Keep the
published receipts and task evidence. Under the existing admission lock and
target session lease, use the [shared cutover procedure](../reports/S22PLUS_MAINLINE_ORDINARY_CUE_H0_2026-11-22.md#integration-hold-and-atomic-adoption)
to close old owners and tasks with their original reviews and resolve staged
approvals. Run the read-only checker against the exact squash before switching
the operating checkout.
