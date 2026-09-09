# S22+ v0.1.2-rc.4: output backpressure and bounded memory observations

Status: **DESIGN_ONLY; private H0 prototype exercised.**

The operator selected output-loss repair and RAM-file retention observations
for rc.4, followed by this design task. No rc.4 candidate, READY manifest,
activation, connected preparation or device effect is created by this document.
Internal candidate registration belongs to implementation; P380 and its approval
remain consumed. The retained functional version remains v0.1.1.

## Selected scope and completion criterion

rc.4 should retain rc.3's exact gauge model/ABI/read guards, text HUD, boot-only
transfer and exact rollback. It should preserve bounded stdout/stderr under
temporary host backpressure and collect two small memory observations after
fixed functional qualification.

RAM-file deletion, module unloading, RBIN/CMA changes, heap-provider insertion,
swap configuration and kernel-memory tuning are outside rc.4. The memory goal
is to determine whether the approximately56MiB of module files outside current
explicit load plans remain in the RAM filesystem, and to narrow Shmem/slab
attribution. It is not a memory-reclamation or leak-absence claim.

The design task is complete when the loss mechanism, proposed execution order,
data/size limits, retained failure behavior and implementation checks are
concrete. Implementation and independent capability review remain separate.

## 1. Change output admission before reading a child pipe

The current `rc1_child_tick()` reads up to768bytes from each pipe, then drops
the bytes when qcount reaches5: RC1_QUEUE is8, with3 response slots reserved.
Each tick can produce two OUTPUT frames but flushes at most one queue frame.
Thus even an output below1MiB/2048frames can lose data during a burst. P380's
authenticated1536-byte loss is consistent with this path; its evidence did
not directly sample queue depth or locate all lost bytes by stream.

The selected repair is producer backpressure, with the same queue capacity:

1. Before reading stdout or stderr, check whether another OUTPUT frame can
   be admitted while retaining the existing three response slots.
2. If there is no credit and the output byte/frame budget is not exhausted,
   leave the bytes in the pipe. Child writes may block; PID1 must not block.
3. Continue exec-status pipe handling, nonblocking reaping, command deadlines,
   cancellation escalation, HUD/collector ticks, transport input and output
   flushing even when both data pipes are deferred.
4. Share available credits fairly between streams. Advance a small stream-turn
   cursor after a successful forwarded read, not on every loop iteration;
   otherwise alternate full/available ticks could repeatedly favor stdout.
5. Keep explicit byte/frame budget exhaustion as truncation. Once exhausted,
   bounded draining/discard accounting must remain possible without waiting
   for an OUTPUT credit. Do not reinterpret a budget drop as complete output.

No whole-function early return is allowed for queue pressure: it would bypass
timeouts, reaping or exec-status handling. No priority reordering may interleave
an already partially written wire frame. Per-stream byte order and aggregate
ordinal/terminal accounting remain exact; cross-stream scheduling is not a
promised producer ordering.

The single owner checks and consumes a queue credit without another producer
running between them. An unexpected enqueue failure after reading still fails
the command/session; it must not be hidden or retried as if no data were read.

### Limits and failure semantics that remain binding

The queue stays8 entries; output stays1MiB and2048frames per command. The existing
session, command, partial-frame, cancellation and CONTROL deadlines stay in
force. The post-reap cancellation/drain path can report incomplete output after
its existing two-second cleanup allowance. This design does not promise complete
delivery for an arbitrarily slow or permanently absent reader.

CONTROL remains admitted independently of ordinary queue admission. It stops
normal output production, kills/cancels the active group as before, drains
already queued frames, then publishes the honest terminal and CONTROL ACK.
Unread pipe bytes during CONTROL are not reported as complete. In particular,
`dropped=0` does not mean complete when OUTPUT_INCOMPLETE/CONTROL flags are set.
Transport errors, uncertain delivery and cleanup failures retain current stops;
there is no reopen, replay, renewed session or recovery-rule change.

### Private feasibility experiment already completed

The existing C supervisor host harness was compiled unchanged and with a small
in-memory backpressure/stream-turn prototype. Real child processes wrote64KiB
of distinct binary data to each stream. The host paused reading for350ms, with
a small socket send buffer, then resumed:

| Case | Retained output | Dropped output | Result |
| --- | ---: | ---: | --- |
| Existing supervisor | 6,912bytes | 124,160bytes | TRUNCATED |
| Backpressure prototype | 131,072bytes | 0 | Both streams matched byte-for-byte; clean terminal |
| CONTROL during prototype pressure | 6,912bytes | 0 | Explicit CONTROL/cleanup/incomplete terminal; ACK observed |

The CONTROL ACK arrived about75ms after the reader resumed in that host test.
That is an observation, not a native latency guarantee. The experiment reproduces
the fault class rather than the exact P380 USB event. It used x86 Linux
fork/pipes/socket and the base supervisor harness, not ARM64, actual USB or the
final generated HUD owner. The private prototype is not a reviewed patch.

## 2. Put memory observations after the six functional qualifications

Restore the sixth command to the bounded gauge/HUD proof without rc.3's full
meminfo/process-table stderr burst. Preserve its three fresh gauge samples,
HUD/console behavior and existing command/deadline requirements. Keep the
corrected rc.3 telemetry provider unchanged.

The prospective sealed plan remains a small three-command plan:

| Plan position | Purpose | Command budget |
| --- | --- | ---: |
| 1 | Ordinary root-console/RAM-state check | Existing bounded plan mechanism |
| 2 | Early memory snapshot | 15seconds |
| 3 | Existing BusyBox sleep2, then late memory snapshot | 15seconds including sleep |

These are design roles, not issued commands or a sealed plan. Exact bytes and
identities will be prepared with the new candidate. All three retain existing
host time/raw-budget reservation and no-replay handling. The two snapshots
produce at most4096bytes each, in separate commands. Their start/end monotonic
times are reported; sequential reads are not an atomic snapshot or a leak test.

The actual native and Python console consumers cap command text at767bytes.
The rc.3 wrapper's1023-byte assertion is a looser check, not the wire consumer's
limit; its640-byte command still fitted. rc.4 commands must be checked against
the actual767-byte consumer. No command-limit or wire-format expansion is needed.

Optional missing/malformed memory values produce explicit field statuses and
do not change the already-established six-command functional qualification.
A helper crash, command timeout, incomplete terminal or transport fault remains
its actual plan/session outcome. Existing aggregate NO_PROOF rules are not
weakened to make optional diagnostics appear successful.

## 3. A short-lived read-only mode in the existing renderer executable

Use a new fixed `--memory-snapshot early|late` mode in `/s22-display`. Dispatch
it before any DRM open, module insertion, display preparation or privilege-drop
path, as a separate root-console child. This reuses the existing static binary,
toolchain and command owner without adding a daemon, transport or PID1 reader.
The fixed phase is the only selector; no caller-supplied path is accepted.

The helper reads into bounded buffers or streams bounded records, constructs a
bounded textual result, then writes at most4096bytes. It emits explicit BEGIN,
END, per-source status/coverage and monotonic time fields. No truncation is
silently converted to an empty or complete source. Numeric parsing rejects
overflow, duplicate required keys and malformed complete records. Missing or
unsupported fields are unavailable, never zero by default.

| Observation | Read/iteration bound | Emitted information and limits |
| --- | --- | --- |
| `/proc/meminfo` | 8192bytes plus EOF probe | Selected memory/RBIN/CMA/slab/hugepage/swap counters; same units as rc.3 |
| `/proc/cmdline` | 8192bytes plus EOF probe | Only ordered memory-debug tokens, duplicate/absence status and root/rootfstype presence/type; never the full command line |
| `/`, `/lib/modules`, `/s22-root-work` | Fixed opened directories and fstatfs/fstatvfs | Backing filesystem type and block totals where meaningful; no raw device identifiers |
| Fixed module-file manifest | One metadata lookup per declared path | Present/type/size/link/device-match counts and summed st_size/st_blocks; no glob, recursion or content read |
| `/proc/slabinfo` | 256KiB input,1024records,512bytes per line | Top5 parsed caches by nominal num_slabs*pages_per_slab*page_size, with geometry and coverage status |
| Existing RAM HUD log | Last16KiB, complete lines only | Latest valid bounded renderer GEM bookkeeping record and age, if available |

The working-buffer requirement must remain small; the slab input cap is not a
requirement to allocate256KiB. Full raw slab listings, process tables, process
arguments, environment, symbol addresses and memory contents are not emitted.
Authenticated raw command output remains private and is preserved before host
interpretation. It is a structured observation, not a raw copy of every leaf
kernel source; no stronger raw-source proof is claimed.

Reserve output sections within4096bytes: BEGIN/END/status256, meminfo1024,
command-line512, filesystem512, file totals512, slab1024 and GEM256. A section
overflow becomes an explicit unavailable section, not a silently cut record.
Reserve the terminal status before formatting any variable source text; emit
numeric errno and fixed reason labels rather than unbounded error strings.

Opening a procfs file with O_NONBLOCK does not bound all kernel-side work. The
parent stays independent and retains existing cancellation/CONTROL behavior;
an uninterruptible helper is incomplete cleanup, not demonstrated recovery.

### File manifest and what it can establish

Generate the fixed metadata manifest on the host from exact vendor/candidate
archives and the union of initial/display/return plans. The current inputs
produce369 out-of-plan module paths, but this is derived input, not a permanent
hard-coded census answer. Include expected type, size and link constraints in
the generated candidate source closure. Preserve the independent event-latch
module and all display/return dependencies in the selected set.

Open the bound directories without following symlinks; inspect exact relative
names without crossing to another filesystem. A mismatch is counted and
reported, not followed or repaired. Sum metadata only for validated entries.
Use the exact target ABI for stat fields and the512-byte st_blocks unit.
Sparse-file, directory, symlink and mount-mismatch fixtures must prevent treating
logical size as allocated storage or metadata match as content identity.

These observations can establish that named files exist on the RAM filesystem
and what allocation metadata reports. They do not prove byte-for-byte contents,
absence of future consumers or immediate reclaimability after unlink. No file
is deleted, repermissioned, rewritten or content-hashed by this mode.

### Slab and GEM scope

Slab ranking covers all parsed slab caches; `/proc/slabinfo` alone does not label
each cache as reclaimable/unreclaimable. An input cap, malformed line or race
prevents claiming a complete global top5. Do not equate object payload totals
with slab pages or sum overlapping counters into an exact footprint.
The selected SLUB source reports the preferred cache order, while allocation
can fall back to a smaller order. Therefore the page-based ranking is a nominal
geometry estimate, not an exact measurement of pages occupied by that cache.

For GEM, record the renderer's own allocation/retirement bookkeeping, not kernel
debugfs object dumps. Emit a separate `HUD_MEM` line after a successful matched
flip and old-buffer retirement (or the first frame), without changing HUD_FRAME
grammar or gauge-field positions. Count successful allocations/retirements and
current/peak owned handles; derive requested bytes from the fixed geometry.
Failure before retirement must not emit a fictitious successful retirement.

Emit at most32 such lines, each at most128bytes: at most4096 additional bytes
under the unchanged256KiB HUD log cap. Report source age and availability after
this bounded window; never promote an old record to a current measurement. The
implementation must check worst-case log use for the entire sealed plan window.
This diagnostic is optional and uses the existing nonblocking parent log drain;
no new IPC channel, file writer or parent DRM operation is introduced.

Renderer ownership accounting does not establish kernel reference release,
physical backing pages, driver-wide GEM totals or a complete Shmem decomposition.
Kernel GEM attribution can remain unavailable in rc.4. No debugfs mount or
driver-locking object walk is added just to fill that field.

## 4. Implementation boundaries and checks

Use the existing candidate-generation/namespace mechanism. Preserve consumed
P380 and ancestor execution-critical bytes and their receipts. Put the new
pipe-admission helper and stream-turn field into the new generated closure;
do not duplicate the entire runner or repin a consumed ancestor to accept edits.
Keep child lifecycle/control logic shared and source-bound. Add the snapshot
mode/manifest and bounded HUD_MEM production in the next renderer generation.

Required changed-path checks before capability review:

| Test family | Required behavior |
| --- | --- |
| Actual producer bursts | Both binary streams exceed pipe/socket capacity; bounded host pauses and repeated short writes/EAGAIN; exact per-stream bytes below budgets |
| Credit and fairness | Both pipes ready with only one credit; neither starves; qcount never consumes response reserve for OUTPUT |
| Budget boundaries | Exact and over1MiB/2048frames; honest counts and truncation, no infinite wait after exhaustion |
| Lifecycle under pressure | STATUS, CANCEL, CONTROL, normal reap with pipe tail, inherited writer, exec failure and existing drain timeout retain correct outcomes |
| Framing/owner | Partial wire frame never reordered; bad authentication, replay, uncertain send, overload and raw-budget admission still reject/stop |
| Real ARM64 execution | Target UAPI and actual static ARM64 supervisor/BusyBox with real pipes under the existing emulator path; new stat/open flags checked against target headers |
| Snapshot parser | Missing/partial/oversize/malformed/duplicate/overflow cases produce explicit coverage; every output remains at most4096bytes |
| Filesystem metadata | Real regular and sparse files, symlinks, wrong types/filesystems and missing entries; no data mutation or content reads |
| Slab/GEM | Correct page-based ranking; incomplete census remains partial; retirement failure cannot create a success record; stale/partial HUD_MEM is unavailable |
| Final generated integration | Gauge qualification completes before optional snapshots; HUD/collector/CONTROL continue; actual logger cap, command/raw limits and authenticated replay match |

The private host prototype covers only part of the first/lifecycle rows. It does
not replace these tests. Use existing integration and ARM64 harnesses and extend
the changed paths rather than creating a new orchestration system.

The output-loss incident requires changed-closure independent review before a
new capability is used. Review the actual generated pipe/renderer/observer paths
and higher-precedence interactions, then perform normal A/B/static qualification,
READY publication and connected preparation. The target contract's current
attendance and fresh Process-v2 approval still precede any device effect.
No extra consent ceremony or standing grant is introduced by this design.

## Evidence and references

The private experiment and its C sources/wire evidence are under
`workspace/private/outputs/s22plus-rc4-design-h0-20260910-1/`.
The script passed py_compile and all three declared experiment assertions.
`prototype-result.json` is2478bytes, SHA-256
`9ef4197e1bbcc0bef29f56b60aa1c5f1345aada2e211e85dd2fac5905be059a3`.
Exact result/source identities are also recorded with the private design-close
evidence. These are prototype identities, not a capability review receipt.

- [rc.3 close and output-loss evidence](../reports/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_RC3_H0_2026-09-10.md)
- [Memory source review and archive/DT attribution](../reports/S22PLUS_FYG8_MEMORY_SOURCE_REVIEW_H0_2026-09-10.md)
- [Root console semantics](../operations/S22PLUS_FYG8_ROOT_CONSOLE_V1.md)
- [Binding S22+ contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
