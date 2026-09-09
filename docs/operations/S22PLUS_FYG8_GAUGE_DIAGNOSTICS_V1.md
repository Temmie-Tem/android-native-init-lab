# S22+ v0.1.2-rc.2 gauge diagnostics

Internal P379 retains [Gauge HUD V1](S22PLUS_FYG8_GAUGE_HUD_V1.md). P378 closed
unproved with healthy rollback and unavailable gauge data; its captured output
could not distinguish failed binding, reads or parsing. This candidate adds
bounded diagnostics without changing measurement reads, units, validity,
root-console limits, qualification, CONTROL, rollback or final health.
This definition creates no device authority or replay.

## Provider snapshot

The `sample` parameter keeps the same S22FG1 record and read behavior. A new
read-only `/sys/module/s22plus_max77705_telemetry/parameters/diagnostic` parameter
returns `S22FGD1 probe=N probe_error=N bound=N read=N read_error=N read_ret=N attempts=N
stopped=N` with one trailing newline. The snapshot shares the sample mutex and
performs no I2C operations. Framework parameter locking and collector isolation
remain; this does not prove recovery from a blocked kernel transaction.

Probe stages: 0 not called, 1 entered, 2 child name, 3 parent basics, 4 parent OF
identity, 5 adapter OF identity, 6 root absent, 7 root model, 8 gauge config
absent, 9 resistor, 10 parent ABI/client relationship, 11 adapter capability,
12 owner claim, 13 bound, 14 removed. Errors are negative kernel errno values.
Stage 0 with bound=0 does not distinguish absent child from an already-owned
child; no extra device census or probe is performed to resolve that distinction.

Read stages: 0 none, 30 parent mutex busy, 31 chip ID, 32 revision, 33 SOCREP,
34 VCELL, 35 CURRENT. Read error includes an identity mismatch. `read_ret` retains the existing
SMBus callback return (including the actual ID/revision byte when that check
rejects it); initial state is -ENODATA and mutex-busy stage uses -EAGAIN.
Attempts and
latched stop state retain their existing meaning. A snapshot reports current
state when read, not an atomic trace of a preceding userspace syscall.

## Collector records

Fixed sample reads retain the bounded raw prefix and distinguish open,
filesystem, read, overflow, embedded-NUL and close errors. Parser results
separate syntax, source error, sequence, timestamp, raw range and each converted
value. Existing acceptance and conversion rules are unchanged; source errors
are reported before their resulting empty/zero-sequence fields.

`GAUGE_DIAG` records carry collector sequence, reason, read stage/errno,
diagnostic-read stage/errno and hex-encoded raw sample/snapshot prefixes.
Userspace errno is positive; errors inside kernel records are negative.
Reasons 0–9 mean success, syntax, source error, sequence, timestamp, raw range,
SOC conversion, voltage conversion, current conversion and voltage range.
Reasons 101–106 mean sample open, filesystem, read, overflow, embedded NUL and
close. Reasons 200/201/202 mean clock failure/future/stale. Reasons 300+mask
identify accepted but partially valid samples; their validity bits are unchanged.

At most eight records, each below 1152 bytes, use one nonblocking stderr write
through the existing diagnostic pipe. Repeated unchanged reasons and snapshot
state are suppressed; sample values, sample sequence and attempt counters alone
do not emit another record. Snapshot reads may continue each collection cycle
until the record budget is spent, without extra bus transactions. Backpressure
may lose a diagnostic but never delays CONTROL or retries a write. The 256 KiB
log limit, 601 samples and parent drain remain unchanged. Raw bytes remain private.

## Qualification

The ordinary sixth capture still requires three distinct fresh gauge plus
memory/CPU samples. Diagnostic availability never substitutes for that condition
and cannot confirm v0.1.2. Unavailable values can still produce a NO_PROOF run,
with the new records helping localize the failure. No old result is relabeled.
Host checks cover actual wrapper snapshots without extra reads, real ARM64
parser/read failures and raw retention, output limits, generated collector/HUD/
PID1 IPC, and blocked/absent collection with console control. Changed execution
closure requires independent review, fresh A/B/static qualification, exact
preparation and fresh attended Process-v2 approval before the one candidate.
