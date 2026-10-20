# S22+ P446 single-CPU candidate: implementation and H0 validation

Target: operator-owned `SM-S906N` / `g0q` / `S906NKSS7FYG8`.
Scope: host source, build, regular-file VM fixtures and independent review.
No device read, transfer, control, partition write or grant occurred.

This implements the [P441/P445 decision](S22PLUS_P441_P445_COMPARISON_NEXT_EXPERIMENT_H0_2026-10-21.md)
as `p446` / `v0.15.0-rc.0`. Its intended functional variable is `maxcpus=1`
on the P441 proc-observer startup path. The current native_data state after
P445 remains unknown. These H0 artifacts are **not an activated capability
or a device-ready candidate**.

## Exact candidate and evidence

The retained FYG8 kernel, 82 modules, Debian initramfs initial PID1, installed
SysVinit, services and first NCM attempt remain. The boot header adds exactly
`cpuidle.off=1 maxcpus=1`; CPU-option conflicts and a kernel/init argument
separator in the retained boot/vendor command lines reject the selection.
The sealed vendor bootconfig has no competing kernel/CPU option.
P445 phase probes, the RAM rcS dispatcher and phase timing adapter are absent.
The candidate uses a distinct observer declaration naming the actual
`post-autoboot-p444-v1` history while retaining P441's proc observation.

Both complete root admissions remain. Seven historical files are permitted:
the previous five and the two P441 files authenticated by closed P444.
The immutable table contains 8976 rows. No P445 file, prefix wildcard, new
mutable path, repair or replay is admitted. The absolute 300000 ms device
deadline, two fixed writable lifetimes, file/record bounds, 360-second host
window and physical original-A recovery requirements remain.

Necessary differences from the retained P441 artifact are explicit:

- Fresh run/key/candidate seals and the two authenticated historical rows.
- `maxcpus=1`, while retaining P441's `cpuidle.off=1`.
- Fixed CPU/watchdog reads and revision-6 interpretation of an existing
  durable progress field; no extra file, process, daemon or kernel probe.
- Fixed health output for CPU online state and uptime, and two sampled SSH
  responses separated by at least 120 device seconds.
- H0 producer/consumer, source closure, failure fixtures and qualification
  changes needed to bind those differences.

## Opus concerns and actual target checks

All 82 selected module ELFs were hash checked and scanned for direct CPU
online/offline imports. None were found. The 54 sealed Debian init.d/rc/default
regular files contain no CPU-online writer match. This is a bounded static
screen, not proof against indirect hotplug. The kernel supports hotplug;
`maxcpus=1` does not disable it.

The runtime requires `/sys/devices/system/cpu/online` to equal `0\n` before
the first admission, before the second admission, and before/after every
watchdog observation. The existing 15 durable progress samples cover rcS
entry/completion and 13 service checks across 120 seconds. Both SSH endpoints
also require the actual CPU online list to be `0`.

The actual FYG8 `qcom_wdt_core.ko` contains the `disable` attribute/getter,
but does not contain the optional `pet_time` or `user_pet_enabled` attributes.
The source's optional interface is therefore not used. Before second
admission and on each progress sample, the candidate reads the fixed
`hypervisor:qcom,gh-watchdog/disable` attribute and requires `0\n`.
There is no watchdog, hotplug, scheduler or firmware-control write.

The authenticated revision-6 `PROGRESS.c` value is exactly 257: CPU0's online
mask plus the driver-enabled bit. Reserved bits or a missing observation
reject the chain. The record remains 128 bytes with the existing HMAC,
sequence/deadline checks, fsync and readback. Legacy revisions 4/5 still require
zero in this field. Post-return prefix retrieval selects revision 6 explicitly.

These facts establish sampled CPU state and **driver software enabled state**.
They do not prove hardware pet/reset success, uninterrupted CPU-online state
between samples, or a particular IPI failure. No exposed reliable pet counter
exists in the selected module; the source's `last_pet` can advance after an
unchecked backend reset result. It is not promoted to hardware pet proof.
The pre-admission observations are gates; the durable evidence starts at rcS.

SSH retains the existing forced `health` command and total 30-call bound.
The initial response is checked immediately; both responses are finally
rederived against the independently authenticated runtime boot and boot count.
Their kernel uptime difference must be at least 120 seconds, with each below
the original 300-second deadline. This proves two sampled reachable endpoints,
not one continuously connected SSH session. No deadline is renewed.

The new checks apply only to this candidate's one-CPU/driver-enabled proof.
Their hazard is accepting a CPU-limit failure, silent software disable or
stale/incomplete evidence as a positive result. They are reconsidered when
this candidate, its exact module ABI or its proof criterion changes; they are
not a new gate for other candidates or targets.

## H0 validation and independent review

The final physical A/B initramfs and boot-only AP are byte identical between
their two builds. The actual CPIO, module set, immutable table, boot command
line, unchanged kernel/carrier fields and source closure pass the existing
producer/archive consumers. `package-2/qualification.json` records
`PASS_H0_ARTIFACT_AND_VM`.

All **22 real ARM64 VM cases pass**. The generic VM exposes eight CPUs; with
the candidate argument its actual kernel boots one CPU. The normal case
records 15 revision-6 platform samples and full installed-init/cron/sshd
service evidence. Its SSH observations are at 19.940 and 140.510 seconds,
**120.570 seconds apart**, with CPU0 alone at both endpoints. Fixed shutdown
leaves clean ext4, readable home data and durable boot count. The second
admission begins at 8.399 seconds and reaches `ROOT_ELIGIBLE` at 14.617 seconds;
the original deadline is retained. This is measured VM timing, not an
eightfold estimate from the physical P441 timing.

The unlimited-CPU negative boots eight real VM CPUs and rejects before any
disk change. The disabled-watchdog model rejects before installed execution.
All eight P441 history missing/changed/link/mode cases, dirty/unknown/history
and existing-file refusals, changed receipt, leaked fd, module error,
second-admission failure and rcS record failure pass their negative predicates.
Network absence preserves authenticated local service proof while explicitly
claiming neither SSH nor clean shutdown; its external VM stop is not recovery
evidence. All cases preserve storage outside the native fixture.

Validation also passes 126 focused autoboot tests, 8 legacy durable-evidence
tests, 12 repository-boundary tests, touched-Python compilation, actual ARM64
sampler execution, `file` checks and the repository boundary/diff checks.

The first independent Opus 5.5 review requested changes. Its variable pet-time
stability concern is superseded by the actual-module correction and the exact
constant observation above. CPU checks at SSH endpoints, an accurate history
declaration, the complete P441 history-negative set, receipt/fd negatives and
slower initial SSH retry spacing were incorporated.
The second review returns `PASS_H0_REVIEW`, conditional on the final VM and
archive results above. Its remaining advisory about the fixed sysfs interface
was settled in H0: the actual 112-byte getter loads the enabled boolean,
inverts it and formats `%d\n`, confirming `0\n` means software enabled. Four
retained exact-target device-name lines, verified capture/healthy closure,
and the kernel's device-printk/bus-link code establish the selected platform
device name and sysfs path. This does not claim a current live read.

Retained legacy provenance was checked separately. The existing P441 normal
VM proof rederives exactly through the current consumer. Rebuilding the
physical P441-selection hook with its original generated headers produces
an ELF **byte identical** to the retained P441 hook. The H0 helper `audit()`
callers are fresh builder/packager paths; retained live image/proof consumers
do not replace historical source receipts with current working-tree bytes.
No retained review, manifest, artifact or consumed action was repinned.

Private evidence root:
`workspace/private/outputs/s22plus-autoboot-singlecpu-h0-20261021-1/`.
The initial build/partial VM corpus is preserved as superseded after the
actual-module attribute check; it is not used for final qualification.
Final evidence is in `build-2/`, `vm-2/`, `package-2/`, `review-2/`,
`legacy-compatibility/` and `interface-path/`; `completion.json` binds them.

## Physical status and interpretation

No target contract adoption, registry registration, activation binding or
attended grant was created. A future physical owner must resolve the unknown
P445-era data/history using the existing authorized profiles, then satisfy
the applicable policy, artifact/current-root, review, health and recovery
conditions. H0 results do not authorize that work.

A successful future run would provide bounded single-CPU Debian functionality
and evidence of a multicore dependency. It would not isolate an IPI callback
as the cause: load, timing, affinity and scheduling also change. Missing or
invalid records remain `NO_PROOF`; healthy Android return remains separate.
A90 and S20+ were untouched.
