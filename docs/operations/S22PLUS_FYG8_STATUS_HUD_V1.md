# S22+ v0.1.1-rc.1 system-status HUD

Internal candidate P377 extends the [immutable boot HUD](S22PLUS_FYG8_BOOT_HUD_V1.md)
with fixed read-only system status. This design is H0 until independent review,
exact qualification, connected preparation and fresh attended F1 approval.
It changes no permanent partition, evidence, recovery or target boundary.

## Fixed presentation and data

The 1080×2340 surface uses a 120-pixel grid, white bitmap text on black.
Uptime and console state come from the existing 40-byte PID1 snapshot.
Memory used is MemTotal minus MemAvailable; available memory is also shown.
The kernel's kB values are KiB, displayed as integer MiB. CPU usage is the
aggregate delta of user, nice, system, idle, iowait, irq, softirq and steal;
idle and iowait are excluded from busy time, guest fields are not added twice.
The first sample, zero delta, overflow or decreasing counters yield N/A.

Only `/proc/meminfo`, the aggregate first `/proc/stat` line and
`/sys/class/power_supply/battery/{type,capacity,status,temp}` are read.
Battery type must be Battery. Capacity is percent, status is the exact kernel
enumeration and temperature is battery temperature in tenths Celsius. Missing,
malformed or out-of-range fields yield N/A independently. No provider module,
charging control, other thermal interface or GPU metric is added. Android D0
availability does not prove native provider availability.
Version `v0.1.1-rc.1` and purpose `SYSTEM STATUS HUD` occupy the bottom grid rows.

## Ownership and failure behavior

PID1 owns the collector and renderer as separate children in separate process
groups, outside the command group. The collector keeps only null stdin, its
nonblocking metrics socket stdout and nonblocking diagnostic stderr; the HUD
keeps its existing three descriptors and metrics input at descriptor 3.
All higher descriptors are closed before exec. PID1 neither reads metrics nor
waits for procfs/sysfs/DRM cleanup. It reaps each exact PID with WNOHANG and
signals each still-owned child at most once on CONTROL or HUD failure.
No child restarts. Collector exit or read stall leaves console control intact;
this is not recovery from a kernel or PID1 stall.

The collector sends at most 601 fixed 72-byte AF_UNIX SOCK_SEQPACKET records,
spaced one second apart. Records bind run, increasing sequence, collection-start
monotonic timestamp, validity mask and bounded values. Reads verify procfs/sysfs
filesystem type, final-component no-follow, bounded text and complete fields.
The fixed sysfs class path may traverse the kernel's intermediate symlinks.
A read can still block, which is why collection has its own process.

The renderer drains at most 32 packets per update. EOF, malformed data, wrong
run, invalid ranges or order close only the metrics endpoint and display N/A.
Samples older than five seconds display STALE and no current values. Full
nonblocking channels drop packets rather than replaying a backlog. The PID1
RAM diagnostic log is bounded at 256 KiB; its drain remains 512 bytes per tick.
The ten-minute console deadline, single transport, immutable GEM lifecycle and
matched flip-event retirement remain unchanged.

## Qualification

Host checks exercise real AArch64 parsing/collection and UAPI, generated PID1
with actual IPC and a deterministic DRM fixture, renderer bounds and lifecycle,
and absent, malformed and blocked collection while console/CONTROL continue.
Live qualification retains five root-console commands plus a sixth fixed HUD
capture. It requires three distinct fresh memory/CPU samples over at least two
seconds, including a BUSY console frame. Battery availability is independent;
N/A is accepted without claiming battery measurement. Matched flip events are
machine evidence; visible text remains operator observation. Exact Download,
one rollback and final rooted FYG8/original-hash health remain separate gates.
No result is replayed after an effect or uncertainty. Changed ownership, data
interfaces, wire format, rendering or recovery requires scoped review again.
