# S22+ P432: Debian-owned autonomous startup to services and SSH

Status: **H0_DESIGN_SELECTED**. The operator requested implementation through a
physical experiment on 2026-10-16 KST. This design opens no device grant.
Only S22+ FYG8 is selected. P430/P431 remain consumed and closed healthy.

## Bounded objective

Build one fresh `debian-autoboot-v1` candidate, prospective P432
`v0.8.0-rc.1`, that starts with Debian as actual initial PID1, prepares the
hardware and storage without host requests, enters installed Debian, starts
ordinary services and the fixed USB NCM link, and supplies authenticated
same-boot SSH evidence. Preserve bounded local progress when USB is absent.
Reuse the retained FYG8 kernel, installed root, module bytes and order proved
by P430, and the existing exact original-A transfer/recovery machinery.

The [code audit](S22PLUS_DEBIAN_BOOT_FLOW_CODE_AUDIT_2026-10-16.md) is the basis.
There is no new resident native manager, second native boot environment,
installation, formatter, journal replay or kernel change in this unit.

## Device sequence and ownership

```text
Debian /init, initial PID1
  -> supervised storage-first preparation, 76 modules
  -> clean protected root admission
  -> bounded early record and six client insertions
  -> checked close/unmount/RO restoration, exact-child collection
  -> exec temporary autonomous PID1 entry
  -> complete protected current-root admission including owned early output
  -> installed-root RW activation and Debian-internal root transition
  -> installed SysVinit / rcS / rc2 / cron / sshd / first USB NCM gadget
  -> bounded local service observations, then normal installed PID1 lifetime
```

Use the P430 preparation order once. The second admission performs no repeated
module insertion. Its extra-file accounting accepts the exact early output
produced by the settled first phase, alongside immutable historical records.
The existing child, source, mount, descriptor and root-identity checks remain.
The old three-native-worker state and host ACM descriptor are not prerequisites.

The early writer retains its checked write/sync/readback, 16 KiB maximum and
successful cleanup prerequisite. Its successful final RAM receipt is published
only after the fixed unmount, protection and clean/GPT post-checks. The initial
PID1 must receive a successful settled child result and verify this receipt
before entering the next phase. Missing or uncertain cleanup parks the boot.
Two precisely owned native_data writable lifetimes are therefore selected:
the early evidence lifetime, then the installed Debian lifetime. Neither can retry.

Root transition here is the same Debian boot moving from its RAM root to the
installed filesystem. Initial and installed PID1, source measurements and all
local records must join one kernel boot. No host START, CONTINUE or RELEASE
is required for automatic preparation, installed init or service startup.

## Filesystem and evidence composition

Keep all installed immutable-root checks. Bind the already captured P430 file
as an exact historical regular file by path, metadata, size and digest in the
new candidate's sealed admission data. Do not delete or rewrite it. New known
historical inputs remain declarative qualified data, not an unrestricted path
or wildcard allowance. Normal boot-count data receives canonical bounded
numeric validation rather than the historical literal `1` predicate.

The new early record and installed-service record have distinct sealed names
under `var/lib/lab`, each at most 16 KiB. Reuse their existing authenticated
formats where possible. Do not let two creators own the same filename or append
one format to another. The second root admission verifies the new early file
against the authenticated, checked RAM copy/receipt from its exact producer;
creating that normal output must not make the same operation inadmissible.
Installed-service records retain the exact run, boot, source and stage chain.

Only the already scoped Debian service data plus these declared records may
change. Initial writes remain below the absolute 300-second kernel BOOTTIME
limit. The prospective automatic startup/observation also uses a single
unrenewed device deadline; final selected constants and negative cases must
be explicit in the new capability. A completed file proves its own records,
not a later unmount, service, SSH or recovery result.

## Services, USB and host observation

Reuse the installed SysVinit, serial rcS/rc2 ordering, exact service checks and
bounded local evidence. Remove the observer's network prerequisite from boot:
network setup runs as a Debian startup service before the 120-second service
observation completes. There is one first `g1` gadget and one fixed NCM setup,
with no prior ACM gadget, second gadget object or retry after partial setup.
A network setup failure may leave local services/evidence useful; it must not
be labelled SSH success or automatically repeat the gadget effect.

The host observes the exact USB topology/NCM identity and pinned SSH key. Fixed
read-only commands collect health plus both bounded evidence records and join
the actual installed PID1, run and kernel boot. The host may perform only the
declared finite read-only polling. It sends one fixed shutdown only after the
required authenticated service/SSH proof; an uncertain shutdown never retries.
All outgoing control and transfer intents remain journaled before dispatch.

Normal completion uses the existing attended physical Download/original-A
return and full Android32 health. A bounded host window ends with physical
recovery on absent/partial evidence, with powered device activity unknown.
No software timeout is presented as cancellation of a blocked kernel call.
If SSH cannot retrieve local records, an independently prepared fixed mountless
reader may retrieve the two sealed files after complete Android closure. That
reader has a separate fresh candidate, finite grant and original-A return.

## Review, authority and validation

This automatic effect sequence needs its own common/target-adopted scope and
source-bound independent review. Candidate transfer owns all automatic effects;
the old integrated wire-start capability does not authorize them. Reuse exact
F1 exclusion, no-replay claims, target binding and recovery. Prepare a concrete
one-operation/3600-second attended task and, if needed, a separate exact reader
task only after complete qualification. Actual returned finite approval,
attendance and usable Download recovery remain live prerequisites.

Record and commit this architecture before implementation. Independently
review reachable changed machinery and the authority interactions. Existing
artifacts, reviews and consumed journals keep their original source provenance.

Qualification must cover actual physical argv, the actual packaged binaries,
storage-first order, old evidence admission, rejection of foreign/changed files,
owned-output admission, record-name separation, exact child settlement,
network absence and partial setup without retry, local service progress,
same-boot SSH, fixed shutdown and partial/failed evidence. Exercise real ARM64
producer/consumer paths and both production package validators. Reuse unchanged
checks and avoid rebuilding or replaying consumed physical candidates.

Applicable past-failure checklist: ABI and SEMANTIC for PID1/children/syscalls;
IO, WIRE and PERSIST for bounded local/SSH records; ROUTE and ARTIFACT for the
new owner and actual packages; HOST and RETURN for current execution and one
physical recovery; AUDIT for retained evidence. DISPLAY is outside this unit.

Completion is a qualified and independently reviewed fresh capability followed,
when its exact live prerequisites are satisfied, by one physical run and its
validated closure/report. Full service/SSH proof and healthy Android return
remain separate. A90/S20+ and unrelated working changes remain untouched.
