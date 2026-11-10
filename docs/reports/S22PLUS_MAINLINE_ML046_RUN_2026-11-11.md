# ML046: local UniPro preparation and one link command, healthy Android closure

## Outcome

ML046 completed the requested single attended physical experiment and is
consumed with **NO_PROOF / ANDROID_CLOSED_HEALTHY**. Both first CFG1 reads
again returned **`0x1c00052c`**, with bit 0 clear. V11 checked and passed the
original budget, then progressed through all six local UniPro commands and
issued the one permitted DME_LINK_STARTUP. The final operation returned EIO;
link success and the underlying hardware cause remain unproved.

Automatic result-bound Download, one original-A transfer and all seven final
Android health reads completed. No physical Download action or connector
recovery dispatch was needed. The owned network profile is absent and no F1
owner remains. This bounded task is complete; it opens no next experiment.
A90, S20+, earlier consumed records and unrelated dirty work remain unchanged.

The [Argon discussions, source analysis and V11 validation](S22PLUS_MAINLINE_ML046_CFG1_SELECTION_H0_2026-11-11.md)
were committed as `0d2a34d0b5`, with 168 passing tests, exact artifact
qualification and an independent PASS_GO without open findings. The operator
returned the exact one-operation, 1800-second approval and current attendance
with usable physical Download recovery. Current preapproval D0 passed all
seven raw health reads. No grant, candidate, observation or effect was replayed.

## First response and witness

The repaired fixed cue caller published its single request at **N+32.359
seconds**, leaving more than 60 seconds in the original window. Notification
and sound succeeded without changing volume. The operator's one phone-end
reconnect completion was recorded at **N+65.821 seconds**; both cue child
captures were retained and verified. No caller retry or window extension occurred.

The first complete authenticated response arrived at **N+56.347 seconds**,
before the completion report and within the original 120-second bound. This
ordering does not establish the exact physical reconnection time or USB cause.
RAM SysVinit PID 1, the selected observer, zero block devices and the fresh
recovery-child response were verified. The same-boot witness advanced
**300.337 host seconds / 300.458 guest seconds**, with a fresh child reply.
The sole module permit produced the authenticated V11 result at
**N+360.673 seconds**.

## Physical progress and limits

Initial HCE/HCS/IS were `0x1` / `0x10f` / `0x400`. One HCE-zero write observed
full zero in one poll, with the reported software interval of 2 microseconds.
All eleven initial predicates passed; the same-read masked HCS sample was
`0x8`. Initial completion acknowledgement flags were 15, with timely full IS
zero. Eleven fixed power records settled with masks `0x7ff`, no reclaimed
slot and no reported error. PHY readiness was set and stage six was reached.

| Field | Observed value |
| --- | --- |
| CFG1 outcome | `BIT_CLEAR_BUDGET_PASS` (1) |
| Existing CFG1 pre/post reads | `0x1c00052c` / `0x1c00052c` |
| Original budget evaluated / expired | true / false |
| Local UniPro command count | 6 |
| Link command issued | true |
| Full HCS immediately before link issue | `0x8` |
| Saved terminal interrupt / result / HCS fields | `0` / `0` / `0` |
| Operation result | EIO (`-5`), `NO_PROOF` |

The source-bound command order establishes progress through HCE enable/ready,
the TX-state GET and expected value, SYS1CLK readback, both local timer
GET/SET pairs, the later CFG1 bit-31 check and the local TX LCC SET. Each
preceding local command returned successfully before link issuance. These
are observed software checks and command progression, not an electrical
state measurement or proof of persistent bit-0 selection.

The immediate bit-0 value therefore did not prevent this run from reaching
the local commands and link attempt. It supports the useful functional reach
of the reviewed V11 correction. It does not explain why the bit reads clear,
prove the alternative lane-order hypothesis, or establish a successful link.
ML045 retains its original bit-clear refusal and cannot be reinterpreted.

The saved terminal zeros require care. In the bound `command()` source,
link issuance records `before` and the issued latch. An IRQ_STATUS sample
with bits outside `UIC_COMMAND_COMPL | UIC_LINK_STARTUP` returns EIO before
assigning the terminal interrupt/result/HCS fields. The completion branch
instead assigns a nonzero interrupt word before checking its result/HCS.
Together with EIO, six local commands and the issued latch, the retained zeros
narrow this run to that unexpected-status early return **by source inference**.
The actual failing status word was not saved. The zeros are unfilled fields,
not measurements proving clear IRQ, successful UIC result or absent device.
No UIC error-register value or specific fault bit can be identified from them.

The next useful H0 question is the link poll's unexpected-status branch and
its existing sample. This report adds no diagnostic access, guard change,
retry, second link command or followup device authority.

## Return, health and raw audit

The complete authenticated negative result selected the existing early
return transaction. Its result digest, control, ACK and EOF were rederived;
exact Download admitted the one original-A transfer. This proves automatic
return after this completed link-command refusal. It does not test timer,
hung-probe or kernel-stall recovery; conditional unattended F1 remains inactive.

One initial final-health ADB read returned 1. Its raw streams and stopped row
remain intact. The same original executor took its existing health-only path
after raw proof of A completion, then passed all seven final reads without
another transfer. The terminal recovered flag reflects this health continuation.
The connector's separate continuation/recovery/health ingresses were unused.

Canonical timeline values below are seconds from grant opening, unlike the
N-launch times above. Observation-step completion does not mean link success.

| Event | Seconds from grant |
| --- | ---: |
| Live session start | 0.000 |
| N transfer start / complete | 24.788 / 26.625 |
| Candidate observation step complete | 399.703 |
| Original-A transfer start / complete | 412.978 / 414.858 |
| Final health / durable session end | 461.172 |

After original-owner healthy closure, the unchanged reviewed paged H0
finalizer and offline audit passed with command acquisition, socket and process
creation blocked. All **497 task captures across two pages**, both separate
cue captures, source snapshots, base/witness/result/return, exact N/A transfer
completion and the canonical timeline were verified. The only nonzero task
producers were the preserved ADB health failure and two expected profile-absence
observations. The final checks proved one N and one A total, seven successful
health reads, owned-profile absence and no F1 owner. The connector reports
`CLOSED_BY_ORIGINAL_OWNER`, closed true and `ANDROID_CLOSED_HEALTHY`.

Private evidence is retained under
`workspace/private/outputs/s22plus-ml046-cfg1-selection-h0-20261111-1/`, including
`task-1/closed.json`, `task-1/timeline.json`, the paged raw index,
`run-audit-1.json`, `raw-fields-audit-1.json`, both cue captures and the exact
approval/source/capability/review records. Argon usage and quota accounting
remain in the linked H0 report and private append-only records; no further
external-model call was made during execution or closure.
