# S22+ FYG8 P2.58A F1 live terminal UDC pass

Date: 2026-07-25 KST
Tier: F1
Status: `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`
Transaction: `CLOSED`
Recovery required: false

## Result

One exact P2.58A E2 candidate and one exact Magisk rollback were transferred
under one prepared Process v2 binding. The operator observed a successful
candidate boot and no boot loop.

Two post-rollback retained reads are byte-identical and contain one exact E2
record:

```text
generation 80: stage=0x87 item=11 outcome=progress detail=0
generation 81: stage=0x8f item=0  outcome=terminal-success detail=0
classification: E2_SUCCESS_ONE_OR_MORE_BOOTS
```

The record has one exact family, one exact record, and one terminal success.
It has zero failures, UNSAT records, fallback records, foreign records,
historical families, integrity issues, delimiter mismatches, partial-head
records, and partial-tail records.

The versioned P2.58A sequence maps stage `0x87`, item 11 to the corrected
real-UDC predicate:

```text
/sys/class/udc/a600000.dwc3
```

The predicate permits unrelated UDC peers but requires exactly one target
entry with the expected symlink identity. Its success therefore closes the
P2.57 singleton-observer defect and proves publication of the exact DWC3 UDC
within the dedicated post-DWC3 dwell.

Terminal `0x8f` proves the complete versioned E2 sequence:

- all 60 exact stock module operations;
- all provider and bind gates through display/QNOC, SSUSB, and DWC3 core;
- exact real-UDC membership at `0x87`; and
- the terminal userspace path after that gate.

This result does not prove a USB host enumeration, gadget pull-up, configfs
composition, ACM bytes, NCM, or a request/response channel. Those remain
separate E3 and E4 rungs.

## Host Qualification

The corrected source-bound candidate completed:

- two clean Full-LTO builds;
- byte equality for `Image`, `vmlinux`, `.config`, `System.map`,
  `vmlinux.symvers`, and `abi.xml`;
- a versioned linked audit of the final Full-LTO control flow;
- two byte-identical deterministic boot-only packages;
- independent artifact and effective-rootfs closure;
- Process v2 offline promotion and host preflight; and
- a clean connected D0 after one bounded normal baseline-rotation reboot.

The build times were `39:05.92` and `39:34.50`. Build B used a measured
4.4 GHz link burst. It reached `69.1 C` and did not improve total wall time
over build A. The qualified host was restored to its original
`schedutil` governor and 4.4 GHz maximum after the build. Sustained candidate
qualification therefore defaults to the stable 2.9 GHz cap unless cooling or
an intermediate P-state is independently qualified.

## Transfer And Observation

The candidate Odin transfer:

- used one regular boot-only AP path;
- contained only `boot.img.lz4`;
- returned zero with empty stderr;
- reached 100 percent and closed the device session; and
- was attempted exactly once.

The bounded observation waited 120 seconds after the Download endpoint
departed. Physical Download recovery was then identified, and the already
authorized exact rollback was transferred once.

## Final Verification

Final evidence proves:

- candidate transfer completed once;
- rollback transfer completed once;
- Android boot complete and boot animation stopped;
- expected FYG8 kernel and Magisk-root boot identity;
- root health;
- boot and supporting-partition identity;
- Odin endpoint absence;
- two byte-identical full retained reads;
- accepted terminal P2.58A evidence;
- transaction state `CLOSED`; and
- all eight canonical timeline events in order.

```text
candidate_completed=true
rollback_completed=true
final_verified=true
marker_accepted=true
recovery_required=false
```

There was no recovery deviation and no repeated transfer.

## Disposition

The P2.57 interpretation that stage `0x87` timed out because the real UDC was
absent is retired. P2.58A proves the exact UDC is published in the corrected
sequence and that the E2 runtime reaches terminal success.

The binding and approval are consumed. No S22+ F1 authority remains.

The next bounded unit is E3 H0 design for one minimal ACM banner over the
proven real UDC. It must retain the existing boot-only recovery envelope and
must not infer configfs, pull-up, enumeration, or host receipt from this E2
record.
