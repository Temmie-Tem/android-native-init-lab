# ML044: initial UIC completion acknowledged, stage-six refusal, healthy closure

## Outcome

ML044 completed one attended physical experiment and is consumed with
**NO_PROOF / ANDROID_CLOSED_HEALTHY**. V9's initial exact completion
acknowledgement reached a timely full-word-zero readback. All eleven initial
guards passed, eleven fixed power records settled, and execution progressed
through the existing reset/PHY/lane preparation to stage six. It then returned
EIO before any local UIC or link command. Automatic result-bound Download and
one original-A transfer completed; the same executor's health-only path passed
all seven final reads after preserving one failed ADB read. No recovery
connector continuation or physical Download request was needed.

[H0 analysis and independent review](S22PLUS_MAINLINE_ML044_UIC_COMPLETION_H0_2026-11-11.md),
committed as `89b758d1d3`, records the two Mythos discussions, 121 passing tests
without skips, exact independent PASS_GO and fresh artifact qualification.
The operator returned this exact task's one-operation/1800-second approval
with current attendance and usable physical Download. The first preapproval
D0 reached its 300-second freshness boundary during admission, so one fresh
fixed D0 completed before opening the first grant. The earlier read and exact
operator response were preserved; no consent, budget or effect was renewed.

## Host cue incident and first response

The planned cue caller did not issue a cue. At N+44.286 seconds, the root host
wrapper supplied unsupported `stdout_limit`/`stderr_limit` keywords to
`acquire_command`; Python raised TypeError before entering that function or
spawning the reviewed caller. That first failure is retained as a retrospective
structured note from the observed host tool result, not presented as a raw
child-process capture. The actual API keywords are `stdout_maximum` and
`stderr_maximum`.

The corrected caller was invoked once at N+67.492 seconds. Its stdout, stderr
and return code were sealed before interpretation. It refused in
`owner-guard-initial` with `cue needs more than 60 seconds`. No cue/resolution
record, notification, sound or physical reconnect instruction was created.
There was no caller retry after that refusal, deadline extension or device
transition replay. This was an avoidable host orchestration error, not a
reason to weaken the existing cue window or interrupt the original owner.
The operator was informed and told to leave the device as it was.

The first authenticated response subsequently completed at **N+116.258
seconds**, within the original 120-second window. The fixed RAM Debian SysVinit
PID 1, observer and zero block devices were verified, with fresh recovery-child
arm evidence. The same owner therefore continued its authorized research path.

After ML047, the operator recalled probably reconnecting the cable during
ML044 after watching the screen and experiment progress. The run log contains
no contemporaneous report or timestamp for that physical action. The
N+116.258 timestamp dates the authenticated response. Whether USB would have
appeared with the cable untouched remains unknown.

## Physical functional evidence

The same-boot witness advanced 300.334 host seconds and 300.450 guest seconds.
One durable module permit followed, and its complete authenticated result
arrived at N+420.522 seconds. The permit-intent-to-result interval was 1.923
host seconds; this is not an instrumented kernel execution duration.

The actual result establishes:

- Pre-stop HCE/HCS/IS were `0x1` / `0x10f` / `0x400`. The exact pre-stop CTL
  configuration and IO latch-high predicates passed. These are register checks,
  not electrical pad measurements.
- One HCE-zero write observed full zero in one poll within the original bounds.
  Handoff flags were `0x1fff`; reported software interval was 2 microseconds,
  not an electrical reset-latency measurement.
- Initial HCS `raw & 0x39` was `0x8`, with the V8/V9 hazard mask passing. Both
  doorbells, both RUN registers, IE, the exact pending-IS admission, AHIT and
  both post-stop pin checks passed. All eleven observed bits were set and no
  failure bit was set.
- Initial acknowledgement flags were `15`: PENDING, write committed, readback
  observed and zero observed. The exact reviewed control flow requires fresh
  full HCE zero and IS `0x400`, one constant `0x400` store, then a timely whole
  IS-zero readback before continuation. The readback is physical progress; it
  does not identify the original completion event or prove that the write
  caused the observed zero.
- Eleven fixed RPMh records were claimed, triggered and acknowledged, with
  matching masks `0x7ff`, no reclaimed slot and no reported power error.
  PHY readiness was set, and the module reached stage six after the existing
  reset, PHY and symbol-clock preparation returned successfully. This does
  not establish electrical pulse efficacy or complete UFS initialization.
- Stage six returned errno 5 (EIO), with `hce_started=1`, **zero local UIC
  commands and no link command**. Initial stage-two evidence remained intact.
  Therefore the UFS link result remains NO_PROOF.

The retained source narrows that final tuple to the first HCI_CFG1 check in
`g0q_hci_link_once`: it sets the software `hce_started` flag, writes bit 0 at
HCI_CFG1 (`0xdc`), then returns EIO if the readback lacks that bit **or** the
module budget check fails. Other EIO sites require at least one local command;
the earlier quiescence and pre-enable checks return different errors. This is
a source-based inference, not a new MMIO observation. The flag is set before
the actual HCE-one write, so it does not prove that HCE was restarted. The
reported tuple does not distinguish the two short-circuit alternatives or
contain the raw HCI_CFG1 value. No new read, write, retry or speculative change
was performed to resolve that question in this consumed run.

The bounded functional criterion was met: V9 admitted the old refusal,
performed its one bounded acknowledgement, observed timely zero and reached
later hardware preparation. Why HCE stop left a completion indication, whether
it was the same event, and the exact cause of the new stage-six refusal remain
unproved. The later strict IS-zero checks and fresh-completion requirement are
still necessary; this result does not justify ignoring completion status.

## Return, health and raw audit

The complete negative result selected the unchanged authenticated return path.
The host rederived its exact result digest, control, acceptance ACK and EOF.
Exact Download admitted the sole original-A transfer at N+447.765 seconds.
This demonstrates normal return after this completed new refusal; it does not
exercise timer or hung-probe/kernel recovery. Conditional unattended F1 remains
inactive.

The first final-health bracket contained one failed ADB read with return code
1. Both streams and status remain preserved. The raw-complete A transfer was
not replayed. The same executor entered its existing recovery-health step and
passed seven fresh health reads. It removed the owned network profile and
verified absence. There is no unresolved F1 owner. The terminal's recovered
flag records health continuation, not a physical Download action.

Canonical seconds from grant opening are distinct from the N-launch times
above. The observation-complete label does not mean UFS success.

| Event | Seconds from grant |
| --- | ---: |
| Live session start | 0.000 |
| N transfer start / complete | 24.775 / 26.628 |
| Candidate observation step complete | 459.375 |
| Original-A transfer start / complete | 472.447 / 474.306 |
| Final health / durable session end | 520.611 |

After the durable healthy terminal and owner release, the unchanged reviewed
paged H0 finalizer and offline audit ran with command acquisition, socket and
process creation blocked. They reopened **586 raw captures across three
pages**, verified the original source snapshot and canonical timeline,
rederived base/witness/result/return, and confirmed one N and one A total,
seven final health reads, profile cleanup and no owner. The preserved ADB
failure and two expected profile-absence observations were the only nonzero
producers in that task index. The separate sealed cue refusal was reopened
and classified explicitly. Closure/audit performed no device effect.

Private evidence is under
`workspace/private/outputs/s22plus-ml044-uic-status-h0-20261111-1/`, including
`task-1/closed.json`, `task-1/timeline.json`, `task-1/raw-index-v2.json`,
`run-audit-1.json`, `attach-caller-failure.json`, the sealed cue refusal,
immutable capability/review/source records, the actual operator response and
both fixed D0 observations. ML043 and all earlier consumed records, A90, S20+
and unrelated candidate-manifest/attachment work remain unchanged.
