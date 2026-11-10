# ML045: CFG1 bit-readback failure identified, healthy Android closure

## Outcome

ML045 completed one attended physical experiment and is consumed with
**NO_PROOF / ANDROID_CLOSED_HEALTHY**. The bounded diagnostic criterion passed:
the first HCI_CFG1 post-read still had bit 0 clear, so the bit-readback branch
returned EIO and the short-circuited time check was not evaluated. The two
existing reads both returned **`0x1c00052c`**. No local UIC or link command was
issued. Automatic result-bound Download, the sole original-A transfer and all
seven final health reads completed. The owned network profile is absent and
no F1 owner remains. No physical Download action or connector recovery was needed.

The [H0 analysis, Argon discussions and independent review](S22PLUS_MAINLINE_ML045_CFG1_DIAGNOSTICS_H0_2026-11-11.md)
were committed as `200b37957f`. They include 159 passing tests without skips,
exact artifact qualification, the independent PASS_GO, and the corrected
reconnect capture CLI. The operator returned the exact one-operation,
1800-second approval with current attendance and usable physical Download.
The single fixed preapproval D0 passed all seven raw health reads; it was
68.273 seconds old when the actual response was recorded. No approval,
readiness, consumption or effect budget was renewed for this run.

## Reconnect caller and first response

The prepared self-capture CLI invoked the existing cue exactly once. Its
original full guards and sealed absence census passed; the cue was published
at **N+33.689 seconds**, with more than 60 seconds left in the original window.
The critical notification and sound both returned successfully at unchanged
volume. The operator reported the requested one phone-end disconnect/reconnect
complete; the fixed resolution CLI recorded that actual response at
**N+64.138 seconds**. Both child stdout/stderr and status were sealed before
interpretation. No keyword construction, caller retry or window extension
occurred. This exercised the repair that ML044's host invocation had lacked.

The first complete authenticated response was already sealed at
**N+57.847 seconds**, within the original 120-second limit. The response-before-
completion-report ordering is permitted by the existing cue protocol; it does
not establish the exact physical action time or a Type-C causal mechanism.
Actual RAM SysVinit PID 1, the selected observer, zero block devices and a
fresh authenticated recovery-child reply were verified. The original owner
then continued the same-boot witness without another connection/request.

## Physical diagnostic evidence

The witness advanced **300.339 host seconds** and **300.453 guest seconds**.
One durable module permit followed. The authenticated V10 result completed at
**N+362.130 seconds**, 1.940 host seconds after permit intent. That interval
is not a kernel-clock measurement; V10's branch evidence resolves the question
without relying on it.

The result retained the same successful initial preparation as ML044:

- Pre-stop HCE/HCS/IS were `0x1` / `0x10f` / `0x400`. One HCE-zero write
  observed full zero in one poll, with a reported software interval of
  2 microseconds and complete timely handoff flags.
- All eleven initial predicates passed. The same-read HCS masked sample was
  `0x8`; it is diagnostic data under the reviewed disabled-state predicate.
- Initial acknowledgement flags were 15, with timely full IS zero. This
  establishes that observed history, not event origin or W1C causality.
- Eleven fixed power records were claimed, triggered and acknowledged with
  masks `0x7ff`, no reclaimed slot and no reported error. PHY readiness was
  set and the existing reset/PHY/symbol-clock preparation reached stage six.

The new fields were:

| Field | Observed value |
| --- | --- |
| Outcome | `READBACK_BIT_CLEAR` (1) |
| Existing pre-read | `0x1c00052c` |
| Existing post-read | `0x1c00052c` |
| Budget evaluated | false |
| Budget expired | unavailable; the check was not executed |
| Return | EIO (`-5`) |
| Local UIC / link commands | 0 / 0 |

The retained source calls the existing write with `pre | 1`, here
`0x1c00052d`, between those two reads. The post-read's bit 0 remained clear.
This proves which branch ML045 took; it does not prove that the write reached
or changed the register, why the bit remained clear, or an electrical clock/
reset state. The values are nonzero register observations, not an aperture or
clock qualification. The subsequent HCE-one statement was not reached; the
software HCE-started latch alone is not evidence of enabling the controller.

ML044's identical high-level EIO tuple remains consistent with this result,
but its raw CFG1 and branch were not recorded. ML045 cannot retrospectively
prove that old run took the same branch. The selected Linux/Samsung drivers'
mode-selection write does not itself impose this immediate readback assertion;
whether this bounded module's check matches the target's required sequencing
remains a separate question. No speculative delay, readback bypass, ordering
change, additional read/write or second experiment was performed.

## Return, health and complete raw audit

The complete negative result selected the existing authenticated return path.
The host rederived the result digest, control, ACK and EOF. Exact Download
admitted the sole original-A transfer; this demonstrates normal return after
a completed diagnostic refusal. It does not test timer, hung-probe or kernel
failure recovery, and conditional unattended F1 remains inactive.

One initial final-health ADB read failed with return code 1 and retained both
streams. The same executor used its existing health-only continuation after
raw proof of A completion; it did not transfer A again. Seven final health
reads passed. The task-owned profile was removed and verified absent. The
terminal's recovered flag reflects this health continuation, not a physical
Download action.

Canonical seconds from grant opening differ from the N-launch times above.
The observation-complete label does not mean UFS link success.

| Event | Seconds from grant |
| --- | ---: |
| Live session start | 0.000 |
| N transfer start / complete | 24.999 / 26.824 |
| Candidate observation step complete | 401.327 |
| Original-A transfer start / complete | 414.627 / 416.490 |
| Final health / durable session end | 462.853 |

After healthy terminal and owner release, the unchanged independently reviewed
paged H0 finalizer and offline audit ran with command acquisition, socket and
process creation blocked. They reopened **532 task raw captures across three
pages**, all source snapshots and the canonical timeline, plus the two separate
cue/resolution captures. Base, witness, V10 result and return were rederived.
The final checks proved one N and one A total, seven health reads, profile
absence and no owner. The preserved ADB failure and two expected profile-
absence observations were the only nonzero producers in the task index.

The first private audit reached its final report construction after these
checks, then failed because a cue-local variable shadowed the terminal result.
Its source and failure log were retained. Renaming that local variable and
rerunning only the offline audit produced PASS; no transition or device
observation was repeated. The durable healthy terminal was never invalidated.
The connector now reports CLOSED_BY_ORIGINAL_OWNER and closed true.

Private evidence is under
`workspace/private/outputs/s22plus-ml045-cfg1-h0-20261111-1/`, including
`task-1/closed.json`, `task-1/timeline.json`, `task-1/raw-index-v2.json`,
`run-audit-1.json`, both cue captures, exact approval, source/capability/review
records and the original Argon accounting. ML044 and earlier consumed
records, A90, S20+ and unrelated dirty work remain unchanged. This task ends
after this one physical run; the result grants no next experiment or replay.
