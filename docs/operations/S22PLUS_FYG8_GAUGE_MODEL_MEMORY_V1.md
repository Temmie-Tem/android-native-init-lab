# S22+ v0.1.2-rc.3 model correction and native memory observation

Internal P380 succeeds consumed P379 under [Gauge Diagnostics V1](S22PLUS_FYG8_GAUGE_DIAGNOSTICS_V1.md).
This definition opens no device authority. Fresh changed-closure independent
review, A/B/static qualification, connected preparation, physical attendance
and a new Process-v2 approval are required. No consumed artifact is edited.

## Exact model correction

P379 authenticated diagnostics localized probe-stage 7 / ENODEV, before any
I2C attempt. One subsequent exact-target Android D0 read observed root model
`Samsung G0Q PROJECT (board-id,12)`. P380 accepts only that exact string,
replacing both speculative Qualcomm SoC strings. It adds no wildcard/fallback.
The native probe still reads and checks its own root model. The Android
observation does not retrospectively prove P379's native model string.

Child name, MFD driver/address/compatible, parent and adapter OF identities,
resistor, private parent/FG-client ABI, adapter capability, owner claim and all
measurement/lock/cache/fault limits remain unchanged. Later checks were not
reached in P379 and may still reject P380. Measurement units, sample format,
diagnostics, collector, HUD packet and three-fresh-gauge-sample qualification
are unchanged. Corrected binding alone does not confirm v0.1.2.

## Optional same-boot memory snapshots

The existing sixth fixed root-console command emits an early snapshot before
the gauge wait and a late snapshot afterwards. It waits at least two existing
one-second iterations, with the same twelve-iteration cap and fifteen-second
command timeout. No new daemon, kernel code, collector or transport is added.
The fixed command remains inside the existing 1023-byte command limit.

Each snapshot reads only:

| Source | Maximum bytes per snapshot | Purpose |
| --- | ---: | --- |
| `/proc/uptime` | 8192 | Snapshot time within this native boot |
| `/proc/meminfo` | 8192 | Kernel memory categories and HUD arithmetic |
| `/proc/1/status` | 8192 | PID1 memory and process state |
| `/proc/device-tree/model` | 256 | Native root model observation |
| Fixed BusyBox `ps -o pid,ppid,vsz,rss,comm` | 16384 | Process memory census, without arguments or environment |

`MEM_SNAPSHOT early/late`, fixed field markers and `MEM_END` frame each
observation. Output is a bounded prefix; reaching a cap does not establish
completeness. Read/ps error text is retained as unavailable data. Process exit
races and process RSS overlap are not interpreted as zero memory or a total.
Uptime and all fields are sequential observations, not an atomic snapshot.

Memory output uses authenticated stderr, remains in the existing raw capture
and receipt, and is replay-compared without changing its original identity.
Only the sixth qualification permits that diagnostic stderr; its terminal,
stdout HUD proof, cwd, timeout, framing and other qualifications stay unchanged.
Optional memory contents never certify or reject gauge functionality. The
shared command output, deadline and transport failure rules remain binding;
diagnostic collection does not excuse a session fault or bypass CONTROL.
All raw process/memory/model output remains private.

## Analysis and evidence limits

The HUD shows integer MiB from `MemTotal - MemAvailable`, not summed RSS.
Compare both native snapshots with their own HUD samples; current Android
memory cannot decompose the prior native 1053 MiB. Separate MemTotal exclusions
from runtime accounting. Slab, reclaimable memory, CMA, cache and process RSS
overlap; do not sum them as disjoint categories. Existing retained boot evidence
may inform reservation analysis, with missing data explicitly unproved.
Detailed attribution is subsequent host analysis and does not gate gauge proof.

Host checks exercise the actual module's corrected and rejected model paths,
unchanged later guards and bus behavior, exact ARM64 module linkage, the real
BusyBox command, output separation and optional failure cases, generated
PID1/collector/HUD IPC and authenticated receipt replay. Host fixtures are not
actual target binding, physical pixels or memory-use proof. HUD image publication
remains deferred until actual rc.3 gauge display is observed.
