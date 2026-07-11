# V3442 S22+ HIGH Set-Only Live: Accepted, MID Restored

## Verdict

`HIGH_ACCEPTED_AND_MID_RESTORED_WITH_HOST_CONTINUATION_AFTER_HELPER_EXCEPTION`.

The S22+ boot chain accepted HIGH exactly. Android returned normally with both
independent debug-level views at HIGH. The exact setter then restored MID, and
Android returned with both views at MID. No flash or crash path was needed.

## Exact Live Inputs

```text
live helper SHA256  43aee96afee7542787a0a0d97a4f919e208516da96de0be281c848d047e4e8e2
setter SHA256       5bc230b87d090dcb694cd5eb68eb7e24a0ba5d8d9062cfada817953e5cc6f346
setter source       288cbc53851ee6a29a9b0579d6868aa1cf1fbcb1c7a62cb2b10da9255ccd6339
HIGH request        debug0x4948
MID request         debug0x494d
```

## Baseline

```text
debug_level          18765
ro.boot.debug_level  0x494d
boot_reason          reboot,download
Android/root         PASS
boot/DTBO/recovery   exact known baseline
```

## HIGH Observation

The raw setter dispatched HIGH once. ADB disappeared and Android returned.

```text
debug_level          18760
ro.boot.debug_level  0x4948
boot_reason          reboot
Android/root         PASS
boot_sha256          2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256          97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
recovery_sha256      93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
classification       HIGH_ACCEPTED
```

This rules out the hypothesis that LCS PROD causes S-Boot to reject or clamp
the HIGH value itself. It does not show that HIGH overrides the separate RDX
token gate, EUD TrustZone policy, or any authenticated secure-debug gate.

## Harness Incident And Continuation

After the expected HIGH reboot, `wait_android_any()` received
`s22plus_v3441_debug_mid_rescue_live_gate.GateError` while ADB was absent. The
V3442 helper caught only its local `GateError`, so the process exited before
durably recording HIGH or dispatching MID. This was a host exception-type bug,
not a device failure.

Android had already returned healthy at HIGH. The operator authorization
already required immediate MID restoration for any HIGH evidence. Host
continuation therefore:

1. captured the exact HIGH state read-only;
2. found the temporary setter had been removed across reboot;
3. re-pushed and hash-verified the exact same setter;
4. dispatched MID exactly once;
5. observed ADB loss and return;
6. removed the temporary setter and verified the complete MID baseline.

No second HIGH request occurred.

## Final MID State

```text
debug_level          18765
ro.boot.debug_level  0x494d
boot_reason          reboot
Android/root         PASS
boot_sha256          2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256          97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
recovery_sha256      93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
```

V3441 rescue, Magisk rollback, and stock fallback were not used. Flash count
was zero. Panic, SysRq, RDX protocol, EUD, LCS/fuse/QFPROM, and raw parameter
actions were zero.

## Durable Evidence

Private run:
`workspace/private/runs/s22plus_v3442_high_set_only_20260711T012441Z/`.
The repaired timeline contains exactly the eight standard events and marks both
candidate and rollback phases as no-flash HIGH/MID dispatch phases.

## Post-Live Fix

The helper now catches both local and imported V3441 gate exceptions and
re-stages the exact setter before MID dispatch because `/data/local/tmp` did not
retain it across this reboot. Fixed helper SHA256 is
`a94066c15e9e6cc62b7790e7e88bfd251a082392b8df65ba06187bf100db72bb`.
The live result remains tied to the authorized pre-fix helper SHA above.

## Decision

Retire V3442. The next question is narrower: with HIGH proven accepted, does a
separately authorized panic still produce `RDX is locked` and S-Boot
`NegativeAck` under LCS PROD? Any such test must remain preamble-only, stop on
negative acknowledgement, restore MID afterward, and use a fresh one-shot
policy. HIGH acceptance alone is not authorization for that test.
