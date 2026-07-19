# S22+ FYG8 R4W1-C Watchdog Carrier Host Close

Date: 2026-07-20 KST

Verdict: `PASS_R4W1C_WATCHDOG_CARRIER_TWO_REPRO_STATIC_CONTRACT`

Scope: host-only build, reproduction, and independent static qualification.
No device contact, USB enumeration, Odin invocation, transfer, flash, connected
gate, live policy, or live authorization occurred.

## Result

The R4W1-C direct-PID1 carrier loads exactly this dependency-derived stock
vendor-ramdisk module closure:

```text
smem.ko
minidump.ko
qcom-scm.ko
qcom_wdt_core.ko
gh_virt_wdt.ko
```

Every `finit_module()` result must be zero. The carrier then reads
`/proc/modules` to EOF under a 32 KiB bound and requires exactly the five runtime
names, once each, with no additional loaded module. Initial, per-module,
completion, and visibility markers require exact `/dev/kmsg` writes. The final
park marker is best-effort; its absence cannot create success evidence. Failure
parks without reboot.

The carrier deliberately reports:

```text
module_closure_visible=1
watchdog_ownership=not_directly_proven
functional_proof=bounded_live_survival
```

Module load and visibility do not directly prove driver bind, watchdog
registration, or active kernel petting. M31B's 120-second survival supports the
architecture, but R4W1-C functional ownership remains a future live gate.

## Artifact Contract

Final reproductions:

```text
workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/reproduction-h
workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/reproduction-i
```

The complete directory trees are byte-identical. Load-bearing pins are:

| Artifact | Size | SHA256 |
|---|---:|---|
| carrier boot | 100663296 | `fc10d94eb0e41a97b40d657e320f8f815870a41b7a6b6df0bc7a51b540a2fe57` |
| candidate boot | 100663296 | `1d394028714c48cfc0fd220acade9ead9a49ea21a81c59b2b87f88e61de704b0` |
| `boot.img.lz4` | 27057849 | `abe6b9069b1bfd04c0aeac4b022e367d5d8450101302d623ea2c9efe3b0c0d66` |
| boot-only `AP.tar.md5` | 27064361 | `85514e79e3400de30b7146606a9e86c3655fc7a8766daba5f054ae1bd54fd42f` |
| manifest | 15635 | `bfb932fd840104b54d41a957b13d56459c635d8939899c6f50d773aa7474ab76` |
| static `/init` | 65984 | `6bf7c60ca8f9b9561a9d38f0591028b23291595dd224853015807993ce97703d` |
| final ramdisk | 1358504 | `298e073bc9dfc3fee7bd3acf0fe902efcfd2407783caae2e6efff8f9ad7c20f3` |

The AP contains exactly one `boot.img.lz4` member. The candidate preserves the
qualified R4W1-B kernel interval and its one exact exec-accept witness. The
ramdisk changes only `/init`; watchdog module binaries remain sourced from the
unchanged stock vendor ramdisk.

## Host Hardening

The builder opens every load-bearing source and tool with `O_NOFOLLOW`, binds
the fd identity before and after the bounded read, rechecks path identity, and
executes only private staged copies. This includes the Magisk base boot, vendor
ramdisk, C source, lz4, and magiskboot. The independent checker separately
stages its pinned source and tools before execution.

The independent checker rederived module dependencies from `modules.dep`,
verified module sizes, hashes, and modinfo names, independently compiled the
carrier, parsed boot v4 and newc, validated the R4W1-B marker cardinality,
decoded LZ4, and parsed the Odin tar.md5. Its final result is:

```text
workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/static-check-result-v3.json
size=8306
sha256=14786803582b62b88db9a3791ac49364a580fe9c5c8459d0e11b66e0f8215c94
```

## Validation

- R4W1-C focused tests: 15/15 pass.
- M31B, R4W1-B, and Odin-core regression set: 127 pass, 4 environment skips.
- M31B/R4W1-B live-helper mock regressions: 43 pass, 1 private-artifact skip.
- `py_compile`, ResourceWarning-as-error, full reproduction diff, and
  `git diff --check`: pass.

The skips are host fixture/tool availability only; none is a failed R4W1-C
contract check.

## Next Gate

Design a new connected read-only qualification that binds these exact artifacts
and rehearses the resumable transaction without transfer. Only after that gate,
an independent review, and a separately committed one-shot exception may a
bounded boot-only live run be considered. This report grants no live authority.
