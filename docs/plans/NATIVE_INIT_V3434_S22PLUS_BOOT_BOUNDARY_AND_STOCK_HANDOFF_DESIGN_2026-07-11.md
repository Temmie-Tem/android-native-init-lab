# V3434 S22+ Boot Boundary And Stock Handoff Design

## Verdict

`HOST_STATIC_MAP_PASS_NO_LIVE`.

The immediate production architecture should retain stock Android `init` as
the global PID 1 and hardware/recovery owner, then launch Debian in new mount
and PID namespaces through a native supervisor. Debian receives a real
`pivot_root`, not a `chroot`, while the O1.1-proven stock USB control channel
stays outside the Debian namespace as the recovery plane.

Direct `/init` replacement is now a research-only track. It must not return to
live testing until it has an observation channel available before the first
userspace module load.

Machine-readable evidence and policy:

```text
docs/plans/s22plus-v3434-boot-boundary-map.json
```

This unit is host-only. It contacted no device, built no image, performed no
flash, and authorizes no live work.

## Exact Boot Boundary

The pinned FYG8/GKI source gives the following path:

```text
ABL
  -> selects boot/vendor_boot/dtb and bootconfig
  -> arm64 kernel entry
  -> start_kernel()
  -> arch_call_rest_init()
  -> rest_init()
       kernel_thread(kernel_init, ..., CLONE_FS)  # becomes PID 1
  -> kernel_init_freeable()
       do_basic_setup() / initcalls
       rootfs_initcall(populate_rootfs)
       init_eaccess("/init")
       integrity_load_keys()
       DEFEX rule load
  -> kernel_init()
       free init memory / mark read-only
       run_init_process("/init")
  -> kernel_execve("/init", argv, envp)
```

The default `ramdisk_execute_command` is `/init`. `rdinit=` replaces it. If it
is absent or inaccessible, the kernel clears the ramdisk command and runs
`prepare_namespace()`. After a ramdisk-init exec failure it tries explicit
`init=`, `CONFIG_DEFAULT_INIT`, `/sbin/init`, `/etc/init`, `/bin/init`, and
`/bin/sh`. Explicit-init failure or no usable init panics. If the successfully
executed global PID 1 later exits, `do_exit()` panics with `Attempted to kill
init!`.

V3432 used the known-booting Magisk kernel unchanged and installed a valid
static AArch64 `/init`, but its first retained proof depended on all of these
later operations:

```text
getpid == 1
  -> construct /dev, mount proc and sysfs
  -> finit_module(sec_log_buf.ko)
  -> platform-driver bind
  -> /proc/last_kmsg + /proc/ap_klog
  -> marker write
```

Any failure before the last line silently parked. Therefore the V3433 marker
absence cannot distinguish kernel non-entry, `/init` non-entry, mount failure,
module failure, probe failure, or marker loss.

## Boot Image Ownership

The pinned stock images parse as Android boot header v4:

| Field | `boot.img` | `vendor_boot.img` |
|---|---:|---:|
| Header size | 1,584 | 2,128 |
| Kernel size | 41,490,944 | referenced load address `0x00008000` |
| Generic ramdisk size | 1,978,967 | - |
| Vendor ramdisk size | - | 21,813,545 |
| Signature size | 4,096 | - |
| Ramdisk load address | - | `0x02000000` |
| Tags load address | - | `0x01e00000` |
| DTB load address | - | `0x0000000001f00000` |
| DTB size | - | 1,721,428 |
| Bootconfig size | - | 164 |

`boot.img` owns the kernel and generic ramdisk. `vendor_boot.img` owns the load
addresses, vendor ramdisk, vendor cmdline, DTB, and bootconfig. The stock vendor
cmdline contains `console=null`; the live combined cmdline also contains
`nohyp_uart`.

## Watchdog Ownership

The running Magisk kernel IKCONFIG proves:

```text
CONFIG_WATCHDOG=y
CONFIG_WATCHDOG_CORE=y
CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y
CONFIG_WATCHDOG_OPEN_TIMEOUT=0
```

The watchdog core schedules an immediate kernel ping when a registered watchdog
reports that hardware is already running. `OPEN_TIMEOUT=0` means the kernel's
pre-userspace care deadline is infinite until userspace takes ownership.

The FYG8 first-stage module order is load-bearing:

```text
5  gh_virt_wdt.ko
6  qcom_wdt_core.ko
```

M21A showed an unmanaged bare PID 1 reaches the PMIC/PON abnormal-reset ceiling
near 30 seconds. M31B loaded the stock watchdog closure and survived the full
120-second park window. A direct PID 1 must therefore load this proven closure
before any unbounded park. The selected stock-first-stage architecture inherits
the already proven owner instead.

## Observation Activation Map

| Channel | Earliest usable stage | FYG8 state | Hard limit |
|---|---|---|---|
| earlycon/UART | kernel entry | unavailable by default | compiled in, but `console=null nohyp_uart`; silence proves nothing |
| ramoops/pstore | after backend platform probe | unavailable by default | pstore is built in but live `ramoops_region` is disabled |
| `sec_log_buf.ko` | stock PID 1 module #2 plus platform bind | live proven | cannot witness kernel entry or code before module load |
| `sec_debug.ko` | stock PID 1 module #105 plus platform bind | live proven | panic notifier, not the retained printk-ring owner |
| PMIC/PON reset reason | XBL/ABL before Linux | available | classifies reset, not the final Linux instruction |
| stock `ttyGS0` protocol | after stock gadget reports configured | O1.1 live proven | proves stock-first-stage control, not direct PID 1 |

`sec_log_buf.ko` creates `/proc/last_kmsg` and `/proc/ap_klog` only after the
exact module registers, matches `samsung,kernel_log_buf`, binds its reserved
memory, and completes procfs setup. `sec_debug.ko` separately registers the
Samsung panic notifier after matching `samsung,sec_debug`.

## Targeted ABL Boundary

The held FYG8 BL package contains `abl.elf.lz4`. Host parsing established:

```text
compressed SHA256  ced0a21ee5deab2ef84503149f45723ea1d09018d158e0aee82cfc644ba0d5f5
ELF SHA256         b828dffa4ea63eeaeb5d374db96daee9e1f696487f724d18aecbbc61ed993a24
container          ELF32 ARM, 4,194,304 bytes
entry              0x9fa00000
inner FV marker    file offset 4136
```

The retained ABL ring contains the following ordered facts around candidate
boots:

```text
(Booting) AUTHENTICATE fail but allow Kernel binary: boot
[AuthSignatureOnBoot] Custom binary(boot) by verifystatus(2)
Device is unlocked, Skipping boot verification
Hyp version: 1
Memory Base Address: 0x80000000
DT/DTBO selection messages
Shutting Down UEFI Boot Services: 19125 ms
```

This proves the custom warning is not a terminal verification rejection and
that the same candidate boot reaches the irreversible UEFI boot-services
shutdown boundary. The firmware side of the handoff is therefore reached. It
does not directly observe the immediately following branch into the candidate
kernel, successful decompression, `start_kernel()`, or PID 1. The ABL payload
is a proprietary stripped UEFI firmware volume; broad ABL RE is deferred unless
header or handoff evidence later contradicts the current map.

## Selected Runtime Architecture

```text
global namespace
  stock Android init (global PID 1)
    |- stock first-stage module loader
    |- watchdog ownership/petting
    |- sec_log_buf + sec_debug
    |- stock USB gadget + ttyGS0 recovery daemon
    `- native supervisor service
          |
          `- clone new PID + mount + UTS + IPC namespaces
                |- mount Debian root read-only for identity preflight
                |- make mount propagation private
                |- create /run and a namespace-specific /proc
                |- bind only the approved /dev and /sys surfaces
                |- pivot_root(newroot, newroot/.oldroot)
                |- detach old root
                `- exec Debian /sbin/init as namespace PID 1
```

This is not `chroot`: Debian receives its own root mount and PID 1 view.
Android `init` remains the global PID 1 solely as the hardware, recovery, and
rollback substrate. If Debian fails, the supervisor kills the namespace,
restores any released devices/services, and keeps the host USB channel alive.

### Mandatory Handoff Gates

1. `sec_log_buf` is registered, bound, and both proc nodes exist.
2. `gh_virt_wdt` and `qcom_wdt_core` are registered and the kernel pet path is
   live.
3. Stock UDC/gadget state is complete and the framed USB protocol passes.
4. Debian rootfs identity, required binaries, libraries, and mount policy pass
   read-only verification.
5. DRM, input, audio, and network ownership each have an explicit release and
   restore action.
6. The global recovery daemon and tty endpoint remain outside the Debian PID
   and mount namespaces.

Do not pass `/dev/ttyGS0` into Debian initially. The recovery/control channel
must remain owned by the global supervisor. The running kernel has
`CONFIG_DEVTMPFS=n`, so Debian must not assume a fresh devtmpfs will populate
devices; use an allowlisted bind model from the stock `/dev` tmpfs.

### Device Ownership Sequence

Each subsystem moves independently:

```text
preflight -> quiesce stock consumer -> prove fd release -> bind into Debian
          -> Debian functional probe -> commit ownership
```

On failure:

```text
kill Debian consumer -> remove namespace bind -> restart stock consumer
                     -> prove stock function -> report failure over ttyGS0
```

DRM/display, input, audio, and network must not be moved in one undifferentiated
step. Their transfer gates require separate host-only contracts and later fresh
live authorization.

## Direct-PID1 Research Track

The direct-PID1 line remains useful for understanding the boot boundary, but
not as the deployment architecture. A future candidate requires one of:

1. an already-enabled kernel-entry console;
2. a built-in retained backend active before userspace;
3. a narrowly instrumented boot kernel that records a one-bit checkpoint before
   `run_init_process()` and another immediately after successful exec handoff.

It must also retain the M31B-proven watchdog closure. Loading
`sec_log_buf.ko` from the candidate cannot serve as the first PID1 witness,
because that repeats the V3433 circular observation dependency.

No such candidate or live gate is authorized by V3434.

## Next Host Units

1. V3435: specify the native supervisor command/state protocol and the exact
   prerequisite bundle, including fail-closed restoration states.
2. V3436: implement and host-test the PID/mount namespace plus `pivot_root`
   launcher against a disposable rootfs; no device contact.
3. V3437: build a stock-first-stage overlay candidate that carries the
   supervisor but remains live unauthorized pending a separate review.
4. Separately design a pre-userspace kernel witness; do not reuse V3433 or any
   consumed direct-PID1 exception.
