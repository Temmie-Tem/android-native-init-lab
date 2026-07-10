# V3426 S22+ Phase Observer Design Host Pass

## Verdict

`PASS; HOST-ONLY OBSERVER CONTRACT CLOSED; NO LIVE CANDIDATE AUTHORIZED`.

V3426 converts the O3/O3F runtime-phase ambiguity into a two-stage evidence
contract. Stage A will eventually prove current-session execution and log-ring
capture through a fresh `/proc/ap_klog` readback. Stage B remains forbidden
until a later stock/Magisk session recovers the exact run-bound FINAL marker
from `/proc/last_kmsg` after one separately selected transition.

No candidate source, boot image, AP, live helper, exception, device write,
module insertion, reboot, or flash was produced or performed.

## Closed Host Facts

```text
sec_log_buf.ko identity                     PASS
hard/soft module dependency closure         PASS (none)
stock load position                         PASS (2)
probe order                                 PASS
last_kmsg pre-probe snapshot semantics      PASS
ap_klog fresh current-ring snapshot         PASS
ap_klog release/freshness                    PASS
strategy-3 vh_logbuf source path            PASS (runtime selection deferred)
/dev/kmsg write -> hook -> return synchrony PASS
sec_debug required                          false
```

The exact printk source proves that the vendor hook runs after printk record
commit and before the `/dev/kmsg` write returns. This removes the proposed
retry/barrier ambiguity: the future contract permits one write and one fresh
read only. A miss is failure.

## Contract Result

The marker is self-delimiting and binds a 128-bit run id, phase, monotonic
sequence, exact module SHA256, contract SHA256, and context SHA256, with payload
length and CRC32. Baseline absence is the negative control. FINAL is re-read
from a fresh current-ring snapshot before Stage A can pass.

Historical foreign-run frames are expected in a retained circular ring. They
cannot satisfy the current run. Malformed current-run data, duplicate frames,
wrong identity, wrong sequence, premature FINAL, or PRECHECK eviction are hard
failures.

## Independent Review

Claude Opus performed two high-effort architecture reviews. The first returned
`GO-WITH-MUST-FIX`. After the design added fresh FINAL readback, baseline
inventory, exact synchronous-source proof, embedded sequence ordering, bounded
frame parsing, eviction failure, and the full negative suite, the second verdict
was `GO` for host-only implementation and `NO-LIVE` until a transition is named.

A third Opus review read the completed implementation and found no blocking
issue. It identified three claim-to-check gaps, all closed before commit: the
invalid-magic reset is now checked inside its exact branch and reset body; the
full `vprintk_store -> log_output -> log_store` dispatch is pinned; and the
contract SHA plus committed JSON have an automated drift test. Raw-token
backstop tests also cover malformed frames whose parser issue lacks a run hint.

## Validation

```text
V3426 focused tests                         24/24 PASS
module-map + USB-role + O2 regressions      27/27 PASS
generated contract --check                 PASS
contract sha256                            dbd3efbdbaece277a34a54f40ab1f2785e8115efa7924c17408f53c9debba8a8
```

## Remaining Boundary

The following remain `UNVERIFIABLE`: preservation across warm reboot, cold
boot, panic, watchdog, RDX, and bootloader transitions, plus bootloader/TZ
reserved-region clearing. V3426 intentionally selects none of them.

Next is one host-only transition-selection unit. It must choose one exact
transition and recovery envelope. It must not build a candidate or request live
authorization until that choice is independently justified.
