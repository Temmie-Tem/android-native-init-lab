# S22+ FYG8 P2.25 target guard and PoC flush host pass

Date: 2026-07-22 KST
Tier: H0, host-only implementation, build, and linked audit
Status: `PASS_P225_GUARD_AND_POC_FLUSH_HOST_ONLY`
Live authority: none

## Result

P2.25 fixes the deterministic P2.23 target-guard failure identified by P2.24.
The patch replaces generic parent-bus resource parsing with an exact
current-node 2/2-cell parser and adds a bounded arm64 cache-clean/readback
sequence around the unchanged ENTRY, USERSPACE, and UNSAT record bytes.

The source contract, exact stock-DT regression, clean Full-LTO build, and two
independent linked-binary toolchains pass. This establishes that the reviewed
machine code contains the intended copy, cache maintenance, and readback
sequence. It does **not** establish that a record survives reset; that remains
a live acceptance property.

Patch SHA256:

```text
fbbbcc43685f4899fdceb95d4b8b9e92d111fad07bfaf582752aa8c36ccf9254
```

## Target Guard

The patched guard requires, before `phys_to_virt()` or any retained access:

1. exact FYG8 root model and `samsung,kernel_log_buf` compatible;
2. node availability and `sec,strategy == 3`;
3. current-node `#address-cells == 2` and `#size-cells == 2`;
4. one exact 16-byte `reg` value;
5. decoded base `0x800200000` and size `0x200000`; and
6. unchanged retained-header and index guards.

The exact stock rev-12 overlay was applied to both applicable Waipio bases.
Both reconstructions preserve the Samsung node shape and prove the direct-map
prerequisites: its `memory-region` resolves to
`/reserved-memory/sec_debug_region_log@8001FF000`, that region covers the full
log range, and it has no `no-map` property. The regression also keeps the P2.24
semantic discriminator: current-node 2/2 parsing yields `0x800200000`, while
parent 1/1 parsing yields `0x8`.

## Store Sequence

Both the kernel ENTRY path and procfs USERSPACE path compile to the intended
bounded order:

```text
copy payload
__flush_dcache_area(slot, proof_size)
read back and compare payload
recheck retained header state
```

The linked flush helper contains `dc civac` and a final `dsb sy`. The kernel
path has exactly one flush call and the userspace writer has exactly one flush
call. No retained `magic`, `idx`, `prev_idx`, or `boot_cnt` write was added.

This is a cache-flush PoC, not a reset-durability proof. Source, contract output,
and linked audit all explicitly report `reset_retention_proven: false`.

## Full-LTO Build

The source-pinned build command completed successfully:

```text
./kernel_platform/build/android/prepare_vendor.sh sec gki
build command rc: 0
elapsed: 35:25.57
maximum RSS: 24,244,452 KiB
swaps: 0
```

The build restored all three patched source files to their exact base content.
The first P2.25 wrapper result returned 7 only after compilation because that
version required the absent host path
`/usr/bin/aarch64-linux-gnu-objdump`. Its output cardinality and fixed-layout
checks had otherwise passed. No rebuild was performed. The audit adapter now
falls back to the pinned LLVM tools, and the exact produced artifacts were
audited separately.

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `Image` | 41,490,944 | `242909cf62c6ee1642f81da6c8d0cece3041d619a13f01e6f4ded5ee7957352a` |
| `vmlinux` | 476,936,664 | `be763ff7ea70c3c3c59b6305fc514f9a1ae75b42a464b252fba519829eb9496f` |
| compiled `.config` | 185,347 | `cf6f6c91bc572daa7d6d44cf6ac7a693698443ed32dc1a0748b769bf99329684` |
| original build result | - | `39f54cbc2349b127ea56083044640c00e6c061167ad4cadb48603296eec4f0a5` |

The Image retains the exact stock-sized kernel slot and 1,536 bytes of
pre-ramdisk slack. Image and vmlinux contain exactly one USERSPACE record, one
UNSAT record, two long-family records, one UNSAT-family record, and zero
retired E0 records.

## Linked Audit

GNU AArch64 tools on the operator host and the pinned LLVM tools on the build
host independently produced the same normalized function identities:

| Function | Normalized machine-code SHA256 |
| --- | --- |
| `__pi___flush_dcache_area` | `92f72446764c8641ba8f966400b3622c51c951e75679b44ed1483285fdd9b886` |
| `s22plus_fyg8_p1s_write` | `19ad2fc98978b0e26ed102e2485b357890db0943133636e3b9f1a33d5d2f41eb` |
| `s22plus_fyg8_p1s_head` | `ac393f9f7a02829d4971e9d4eae76cacbb47268047126733cf2a9cf0ce52d919` |
| `kernel_init` | `c0810cf558d4e6cfa278d7d577d40fc6bcf3c1c81edf25a9a2043485d787b1c1` |

The audit also proves the corrected guard no longer calls
`of_address_to_resource()` or `of_get_address()`, and verifies the ordered
guard, ENTRY-store, and USERSPACE-store call subsequences. The symbol-range
collector was changed from quadratic scanning to one adjacent-address map;
the same real-artifact audit fell from minutes to 1.1 seconds locally and 6.5
seconds on the older build host.

## Independent Review Closure

Independent review found two load-bearing issues before close:

- source ordering plus a cache flush was being described too strongly as
  reset durability; all claims and result fields now say PoC and keep reset
  retention unproved;
- the initial linked audit depended on one absent GNU tool path and brittle
  symbol disassembly; it now pins the exact vmlinux, normalized function
  bytes, range disassembly, call order, and GNU/LLVM-equivalent output.

It also requested an exact direct-map premise. The stock-DT contract now binds
the memory-region phandle, containing reserved range, compatible, and absence
of `no-map` on both applicable merged bases.

## Validation

- Python compilation: pass.
- Default focused tests: 12 tests, pass with one explicitly gated private-ELF
  integration test skipped.
- Private exact-vmlinux GNU integration audit: pass.
- Build-host pinned-LLVM integration audit: pass.
- Standalone source and stock-DT contract:
  `PASS_P225_GUARD_AND_POC_FLUSH_IMPLEMENTATION_HOST_ONLY`.
- `file`: ARM64 Linux kernel Image and AArch64 linked ELF.

## Boundary And Next Unit

This unit contacted no device, invoked no Odin transport, created no boot
candidate or AP, created no ready manifest, and grants no D0, D1, F1, or live
authority.

P2.26 is H0 only: construct one deterministic boot-only candidate from the
exact P2.25 Image and independently re-derive its artifact closure. It must not
create Process v2 ready data, contact the device, or imply live authority.
