# S22+ ML015 existing V2 early-marker calibration

Status: **Qualified and independently reviewed; fixed preapproval D0 passed;
the separately approved physical run is consumed and closed healthy**.

The [ML015 run](S22PLUS_MAINLINE_ML015_RUN_2026-11-03.md) recovered neither V2
record and no USB/PID1 proof. Observed return boot IDs agree; one health-only
continuation closed after a readiness-read failure. This preparation and the
reused capability/backend records retain their original provenance.

ML014 returned no V10 records while its observed Android boot IDs agreed
across the return-health ADB disappearance. That closes an observation gap
without explaining marker eligibility, earlier unseen boots or retention
loss. Two-round Claude/Argon discussion selected a fresh candidate using the
already adopted V2 format, whose two early sites were physically observed in
[ML004](S22PLUS_MAINLINE_ML004_RUN_2026-10-30.md).

V2 places one MMU-off assembly record at the start of `__primary_switch`,
before `__enable_mmu`, and one MMU-on C record immediately after
`early_ioremap_init`, before `setup_machine_fdt`. The latter is the source
site of V10's first event, with the existing independent per-call writer.
The two 128-byte slots preserve the four-word Samsung header and require
their existing eligibility and stability checks. No new format or mixed
V2/V10 writer is introduced.

The exact corrected ML014 DTB and kernel configuration are retained,
including GPIO reservations 36..39, 50 and 93. A clean copy of the retained
ML012 unmarked base supplies the kernel source; V10 hooks in `main.c`,
`dd.c` and `pinctrl-msm.c` are absent. A fresh key, candidate identity,
initramfs and exact boot package replace the consumed ML014 artifacts.

The mainline capability, ML014 return-identity observer, backend V22 and
stable worker are reused while their reviewed hashes remain unchanged.
Fresh candidate qualification and independent exact entry/artifact review
remain required. The existing finite attended grant, original-A recovery,
complete seven-read health, health-only continuation and post-closure D0
collection rules are unchanged. No new capability receipt, policy gate,
watchdog operation, Linux storage access or GPIO reversal is selected.

## What the experiment can establish

| Retained V2 result | Bounded interpretation |
| --- | --- |
| Both sites | Each committed point occurred at least once in this candidate and its record survived to collection. |
| Pre-MMU only | Pre-MMU occurrence is observed; the C point remains unproved. |
| Early-C only | The guarded MMU-on C commit point is observed; the pre-MMU point remains unproved. |
| Neither | Both points remain unproved in this candidate. |

Records need not belong to one boot or invocation. None proves the writer's
later return, the last attempt, a stop location, RAM-userspace PID1 or USB.
A positive result cannot isolate the cause of earlier V10 zeros across
different candidates and trials. A zero cannot exonerate V10 in those earlier
runs or establish GPIO, kernel, firmware or retention causality.

V2 and V10 have different eligibility and window calculations, so equal
physical slot placement is not assumed. Pre-FDT source ordering also does
not isolate retention: later candidate or firmware activity can affect an
earlier record before collection. These limits are evidence interpretation,
not new runtime or approval gates.

## Preparation and checks

The clean-base check verifies all five previously instrumented source files
against the unmarked baseline. After V2 generation, `main.c`, `dd.c` and
`pinctrl-msm.c` remain byte-identical to that baseline. DTB and configuration
equality with ML014 are checked directly. Fresh physical and VM initramfs
builds completed. Fresh qualification passed 171 assembly and 159 C cases,
three assembly exception-level cases and eleven whole-kernel MMU cases,
loader copy/entry checks, RAM PID1 virtual boot and offline raw revalidation.
Both generated AP/boot packages agree. The current production consumer accepts
the fresh V2 proof join and rejects four missing or substituted proof cases.

Independent source/reuse assessment passed without blockers. It confirmed
the clean ancestry, preserved boot arguments and pre-MMU scratch-register,
link-register and flag liveness against matching historical source/toolchain
evidence. Final independent exact-artifact review passed with no findings,
binding 93 unchanged sources and 271 artifact/raw evidence pins. Eight
selected linked functions match ML004 in bytes, address and size.

Private production admission reused the existing capability/backend receipts
without modifying them or the worker. One fixed preapproval D0 attempt
completed the required seven-read rooted Android health and fresh task
binding. At preparation close, no experiment grant, candidate control or
partition transfer had occurred; the later approved run is recorded above.

The retained ML011/ML012 layout comparison found unchanged kernel/DTB
destinations and entry-related symbols, with small payload-size and trailing
buffer shifts already covered by the original range checks. It is not a
whole-image claim that only DTB bytes changed. Fresh V2 bounds must be checked
because removing V10 changes the embedded image layout.

The bounded ML011–ML014 text census supplies no unique boot identity or
transfer-time join. Its service-start counts do not diagnose an intervening
boot and create no reason for another heuristic gate. No further content
analysis is a prerequisite for this candidate.

Applicable past-failure checklist rows are ABI, ARTIFACT, WIRE, SEMANTIC and
RETURN: exact call-site/register/mapping behavior, fresh producer/consumer
binding, positive-only interpretation and independent original-A closure.
Private discussion, usage accounting, source checks and build evidence are
retained in the existing private output tree. A90 and S20+ are untouched.
