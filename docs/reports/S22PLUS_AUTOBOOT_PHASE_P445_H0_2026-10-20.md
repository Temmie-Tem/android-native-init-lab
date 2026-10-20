# S22+ P445 bounded watchdog and rcS phase qualification

Status: **H0 READY; independent PASS_GO; fresh fixed D0 preparation passed**.
Only `SM-S906N/g0q/S906NKSS7FYG8` is selected. No P445 grant, transfer, control
or native_data write has occurred. P441 through P444 remain consumed.

The [committed design](S22PLUS_AUTOBOOT_PHASE_OBSERVER_DESIGN_2026-10-20.md)
preserves Debian initial PID1, both protected-root admissions, installed
SysVinit, rcS/runlevel 2, 120-second services, same-boot SSH and physical
original-A return. P444's complete authenticated P441 pair adds exactly two
historical rows to the retained five, producing an 8,976-entry immutable
table. Historical retrieval does not replace either current-root admission.

## Implementation and proof limits

The existing rcS/runlevel parents own twelve fixed entry/offset kprobes in
the exact retained watchdog module, an initially absent tracefs group/instance
and one authenticated RAM handover. Exact function bodies, relocations,
register meanings, ARM64 instruction support and target trace producer
formats were independently checked. There is no return probe, memory fetch,
instruction skip, forced return, watchdog write or added process.

The parent verifies the two exact installed scripts and creates a RAM
dispatcher. Its immediate child retains one nonblocking datagram endpoint;
every invoked helper and service closes it. Fixed script IDs and begin/end/
status packets preserve the original serial workload. The parent drains
after reaping without interpreting datagram peer closure as EOF.

The physical start limit remains 8.5 seconds BOOTTIME, with a 15-second
event-admission/normal-pump cutoff. Twenty-eight kernel and 34 script records
share the existing authenticated logger limits. Timed parent phase work
shares 2000 ms including 500 ms cleanup reserve. The eight-CPU ring is at most
160 KiB. Shared time includes the handover gap; the child has its separate
actor logger budget. A blocked kernel call is not cancellable. First-opportunity
owned disable can follow a budget overrun; bounded cleanup may drain only
pre-cutoff events and summarize loss before verified removal. Missing cleanup
confirmation leaves instrumentation activity unknown until physical return.

Kernel event time and collection time remain distinct. Positive observations,
profile/missed counts, ring loss, retained-record gaps, script completion and
cleanup are separate. Per-event hits may exceed decoded events. Missing,
truncated or duplicate metadata does not become zero loss. A pet API return
does not prove hardware renewal; missing records do not locate a stall.

## H0 evidence and corrections

The actual C decoders run on host and ARM64. Generic ARM64 component execution
uses the retained P311 guest assets with a declared module-site adapter.
Normal execution produces twelve actual probe events and 24 profile hits,
with authenticated metadata and owned cleanup. It does not prove physical
watchdog callsites or electrical renewal.

Six partial-setup failures, actor-budget exhaustion, delayed handover, logger
loss, cleanup/registry failure, preserved foreign return-probe group and
missing/torn/stale handovers exercise the actual lifecycle. Two cases apply a
registration/arming write and then return EIO: occurrence remains consumed,
readback identifies owned state and cleanup does not replay setup.

Framing tests supply the exact target's 4095-plus-one-byte boundary through
the real drain's open descriptor. One completes all 26 records on that same
fd; the budget-limited case retains 25 and marks the lost tail/cap. These are
controlled target-shaped reads, not a claim that the generic kernel naturally
produced that precise boundary. Original failed fixtures, corrected fixtures,
raw output, executable hashes and matching historical source copies remain.

The first full Debian VM completed its protected root work after about
20 seconds, so the physical 8.5-second startup limit correctly omitted
observation. Functional progress did not waive the missing dispatcher proof;
the qualification was rejected. The declared full-VM adapter alone uses
58.5/65-second startup/window limits, guarded at compilation and bound to
`virtual=True` metadata. Raw BOOTTIME, two-second budgets and the 300000 ms
device deadline remain unchanged. The physical consumer still defaults to
15 seconds and rejects later observations. Diskless lifecycle fixtures use
the physical timing limits. Integrated VM timing is not physical eligibility.

The corrected normal VM authenticates 175 records from all eight actors and
all 34 dispatcher packets, including actual dispatcher entry and exit. rcS
completion, 120-second services, same-boot pinned SSH health, accepted fixed
shutdown followed by poweroff, clean ext4 and durable boot count pass.
The generic guest has two CPUs and no selected watchdog module; trace setup
correctly returns EPROTO before a trace effect, while the independently working
dispatcher continues. It supplies no kernel-phase metadata or losslessness
claim. Separate eight-CPU component runs cover kernel setup and cleanup.

Current checks: 76 observer tests, 31 related autoboot/host-owner tests and
12 boundary tests pass; the repository boundary check is clean.
The corrected physical build has identical A/B static ARM64 helpers,
initramfs and actual boot-only AP with 150 frozen runtime source files.
The actual archive consumer also rejects eight coherently repinned mutations
to idle options, hidden padding, header fields, kernel and signature.
All 57 integrated ARM64 cases pass, including the 54-case failure/history
batch and separately run network-absent and pending-child cases. The network
case authenticates local service completion directly from its original image;
it retains forced host stop and no SSH or clean-shutdown claim. The pending
child case requires the actual parent heartbeat and makes no child-completion
claim. No copied-image journal replay was needed. The final 57-case aggregate
is 1,385,871 bytes and reopens through the actual image consumer. Its final
AP and boot bytes match the paired archive used by the mutation checks.

Independent review is **PASS_GO**, with no open findings, covering the common/
target specialization, actual producer/consumer, lifecycle, 23 preserved
component executions, all 57 integrated cases and final package. The new
[P445 binding](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p445_review.json)
binds 140 host files and 150 runtime source files. Host and runtime snapshots
retain the exact reviewed bytes; no consumed predecessor binding is repinned.

Fresh fixed foreground Android D0 preparation passed current health, shell-v2,
GPT and Android32 capacity checks. The 57,778-byte task reopens through its
actual validator and selects one attended `debian-autoboot` operation for
3600 seconds. No grant, mode change, image transfer or native_data write
occurred; no F1 owner is open. These reads do not admit the current native root.

## Past-failure checklist applicability

| ID | Current finding | Evidence and remaining scope |
| --- | --- | --- |
| ABI | H0 checked; physical unproved | Exact target callsites/registers, producer text, page rounding and syscall ABI; actual ARM64 lifecycle/decoders. |
| IO | H0 checked | Same-fd partial reads, full/dead datagram peer, finite caps, applied-error writes and owned cleanup; blocked syscalls remain uncancellable. |
| SEMANTIC | H0 checked; physical unproved | API return, script entry, rcS completion, services, SSH and recovery retain separate predicates; normal VM proves services/SSH and controlled shutdown. |
| WIRE | H0 checked | Actual C authentication and rederived projections; per-event/profile and retained-count deficits remain explicit. |
| PERSIST | H0 checked | Raw fixtures, immutable source copies, restored exact historical source hashes and reopened final artifact/task; no new persistent observer file. |
| ROUTE | H0 checked | Phase selection reaches history, builder, decoder and retained-log routing; 57 actual VM cases pass, dispatcher packets join the normal VM and the VM-only time adapter is explicitly sealed. |
| ARTIFACT | H0 checked | Exact retained kernel/module identity; actual A/B helpers/initramfs/AP match and eight actual-AP mutations are rejected. |
| AUDIT | H0 checked | Failed attempts retained; no missing-return, pet-renewal or physical timing promotion. |
| HOST | H0 and fixed D0 checked | New P445 capability preserves consumed P441 binding; current Android health/preparation and task reopening pass, with no grant or owner. |
| DISPLAY | Inapplicable | Headless service/SSH candidate; no display inference. |
| RETURN | Retained machinery; new physical result unproved | One physical original-A return, no uncertain replay, health-only continuation after proved A. |

## Authority and next bounded step

Root revision 53 and the incorporated details, target and automatic-boot
policy describe this precise observer specialization. They do not open a
grant. Current source-bound review, artifact qualification and existing fixed
D0 preparation have produced a reviewable task. Physical execution still needs the exact returned attended
one-operation/3600-second grant, usable Download/original-A recovery and
fresh machine checks. A does not undo native_data writes.

A90 and S20+ remain outside this work. Private evidence is under
`workspace/private/outputs/s22plus-autoboot-phase-p445-h0-20261020-1/`.
