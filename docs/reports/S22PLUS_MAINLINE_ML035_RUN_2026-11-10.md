# S22+ ML035: USB admission passed; stage-two stop and healthy return

ML035 is **consumed** with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.
Its corrected ordinary BCM producer passed the unchanged USB/PM/ICC/BCM
admission on the S22+. The same-boot five-minute witness passed. The late
module then returned `EBUSY(16)` at stage 2 without a local UniPro or link
command. Original A transferred once, and a health-only continuation completed
seven fresh health reads after one ADB disappearance. No F1 owner remains.

This completes the operator-requested correction and next attended experiment.
The UFS link remains unproved. ML035's grant and candidate cannot replay.
A90, S20+ and unrelated Debian journal work were untouched.

## Scope and preparation

[H0 qualification and discussion](S22PLUS_MAINLINE_ML035_BCM_ALIAS_H0_2026-11-10.md)
reproduced the duplicate display BCM producer with actual functions and the
full SM8450 tables. The corrected kernel removes six unused producer objects
and registrations while retaining all nodes, indices, normal BCMs and guard
predicates. The fixed module rebuilt byte-identically to ML034. Fresh observer
keys, archives, loader and boot-only AP received independent candidate and
owner reviews before preparation commit `d1eca24fbe`.

The operator returned the exact one-operation 1800-second approval and
confirmed current attendance and usable physical Download recovery. The
[ML035 policy](../operations/S22PLUS_MAINLINE_UFS_LINK_BCM_ALIAS_V1.md), current
reviewed capability and immutable backend v39 governed this one run. The fixed
foreground D0 health was fresh at entry. One start, one original-A recovery
and one health-only continuation were dispatched; none was repeated.

## Functional evidence

Times below use the original N-launch window, not file publication time or the
end of the N transfer.

| Event | N-relative time or result |
| --- | --- |
| N transfer completed in the durable journal | +2.306 s |
| One recorded reconnect cue | +57.627 s; 62.373 s remained in the first-response window |
| First selected USB census present | +88.742 s |
| First authenticated base sealed | +90.749 s, inside the original 120 s |
| Operator completion reply resolved | +95.082 s |
| Fresh same-boot witness | 300.405 s host interval; 300.525 s guest uptime advance |
| One module permit sent | +393.766 s |
| Authenticated module result sealed | +393.793 s |
| Original owner stopped new commands | +395.210 s |
| Separate physical Download completion reported | +483.464 s |
| Original-A transfer completed in the journal | +488.929 s |
| Complete final health bracket sealed | +582.999 s |

The base proved the selected kernel/DT/observer, packaged Debian PID 1 and
zero block devices. Guest uptime advanced from 78.938 seconds to 379.463
seconds on the same authenticated boot and socket before the one-shot permit.
The operator reported the single three-second phone-end reconnect complete;
its actual physical timing is unmeasured. The cue was resolved before any
separate physical Download instruction. There was no window extension.

The exact authenticated result was:

- `operation_errno=16`, `stage=2`, `status=NO_PROOF`, `normal_return=false`.
- `usb_covered=true`, `usb_released=true`, `usb_reason=OK`,
  `usb_first_lock=OK`, `usb_attempts=1`, `usb_detail=0`.
- Fixed RPMh request records, claims, triggers, acknowledgments and reclaims:
  all zero.
- Local UniPro commands: zero; `link_issued=false`.

Unlike ML034's known-zero SH1 rejection, ML035 passed the unchanged locked
SH1/CN0 confirmation predicates. This demonstrates that the prepared correction
was sufficient to pass this admission on this boot. It does not establish which
object/order produced ML034's historical row or prove electrically applied
votes. The overall UFS result remains distinct from the successful USB admission
and five-minute witness.

## New stop boundary

The exact retained module sources and their build hashes place stage 2 after
MMIO-window/reset-handle acquisition and successful `access_power` calls for
runtime PM and the five access clocks. Stage 2 contains the HCI quiescence
composite guard, reset-pin output/high guard, core/UniPro rate selection and
host supply setup. The report does not identify which of those returned
`EBUSY`; no specific register value or inherited-controller cause is inferred.

Zero fixed RPMh records and zero UniPro/link commands do **not** mean that the
whole candidate performed no hardware work. Ordinary boot-time BCM commands,
late platform initialization and the earlier PM/clock preparation occurred.
The specific fixed regulator requests and later link operations remained
unissued according to their authenticated counters. No new experiment or
relaxed guard was used to investigate this stop.

## Recovery and raw audit

After the stop and closed reconnect cue, the operator separately confirmed
physical Download. The existing owner transferred its exact original A once.
Raw transfer completion was rederived before the health-only continuation.
The first health bracket's `03-health` read failed with return code 1, empty
stdout and ADB reporting the selected device absent. That failed bracket is
retained separately; no successful prefix was combined with later reads.

The original health-only continuation performed a complete fresh seven-read
bracket. Raw health projection, original-A identity, owned-network removal
and terminal state were verified. The network was removed once and later
observed already absent. The original owner is closed and released.

H0 `close_task` and the final auditor ran with command acquisition, socket
creation and process creation blocked. The auditor reopened all **553 indexed
raw captures**, plus both sealed cue caller captures; rederived N/A transfer
completion, authenticated base/witness/permit/result, source binding, final
health, network cleanup and no-replay effect history; and verified all 2,970
preceding protected records and 11 unrelated files unchanged.

The empty ACK capture is the finalizer's record after the late module rejection.
No native Download control was sent, so its `timed_out` flag is not evidence
that a sent Download command timed out. Expected owned-profile absence and the
one failed ADB health read remain explicitly classified in the raw audit.

Private evidence is retained under:

- `workspace/private/outputs/s22plus-ml035-policy-adoption-h0-20261110-1`
- `workspace/private/outputs/s22plus-mainline-ml035-bcm-alias-h0-20261110-1`
- `workspace/private/outputs/s22plus-ml035-sh1-discussion-h0-20261110-1`

The functional frontier is now stage-two UFS admission. A future investigation
starts from these retained sources and raw facts; this closed grant supplies
no successor authority.
