# ML043: disabled readiness admitted, completion-status refusal, healthy closure

## Outcome

ML043 completed one attended physical experiment and is consumed with
**NO_PROOF / ANDROID_CLOSED_HEALTHY**. V8 admitted the sampled post-stop UCRDY
bit and reached five later predicates, all of which passed. IRQ_STATUS then
refused raw `0x400`. No status clear or local/link command followed. The
complete authenticated negative result selected automatic Download and one
original-A transfer. The existing executor's health-only recovery passed all
seven final reads after preserving one failed ADB health read. Physical
Download and connector continuations were not needed.

[H0 analysis and review](S22PLUS_MAINLINE_ML043_DISABLED_HCS_H0_2026-11-11.md),
committed as `9fd5fa82f0`, records the two Mythos discussions, 113 passing
tests without skips, independent PASS_GO and fresh artifact qualification.
The operator returned this exact task's one-operation/1800-second approval
with current attendance and usable physical Download. The earlier fixed D0
had become stale while awaiting that response, so one fresh fixed D0 completed
before the first grant, preserving the prior observation. This did not renew
or replay an operation. ML042 and all earlier consumed records stay unchanged;
A90, S20+ and the unrelated candidate-manifest edits were untouched.

## Physical evidence

The one attach cue occurred at N+32.583 seconds, accompanied by a successful
host notification and sound at unchanged volume. The actual completion reply
was recorded at N+79.397 seconds. Both fit the original window; the reply time
does not measure the physical reconnection time or prove its causal role.

The authenticated base response completed at N+57.373 seconds. The exact RAM
Debian SysVinit PID 1, observer and zero block devices were verified, together
with fresh recovery-child arm/liveness evidence. The same-boot witness advanced
300.344 host seconds and 300.428 guest seconds. One module permit followed,
and its complete result arrived at N+361.693 seconds.

The result distinguishes these phases:

- Before handoff, HCE/HCS/IS were `0x1` / `0x10f` / `0x400`. The admitted prefix
  establishes the exact CTL `0xb` and IO bit-0 high-latch checks passed at that
  time. It does not report whole IO or electrical pad voltage.
- One HCE-zero write observed full zero in one poll within the original
  one-ms/module deadlines. All handoff flags were set (`0x1fff`). Its reported
  software interval was 4 microseconds, not an electrical-latency measurement.
- The initial post-stop HCS sample was `raw & 0x39 == 0x8`: UCRDY set, with
  DEVICE_PRESENT and the existing two error indicators clear. This is a masked
  sample, not a report of the full HCS word. V8's `0x31` failure predicate passed.
- Transfer and task doorbells, transfer and task RUN, and interrupt enable
  subsequently passed their whole-word-zero predicates. IRQ_STATUS then read
  full raw `0x400` and failed. The observed mask was `0xff`, failed mask `0x80`,
  stage 2 / HCI / QUIESCENT, errno 16. Auto-hibernate and both post-stop pin
  predicates remain unobserved because the original short-circuit order stopped.
- Fixed power-command counters and local-command count were zero, and no link
  command was issued. The device-reset pulse, PHY preparation and later HCE
  initialization were not reached. No additional status write or retry occurred.

The selected `ufshci.h` defines `0x400` as UIC_COMMAND_COMPL. Its presence both
before and after the stop does not identify the event's origin, establish that
the same event survived, or measure a clearing delay. The existing post-stop
predicate requires the whole interrupt-status word zero; that condition
explains this refusal. It is not proof of a hardware fault. No completion bit
was cleared to continue. Its semantics and any prospective change are the next
bounded H0 question, not part of this consumed run.

The experiment met the bounded progress criterion: an authenticated V8
readiness sample was admitted and later conditions were actually evaluated.
ML042's full-word `0x8` and this run's masked sample both show UCRDY set in
their respective samples; they do not establish a persistent property or its
internal cause. UFS link and media access remain unproved.

## Return and raw audit

The host rederived the complete result-bound control, acceptance ACK and
connection closure. Exact Download admitted the sole original-A transfer at
N+389.384 seconds. This exercises automatic return after the completed new
refusal. It does not exercise the timer or prove recovery of a stuck probe,
dead PID 1 or failed kernel; conditional unattended F1 remains inactive.

The first final-health bracket contained one ADB read with return code 1.
Both streams and status remain retained. Raw-complete A prevented replay;
the same running executor entered its existing recovery-health step and
passed all seven fresh reads. The owned NetworkManager profile was removed
and absence verified. There is no unresolved F1 owner. The terminal's
`recovered=true` records this health recovery, not a physical Download action.

Canonical seconds from grant opening are distinct from the N-launch times
above. The observation-complete event does not mean UFS success.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 24.691 / 26.512 |
| Candidate observation step complete | 400.703 |
| Original-A transfer start / complete | 413.991 / 415.854 |
| Final health / durable session end | 462.253 |

After the durable healthy terminal and owner release, the unchanged reviewed
paged H0 finalizer and offline audit ran with process, socket and acquisition
entry points blocked. They reopened **542 raw captures across three pages**,
verified the source snapshot and canonical timeline, rederived the actual
base/witness/result/return, and confirmed one N and one A total, seven final
health reads, profile cleanup and no owner. The only nonzero producers were
the preserved ADB failure and two expected owned-profile-absence observations.
Cue issue/resolution captures were separately reopened. No device effect was
performed by closure or audit.

Private evidence is under
`workspace/private/outputs/s22plus-ml043-hcs-ready-h0-20261111-1/`, including
`task-1/closed.json`, `task-1/timeline.json`, `task-1/raw-index-v2.json`,
`run-audit-1.json`, immutable task/capability/review/source records, actual
operator responses, both fixed D0 observations and complete raw evidence.
