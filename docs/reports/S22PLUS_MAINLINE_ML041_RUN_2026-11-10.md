# ML041: missing first response, automatic arrival and healthy return

## Outcome

**NO_PROOF / ANDROID_CLOSED_HEALTHY.** The second requested physical experiment
used the unused, freshly qualified peer of ML040 with unchanged V6 capability,
review and v42 execution machinery. Its separately returned attended grant
covered one operation. The predeclared existing no-cue branch instructed the
operator to leave the cable and buttons untouched; no physical action or
recovery continuation was requested or reported.

All 88 first-window USB censuses showed the selected endpoint absent. No
protocol request, child-arm receipt, five-minute witness, module permit or UFS
command followed. The original owner then observed exact new-generation
Download at **N + 587.921 seconds**, inside its original N + 660-second cap.
Original A transferred once and all seven final-health reads passed in the
first bracket. N and A each transferred once. No network profile was created,
no F1 owner remains, and ML041 is consumed without replay authority.

This proves the observed return and original-A recovery without a host protocol
request or a requested physical fallback. It does **not** identify the guest
reset trigger: no authenticated child/timer receipt survived. The terminal
therefore retains `automatic_download_arrival_observed=true` and
`automatic_recovery_trigger_proved=false`, with `automatic_recovery_proved=false`.
PID1 execution, a UFS link, kernel/probe-stall recovery and conditional unattended
F1 are not proved. The latter remains inactive.

## Relation to ML040

[ML040](S22PLUS_MAINLINE_ML040_RUN_2026-11-10.md) proved authenticated USB,
child arm/liveness, the same-boot witness and result-bound automatic return
following a complete HCE pre-admission refusal. Its raw reset-pin control word
was `0xb`; the HCE stop write did not occur. ML041 instead exercised the existing
host path that waits for exact Download even without the first response.
The two results establish different coverage and do not resolve the historical
USB failure cause or the pin-direction admission question.

The [implementation and Mythos discussion](S22PLUS_MAINLINE_ML040_HCE_AUTORECOVERY_H0_2026-11-10.md)
record the three actual Mythos 5.2 advisory calls, source-grounded HCE design,
automatic-return implementation, independent review and provider/CLI accounting.
No additional model call, candidate rebuild, policy change or device retry was
needed for ML041. A90 and S20+ were untouched.

## Post-terminal reporting repair

After device closure, the original H0 task finalizer tried to serialize all
6,807 raw-capture entries into one immutable JSON record. Its 2,431,024 bytes
exceeded the existing 2 MiB record limit. Publication failed before creating
`raw-index.json` or `closed.json`; the complete raw files, original terminal,
health, journal and consumed state remained intact. A subsequent offline audit
correctly refused the missing closure. Neither failure caused a device action.

The separate `s22plus_mainline_close_h0_v2.py` H0 tool retains the original task,
grant, Session terminal rederivation, transfer counts and canonical timeline.
It requires an existing healthy terminal and no F1 owner. It divides the raw
index into deterministic 256-entry pages, publishes pages before the index and
publishes `closed.json` last. ML041 uses 27 pages; the largest is 100,037 bytes.
Every verification reopens the complete discovered capture set and both raw
streams, checks exact page order, contents, pins and counts, and rejects missing,
extra, duplicated, reordered or altered evidence. An existing index is verified
without writes. Interrupted publication resumes only through byte-identical
existing outputs, with no overwrite or deletion.

The v2 outer closure retains the original execution `source_binding` and
`source_snapshot`. Its separate `reporting_provenance` pins the reviewed finalizer
and retained source text. Existing v1 closures use the original verifier and
remain byte-identical. v42, the common/target policies, all consumed grants and
the original execution source closure are unchanged. The 2 MiB limit is unchanged.

## Validation and retained evidence

The focused H0 checks exercise 256/257 boundaries, complete discovery, altered
raw bytes, missing/duplicate/reordered pages and captures, mismatched partial
outputs, interruption, idempotence and closed-last publication. The real 6,807-
capture set and original Session derivation were checked with process, socket
and raw-acquisition entry points blocked; ML040's existing v1 closure was
revalidated through its original consumer without changing bytes. The independent review returned **PASS_GO with no findings**, independently
passed all eight focused tests, and rechecked the current-source complete raw
set, Session derivation and v1 parity. Its receipt is
`reporting-repair/independent-review-1.json`, SHA-256
`99e4270b4dd3cf7768a758f2d3677aef92bbd17bffd78eb62cef49b5e6723c3e`.

The reviewed finalizer published the closure successfully and a second invocation
returned the identical receipt. The final offline audit passed all 6,807 captures
across 27 pages, exact N/A transfer proofs, the original arrival/transfer cap,
all seven healthy reads, source snapshots and absence of a remaining F1 owner.
There were no nonzero, timed-out or producer-error raw commands to classify.
Original A launched at N+589.369 seconds and final health completed at
N+635.900 seconds. All finalization and audit work performed zero device actions.
Touched Python compiled; scoped privacy, link and diff checks passed.

Past-failure checklist: PERSIST is confirmed by the actual serialized-size
failure and bounded-page repair; WIRE/SEMANTIC/AUDIT are checked against the
real complete raw set and unchanged health/transfer/terminal derivation;
ROUTE/RETURN retain the original owner, automatic arrival cap and no-replay
semantics. ABI, DISPLAY and media persistence are inapplicable to this
post-terminal reporting change. No new execution gate was added.

Private evidence is under
`workspace/private/outputs/s22plus-ml041-automatic-noresponse-h0-20261110-1/`,
including the original failed audit log, `reporting-repair/`, the paged
`task-1/` closure and the final offline run audit. The two requested physical
experiments are complete; further hardware changes require a separate bounded
unit under the existing capability rules.
