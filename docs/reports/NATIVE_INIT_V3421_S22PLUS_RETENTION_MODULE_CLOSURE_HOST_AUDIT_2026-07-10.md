# V3421 S22+ Retention Module Closure Host Audit

## Verdict

`HOST/SOURCE AUDIT PASS; CAPTURE OWNER CORRECTED; NO LIVE CANDIDATE AUTHORIZED`.

The exact FYG8 module metadata, official Samsung kernel source archive, existing
O3 plans, and current rooted Android bind state identify `sec_log_buf.ko` as the
owner of the retained printk ring. `sec_debug.ko` is a separate panic-notifier
and diagnostic component.

This corrects V3420's first post-run explanation. V3420 was right that O3R1 did
not carry Android module state into a new kernel boot, but wrong to name
`sec_debug.ko` as the missing retained-log writer. O3/O3F also omitted the
actual writer despite including `sec_debug.ko`.

No module was inserted, no sysfs/configfs value was written, no reboot was
requested, and no image was built or flashed in this unit.

## Exact Inputs

FYG8 module directory:

```text
workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/
  extracted-images/ramdisk-list/vendor/extract/lib/modules
```

Samsung source archive:

```text
workspace/private/inputs/s22plus_kernel_source/
  SM-S906N_15_base_osrc/Kernel.tar.gz
```

Exact modules:

```text
sec_log_buf.ko size=76688
sha256=b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61

sec_debug.ko size=51248
sha256=9936d5622f55530480bd167ba4ca000cbc7c6dbb2bc9c99623b895a4ae087d3d
```

Both report exact FYG8 vermagic:

```text
5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8
SMP preempt mod_unload modversions aarch64
```

## Dependency Matrix

| Property | `sec_log_buf.ko` | `sec_debug.ko` |
|---|---|---|
| Stock `modules.load` position | 2 | 105 |
| `modules.dep` loadable dependencies | none | none |
| `modules.softdep` edges | none | none |
| DT compatible | `samsung,kernel_log_buf` | `samsung,sec_debug` |
| Primary runtime role | retained printk ring | panic notifier/statistics/control |
| Creates `/proc/last_kmsg` | yes | no |
| Creates `/proc/ap_klog` | yes | no |
| Required DT data | strategy, memory-region, optional partial range/compression | panic notifier priority |
| Current Android bind | `8.samsung,kernel_log_buf` | `soc:samsung,sec_debug` |

An empty `depends` field means there is no other loadable `.ko` supplier. It
does not mean the module has no prerequisites. Both modules still require their
exact GKI ABI/exported symbols and a matching DT platform device. The exact
vermagic/modversions and current stock Android binds are the relevant closure
evidence.

## `sec_log_buf.ko` Source Closure

Relevant source members in `Kernel.tar.gz`:

```text
kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/sec_log_buf_main.c
kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/sec_log_buf_logger.c
kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/sec_log_buf_vh_logbuf.c
kernel_platform/msm-kernel/drivers/samsung/debug/log_buf/sec_log_buf_last_kmsg.c
kernel_platform/msm-kernel/include/dt-bindings/samsung/debug/sec_log_buf.h
```

The probe path is explicit:

1. Parse `sec,strategy`.
2. Resolve the `memory-region` phandle with `of_reserved_mem_lookup()`.
3. Select the whole or DT-provided partial reserved-memory range.
4. Map and validate the `LOGM` ring header.
5. Copy the previous boot's ring into a last-kmsg buffer.
6. Create `/proc/last_kmsg`.
7. Pull the current early printk ring into reserved memory.
8. Initialize the selected logger.
9. Create `/proc/ap_klog`.

The FYG8 DT reports strategy `3`, defined by Samsung as
`SEC_LOG_BUF_STRATEGY_VH_LOGBUF`. That implementation registers
`android_vh_logbuf` and `android_vh_logbuf_pr_cont`; every accepted printk record
is copied into the reserved ring. The Android 12 GKI printk path invokes those
vendor hooks after committing records.

Compression is not a separate loadable-module dependency. The module requests
the DT-selected `zstd` crypto compressor through the kernel crypto API in a
threaded post-probe stage; failure disables compression rather than changing
the identity of the retention owner.

## `sec_debug.ko` Source Closure

Relevant source member:

```text
kernel_platform/msm-kernel/drivers/samsung/debug/common/sec_debug_main.c
```

Its probe parses `sec,panic_notifier-priority`, creates Samsung debug controls,
and registers a callback in `panic_notifier_list`. Its module parameters include
`debug_level`, `force_upload`, and `enable`. It can change panic diagnostics and
upload behavior, but it does not map the retained printk ring or create
`/proc/last_kmsg`.

MID may still matter to Samsung reset/upload presentation. It is not a source
dependency of `sec_log_buf.ko` and cannot substitute for loading the log-buffer
driver.

## Existing Candidate Audit

The generated O3/O3F 59-module plan contains:

```text
17 sec_debug.ko sec_debug
```

It contains no `sec_log_buf.ko`. O3R1 goes further and forbids every
`finit_module` call. Therefore:

- O3/O3F could register Samsung panic diagnostics but not the source-proven
  retained printk writer.
- O3R1 had neither component.
- Android preflight reads of `sec_debug enable=1` and MID described the Android
  boot only; they did not prove candidate-boot capture state.
- Marker absence in post-rollback `/proc/last_kmsg` cannot distinguish no PID1
  entry, a marker emitted without the retention hook, or an earlier failure.

The O3R1 verdict remains `NO-PROOF`. Its consumed exception remains retired.

## Functional Gates For Any Future Retention Probe

Static `modules.dep` closure is insufficient. A future, separately authorized
direct-PID1 probe would need these ordered runtime gates:

1. Mount procfs and make the stock `/lib/modules` visible.
2. Verify the exact `sec_log_buf.ko` hash and FYG8 kernel identity.
3. Call `finit_module` and accept only success or a proved preloaded state.
4. Read `/proc/modules` to EOF and find runtime name `sec_log_buf`.
5. Prove driver bind at
   `/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf`.
6. Prove `/proc/last_kmsg` and `/proc/ap_klog` exist.
7. Only then emit a unique `/dev/kmsg` marker.
8. Recover on the next boot and classify the exact marker in
   `/proc/last_kmsg`.

`sec_debug.ko` should be a separate optional rung when the named discriminator
is panic notifier/upload behavior. It should not be bundled into the first
retention-owner proof.

No such live rung is authorized now. The active goal remains O0 stock Android
TTY roundtrip, then O1 stock-first-stage observation.

## External Cross-Check

The AOSP kernel-module documentation confirms that first-stage vendor modules
live in vendor ramdisk `/lib/modules`, alongside `modules.dep`,
`modules.softdep`, aliases/options, and `modules.load`; first-stage init loads
the listed modules while satisfying hard and soft dependencies:

<https://source.android.com/docs/core/architecture/kernel/kernel-module-support>

AOSP `libmodprobe` exposes separate hard, pre-softdep, and post-softdep sets,
matching the O2 planner model:

<https://android.googlesource.com/platform/system/core.git/+/refs/heads/main/libmodprobe/include/modprobe/modprobe.h>

Android common 5.10 declares and invokes the exact log-buffer vendor hooks used
by FYG8 `sec_log_buf.ko`:

<https://android.googlesource.com/kernel/common/+/3d213a626d2d/include/trace/hooks/logbuf.h>

<https://android.googlesource.com/kernel/common/+/refs/tags/android12-5.10-2024-08_r5/kernel/printk/printk.c>

The Linux driver model confirms that registering a platform driver only
advances to a functional state after device matching and successful `probe()`,
which is why a `finit_module` rc or `/proc/modules` line is not enough:

<https://docs.kernel.org/driver-api/driver-model/platform.html>

## Incidental `/dev/null` Baseline Warning

During read-only Android diagnostics, `/dev/null` was observed as:

```text
type=regular file
logical_size=2445099008
allocated_blocks=346368 x 512
mode=0600
mount=tmpfs /dev
```

Normal `/dev/zero`, `/dev/random`, `/dev/urandom`, and `/dev/kmsg` remained
character devices. The first diagnostic command itself used `2>/dev/null`
before the malformed path was classified. It may have encountered a preexisting
bad path, or it may have materialized a missing path before another process
wrote it. Causality is therefore `UNVERIFIABLE`; do not attribute it to O3R1 or
to hardware.

Because `/dev` is tmpfs, no persistent-partition write is implied. O0 must not
start from this baseline. First require a normal Android boot and read-only
proof that `/dev/null` is character device major 1, minor 3. This audit did not
remove, recreate, relabel, or otherwise modify the path.
