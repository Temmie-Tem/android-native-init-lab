# S22+ FYG8 P2.55 F1 live qnoc MC virtual bind absent

Date: 2026-07-24 KST
Tier: F1
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Transaction: `CLOSED`
Recovery required: false

## Result

One exact P2.54 proof-bound SSUSB classifier candidate and one exact Magisk
rollback were transferred under the P2.55 prepared binding. The operator
observed no candidate boot loop.

Two post-rollback retained reads are byte-identical and contain one exact E2
terminal-failure record:

```text
generation 76: stage=0x83 item=8 outcome=success
generation 77: stage=0x84 item=9 outcome=failure detail=0xa04
detail name:   qnoc-mc-virt-bind-absent
```

The record has one exact record and one failure, with zero integrity,
foreign-family, historical-family, partial-head, partial-tail, fallback, and
UNSAT findings. It proves that this candidate reached the SSUSB classifier
after the proven GCC boundary.

Detail `0xa04` means that at the settled classification instant the exact bind
symlink below was absent:

```text
/sys/bus/platform/drivers/qnoc-waipio/soc:interconnect@1
```

This is a bounded classifier-time coordinate, not proof of a permanent root
cause. It does not distinguish a missing supplier, deferred probe, ordering,
node-selection error, or a bind that would occur after the bounded grace. It
does not prove SSUSB bind, DWC3, UDC, USB, or terminal stage `0x8f`.

The manifest requires a terminal-success record. Therefore the formal verdict
is no-proof even though the failure record proves candidate execution and
narrows the live frontier.

## Rollback Recovery Deviation

The exact rollback transfer returned `odin_transfer_completed` and the durable
journal reached `ROLLBACK_FLASHED`. The initial execution process then stopped
fail-closed while measuring Download-endpoint departure:

```text
measured USB endpoint evidence failed
```

No candidate or rollback transfer was repeated. Android MTP enumeration
returned. Process v2 `--recover` reopened the existing transaction at
`ROLLBACK_FLASHED`, observed no live Odin endpoint, waited for the same Android
target, and performed only final health and retained-evidence verification.

The measured observer does not preserve the wrapped inner `OSError` or
USBFS-identity exception, so the exact low-level cause is not established by
this run. This is a process-observability issue to close H0 before another F1,
not a reason to weaken endpoint identity checks.

## Final Verification

The production live-result validator passes. Final evidence proves:

- exact candidate and rollback transfer completion;
- Android boot complete and boot animation stopped;
- FYG8 kernel and expected Magisk-root boot identity;
- root health;
- boot and supporting-partition identity;
- Odin endpoint absence;
- two byte-identical full retained reads;
- transaction state `CLOSED`; and
- all eight canonical timeline events in order.

The timeline contains only:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

## Safety State

```text
candidate_attempts=1
rollback_attempts=1
candidate_completed=true
rollback_completed=true
final_verified=true
marker_accepted=false
recovery_required=false
```

The binding and approval are consumed. No S22+ F1 authority remains.

## Next Bounded Unit

P2.56 is H0 only:

1. close the exact qnoc MC virtual DT, source, module, and probe dependencies;
2. determine whether `0xa04` points to dependency, ordering, timing, or an
   incorrect expected bind-node identity; and
3. preserve the inner measured-USB departure exception and add a focused
   replay before another F1.

Do not build or flash until those host questions are closed.
