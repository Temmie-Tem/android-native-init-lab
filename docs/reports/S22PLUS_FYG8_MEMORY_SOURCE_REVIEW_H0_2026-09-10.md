# S22+ FYG8 memory settings and allocation paths: H0 source review

The operator requested a memory review alongside source inspection. This unit
examined the consumed P380 candidate's actual embedded configuration, generated
renderer, retained native observations and the relevant kernel implementations.
It made no configuration/code change and contacted no device. The prior P380
NO_PROOF, rollback and final-health result remain unchanged. This is analysis,
not qualification of a memory-release capability or a new candidate.

The most useful next attribution targets are the 800 MiB RBIN reservation,
89.594 MiB Shmem and approximately 46 MiB unreclaimable slab. Several enabled
debug/pool options have conditional or small costs and are lower priorities.

## Bound inputs

The actual P380 `fixed-Image` is 41,490,944 bytes, SHA-256
`13e482969b6ecd0498de901e8bb223434d4dbca4f70437740f5b7ad195825417`.
Its extracted IKCONFIG is 185,508 bytes, SHA-256
`91c1b48522931f6cdbcb6da9d472af4b8a93bba5b833e511d9c7df26a2067cc5`,
matching the existing candidate build result. A prepared vendor `.config`
was not substituted for this input.

Kernel source references below are relative to the retained private
`s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel` tree.
The display allocator reference is the separate retained
`s22-display-build-h0/display-drivers/msm/msm_gem.c`, whose bytes match the
existing KMS source fixture. The generic in-tree MSM driver was not used to
infer this module's allocation behavior. The actual generated P380 renderer
was inspected, including allocation, matched-event retirement and its loop.
Source branches explain possible behavior; they are not a native branch trace.

## Accounting: the adjusted 254 MiB also contains an availability estimate

The retained native samples give this exact arithmetic decomposition:

| Expression | Early MiB | Late MiB |
| --- | ---: | ---: |
| MemTotal - RbinTotal - MemFree | 221.742 | 222.113 |
| MemFree - MemAvailable | 31.996 | 31.805 |
| Sum: MemTotal - RbinTotal - MemAvailable | 253.738 | 253.918 |

`mm/page_alloc.c:5618` computes availability from free pages minus reserves,
plus estimated reclaimable file/slab memory; `fs/proc/meminfo.c:72` applies
the vendor RBIN adjustment. Thus the second row is the net estimator gap,
not a measured allocation or an exact value of `totalreserve_pages`.
Reducing watermarks to shrink that row would change allocator headroom and
the displayed estimate; it would not by itself free occupied pages.

The first row is also an accounting difference, not an exact full kernel or
process footprint. Memory excluded from MemTotal is not restored by this
formula. Shmem, Cached, slab, VmallocUsed, mappings and module sizes cannot be
added as independent components without resolving their overlap.

## Settings and their actual consumer conditions

| Setting in actual Image | Source finding | Assessment |
| --- | --- | --- |
| `CONFIG_RBIN=y` | DT reservation precedes provider initialization; disabling this option does not remove the generic reservation | Largest capacity design candidate; ownership and surviving consumers still unresolved |
| `CONFIG_CMA=y`, `CONFIG_DMA_CMA=y`, default size16MiB | Native aggregate CMA444MiB, of which only3.371/3.488MiB was nonfree in the two samples | Do not budget444MiB as occupied or treat the default as the aggregate; map areas/consumers before tuning |
| `CONFIG_PAGE_OWNER=y`, `CONFIG_PAGE_PINNER=y`, `CONFIG_PAGE_EXTENSION=y` | Both need callbacks are false initially; page extension allocation is skipped when no consumer requests it | Enabled config does not prove a large per-page allocation; effective boot arguments matter |
| `CONFIG_KASAN_HW_TAGS=y`, generic/software-tags variants unset | `kasan_init_hw_tags()` checks MTE support and the `kasan` argument; stack collection has its own condition | Do not apply a generic KASAN shadow-memory percentage to this image |
| `CONFIG_KFENCE=y`,63objects,4KiB pages | Pool formula `(objects+1)*2*PAGE_SIZE` gives524288bytes | Configured pool is0.5MiB, excluding metadata; small compared with RBIN/Shmem, runtime activation unverified |
| `CONFIG_SLUB_DEBUG=y`, `CONFIG_SLUB_DEBUG_ON` unset | Debug support is built, default full SLUB debugging is not selected | No evidence that debug redzones/tracking explain the observed slab; final arguments and cache attribution are missing |
| `CONFIG_DEBUG_INFO=y`, DWARF4, BTF unset | ARM64 Image construction uses binary objcopy with `-S` | Large host debug information is not an equivalent resident Image allocation; low-priority RAM optimization |
| `CONFIG_HUGEPAGE_POOL=y`, `CONFIG_KZEROD=y` | Quota function returns1GiB only above10GiB physical RAM; otherwise zero, and initialization skips the pool/threads on zero quota | Source predicts no such pool for the8GiB target, consistent with both native HugepagePool=0 observations |
| `CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y` | Pool policy above is separate from transparent hugepage support; native AnonHugePages/ShmemHugePages were zero | No measured hugepage allocation to reduce in these samples |
| `CONFIG_ZRAM=m`, `CONFIG_SWAP=y` | ZRAM is absent from the18 packaged modules and native SwapTotal/SwapFree are zero | No observed active swap capacity; adding compression is not a demonstrated solution to this mostly non-anonymous footprint |
| `CONFIG_NR_CPUS=32` | Native Percpu=1856KiB and KernelStack=2752KiB were observed | Possible later static sizing study;32 is not evidence of32 running CPUs or a proportional saving |

Key source locations are `mm/page_owner.c:43`, `mm/page_pinner.c:67`,
`mm/page_ext.c:91` and `:468`, `mm/kasan/hw_tags.c:156`,
`include/linux/kfence.h:22`, `mm/kfence/core.c:647`,
`mm/kzerod.c:485` and `:1023`, and `arch/arm64/boot/Makefile:17`.
The hugepage quota's nearby comment says2GB@12GB, while the executable branch
returns1GiB above10GiB; the code and measured zero take precedence here.

One concrete configuration trap: this source's `early_page_pinner_param()`
sets its flag true without parsing the value. Therefore `page_pinner=off`
would also enable that handler's flag; it is not a valid disable spelling in
this implementation. No boot arguments were changed.

The embedded `CONFIG_CMDLINE` already includes `stack_depot_disable=on` and
`kasan.stacktrace=off`, with `CONFIG_CMDLINE_EXTEND=y`. The boot-v4 candidate
header contains no matching memory-debug override tokens in the inspected
field. Neither input proves the final combined command line: vendor/DT/
bootloader arguments and their ordering were not recovered for this native
sample. Do not claim PAGE_OWNER/PINNER/KASAN/KFENCE runtime state from config
alone. `lib/stackdepot.c:152` confirms the separate depot-disable parser.

No security hardening option was disabled. Allocation zeroing, freelist
hardening and stack protection have no demonstrated large removable memory
cost in the retained evidence.

## Shmem and the HUD buffer lifetime

The actual renderer requests1080x2340 pixels with4352-byte pitch:
10,183,680 bytes, rounded by the GEM allocator to10,186,752 bytes
(9.715MiB) per buffer. The normal userspace loop holds the current buffer and
one fresh buffer during a flip, about19.430MiB of rounded backing size.
After the exact matching flip event it removes the old framebuffer, unmaps
the pixels and closes the GEM handle. This bounds userspace-held buffers on
that successful path; it does not prove immediate destruction of every
kernel reference, or prove the absence of a driver leak.

The selected MSM allocator has both VRAM and ordinary GEM branches. In the
ordinary GEM branch, `drm_gem_object_init()` creates a shmem backing file and
`drm_gem_get_pages()` obtains its pages. Therefore display backing is a
concrete possible contributor to Shmem, but that branch and each live object's
attribution were not captured. The renderer buffer sizes do not account for
all89.594MiB Shmem by themselves. The earlier15.762MiB ramdisk inventory also
cannot be equated to this whole counter.

References: generated renderer `allocate_buffer()` and main loop;
display `msm_gem.c:84`, `:1156`, `:1021`; core `drivers/gpu/drm/drm_gem.c:130`.
Reusing buffers might reduce allocation churn, but changing the reviewed
immutable-buffer lifecycle requires proving CPU/scanout synchronization.
It is not a demonstrated memory saving and was not implemented here.

## Useful next work and validation

1. Map RBIN's boot reservation to the final DT and surviving consumers; keep
   real capacity changes separate from HUD presentation changes.
2. Attribute Shmem and unreclaimable slab using bounded per-owner totals in
   an otherwise authorized future observation. Avoid another burst of full
   process output: the existing1536-byte output-loss incident remains open
   for any changed observer design.
3. Resolve the effective native memory-debug arguments before considering
   PAGE_OWNER/PINNER or other conditional diagnostics as optimization targets.
4. Treat CMA defaults, watermark changes, DWARF removal and the zero hugepage
   pool as lower priorities until evidence identifies a concrete benefit.

H0 checks re-extracted and matched the Image configuration, verified the
display source fixture identity, recomputed the retained sample arithmetic
and checked source/document identities. No new build or runtime test was
needed for this documentation-only analysis. Exact source hashes and derived
numbers are retained privately at
`workspace/private/outputs/s22plus-memory-source-review-h0-20260910-1/findings.json`
(5588bytes, SHA-256
`e51afe1d56ca2982842ba43a2fc5485da36fcc3eaffde0a66861dc7eeaa741cb`).
The [prior rc.3 report](S22PLUS_FYG8_GAUGE_MODEL_MEMORY_RC3_H0_2026-09-10.md)
retains the raw-evidence limits and earlier accounting findings.

## Follow-up: retained vendor ramdisk and merged DT attribution

The operator accepted further investigation and requested other useful checks.
This follow-up remained H0: it read retained files, decompressed archives in
host memory, merged the two applicable stock DT bases with the board12 overlay,
and examined ELF section sizes and the current explicit module plans. No device
was contacted, no filesystem on a device was cleaned, and no configuration,
partition or candidate changed.

### A larger Shmem candidate: the vendor ramdisk was outside the earlier inventory

The earlier 15.762 MiB inventory covered only the candidate boot ramdisk.
The retained original FYG8 vendor_boot, verified against SHA-256
`096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
contains one vendor ramdisk fragment. That exact fragment matches the retained
compressed vendor ramdisk and expands to 63,974,144 bytes of newc data.
Both archives were parsed with the existing strict newc parser.

| File inventory | Regular files | Logical bytes | Sum rounded per file to4KiB |
| --- | ---: | ---: | ---: |
| Stock vendor ramdisk | 449 | 63,910,792 | 64,860,160 |
| P380 boot ramdisk | 30 | 16,527,132 | 16,584,704 |
| Combined names, vendor followed by candidate | 479 | 80,437,924 | 81,444,864 |

No regular-file path overlaps or regular-file hardlinks were found in these
inputs. The combined page-rounded size is **77.672 MiB**, not15.762 MiB.
The kernel's initramfs path unpacks into rootfs; with TMPFS enabled, rootfs
selects shmem when the relevant root arguments do not select another backing.
The retained candidate, vendor header and merged DT have no root/rootfstype
override in the inspected fields. Their contents do not prove the final
bootloader arguments or an exact same-boot filesystem block count.

This yields a useful attribution hypothesis: 77.672 MiB of rounded file data
plus one9.715MiB HUD backing buffer leaves2.207MiB relative to the measured
89.594MiB Shmem. The closeness is not a per-page ownership proof. Unpacking,
rootfs backing, file lifetime, other tmpfs files and the number of live GEM
references still need direct attribution. The previous unexplained Shmem
should not be labelled a leak from the15.762MiB inventory alone.

There is also a scope correction to the earlier module count:18 refers to
the display/return package. The full candidate contains19 `.ko` files,
including the423232-byte `s22plus_dwc3_event_latch.ko` under `/lib/modules`.
The earlier11.109MiB module-byte sum was that18-file subset, not all candidate
module files. The overall15.762MiB regular-file inventory already included
the extra module, so its byte total does not change.
Likewise, the vendor archive does contain `lib/modules/zram.ko`; it is absent
from the current explicit load plans. The earlier18-file package observation
must not be read as absence from the full boot environment. Native SwapTotal=0
remains the observed reason not to claim active swap capacity.

### A concrete file-retention reduction candidate

The generated initial module plan names73 files. The actual display plan
names13 more and the return preparation names5 distinct files. Those91 paths
were checked against the archive. Across the460 module files in the combined
archives,369 are absent from these explicit plans:

| Module-file category | Count | Logical bytes | Page-rounded MiB |
| --- | ---: | ---: | ---: |
| Selected by initial/display/return plans | 91 | 17,903,816 | 17.250 |
| Not selected by those plans | 369 | 57,932,664 | 55.988 |

This supports investigating cleanup of unnecessary files in the RAM rootfs
as a roughly56MiB file-retention candidate. It does not qualify369 files for
deletion. A cleanup design must first establish actual RAM backing, exact
file identities, absence of later consumers and retention of all console,
display and return prerequisites. Loaded module allocations and the stored
`.ko` file pages are distinct. No module unload or vendor_boot modification is
needed merely to investigate an eventual RAM-file cleanup design.

ELF section inspection found only458380bytes (0.437MiB) of `.debug*`/`.zdebug*`
sections across all460 module files; none were in the369 unselected files.
Blind debug stripping therefore has little relevant benefit. SHF_ALLOC and
NOBITS totals were retained privately for reference, but are not measured
loaded-module memory because allocation alignment, metadata and init-section
lifetimes differ.

The native console's `tmpfs size=64m` work directory is a size limit, not a
64MiB allocation at mount. `mm/shmem.c` stores that limit in max_blocks and
allocates pages separately as data is populated. Lowering this limit would
not by itself release64MiB.

### RBIN and the full444MiB CMA map

Both applicable vendor DT bases, each merged with the retained board12 overlay
(index10), have identical reserved-memory records and memory-region references.
The 800MiB `/reserved-memory/rbin` node has `reusable` but no
`shared-dma-pool` compatible. Its sole explicit memory-region reference in
each merged tree is `/soc/qcom,dma-heaps/rbin_dma_heap`, heap type3.
This confirms the exact retained DT linkage beyond the earlier r07 source
example. Bootloader fixups and the final running FDT remain outside this H0
observation; a single DT reference is not proof of exclusive runtime use.

Thirteen enabled, reusable shared-dma-pool regions without no-map sum to
exactly444MiB, matching both retained native and Android CmaTotal:

| Region | MiB |
| --- | ---: |
| non_secure_display | 164 |
| mem_dump | 48 |
| demura_heap | 40 |
| linux,cma | 32 |
| qseecom_ta | 32 |
| audio_cma | 28 |
| qseecom | 28 |
| sp | 16 |
| user_contig | 16 |
| va_md_mem | 16 |
| adsp_heap | 12 |
| sdsp | 8 |
| cdsp_eva | 4 |

The32MiB `linux,cma` node is explicitly linux,cma-default. The source skips
the configured fallback allocation when a default area already exists, which
explains why CONFIG_CMA_SIZE_MBYTES=16 is not the default area's actual DT size
or the aggregate. The disabled32MiB WLAN region is excluded from this sum.
Most of the measured native CMA was free; none of these capacities is thereby
a proved saving, and display/security/remoteproc ownership remains material.

The retained qcom_dma_heaps module file exists in the vendor archive but is
absent from the91 explicit module paths. Its source bundles RBIN with other
heap creation: probe creates system and secure heaps and then traverses the
DT heap catalog. Inserting it is not a statistics-only observation or an
isolated way to lend800MiB. No such insertion was attempted.

### Additional configuration finding and remaining measurement gap

Both merged trees carry `kasan=off` in `/chosen/bootargs`. This strengthens
the evidence against treating CONFIG_KASAN_HW_TAGS=y as a large active native
allocation, while preserving the missing final effective-command-line check.
The inspected vendor header/bootconfig add no memory-debug override tokens.

The approximately46MiB SUnreclaim still has no same-boot per-cache attribution.
The next useful native observation is a compact set of rootfs backing/block
totals, effective memory-debug arguments, GEM owner totals and largest slab
caches. An Android-only slab census would describe another workload and cannot
retroactively decompose P380. This analysis did not start a native experiment
to fill that gap. Any prospective collector must account for the existing
output-loss incident before joining a new candidate.

The nearest useful reduction design is now RAM-file retention, followed by
RBIN reservation ownership. Watermark tuning, a new swap setup, blanket
module stripping and enabling the full heap provider are not justified as
immediate optimizations by these results.

All artifact/source hashes, archive counts, plan membership and DT totals
were checked. The two-file documentation update also passed local-link,
goal-length, diff and repository-boundary checks. Private outputs are under
`workspace/private/outputs/s22plus-memory-followup-h0-20260910-1/`:

| Derived artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| ramdisk-inventory.json | 103,929 | `77ca8efdfefdfe34987ef094047942cc54c259313c751b8643c207c5bbc48945` |
| dt-reservations.json | 68,929 | `4b4f18e51fd5ca15ec4aaf403741236460642349997fee516214adb5d6002730` |
| module-attribution.json | 120,715 | `e29f524dea44a6eba99b73ca0d32d758fa848934dcdb5541c7af6e78a49b8e7b` |
| summary.json | 5,170 | `5da12b78f6746b9fda1bbbeeadaf498905eae8edba0ae4322a15c11b8094752f` |
