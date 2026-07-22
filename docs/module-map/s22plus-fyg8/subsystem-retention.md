# Retention Subsystem

## Status

`SOURCE_VERIFIED + LIVE_BOUND` on the rooted FYG8 Android baseline. A direct
kernel write into the existing retained ring is also `LIVE_PROVEN` for the
R4W1-D 45-byte contiguous pre-cursor witness, even though the candidate did not
load the owner module. Direct candidate `printk` capture without the owner and
the E0 zero-carrier branch remain `UNVERIFIABLE`; P2.24 isolated E1 and P2.23 at
their pre-store target guard.

| Module | Stock order | Hard deps | Softdeps | Role | Runtime proof |
|---|---:|---|---|---|---|
| `sec_log_buf.ko` | 2 | none | none | reserved-memory printk ring; creates `/proc/last_kmsg` and `/proc/ap_klog` | `8.samsung,kernel_log_buf` bound |
| `sec_debug.ko` | 105 | none | none | panic notifier, statistics, MID/upload controls | `soc:samsung,sec_debug` bound |

Exact hashes:

```text
sec_log_buf.ko b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61
sec_debug.ko   9936d5622f55530480bd167ba4ca000cbc7c6dbb2bc9c99623b895a4ae087d3d
```

## Load-Bearing Conditions

`sec_log_buf.ko` requires more than an empty `depends=` field:

1. Exact FYG8 GKI ABI and exported `android_vh_logbuf` hooks.
2. DT compatible `samsung,kernel_log_buf`.
3. DT `sec,strategy=3` (`SEC_LOG_BUF_STRATEGY_VH_LOGBUF`).
4. A valid DT `memory-region` reserved-memory phandle and range.
5. Successful platform-driver probe and procfs registration.

## FYG8 `reg` Encoding Trap

The merged FYG8 node is `/soc/samsung,kernel_log_buf`. Its `reg` property is
four cells (`0x8 0x200000 0x0 0x200000`), the node declares current-node
`#address-cells=2` and `#size-cells=2`, while parent `/soc` declares `1/1`.

Samsung's `sec_of_parse_reg_prop()` intentionally uses the current node's cell
counts and obtains physical base `0x800200000`, size `0x200000`. Generic
`of_address_to_resource()` uses the parent bus counts and obtains resource index
zero at `0x8`, size `0x200000`. The live platform name
`8.samsung,kernel_log_buf` is consistent with the generic resource value.

R4W1-E E1 and P2.23 used the generic helper and therefore rejected the target
before touching retained magic, index, or payload. Future direct-ring guards
must use an exact current-node 2/2-cell parser and must regression-test this
semantic difference against the stock DT artifacts.

`sec_debug.ko` separately requires DT compatible `samsung,sec_debug` and
`sec,panic_notifier-priority`. MID can affect Samsung panic/upload behavior but
does not instantiate the retained printk ring.

## Candidate Consequence

The O3/O3F 59-module plan included `sec_debug.ko` and omitted
`sec_log_buf.ko`. O3R1 loaded neither. Their retained marker misses therefore do
not disprove marker retention with the actual owner active.

## Observed Carrier Geometry

The retained payload is `0x1ffff0` bytes (2,097,136 bytes) after the 16-byte
Samsung header. The relevant experiments do not support a 73-byte retention
window:

| Candidate | Write geometry | Live observation | Supported interpretation |
|---|---|---|---|
| R4W1-B | append 99 bytes at `idx % payload_size`, publish `idx + 99` | first 73 bytes retained, final 26 replaced | the append crossed the circular payload boundary; 73 is the first-fragment length, not a window limit |
| R4W1-D | 45 contiguous bytes before the cursor, no index mutation | one exact marker in two complete byte-identical reads | this exact guarded geometry survived and proved post-exec PID 1 |
| R4W1-E E1 | 173 contiguous bytes before the cursor, no index mutation | zero entry family and zero `S22C` slot magic | P2.24 proved the generic OF parser rejects the Samsung `reg` encoding before carrier initialization |
| R4W1-E0 | 45 contiguous bytes using the D placement rule, ENTRY later replaced in place by USERSPACE | zero ENTRY, USERSPACE, and family bytes | size alone cannot explain absence because D used the same 45-byte geometry |

For the observed R4W1-B 73/26 split, the reconstructed append cursor is
`payload_size - 73 = 0x1fffa7`. At that same illustrative cursor, D/E0 would
occupy `[0x1fff7a, 0x1fffa7)` and E would occupy
`[0x1ffefa, 0x1fffa7)`. Both are contiguous and leave the same 73 bytes between
the cursor and the physical payload end. Candidate-time cursors can differ, but
the D/E/E0 placement formulas explicitly choose a non-wrapping range on either
side of their size threshold.

R4W1-E already has a candidate-specific static fit gate. Its host contract
requires `REGION_SIZE <= payload_size`, models the exact 173-byte placement,
and rejects a truncated observer region. The patched kernel independently
checks `sizeof(*region) <= payload_size`. Process v2 should remain transport-
generic; it must not acquire a device-specific `<=73` rule.

## Discriminator Constraints

1. Target, physical-layout, and retained-magic checks are safety guards. No
   candidate may write an "unconditional" heartbeat before those checks.
2. The full-saturation check is source-proven to be stronger than stock
   visibility requires. Stock rotates only when `idx > payload_size`; otherwise
   it exports `[0, idx)`. For the current contiguous no-index-mutation record of
   `L` bytes, valid magic and `idx >= L` are sufficient. At `idx ==
   payload_size`, stock uses the prefix branch and exports the full payload.
3. `printk` padding cannot deterministically saturate this Samsung ring while
   `sec_log_buf.ko` is absent. Loading that module would install a live writer
   and invalidate the frozen-cursor carrier contract.
4. A fixed offset inside this ring is not owned scratch space. It must not be
   treated as an independent channel without a separate source- and DT-backed
   ownership proof.
5. A candidate-derived nonce strengthens positive identity when a record is
   present. It does not classify an all-zero observation and therefore is not
   an independent candidate-selection witness by itself.
6. No new E0-class F1 candidate should be prepared until a statically reviewed
   discriminator adds information to the zero-result branch.

`boot_cnt` and `prev_idx` are not inputs to the stock snapshot copy. Invalid
magic causes stock to set magic, `idx=0`, and `prev_idx=0` before taking an
empty snapshot while preserving `boot_cnt` and untouched payload bytes.
FYG8's configured zstd compression is transparent to this geometry: the
private snapshot is decompressed to its original recorded size when
`/proc/last_kmsg` is opened.

## Independent Witness Inventory

No reusable independent candidate-selection witness is established inside the
current FYG8 safety envelope:

- the separate Samsung pmsg carveout has a write path but its backend `read()`
  always returns zero;
- debug-region clients and Qualcomm summary structures are initialized for the
  current boot, not snapshotted from the prior generation;
- reset history and auto-comment depend on the dedicated Samsung debug
  partition, whose writer is outside the boot-only boundary;
- the corrected mainline ramoops path retained no current-run record;
- RDX is locked, EUD was a controlled negative, and no physical UART observer
  is demonstrated; and
- USB, display, and audio are later bring-up targets rather than existing
  selection witnesses.

Accordingly, an all-zero same-ring observation remains ambiguous even after
the saturation gate is corrected. A short `UNSAT` record can reduce that class
only when the current index is large enough to expose the short record; invalid
magic, `idx=0`, nonselection, and later loss cannot all be separated on the
same channel without weakening a safety guard or changing ring metadata.
The bounded positive states are therefore `ENTRY` for `idx >= entry_size` and
candidate-bound `UNSAT` for `reason_size <= idx < entry_size`; every smaller or
invalid case remains in an explicit `ZERO/AMBIGUOUS` class.

Detailed source audit:

`docs/reports/NATIVE_INIT_V3421_S22PLUS_RETENTION_MODULE_CLOSURE_HOST_AUDIT_2026-07-10.md`

P2.24 target-guard root cause and implementation boundary:

`docs/reports/S22PLUS_FYG8_P224_GUARD_ROOT_CAUSE_H0_2026-07-22.md`

Geometry and feedback reassessment:

`docs/reports/S22PLUS_FYG8_RETENTION_DISCRIMINATOR_FEEDBACK_REASSESSMENT_2026-07-22.md`

Exact snapshot model and independent-witness audit:

`docs/reports/S22PLUS_FYG8_SNAPSHOT_AND_INDEPENDENT_WITNESS_H0_2026-07-22.md`

The bounded 45-byte ENTRY / 24-byte UNSAT / residual-zero design is complete
host-only. It creates no candidate or live authority:

`docs/plans/S22PLUS_FYG8_P2_18_SAME_RING_DISCRIMINATOR_DESIGN_2026-07-22.md`

P2.19 implements that exact state partition in a source-pinned kernel patch,
candidate-contract checker, typed raw-byte observer, and one common-runner
dispatch. Connected D0 baseline checking uses the same typed decoder for both
families and edge partials. It never loads the owner module or writes header
metadata. P2.20-P2.23 subsequently reviewed, built, transferred, and observed
that closure. P2.24 then proved that its generic OF resource helper rejects the
Samsung current-node `reg` encoding before accessing the retained header; the
checker had required the wrong helper as a positive source marker.

P2.25 replaces that helper with the exact current-node 2/2-cell parser. Its
stock-DT contract also binds the log node's `memory-region` to the containing
`samsung,carve-out` reserved range and proves that range has no `no-map`
property on both applicable Waipio bases. The exact Full-LTO vmlinux contains
one `__flush_dcache_area()` call in each store path, ordered after the payload
copy and before readback; GNU and pinned LLVM audits agree on the reviewed
function bytes. This is host proof of the linked guard and cache-flush PoC. It
does not prove that the payload survives reset, and no P2.25 device run or live
authority exists.

`docs/reports/S22PLUS_FYG8_P225_GUARD_POC_FLUSH_HOST_PASS_2026-07-22.md`

`docs/reports/S22PLUS_FYG8_P219_SAME_RING_IMPLEMENTATION_HOST_PASS_2026-07-22.md`
