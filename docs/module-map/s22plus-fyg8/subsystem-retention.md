# Retention Subsystem

## Status

`SOURCE_VERIFIED + LIVE_BOUND` on the rooted FYG8 Android baseline. Direct-PID1
retention remains `UNVERIFIABLE` for candidates that did not load the owner.

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

Detailed source audit:

`docs/reports/NATIVE_INIT_V3421_S22PLUS_RETENTION_MODULE_CLOSURE_HOST_AUDIT_2026-07-10.md`
