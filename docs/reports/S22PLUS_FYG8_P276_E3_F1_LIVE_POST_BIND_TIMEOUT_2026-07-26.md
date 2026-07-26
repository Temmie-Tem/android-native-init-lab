# S22+ FYG8 P2.76 E3 F1 live post-bind timeout

Date: 2026-07-26 KST
Tier: F1
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Transaction: `CLOSED`
Recovery required: false

## Result

One exact P2.76 ready2 candidate and one exact Magisk rollback were
transferred once under one Process v2 approval. The operator observed a
successful candidate boot and no boot loop.

The typed CDC-ACM observer ran for its full 180-second bound after Download
departure. It found no exact candidate endpoint and received zero bytes:

```text
classification=endpoint-timeout
accepted=false
elapsed_sec=180.022353
raw_size=0
```

Two post-rollback retained reads are byte-identical and contain one exact
terminal-failure record:

```text
generation 87: stage=0x8e item=0 outcome=progress detail=0
generation 88: stage=0x8f item=0 outcome=failure  detail=110
detail: ETIMEDOUT
classification: E2_FAILURE_OBSERVED
```

The record has one exact family and one exact record. It has zero integrity,
foreign-family, historical-family, fallback, UNSAT, delimiter, partial-head,
and partial-tail findings.

## Proven Frontier

The selected P2.60 runtime maps the retained stages as follows:

```text
0x88 configfs mount and exact statfs validation
0x89 gadget construction and configfs readback
0x8a ttyGS0 class publication
0x8b ttyGS0 node and raw open
0x8c exact banner queued to ttyGS0
0x8d parent role read/write plus exact a600000.dwc3 membership
0x8e configfs UDC bind and exact UDC readback
0x8f configured/high-speed wait
0x90 terminal success
```

Generation 87 therefore proves every stage through `0x8e`. In particular, it
proves more than the existence of `/sys/class/udc/a600000.dwc3`: the write of
`a600000.dwc3` to the gadget's configfs `UDC` attribute returned successfully
and the exact value was read back.

Generation 88 proves that the exact UDC did not reach both:

```text
state=configured
current_speed=high-speed
```

within the device-side 30-second configured-state deadline. The retained ABI
does not preserve the last non-configured UDC state or speed, so it does not
distinguish no electrical connect, reset/descriptor failure, or a later
enumeration stall.

## Host Evidence Gap

The P2.74 USB trace sidecar was available as a standalone diagnostic tool but
was not started for this transaction. The run therefore has no continuous
host kernel USB messages, udev events, or `lsusb` transition record.

This omission does not invalidate the Process v2 result or rollback. It does
remove the independent discriminator between:

- no host connect event at all; and
- connect/reset/descriptor activity that never produced the exact ACM
  endpoint.

The typed observer's zero-byte timeout alone cannot make that distinction.

## Final Verification

Final evidence proves:

- exactly one completed candidate transfer;
- exactly one completed rollback transfer;
- Android boot complete and boot animation stopped;
- expected FYG8 kernel and Magisk-root boot identity;
- boot and supporting-partition health;
- Odin endpoint absence;
- two byte-identical full retained reads;
- transaction state `CLOSED`; and
- all eight canonical timeline events in order.

```text
candidate_completed=true
rollback_completed=true
candidate_observer_accepted=false
final_verified=true
marker_accepted=false
recovery_required=false
```

The binding and approval are consumed. No S22+ F1 authority remains.

## Disposition

This run is a real E3 advance but not E3 proof. Configfs, gadget construction,
`ttyGS0`, banner queuing, forced peripheral-role readback, real-UDC membership,
and UDC binding are no longer the frontier. The first unresolved boundary is
post-bind transition from a connected gadget request to host-visible USB
configuration.

Do not repeat this candidate or add firmware, Max77705, descriptor functions,
or `soft_connect` based only on the generic timeout. The next unit is H0
focused analysis of the exact FYG8 DWC3-MSM role state machine and the missing
post-bind discriminators.
