# A90 WP2-5b streaming kernel-log observer requirement

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 source and design analysis
Device, `/dev`, USB, network, or other-target contact: none
Disposition: permanent invariant; H0 trace core separate, runtime observer absent

## Result

Any future `WP2-5b` unit that relies on a kernel-log record must arm a trusted
`/dev/kmsg` streaming observer before the first possible driver-init effect.
A post-result `dmesg` or kernel-ring snapshot is not proof that a required
record was absent or unique. Increasing the kernel log buffer is not a
substitute for sequence-complete streaming.

This requirement is named
`A90_WP2_5B_POSTHOC_KMSG_RETENTION_GAP`. Its runtime form,
`WP2_5B_KMSG_STREAM_COMPLETENESS`, is permanent for every terminal whose proof
depends on a kernel-log record. The temporary implementation gate
`WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` retires only after an exact
byte-derived runtime observer, durable raw/journal writer, result consumer,
qualification, hostile execution corpus, and independent execution review
exist. The separate WP2-5b.1 H0 trace encoder/consumer core does not open the
device or retire this gate. Neither gate grants device or execution authority.

## The effective ring is not proved to be 128 KiB

The matching defconfig contains:

```text
CONFIG_SMP=y
CONFIG_NR_CPUS=8
CONFIG_LOG_BUF_SHIFT=17
CONFIG_LOG_CPU_MAX_BUF_SHIFT=17
CONFIG_MESSAGE_LOGLEVEL_DEFAULT=4
# CONFIG_SEC_DEBUG_MSG_LOG is not set
```

`CONFIG_LOG_BUF_SHIFT=17` selects the **minimum** static 128 KiB buffer. It is
not the final-size proof. In this 4.14 source, `log_buf_add_cpu()` computes

```text
cpu_extra = (num_possible_cpus() - 1) * (1 << CONFIG_LOG_CPU_MAX_BUF_SHIFT)
```

and calls `log_buf_len_update(cpu_extra + __LOG_BUF_LEN)`. With eight possible
CPUs and no earlier `log_buf_len` override, the source-default calculation is
1 MiB after power-of-two rounding. An early `log_buf_len=` parameter can choose
a different larger-than-minimum allocation before that CPU scaling path.
Neither the exact live command line nor the effective live `log_buf_len` is
bound by the current H0 evidence, so the actual ring size remains **unproved**.

The MAC absence line is emitted with `pr_err`, so it is written as an explicit
kernel error-level record; console visibility is not the issue. Preservation
until a later snapshot is the unproved property. The disabled Samsung
`SEC_DEBUG_MSG_LOG` option supplies no selected alternate retained log here.
No finite ring size proves that an earlier record will survive an unbounded
boot or observer delay.

## Why `/dev/kmsg` is the required source

The selected kernel's `/dev/kmsg` reader has per-open `seq` and `idx` state.
`SEEK_END` places that reader after the last existing record. Each later read
returns the structured priority, sequence number, timestamp, continuation
flag, and message body. If the reader falls behind the ring,
`devkmsg_read()` resets it to the first retained record and returns `-EPIPE`;
`poll()` also reports an error when data vanished. Reading `/dev/kmsg` does not
clear the global ring or move another reader's cursor.

The exact source-side maximum exported record buffer is
`CONSOLE_EXT_LOG_MAX=8192`. A future reader must use a buffer at least that
large and parse one complete record at a time. A smaller fixed buffer can
receive `-EINVAL` for a valid record and is not a complete observer.

`/proc/kmsg` is not an acceptable automatic fallback. Its read path calls
`do_syslog(SYSLOG_ACTION_READ, ...)` and advances the one global
`syslog_seq/syslog_idx/syslog_partial` cursor. It lacks the independent
per-reader sequence boundary needed by this proof and can interfere with
another legacy reader. If `/dev/kmsg` cannot be opened, sought, and armed
exactly, the unit must stop before durable effect intent.

## Required WP2-5b ordering and evidence

The future implementation must enforce all of the following:

1. **Pre-effect arm.** A trusted native observer opens the exact non-symlink
   character device `/dev/kmsg` with rdev `1:11`, read-only, nonblocking, and
   close-on-exec; seeks exactly to `SEEK_END`; and publishes a bounded
   `OBSERVER_ARMED` receipt before durable effect intent or any component can
   trigger the bound WLAN driver initialization.
2. **No snapshot substitution.** `dmesg`, a post-result ring dump,
   `/proc/kmsg`, `last_kmsg`, pstore absence, or a larger `log_buf_len` cannot
   satisfy the stream-completeness field.
3. **Continuous drain.** A dedicated reader drains all available records
   without a periodic one-record sleep. It uses a buffer of at least 8192
   bytes, preserves every complete structured record in the bound epoch under
   an operator-accepted byte/count cap, and frames and hashes the exact raw
   bytes for the result consumer.
4. **Sequence proof.** The consumer rejects `EPIPE`, `POLLERR`, sequence gaps,
   duplicates, regression, malformed headers/bodies, continuation ambiguity,
   short or oversized records, byte/count cap exhaustion, read/poll error,
   premature EOF, unknown start/end, and mixed boot/run/driver-init epochs.
5. **Parent-controlled end.** Only after the exact driver outcome is bound may
   the parent close the observation epoch. The observer then drains to
   `EAGAIN`, fsyncs/publishes its bounded result through the future reviewed
   journal channel, closes the sole FD, and proves no duplicate reader or FD
   survives cleanup.
6. **Exact MAC classification.** Within that one epoch,
   `MAC_PROVISION_FALSE_PROVED_EXACT_RUN` requires exactly one kernel-facility
   error record whose body is
   `WLAN MAC address is not set, type 0`, zero matching type-1 absence records,
   and the exact `wlan0`-up result from the same driver initialization.
   `MAC_PROVISION_TRUE_PROVED_EXACT_RUN` retains its source-unique
   `getting MAC address from platform driver failed` record and exact bound
   failure outcome. Debugfs state remains corroboration only.
7. **Fail before spending when possible.** Open, identity, seek, buffer,
   parser-selftest, and `OBSERVER_ARMED` failures stop before effect intent and
   consume no live ordinal. Any loss detected after effect intent becomes
   `NO_PROOF_OBSERVER`; the effect is never replayed, and cleanup/recovery and
   final resident health remain separate safety work.

The exact byte and record caps, scheduling/cgroup reserve, durable result
channel, attended-session count, and ordinal budget remain unset. They must be
derived from a corrected healthy baseline and accepted before execution
qualification. This H0 requirement does not invent them.

## Existing source is precedent, not an implementation

The current public V724 source already demonstrates that the native process
can open `/dev/kmsg` with `O_RDONLY|O_NONBLOCK|O_CLOEXEC` and seek to
`SEEK_END`. Its historical RC1 watcher falls back to `/proc/kmsg`, reads into a
768-byte buffer, samples one record and then sleeps 20 ms, and does not publish
the WP2-5b sequence-complete framed stream. That code is evidence that the
surface exists, not a reusable or qualified WP2-5b observer.

## Source anchors

Matching operator-staged A90 kernel source, read only:

- `arch/arm64/configs/r3q_kor_single_defconfig:30,135-138,208,554,5803,6327-6329,6561`
- `init/Kconfig:569-622`
- `include/linux/printk.h:45`
- `kernel/printk/printk.c:351-357,459-461,499-503,852-1106,1137-1243,1412-1460,1588-1600`
- `fs/proc/kmsg.c:18-57`

Public current source:

- `workspace/public/src/native-init/v724/90_main.inc.c:3800-4018`
- `docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md`
- `docs/reports/A90_WLAN_MAC_PROVISIONING_EXISTING_EVIDENCE_H0_2026-08-16.md`

## Authority

This report is H0 only. It creates no observer binary, candidate identity,
qualification, approval, journal, D0, D1, F1, handoff, UFS mutation, property
provisioning, live ablation, recovery, or execution authority. Option C and
full runtime `WP2-5b` remain unimplemented and unauthorized. The later H0 trace-core
implementation is documented separately in
`A90_WLAN_WP2_5B_KMSG_TRACE_CORE_H0_2026-08-16.md`.
