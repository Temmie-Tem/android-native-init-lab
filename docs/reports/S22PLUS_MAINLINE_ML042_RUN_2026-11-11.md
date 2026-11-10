# ML042: HCE stop observed, post-stop HCS refusal, healthy Android closure

## Outcome

ML042 completed its one attended physical experiment across 2026-11-10/11 KST
and is consumed with **NO_PROOF / ANDROID_CLOSED_HEALTHY**. The reviewed V7
reset-configuration predicates admitted the initial HCE handoff. One HCE-zero
write observed full-word zero within the original limit. The next HCS predicate
refused, before fixed RPMh requests, the device-reset pulse, PHY preparation,
local UniPro commands or a link command. The authenticated negative result
selected automatic Download and one original-A transfer. Final health passed
through the same executor's existing health-only recovery after one failed
ADB read. No physical Download or connector continuation was needed.

The preceding [H0 work](S22PLUS_MAINLINE_ML042_RESET_CONFIG_H0_2026-11-10.md)
contains the two Mythos discussions, source limits, complete qualification and
independent PASS_GO with no findings. Its 102 focused tests passed without
skips. Commit `84ab7dabdc` records that reviewed capability and v43 backend.
Fresh fixed D0 health, the actual returned exact one-operation/1800-second
approval and attendance preceded dispatch. ML040/ML041 and every earlier
consumed candidate remain unchanged. A90 and S20+ were untouched.

## Functional evidence and limits

- The one attach cue was issued at N+39.631 seconds. The operator's actual
  completion reply was recorded at N+76.021 seconds, inside the original
  120-second window. The host notification and sound both completed at unchanged
  volume. The reply timestamp is not a measurement of physical reconnection.
- The authenticated base response completed at N+61.065 seconds. It proved
  the selected RAM Debian SysVinit PID 1, direct observer and zero block devices.
  Fresh recovery-child arm and late-liveness responses were verified.
- The same-boot witness advanced 300.376 host seconds and 300.507 guest seconds.
  Exactly one durable module permit followed. The result completed at N+365.440
  seconds, within the original research window.
- Pre-handoff HCE/HCS/IS were `0x1` / `0x10f` / `0x400`. The complete admitted
  prefix proves the exact CTL `0xb` and IO bit-0 high-latch predicates passed
  before the stop. Successful whole IO was not reported; upper bits and pad
  voltage remain unknown. Later post-stop pin checks were not reached.
- The handoff flags were `0x1fff`: one HCE-zero write, one readback of full
  zero and timely completion. The reported software interval was 2 microseconds,
  unsaturated; it is not a separate electrical or hardware-latency measurement.
- The next HCS read was raw `0x8`. Stage 2 returned HCI/QUIESCENT, errno 16,
  with post-check HCE PASS and HCS FAIL. Its later predicates remain UNOBSERVED.
  The retained kernel header defines `0x8` as UIC_COMMAND_READY, while the host
  and device error bits are `0x10` and `0x20`. The actual consumer currently
  requires all of DEVICE_PRESENT, UIC_COMMAND_READY and those error bits clear
  after handoff. This precisely explains the rejection; it does not establish
  that continued initialization would be safe or which actor maintains the bit.
- Fixed power-command counters and local-command count were zero, and no link
  command was issued. Stage-three reset and later PHY/HCE-start paths were not
  reached. No electrical reset efficacy, UFS device link or media access is proved.

The changed predicate therefore answered the selected physical question: it
allowed a bounded HCE stop, which actually completed. The next bounded H0
question is whether the existing post-stop HCS readiness requirement matches
this controller's disabled-state semantics. No predicate was changed after
the run, and this observation grants no retry or subsequent experiment.

## Return, health and closure

The host rederived the complete result-bound control, acceptance ACK and
connection closure. Exact Download admitted the sole original-A transfer at
N+393.053 seconds. This proves automatic return after this completed refusal,
including the newly executed HCE stop. It does not exercise the fixed timer,
recover an unresponsive probe/kernel, or activate unattended F1.

The first final-health bracket failed at one ADB read with return code 1. Both
raw streams and status were preserved. Raw-complete original A prevented any
transfer replay; the same running executor entered its existing recovery-health
step and passed all seven fresh reads. The owned NetworkManager profile was
removed and its absence verified. There is no unresolved F1 owner. The terminal
uses `recovered=true` because of that health recovery, not physical Download.

Canonical times below are seconds from grant opening, distinct from the N-launch
times above. The `candidate_boot_ready` event means the bounded observation step
completed; its scientific result remains NO_PROOF.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 23.842 / 25.663 |
| Candidate observation step complete | 403.635 |
| Original-A transfer start / complete | 416.828 / 418.689 |
| Final health / durable session end | 465.714 |

The unchanged, independently reviewed H0 paged finalizer ran only after the
durable healthy terminal and owner release, with process, socket and acquisition
entry points blocked. It preserved the original execution source snapshot and
published three bounded pages containing **537 raw captures**, then the close
record. The separate offline audit re-opened every raw stream and receipt,
rederived transfers, base/witness/handoff/return, final health and cleanup, and
confirmed one N and one A total. The only nonzero raw producers were the retained
ADB failure and two expected owned-profile-absence observations. Cue issue and
resolution captures were also re-opened, separately from the task raw index.

Private evidence is retained under
`workspace/private/outputs/s22plus-ml042-reset-pin-h0-20261110-1/`:
`task-1/closed.json`, `task-1/timeline.json`, `task-1/raw-index-v2.json`,
`run-audit-1.json`, the immutable task/capability/review, actual operator records,
source snapshots and the complete raw evidence. The original failed health
read remains in that record. No consumed artifact, approval or journal was edited.
