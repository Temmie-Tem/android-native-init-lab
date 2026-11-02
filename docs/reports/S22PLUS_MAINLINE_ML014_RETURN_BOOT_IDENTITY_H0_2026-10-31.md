# S22+ ML014 return-boot identity H0

Status: **Qualified and independently reviewed; fixed preapproval D0 passed;
the separately approved physical run is now consumed and closed healthy**.

The [2026-11-03 run](S22PLUS_MAINLINE_ML014_RUN_2026-11-03.md) returned no V10
or USB/PID1 proof. Readiness captured the same Android boot ID before and after
the return-health ADB disappearance; one health-only continuation closed
healthy. This preparation's sources and qualification records are unchanged.

ML012 and ML013 each returned a complete retained log with no candidate
records, after an original-A health read lost ADB and a later health-only
continuation closed healthy. Neither abandoned properties prefix contained a
boot ID. Those records cannot distinguish a different Android boot from loss
of transport within the same boot.

Two-round Claude/Argon discussion selected a fresh V10 candidate with the
same GPIO reservations and runtime observation. The host now reads `boot_id`
first in the existing readiness and properties commands, only during mainline
original-A return health and its existing continuation. Successful lexical
EOF prefixes remain not-ready within the original bounded wait. A complete
UUID and completion value are required for readiness; the seven-read exact
target, same-boot and partition-digest health requirements are unchanged.

The selected class does not inherit the other native profile's in-call
root-read reobservation exception. Preapproval, preflight, post-closure D0,
loader comparison and other native profiles retain their existing commands.
No new connected command, root snapshot prelude, transfer, replay, watchdog
operation or Linux storage access is added. Original-A recovery never depends
on diagnostic continuity or retained-marker results.

An auxiliary early `last_kmsg` read was deferred: it could capture an earlier
snapshot, but would add a new recovery-time root read, cumulative budget,
once-only state and authority scope before a distinct return boot has been
observed. This is a sequencing choice, not a gate on future research.

## Evidence limits

Readiness IDs carry the exact serial/inventory binding, without an additional
topology read. An abandoned properties prefix carries only its actual captured
prefix and preceding checks. Neither is health. Offline analysis must retain
that distinction and must not combine a prefix with a new health attempt.

The earliest observed Android boot need not be the earliest actual return
boot. Different observed IDs do not prove candidate frames existed or were
erased. Equal IDs do not diagnose the internal cause of an ADB disappearance.
The existing ML011/ML012/ML013 logs contain respectively 0/63/53 matching
Android service-start strings; those unjoined content positions establish no
post-transfer chronology. The source-matched frozen-snapshot model is not
proof of the currently loaded module's complete binary identity.

Positive V10 records remain at-least-once site occurrences. Missing records
locate no failure and establish no GPIO-correction effect, last invocation or
same-boot pairing. This observer change does not fix kernel boot or retention.

## Validation and authority

The focused return tests exercise every readiness truncation offset, every
truncated first properties read against a complete final bracket, malformed
outputs, vanished/error producers, bounded waiting, unchanged health
projection and normal/recovery route selection. Existing target and adapter
tests pass. The mainline test set's missing Unicorn dependency was resolved
using the retained private dependency path, and only that missing case was
rechecked; the earlier successful cases were retained.

Fresh kernel, initramfs, loader and repeated AP packaging passed. The new
kernel's `.text` and `.init.text` bytes, addresses and sizes match ML013;
candidate/key-dependent records and userspace identity are fresh. Qualification
includes 361 actual C cases, 30 independent hook cases, 14 real EL/MMU cases,
loader copy/entry cases, RAM PID1 virtual boot and offline raw revalidation.
The production proof consumer accepts the complete join and rejects ten
specific missing or substituted proof cases. Four complete retained ML013
health brackets rederive unchanged under the current checker.

Independent source and final exact-artifact review passed without findings.
The new return-identity capability and backend V22 receipts are published;
earlier reviews and consumed owners retain their original pins. The connected
stable terminal worker is unchanged. One fixed preapproval D0 attempt passed
the complete seven-read rooted Android health transcript and task freshness
validation. At preparation close, no candidate control, partition transfer or
grant had occurred; the later approved run is recorded separately above.
The applicable past-failure checklist rows are ARTIFACT, HOST, RETURN and
AUDIT: fresh producer/consumer binding, actual raw producer status, original-A
closure without replay, and bounded evidence interpretation. Unrelated
initial work remains unchanged. A90 and S20+ are untouched.

Private discussion responses, before/after external-model usage, selection,
build and test evidence are retained under the existing private output tree.
The [mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md) still requires
the generated exact finite attended approval after completed preparation.
