# S22+ P441 watchdog/idle comparison design

## Bounded task and completion

Continue the operator-requested physical watchdog comparison after P439 recovery
and P440 retrieval. Prepare matched automatic-Debian variants using the existing
FYG8 diagnostic kernel, modules, Debian startup and bounded watchdog observer.
The selected first physical candidate adds only `cpuidle.off=1` to the retained
boot command line. The matched default variant has the same observer and root
history. Neither consumed P437 nor its seven-actor build is a matched control.

The functional aim is continued rcS/service execution through multiple stock
watchdog renewals, followed by same-boot authenticated SSH and fixed shutdown.
Report these facts separately. A single successful idle-disabled boot would not
establish idle policy as the cause of the old reset. Detailed causal diagnosis
is not a prerequisite for a useful working Debian capability.

## Evidence and exact change

[P440](S22PLUS_AUTOBOOT_EVIDENCE_P440_RUN_2026-10-20.md) authenticated the complete
P437 early/runtime pair after the separate P439 journal recovery. The early file
equals P438's prior capture; runtime reaches rcS entry and fork only. The new
`post-autoboot-p440-v1` selection adds exactly these two files to the three
previously qualified historical rows. Paths, root-owned 0600 single-link
metadata, lengths and hashes come from the closed P440 reader. No wildcard or
new mutable-directory rule is introduced.

Both existing same-boot complete clean protected-root admissions remain
mandatory. P439's incomplete full-root result stays RECOVERY_NOT_PROVED.
Historical retrieval and aggregate entry counts do not replace current
admission. A dirty or unexpected root stops before the first writable lifetime.

The [stock comparison](S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md) resolved
the retained kernel's `cpuidle.off` parameter and its default WFI branch.
No kernel build is needed. Packaging must positively bind either the unchanged
retained command line or that exact appended argument, reject duplicate or
conflicting idle arguments, and preserve every other retained header field,
kernel byte and signature byte except the existing ramdisk sizing/offset rules.
The actual boot and vendor-boot inputs must be checked for conflicting options.

The [inactive observer](S22PLUS_WATCHDOG_OBSERVER_H0_2026-10-19.md) is selected
explicitly in both variants. Its existing rcS and runlevel parents observe one
uniquely identified `gh-watchdog` kernel thread through bounded proc reads.
It adds actor eight, at most five opportunities per owner before 12.5 seconds,
250 ms total proc work per owner, and shares the existing 2000 ms logging budget.
No new process, pet/control write, scheduler setting, persistent output,
workload prerequisite or lifetime is added. Observations can perturb timing;
CPU ticks and wait-symbol classes do not prove a pet, timer/IPI/SMC phase or cause.

## Qualification and authority

Preserve historical selectors and outputs. Exercise the actual enabled ARM64
producer and consumer, normal startup and representative failure paths,
history mutation/rejection, command-line binding and matched packaging.
Retained evidence is reusable only where its relevant inputs remain unchanged.
No VM result establishes Samsung watchdog or idle behavior.

Prospective common details, root digest, target and automatic-boot policy must
adopt the exact selection and observer before independent review of the changed
execution-critical closure. Review and H0 qualification grant no device action.
The physical candidate requires its own returned attended one-operation,
3600-second grant under the existing automatic-boot lane.

Retain two bounded filesystem lifetimes, the absolute 300000 ms device deadline,
360-second host window, 120-second local service observation, one NCM attempt,
pinned same-boot SSH, one fixed shutdown and one physical original-A return.
There is no claimed automatic recovery or proof of quiescence. Uncertain effects
never replay. Final Android32 health and durable closure are required; original
A does not undo native_data writes. Later retrieval or replay remains separate.
A90 and S20+ are outside this task.

The initial private preservation record is
`workspace/private/outputs/s22plus-autoboot-watchdog-p441-h0-20261020-1/baseline.json`.
It preserves all 46 pre-existing dirty paths before implementation.
