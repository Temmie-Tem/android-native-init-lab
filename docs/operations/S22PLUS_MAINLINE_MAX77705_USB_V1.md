# S22+ one attended MAX77705 USB switch observation

Status: **DRAFT_H0**

For the proposed SM-S906N / g0q / FYG8 observation, the existing mainline RAM owner would run one Android-origin operation. Every condition of that owner applies unchanged:
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

This scope is prepared in an isolated checkout. Execution requires:
- independent review of the affecting owner closure;
- explicit target adoption;
- the exact finite attended run grant under the [mainline RAM policy](S22PLUS_MAINLINE_RAM_V1.md).

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
  this scope's own review ([`s22plus_mainline_max77705_usb_v1_review.json`](../../workspace/public/src/device-action/bindings/s22plus_mainline_max77705_usb_v1_review.json)).
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

The H0 branch selects four pending records under
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

MAX77705 remains H0 until its separate target adoption. If that adoption
changes a source bound by these drafts, regenerate the affected pins and
review the resulting bytes before publication. The exact board
qualification and separate finite attended approval apply to any later run.
