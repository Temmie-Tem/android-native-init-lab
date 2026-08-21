# A90 boot-failure evidence channel — H0

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only static analysis
Device contact: none
Authority: none — this report creates no D0, D1, F1, manifest, approval, token,
candidate, or replay authority.

## Purpose

H27 is the only candidate that ever received a boot opportunity. It boot-looped
and its cause is recorded as unproved because the observation channel failed.
H28, H29, and H30 each stopped before a boot opportunity for a different
host-side reason. Before another boot opportunity is spent, this unit asks a
narrow question offline: **does a usable failed-boot evidence channel exist on
this device, and can it be read from the state a boot loop actually leaves the
device in?**

Everything below is derived from files already on the host plus two public
files fetched for this analysis. No device was contacted.

## Result

A usable channel exists and does **not** require mounting anything:
`/proc/last_kmsg`, mode `0444`, present in every relevant kernel including the
installed TWRP. The lab already consumes this exact source on the S22+ target
and has never used it on A90.

Separately, the `pstore entries=0` value currently cited as an A90 health signal
is a tautology and proves nothing.

## New facts

### 1. RKP CFP instrumentation is verified present in H30, on both axes

`CONFIG_RKP_CFP_JOPP=y` in a config does not imply the instrumentation exists.
`docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md` line 147 records why: the
flag reaches the build through `cc-option`, so an unsupporting compiler drops it
silently. The only way to know a rebuild emitted it is to count it in the
binary. That had not been done.

Counted directly in the kernel extracted from each boot image. JOPP uses
`CONFIG_RKP_CFP_JOPP_MAGIC=0x00be7bad`. ROPP was derived from
`scripts/rkp_cfp/instrument.py`, which rewrites `stp x29, x30, [sp,...]` into
`eor RRX, x30, RRK` + `stp x29, RRX, ...` with `RRX_DEFAULT=16`,
`RRK_DEFAULT=17`.

| kernel | JOPP magic | ROPP prolog | ROPP epilog |
|---|---:|---:|---:|
| V2321 stock — boots | 73,404 | 65,102 | 69,615 |
| H27 `nocfp` — boot-looped | 0 | 0 | 0 |
| H29 = H30 exact-toolchain | 73,415 | 65,113 | 69,625 |

H27 carried no CFP instrumentation at all. H30 restores all three counters to
within 0.02% of stock.

### 2. H29 and H30 kernels are byte-identical

Both are SHA-256
`59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac`,
49,827,613 bytes, confirming the goal's identity-only claim from the artifact
rather than from the build record.

### 3. H30's kernel configuration is identical to the booting resident's

Embedded `IKCFG` extracted from all three boot images. `V2321` versus `H30`
differ on zero lines of 6,928. `V2321` versus `H27` differ on exactly the nine
`RKP_CFP` lines already recorded on 2026-08-16. H30's version banner is also
byte-identical to stock, including Samsung's build identifier, build host,
`clang version 10.0.7`, and timestamp; H27's banner shows the wrong toolchain.
Kernel size matches stock exactly at 49,827,613 bytes.

### 4. H30 is not a bit-for-bit reproduction, and this is unresolved

55.4% of 4-byte words differ between the stock and H30 kernels. Classified by
the stock-side opcode: `bl` 5.7%, `adrp` 5.2%, `b` 2.2%, `adr` 0.8%, other
86.0%. Address-dependent data such as the `kallsyms` address table and function
pointer tables also shifts when layout shifts, so the 86% does not establish
different code — but nothing here establishes semantic equivalence either.
Offline analysis cannot settle this.

### 5. The `pstore entries=0` health signal is a tautology

Every A90 capture on the host reports the same native status line, 513
occurrences, no variation:

```
pstore=fs=yes mounted=no dir=yes entries=0 ramoops_cmdline=no module=yes params=9
```

`mounted=no`. An unmounted pstore directory is empty by construction, so
`entries=0` carries no information about device health or about whether a prior
boot recorded anything. `GOAL_A90.md` cites "pstore entries zero" as a proof
element in the H28, H29, and H30 reconciliations; that element should be
withdrawn or re-derived.

The `ramoops` reserved-memory node lives in the device-tree **overlay**, not in
any boot image:

```
ramoops@A1300000   reg = <0x0 0xc1300000 0x0 0x100000>
record-size / console-size / ftrace-size / pmsg-size = 0x40000 each
```

Four revision variants are present in the TWRP `dtbo.img`. The F1 owner writes
only `boot`, and `twrp.flags` lists `/dtbo` as a separate flashable partition
the owner never touches, so this region is provided identically to the
candidate, the rollback, and TWRP.

### 6. `/proc/last_kmsg` is readable without mounting, in every relevant kernel

`drivers/samsung/debug/sec_log_buf.c:163` creates the node:

```c
#define LAST_LOG_BUF_NODE "last_kmsg"
entry = proc_create_data(LAST_LOG_BUF_NODE, 0444, NULL, &last_log_buf_fops, NULL);
```

`CONFIG_SEC_LOG_LAST_KMSG=y` in V2321, H27, H30, and the installed TWRP kernel.
Its backing region is provisioned from the kernel command line via
`early_param("sec_log", ...)`, not from the device tree; 118 device
observations report `sec_debug_or_sec_log=yes`, so the bootloader does pass one
of those parameters.

A richer Samsung post-mortem set exists — `/proc/reset_reason`,
`/proc/reset_klog`, `/proc/reset_summary`, `/proc/reset_tzlog`,
`/proc/auto_comment`, all `0444`, from `sec_debug_user_reset.c` — but it is
gated by `CONFIG_SEC_USER_RESET_DEBUG`, which is `y` in V2321, H27, and H30 and
**not set** in the TWRP kernel. A boot loop leaves the device in TWRP, so only
`/proc/last_kmsg` is available in the state that actually matters. The richer
set opens only if a candidate boots far enough for native init to run.

The lab already treats this source as reviewed evidence on the sibling target:
39 S22+ device-action manifests declare `"source": "/proc/last_kmsg"` with a
decoder, policy identifier, and source contract. A90 has never used it.
The A90 work should port that pattern rather than invent one.

## Corrections to claims made earlier in this session

1. **"The H30 candidate image carries the ramoops node" is wrong.** The `grep`
   counts behind that claim were the ramoops driver's own `printk` strings, its
   module-parameter names, the device-tree property-name literals inside
   `fs/pstore/ram.c`, and the lab's own `a90_changelog.c` text. No boot image
   contains the node. The node is in the overlay, as recorded above.

2. **"TWRP uses the stock Samsung kernel" is wrong.** `TARGET_PREBUILT_KERNEL`
   supplies a third-party custom kernel, `4.14.334-ShareMyPerf`, not stock
   `4.14.190`. The conclusion that pstore is available survives, but it now
   rests on the extracted `IKCFG` of that kernel rather than on stock lineage.

## Withdrawn

The earlier statement that the evidence design must first classify a
`mount -t pstore` action under the mount counters is withdrawn. `/proc/last_kmsg`
requires no mount, so that decision is not on the critical path.

## What remains unresolved offline

1. Whether `sec_log=` specifically, rather than only `sec_debug`, is present on
   the command line. The native summary field is an OR of the two. One read of
   `/proc/cmdline` settles it.
2. Whether `/proc/last_kmsg` is non-empty in TWRP after a failed boot.
3. Whether the backing DRAM survives this SoC's watchdog-bite reset path
   (`CONFIG_QCOM_FORCE_WDOG_BITE_ON_PANIC=y`, `CONFIG_PANIC_TIMEOUT=-1`).
4. Whether H30 boots.

Items 1 and 2 are reads, and the F1 owner already opens a root shell in TWRP for
`sha256sum` and `dd`, so they introduce no new capability class. Items 3 and 4
require a boot opportunity.

## Inputs recorded

Two public files were fetched for this analysis and kept under
`workspace/private/`:

| file | size | SHA-256 |
|---|---:|---|
| `prebuilt-kernel` | 44,428,140 | `609d8f83864e85910c0d85c23ff99a5ab3841ada7c43c41fe6a42f675420f2bc` |
| `prebuilt-dtbo.img` | 1,077,581 | `63c519fbbc9ae41cfcc813b3334daab0844267ed90a96361a9658070a44032e2` |

Source: `github.com/Roynas-Android-Playground/device_samsung_r3q-twrp`. That
tree is confirmed to be the origin of the installed recovery: its
`recovery/root/system/bin/rebootsystem.sh` is 89 bytes at SHA-256
`3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`, matching the
TWRP identity already pinned in
`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_backend_v1.py`.
There is no official TWRP build for `r3q`. Nothing was written to any device.

## Relationship to prior work

The CFP deviation, the `cc-option` silent-drop mechanism, and the exact
Snapdragon LLVM 10.0.7 requirement were all recorded on 2026-08-16 in
`docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md`, and the exact-toolchain
rebuild was already carried out for H29 and H30. This report does not
rediscover them. Its additions are the binary confirmation that the rebuild
actually emitted both CFP axes, the tautology in the pstore health signal, and
the identification of a mount-free evidence channel that the sibling target
already uses.
