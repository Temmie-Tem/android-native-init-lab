# S22+ FYG8 P2.57 F1 live DWC3 core pass and UDC-gate timeout

Date: 2026-07-25 KST
Tier: F1
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Transaction: `CLOSED`
Recovery required: false

## Result

One exact P2.57 display-closure E2 candidate and one exact Magisk rollback
were transferred under one prepared Process v2 binding. The operator observed
a successful candidate boot and no boot loop.

Two post-rollback retained reads are byte-identical and contain one exact E2
terminal-failure record:

```text
generation 79: stage=0x86 item=10 outcome=success
generation 80: stage=0x87 item=11 outcome=failure detail=110
detail name:   errno (ETIMEDOUT)
```

The record contains one exact record and one failure, with zero integrity,
foreign-family, historical-family, partial-head, partial-tail, fallback, and
UNSAT findings.

The versioned P2.57 sequence maps item 10 to the DWC3 core bind gate and item
11 to the UDC class-device gate:

```text
/sys/bus/platform/drivers/dwc3/a600000.dwc3
/sys/class/udc/a600000.dwc3
```

The strict sequence therefore proves all 60 exact module insertions and all
standard gates through SSUSB and DWC3 core bind. Combined with the
source-closed `fw_devlink` dependency chain, successful SSUSB bind clears the
P2.55 qnoc MC virtual blocking boundary. The retained record does not directly
encode separate display or qnoc bind checkpoints.

It does not prove UDC publication, USB device enumeration, ACM, or terminal
stage `0x8f`. Post-live P2.58 H0 analysis found that the stage `0x87`
predicate did not test only the exact target. It required
`/sys/class/udc` to contain one and only one entry and for that entry to be
`a600000.dwc3`.

That predicate conflicts with both `CONFIG_USB_DUMMY_HCD=y` in the exact
candidate and the stock-observed coexistence of `dummy_udc.0` and
`a600000.dwc3`. The desired two-entry topology is rejected. Detail 110
therefore proves only that the flawed singleton predicate did not pass; it
does not prove that the exact DWC3 UDC was absent.

P2.58 also found a secondary observation ambiguity. A late SSUSB bind during
the five-second classifier grace enters a zero-wait downstream drain, and the
retained ABI does not encode whether that branch ran. The corrected exact
membership predicate therefore also needs its own bounded dwell. The focused
correction is documented in
`S22PLUS_FYG8_P258_UDC_FRONTIER_FOCUSED_ANALYSIS_H0_2026-07-25.md`.

The manifest requires a terminal-success record. The formal verdict is
therefore no-proof even though the failure record proves substantial new
candidate progress.

## Rollback Recovery Deviation

The exact rollback transfer returned `odin_transfer_completed`, and the
durable journal reached `ROLLBACK_FLASHED`. The initial execution process then
stopped fail-closed while taking the final measured USB endpoint inventory:

```text
measured USB endpoint inventory failed
```

No candidate or rollback transfer was repeated. Android ADB returned, and
Process v2 `--recover` reopened the existing transaction at
`ROLLBACK_FLASHED`. It reconciled the durable rollback result and performed
only final health and retained-evidence verification.

This failure occurs before the P2.57 allowlisted post-snapshot measurement
diagnostic is available, so no diagnostic receipt was published. The exact
inner exception is not established by this run. The durable state machine
still prevented a repeated device transition.

## Final Verification

Final evidence proves:

- exactly one completed candidate transfer and one completed rollback;
- Android boot complete and boot animation stopped;
- FYG8 kernel and expected Magisk-root boot identity;
- root health;
- boot and supporting-partition identity;
- Odin endpoint absence;
- two byte-identical full retained reads;
- transaction state `CLOSED`; and
- all eight canonical timeline events in order.

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

## Post-Live Disposition

P2.58 H0 found a deterministic contract bug before attributing the result to
DWC3 internals. The next bounded unit is P2.58A design and host implementation:
replace global UDC singleton cardinality with exact target membership,
independently validate the target symlink, and give that corrected predicate
one fresh five-second deadline after DWC3 bind. Do not add modules, force role,
create configfs state, or build another candidate until that versioned
contract and its semantic topology fixtures are complete.
