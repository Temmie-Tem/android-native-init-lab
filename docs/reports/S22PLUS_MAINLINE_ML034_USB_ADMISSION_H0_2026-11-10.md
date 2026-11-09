# S22+ ML034 USB-admission correction and H0 qualification

ML033 proved its authenticated first response and five-minute same-boot
witness, then returned `EBUSY` before USB coverage or UFS hardware work.
The retained implementation identifies `g0q_usb_cover()` as the rejecting
function, but its 19-field report does not identify the branch. That historical
cause remains unknown. Its consumed `NO_PROOF` / `ANDROID_CLOSED_HEALTHY`
result is unchanged.

ML034 preserves every coverage predicate, adds bounded retry only for failed
trylocks, and reports the exact final rejection. The new Image, module, RAM
archive, loader and boot-only AP have completed H0 qualification. Independent
candidate and owner/bridge reviews are `PASS_GO`; fixed preparation has
completed. This report is not physical authority or a successful UFS-link claim.

## Discussion and correction

Argon and Opus reviewed the retained result and actual kernel/DT/producer code.
The retained DT still has the required ICC path; tags, provider/node naming,
driver data and target command bit positions match the checks. There was no
evidence to remove a guard. Both models initially treated the ordinary RPMh
prohibition as global. Source comparison showed it is issuer-task-specific;
both explicitly corrected that premise. A concurrent ordinary ICC holder can
finish its commit. Calling the prohibition as a diagnostic would itself latch
`EPERM` and is forbidden.

Only USB-device, ICC-bandwidth, global BCM-voter and selected-voter trylock
failures may recheck the complete coverage. Every attempt releases all locks
and PM/device references before sleeping. Other failures return immediately.
The loop admits at most 25 calls in 250ms, within the unchanged absolute 15s
budget. It checks deadlines before calls and after success, releasing late
successful references before any hardware work. There is one begin and no
new PM resume, vote, overlay/rail/probe retry or hardware-command replay.

The report adds two unsigned scalar words to the original 19 fields. They
record final reason, first retryable lock reason, attempt count and bounded
final detail. The complete worst-case line is 233 bytes in the existing
256-byte payload. The exact AP selects version 2; old APs retain version 1.
No length-based fallback exists. Coverage success remains distinct from
operation/link success and normal Download admission.

## Validation and evidence limits

- Fourteen focused transport/wire tests include the actual USB/ICC/BCM and
  retry C bodies, balanced reference/lock recording, all four retry types,
  exhaustion, late success, pre-call expiry, non-lock rejection, malformed
  reason/errno combinations and C-to-Python report parsing. The Python reason
  numbering is checked against the actual kernel header.
- The BCM fixture uses byte-identical retained `tcs_cmd_gen` and `tcs_list_gen`
  functions. Multi-VCD batches, repeated ordinary commits, later commit failure,
  absent completion waits and value saturation are exercised. It does not
  establish actual target scheduling or electrical state.
- Nine actual host-collector socket tests preserve raw failures, reject a USB
  coverage failure before normal control, retain independent link facts after
  return failure, and exercise the selected 21-field successful-return path.
- The fresh kernel, module and observers compile for ARM64. Both observers
  and canonical CPIOs reproduce exactly from their sealed inputs. Actual
  loader instructions, rejection cases and QEMU EL1/EL2/EL3 entry are checked;
  two packaging passes produce identical boot/AP bytes.
- Two fresh ARM64 QEMU runs exercise the real host collector and original
  five-minute wait: the modeled link/result/normal-return case records a
  300.019s host gap; the real module's wrong-board rejection records 300.017s
  and load `ENODEV`. The modeled power/coverage fields are fixtures, not g0q
  hardware proof. Unchanged guest early-query/bad-permit evidence is reused
  only with its retained source identity.
- The current legacy decoder reopens the exact retained ML033 bundle and raw
  19-field result as its original `NO_PROOF` / `EBUSY`, without inventing a
  reason. The old review's seven now-changed development source paths are
  joined to exact hash-matching Git bytes in a separate retained snapshot;
  old artifacts, reviews and consumed records are not repinned.

An initial loader-test launch lacked the retained Unicorn import path; it
failed before creating test output. Selecting that existing private dependency
completed the test. An initial aggregate qualifier incorrectly compared an
old review with moving development sources; the exact historical-source join
above corrected that provenance check. Both failure logs are retained.

Private artifacts and raw evidence are under
`workspace/private/outputs/s22plus-mainline-ml034-usb-cover-h0-20261110-1/`.
Model discussions and protected-record checks are under the separate
`s22plus-ml034-usb-cover-discussion-h0-20261110-1` output. External-model usage,
including the first empty timed-out Argon call and later completed calls, is
recorded privately. Model-call time limits were removed at the operator's
request. No credentials or raw target identifiers are included here.

## Scope, review and preparation

The [exact ML034 policy](../operations/S22PLUS_MAINLINE_UFS_LINK_USB_ADMISSION_V1.md)
contains the completed artifact table and original observation/return/recovery
conditions. The 120/300/540/15-second bounds, one N, one link attempt and one
original A total remain. The separate finite 1800-second approval, current
attendance and usable physical Download recovery are still required.

The candidate review binds `review-inputs-2.json` and the actual new artifacts.
The separate owner/bridge review binds the final exact declaration and source
closure. Actual admission accepts five exact retained/new bundles, selects
legacy version 1 or ML034 version 2 explicitly, and rejects 75 mixed/unknown
cases, including foreign kernel/module receipts. Four actual Session fixtures
also close with one original A when the candidate decoder is absent or invalid,
including health-only continuation after a failed health read.

The new capability and immutable terminal backend V38 are published from those
reviews; V37 remains unchanged and the stable worker bytes are identical. The
exact task and its preceding ML033 healthy closure are joined in
`workspace/private/outputs/s22plus-ml034-policy-adoption-h0-20261110-1/`.
The prepared caller's help and prospective operation/capture paths are recorded;
no attach cue has been issued.

The fixed foreground D0 completed all seven Android health reads and passed
fresh raw rederivation. At that observation there was no F1 owner, ML034 grant,
operation, saved approval or transfer. The latest readiness must still satisfy
its existing freshness rule when the returned approval opens the grant. All
1291 protected consumed records and 11 unrelated files remained byte-identical.
No physical UFS result exists. A90 and S20+ were untouched.

Checklist application: ABI/SEMANTIC/WIRE/IO are covered by exact target APIs,
real producer/consumer code, bounded records and explicit proof limits;
ARTIFACT by fresh builds and byte joins; AUDIT/PERSIST by raw preservation,
historical provenance and consumed-record checks. ROUTE and RETURN are covered
by exact declaration/mixed-input checks, independent owner review and the
missing/invalid candidate-decoder recovery fixtures.
DISPLAY is unchanged and outside this correction.
