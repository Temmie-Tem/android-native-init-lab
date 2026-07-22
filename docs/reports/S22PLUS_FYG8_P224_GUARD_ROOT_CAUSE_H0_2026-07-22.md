# S22+ FYG8 P2.24 guard root-cause analysis

Date: 2026-07-22 KST
Tier: H0, host-only analysis
Status: `PASS_P224_GUARD_ROOT_CAUSE_ISOLATED_HOST_ONLY`
Live authority: none

## Question

P2.23 transferred the exact P2.21 candidate and rollback once and finished with
healthy Android, but two complete byte-identical `/proc/last_kmsg` reads were
`ZERO_AMBIGUOUS`. This unit asks where the candidate path first becomes
deterministically unable to write ENTRY or UNSAT. It does not infer candidate
selection from Odin completion and does not create another candidate.

## Root Cause

The P2.19 target guard uses `of_address_to_resource(log_node, 0, ...)` and then
requires the returned start address to equal `0x800200000`. That generic helper
does not implement the Samsung encoding used by this node.

Host reconstruction used the exact FYG8 stock `vendor_boot.img`, the active
g0q revision-12 entry from stock `dtbo.img`, and both applicable Waipio base
DTBs. In both merged trees the relevant shape is:

```text
node path                       /soc/samsung,kernel_log_buf
reg cells                       0x8 0x200000 0x0 0x200000
node #address-cells/#size-cells 2 / 2
parent /soc cells               1 / 1
```

The exact FYG8 Samsung helper `sec_of_parse_reg_prop()` deliberately reads the
current node's cell counts. It therefore decodes the property as:

```text
base = 0x00000008_00200000 = 0x800200000
size = 0x00000000_00200000 = 0x200000
```

Linux `of_get_address()`, which backs `of_address_to_resource()`, derives cell
counts from the parent bus. For index zero it therefore decodes the same bytes
as:

```text
start = 0x8
size  = 0x200000
```

The rooted stock bind name `8.samsung,kernel_log_buf` is live evidence
consistent with this generic resource address. The actual P2.21 `vmlinux`
calls `of_address_to_resource()`, compares the returned start with
`0x800200000`, and returns `NULL` on mismatch. The compiled post-exec path then
returns before reading retained magic or index and before calling `memcpy()`.

Verdict: P2.23 did not test ENTRY/UNSAT storage or cache-to-DRAM persistence.
Its first deterministic failure is the target guard's parser mismatch.

## Prior-run Reconciliation

| Run | Address parser | Other material gate | Result | Interpretation |
|---|---|---|---|---|
| R4W1-D | direct pinned physical address | saturated index | exact 45-byte marker retained | direct map and one store lifecycle live-proven |
| R4W1-E E1 | generic OF resource parser | 173-byte carrier | zero | same parser mismatch prevents carrier initialization |
| R4W1-E0 | direct pinned physical address | saturated index | zero | not explained by this bug; selection, saturation, and durability remain open |
| P2.23 | generic OF resource parser | 45/24 index split | zero | parser mismatch occurs before either index branch |

The three zero runs must not be treated as three repetitions of one failure.
E1 and P2.23 share the confirmed parser defect; E0 does not.

The P2.23 retained observer itself remained healthy: both reads were complete
and byte-identical, and the surrounding XBL generations form the same ordered
shape seen in R4W1-D. This lowers observer-file failure and wholesale retained
lifecycle loss, but does not create candidate-selection evidence.

## Corrected Parser Contract

The next implementation must not use `of_address_to_resource()` for
`samsung,kernel_log_buf`. Before deriving a physical pointer it must:

1. require the exact model, compatible node, availability, and strategy 3;
2. require current-node `#address-cells == 2` and `#size-cells == 2`;
3. require an exact 16-byte `reg` property;
4. decode base and size with `of_read_number()` using those current-node counts;
5. require exact base `0x800200000` and size `0x200000`; and
6. only then use `phys_to_virt()`.

This is a stricter local equivalent of `sec_of_parse_reg_prop()`. It avoids a
new dependency from common GKI `init/main.c` on a vendor header while retaining
the exact FYG8 semantics.

## Reset-durability Contract

P2.19 emits `memcpy(); smp_wmb(); memcmp()`. The linked machine code contains a
`dmb ishst` but no data-cache maintenance. The barrier orders stores; it does
not prove that the changed cache line reached a reset-surviving coherency point.

For this arm64 kernel, `__flush_dcache_area(addr, len)` is declared by
`asm/cacheflush.h`, linked in the exact `vmlinux`, and used by existing built-in
code. Its implementation performs `dc civac` over every covering line followed
by `dsb sy`, cleaning and invalidating to the point of coherency. Because the
candidate excludes `sec_log_buf.ko` and every other ring writer, flushing the
24- or 45-byte slot and its covering cache lines has no concurrent-writer race.
Cleaning before invalidation also preserves adjacent bytes, including the
header if a position-zero slot shares its cache line.

The next store sequence should therefore be:

```text
memcpy(slot, proof, proof_size)
__flush_dcache_area(slot, proof_size)
memcmp(slot, proof, proof_size)
recheck magic, idx, and boot_cnt
```

The post-flush `memcmp()` refills invalidated lines and checks the lower-level
copy. This is narrower and more testable than enabling the unused persistent-
memory API or adding a new retained channel. It does not prove survival of a
power loss; the required property is bounded warm-reset retention.

## Static Regression Requirements

Before another build or F1 preparation, the changed closure must prove:

- the source contains the exact current-node 2/2-cell parser and no generic
  resource helper for this node;
- a model of the exact stock merged node produces `0x8` under parent-cell
  parsing and `0x800200000` under Samsung current-node parsing;
- all applicable Waipio base DTBs produce the same node path and cell shape;
- linked `vmlinux` calls `__flush_dcache_area()` after the payload copy and
  before readback;
- the compiled store reaches neither physical memory nor cache maintenance
  before every target/layout guard passes; and
- ENTRY, USERSPACE, and UNSAT wire bytes and Process v2 machinery remain
  unchanged.

Standard `fdtoverlay` leaves the Qualcomm base root `model`, while rooted stock
live evidence reports the Samsung g0q model. The regression must therefore use
the merged artifact for node/parent/reg geometry and keep the exact root-model
predicate bound to the existing live D0 evidence; it must not claim that a
generic host overlay tool reproduces Samsung bootloader top-level metadata.

## Process Finding

The P2.19 checker required the literal generic helper as a positive source
marker. It verified implementation shape but not the helper's semantics against
the actual parent/current-node cell mismatch. P2.20 reviewed the physical range
and direct mapping but inherited that assumption. The corrected checker must
test the vendor encoding rather than requiring an API name.

## Next Unit

P2.25 is H0 only: implement the corrected parser, bounded cache flush, exact
stock-DT regression model, source checker changes, focused tests, and linked
binary audit. It may build host artifacts for static validation, but creates no
ready manifest, connected binding, approval, or live authority.
