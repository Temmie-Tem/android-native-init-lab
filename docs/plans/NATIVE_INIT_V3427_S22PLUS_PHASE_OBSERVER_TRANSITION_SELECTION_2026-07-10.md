# V3427 S22+ Phase Observer Transition Selection

## Decision

`HOST SELECTION PASS; ATTENDED MANUAL RDX/DOWNLOAD; POSITIVE CONCLUSIVE; NEGATIVE INCONCLUSIVE; NO LIVE`.

The selected transition is a quiet candidate park followed by attended manual
RDX/Download entry, boot-only Magisk rollback, and duplicate full reads of
`/proc/last_kmsg` on the first rooted rollback boot. This is the least-confounded
available path with a repeatedly proven recovery envelope.

V3427 creates no candidate, live helper, exception, reboot request, or device
action. The operator's live approval intent is acknowledged but cannot activate
an unknown future artifact.

## Mandatory V3426 Correction

The candidate internally verifies PRECHECK and FINAL in the current ring, but
the host has no signal before the transition. Two hidden variables therefore
share one negative observation:

```text
later marker absent = Stage A not reached OR transition lost the ring
```

Absence is `NO_PROOF/STOP`, not `RETENTION_FAIL`. Conversely, a fresh run's exact
PRECHECK+FINAL pair can only exist if Stage A emitted it and the pair survived,
so that positive proves both execution and cross-session preservation. V3426
schema v2 and its contract hash encode this asymmetric boundary.

## Selected Transition

```text
candidate flash completes and original Odin disconnects
  -> candidate internally completes G0..G11 and enters quiet park
  -> operator waits 60 seconds, acts no later than 90 seconds
  -> operator manually enters Samsung RDX/Download
  -> host flashes pinned Magisk boot-only rollback AP
  -> first rooted Android boot, no intervening reboot
  -> read /proc/last_kmsg to EOF twice
  -> require identical byte count and SHA256
  -> classify exact run-bound PRECHECK+FINAL pair
```

Primary rollback:

```text
AP SHA256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
member=boot.img.lz4 only
resulting boot SHA256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The stock boot-only AP is only a fallback if the Magisk transfer fails while
Download remains available:

```text
AP SHA256=2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94
member=boot.img.lz4 only
resulting boot SHA256=4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae
```

Using the stock fallback makes the run recovery-only and `NO_PROOF/STOP`; it is
not an alternate evidence path. After FINAL the candidate performs no userspace
log writes and only parks. Background kernel log volume remains unverifiable but
is bounded by the 90-second operator window.

## Why This Transition

- M4T0/M4T1 did not prove candidate-side `reboot("download")`; reject it.
- Cold power loss maximizes the chance of clearing reserved RAM; reject it.
- Panic, watchdog, and `sec_debug` alter behavior and violate observer-only
  isolation; reject them.
- M4T0, O3, O3F, O3R1, and M29 repeatedly recovered through attended manual
  Download plus boot-only rollback.
- M29's first rollback retained Android-origin reboot/download log data, proving
  this path can preserve the ring for that origin. It does not prove direct-PID1
  origin, which remains the positive result under test.

## Provenance Boundary

On the first rollback boot, `sec_log_buf` copies the existing reserved ring into
`last_kmsg` before pulling current early printk or registering current hooks.
Download mode does not instantiate the Linux module or create the run-bound
frames. A nonce that was absent at baseline and appears as an exact pair in the
first rollback snapshot therefore originated before that probe and proves the
candidate path.

The first collection must occur before any additional reboot. Two full EOF reads
must match exactly. An unreadable, truncated, oversized, or changing snapshot is
`UNAVAILABLE/STOP`, not absence.

## Classification

| Observation | Verdict |
|---|---|
| Exact PRECHECK+FINAL pair | `PASS_STAGE_A_AND_CROSS_SESSION_RETENTION` |
| Neither current-run marker | `NO_PROOF_STAGE_A_VS_TRANSITION_UNRESOLVED_STOP` |
| One marker, duplicate, malformed, bad identity/order | `FAIL_STOP` |
| Non-EOF, empty, oversized, or double-read mismatch | `UNAVAILABLE_STOP` |

## Remaining Gate

Before any direct-PID1 candidate, run the same transition once from the known
Android/Magisk baseline using the same per-run marker encoder, manual Download,
boot-only rollback, first-boot double-read, and classifier. That stock-origin
positive control validates collection sensitivity and session provenance.

This positive control itself needs a fresh exact exception and explicit approval
after its helper and hashes exist. V3427 does not create or authorize it.
