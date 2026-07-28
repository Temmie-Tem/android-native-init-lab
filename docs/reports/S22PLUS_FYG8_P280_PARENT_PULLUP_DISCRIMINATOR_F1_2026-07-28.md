# S22+ FYG8 P2.80 parent/pull-up discriminator F1

Date: 2026-07-28 KST

## Verdict

`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

The exact P2.80 candidate and exact Magisk rollback each completed one
boot-only Odin transfer. The candidate did not expose an accepted ACM endpoint,
so E3 did not pass. Two byte-identical retained reads did preserve one exact
run-bound diagnostic record:

```text
generation 87: stage=0x8e outcome=progress detail=0
generation 88: stage=0x8f outcome=failure detail=0xb22
```

The selected contract decodes `0xb22` as
`run-stop-zero-no-bus-state`, category `electrical-boundary`.

The transaction is closed. Exact rollback, final Android/root/boot and
supporting-partition health, Odin absence, and all eight canonical timeline
events passed. Recovery is not required and the consumed approval is not
reusable.

## Bound execution

- manifest: `s22plus-fyg8-p280-process-v2-ready-1`
- source contract:
  `s22plus-fyg8-p280-parent-pullup-discriminator-v1`
- candidate run ID: `568abdddae4a0320e14c95aad8bf1e9c`
- candidate transfer classification: `odin_transfer_completed`
- candidate observer classification: `endpoint-timeout`
- observer guard release: commanded and verified
- rollback transfer classification: `odin_transfer_completed`
- final state: `CLOSED`
- live-result SHA256:
  `9ab8b844ded82426a92c5db49c6d59688e1ae1f7f310a2941b237303c1729f5f`

Private raw evidence remains under the Process v2 run directory and is not
tracked.

## What the retained record proves

Stage `0x8e` is written only after the role phase and synchronous configfs UDC
bind phase complete. Its zero detail means no fail-soft trace warning survived
either phase.

For the role phase, the exact P2.80 parser requires one ordered same-PID
sequence containing:

1. `dwc3_otg_start_peripheral(on=1)` entry;
2. non-negative parent runtime-PM result;
3. non-negative child runtime-PM result; and
4. `dwc3_otg_start_peripheral()` return zero.

For the bind phase, the clean `P280_BIND_RUN_STOP_ZERO` classification requires
one ordered PID1 trace containing:

1. `dwc3_gadget_pullup(on=1)` entry and return zero;
2. a nested `dwc3_gadget_run_stop(on=1)` entry and return zero; and
3. no missed, malformed, foreign-PID, or cleanup-uncertain trace condition.

The configured-state deadline then expired while:

- the canonical UDC state remained exactly `not attached`;
- the role readback remained `peripheral`; and
- the host observer found no matching ACM endpoint.

This rules out the earlier broad explanations that the parent start path was
never entered, parent or child runtime PM returned a negative error, configfs
UDC bind failed synchronously, child pull-up was never entered, or nested
run-stop returned an error.

## What it does not prove

Post-live exact-source review corrected an underclaim here. Return zero from
`dwc3_gadget_run_stop()` means DCTL RUN_STOP was written and the bounded DSTS
poll observed `DEVCTRLHLT` clear. The traced caller also excludes the
runtime-suspended early return and proves the preceding core soft reset
returned success. This is hardware-backed controller-running evidence.

It still does not prove that a physical attach reached the host, that the
active femto-HS PHY or redriver produced the required electrical state, that
VBUS override and connect notifications reached every downstream block, or
that the link advanced beyond the retained UDC state `not attached`.

The result therefore narrows the next H0 question to the post-run-stop
electrical boundary. It does not identify one permanent root cause inside that
boundary and does not justify an uninstrumented retry, role retrigger, or
generic soft-connect workaround.

## Host interruption and recovery

The original host invocation ended after durable state `OBSERVED` and before a
rollback attempt was journaled. The exact cause of that host-process exit is
not established. No candidate replay or rollback attempt occurred in the
interrupted invocation.

Post-live host-journal review found no OOM kill, coredump, or process segfault
in the relevant interval. No launcher exit receipt survived, so the cause
remains a tracked host-tooling gap rather than a device conclusion.

`--recover` reopened the same immutable binding and journal, resumed only the
preapproved rollback path, transferred the rollback once, and completed final
health verification. This is a recovery deviation, not additional candidate
authority and not candidate evidence.

## Timeline and final health

The canonical event order is complete:

1. `live_session_start`
2. `candidate_flash_start`
3. `candidate_flash_done`
4. `candidate_boot_ready`
5. `rollback_flash_start`
6. `rollback_flash_done`
7. `rollback_boot_ready`
8. `live_session_end`

The candidate booted without an observed boot loop. Final Android reported boot
complete with the boot animation stopped, Magisk root available, expected
FYG8 kernel and partition identities, and no Download endpoint.

## Next

Do not repeat P2.80. Post-live H0 ruled out the proposed external eUSB2
repeater closure: the exact FYG8 DWC3 path uses the femto HS PHY and QMP SS PHY,
and neither the four vendor DTBs nor 11 DTBO entries select an eUSB2/repeater
node. Perform focused analysis of that exact active PHY/connect/VBUS electrical
path after the now-proven running controller. If another discriminator is
needed, retain the already-read `current_speed` value and preserve an explicit
host launcher exit receipt.

See
`S22PLUS_FYG8_P280_POST_LIVE_EVIDENCE_CORRECTION_H0_2026-07-28.md`.
