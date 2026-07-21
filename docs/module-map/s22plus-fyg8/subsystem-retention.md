# Retention Subsystem

## Status

`SOURCE_VERIFIED + LIVE_BOUND` on the rooted FYG8 Android baseline. A direct
kernel write into the existing retained ring is also `LIVE_PROVEN` for the
R4W1-D 45-byte contiguous pre-cursor witness, even though the candidate did not
load the owner module. Direct candidate `printk` capture without the owner and
the E/E0 zero-carrier branches remain `UNVERIFIABLE`.

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
| R4W1-E E1 | 173 contiguous bytes before the cursor, no index mutation | zero entry family and zero `S22C` slot magic | carrier initialization, candidate selection, and later visibility remain inseparable |
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
2. The saturation check is a visibility assumption, not proof that the physical
   region is unsafe. A future H0 design may distinguish it from the immutable
   safety guards, but must first model both saturated and unsaturated stock
   snapshot behavior.
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

Detailed source audit:

`docs/reports/NATIVE_INIT_V3421_S22PLUS_RETENTION_MODULE_CLOSURE_HOST_AUDIT_2026-07-10.md`

Geometry and feedback reassessment:

`docs/reports/S22PLUS_FYG8_RETENTION_DISCRIMINATOR_FEEDBACK_REASSESSMENT_2026-07-22.md`
