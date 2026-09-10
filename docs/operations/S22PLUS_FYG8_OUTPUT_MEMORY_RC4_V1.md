# S22+ v0.1.2-rc.4 output delivery and bounded memory observations

Internal P381 implements the [rc.4 design](../plans/S22PLUS_FYG8_V012_RC4_DESIGN_2026-09-10.md)
after consumed P380's output-loss incident. This definition grants no device
authority. Changed-closure independent review, A/B/static qualification, current
exact preparation, physical attendance and fresh Process-v2 approval remain
required. Consumed predecessors and their source pins remain unchanged.

## Output delivery

The generated PID1 reserves queue capacity before reading stdout/stderr pipes.
With eight queue entries and three response-reserve entries, OUTPUT admission
requires qcount below five. A partly written frame retains its entry until fully
sent. Streams rotate after a successful forwarded read, including when only
one credit becomes available per loop. Child pipe backpressure leaves receive,
STATUS, exec-status, reap, deadline, cancellation, HUD drain and CONTROL running.

The wire format, 768-byte pipe chunk, 767-byte command maximum, 1MiB output limit,
2048-frame limit and lifecycle timers are unchanged. Once either output budget
is exhausted, bounded discard/drain retains explicit truncation and drop counts.
CONTROL freezes further output and keeps the existing incomplete-terminal and
single acceptance-ACK rules. Zero dropped bytes alone does not establish complete
output: a cleanup deadline or CONTROL may still close an incomplete stream.
The normal reap cleanup allowance remains finite; an indefinitely stalled host
does not receive a lossless-delivery guarantee.

The new namespace injects a small output helper and stream-turn field into the
sealed ancestor generation. It does not alter the consumed shared C source,
replace recovery, or introduce a second console/transport.

## Qualification and optional plan

The first six qualifications retain root/console/cancellation and three fresh
gauge/HUD samples. The sixth command has gauge output only. P380's diagnostic
stderr burst is removed from this new command. The provider model, I2C reads,
units, three-sample criteria and HUD_FRAME grammar remain unchanged.

The prospective three-command sealed plan contains one normal root/RAM check,
then `/s22-display --memory-snapshot early`, then
`/bin/busybox sleep 2; /s22-display --memory-snapshot late`.
Each memory command has a 15-second timeout, including the late sleep, and uses
`/s22-root-work`. Each snapshot emits at most4096bytes on stdout, at most8192bytes
across both. No diagnostic output is required for gauge qualification.
The observer annotates only those exact post-qualification commands and binds
the interpretation to authenticated raw output and its terminal. A missing or
partial source is explicit unavailable/partial data; an actual command/session
failure remains subject to existing plan, terminal and CONTROL rules.

## Fixed read-only helper

The renderer executable's exact two-argument memory mode branches before DRM
open, module load and credential changes. It runs as an ordinary separately
owned console child, with no new daemon, PID1 reader or transport. No files are
deleted, rewritten, repermissioned or content-hashed on the device.

| Source | Read/record bound | Interpretation |
| --- | ---: | --- |
| meminfo | 8192bytes plus EOF check | Selected counters in KiB; missing fields remain unavailable |
| cmdline | 8192bytes plus EOF check | Ordered memory/debug tokens and duplicate counts; only root presence and summarized rootfstype |
| `/`, `/lib/modules`, `/s22-root-work` | Fixed directory descriptors | RAM filesystem identity and available statvfs accounting |
| Vendor modules outside the unchanged initial load plan | Fixed generated manifest, currently369 entries | No-follow metadata calls, expected type/UID/GID/mode/size/nlink/filesystem; no module content opens |
| slabinfo | 256KiB, 1024records, 512bytes/line | Top5 among valid records by nominal slab geometry; incomplete input remains partial |
| Existing RAM hud.log | Last16KiB, complete HUD_MEM lines only | Last successful renderer retirement bookkeeping, age and availability |

Section output allocations are BEGIN/END256, meminfo1024, cmdline512,
filesystem512, file census512, slab1024 and GEM256bytes, totaling4096.
Overflow replaces that section with a bounded unavailable record; the terminal
record retains its allocation. Reasons use numeric errno/fixed labels.
Proc inputs require the expected filesystem and complete EOF within their caps.
Nonblocking open does not bound time spent inside a kernel read; parent deadline,
cancellation and existing cleanup behavior remain applicable.

Logical file size, st_blocks times512 allocation metadata, resident pages and
reclaimability are different quantities. Matching metadata does not establish
content identity or absence of future consumers. The slab estimate uses the
preferred SLUB order and can differ from actual fallback allocations; slabinfo
alone does not identify reclaimability per cache. No overlapping counters are
summed into an exact memory footprint.

## Bounded GEM bookkeeping

The existing renderer emits at most32 HUD_MEM lines of at most128bytes after
successful matched flip and old-buffer retirement, or the initial frame. Counts
cover successful allocations/retirements, live/peak owned handles and requested
bytes. A failed retirement cannot emit a successful retirement record. These
lines add at most4096bytes under the unchanged256KiB HUD log cap. The final plan
must fit the existing session/raw/log budgets; the observation cap introduces
no new standing gate. Source age above five seconds is stale.

This is renderer ownership bookkeeping, not proof of physical backing, kernel
reference release, driver-wide GEM totals or complete Shmem attribution. No DRM
debugfs object walk, heap initialization, RBIN/CMA change or memory release is
included. Physical gauge pixels and actual target memory observations still
require a separately authorized device run.
