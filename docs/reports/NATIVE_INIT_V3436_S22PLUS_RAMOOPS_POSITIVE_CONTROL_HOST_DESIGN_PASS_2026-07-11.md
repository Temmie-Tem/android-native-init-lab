# V3436 S22+ Ramoops Positive-Control Host Design Pass

## Verdict

`HOST_DESIGN_PASS_NO_LIVE`.

V3436 pins the V3435 DTBO candidate and stock rollback, defines the Android
positive-control state machine, and implements the `S22RPC1` marker parser and
retained-evidence classifier. No live helper, policy activation, device action,
flash, reboot, or panic was performed.

## Closed Decisions

- Final target remains native/Debian without Android userspace.
- Android is only the known-good observer positive control.
- DTBO write and intentional panic need separate exceptions and ack tokens.
- Backend registration and exact live sizes must pass before marker emission.
- Patched Android must return and pstore must be collected before stock rollback.
- pmsg-only retention is partial, not PASS.
- Only a valid run-bound console/dmesg frame reopens direct PID1.
- Clean negative after proven backend moves the observer track to EUD/UART.

## Validation

```text
py_compile                                  PASS
V3436 focused tests                        14/14 PASS
V3426-V3436 regression tests             149/149 PASS (53.899 s)
V3435 artifact/hash/member pins             PASS
full state path validation                  PASS
marker roundtrip/CRC/identity tests         PASS
PASS/PARTIAL/NO_PROOF/FAIL classifier tests PASS
device actions                                  0
```

## Next

V3437 is the host-only resumable helper and inert two-policy draft. It remains
non-live until separate explicit authorization activates both policy scopes.
