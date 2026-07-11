# Native-init V3443R Corrected HIGH Panic Comparison Gate Source Ready

Date: 2026-07-11 KST

## Verdict

`HOST_SOURCE_READY_NO_LIVE_AUTHORIZATION`

V3443R corrects only the V3443 ADB shell-boundary defect and adds a pre-panic
positive control. The comparison target, pinned MID evidence, preamble-only
protocol ceiling, and mandatory MID recovery remain unchanged.

## Root Fix

V3443 passed the compound command as split ADB argv. V3443R constructs exactly
one remote shell argument:

```python
remote_shell = f"su -c {shlex.quote(command)}"
["adb", "-s", serial, "shell", remote_shell]
```

Before marker or SysRq, the same path runs `id; id`. Exactly two root lines are
required; shell UID or a nonzero return stops before panic. Focused tests prove:

- one quoted remote shell argument and five total host argv entries;
- two root lines pass;
- the observed V3443 split-scope shape, root then shell UID 2000, fails;
- a clean SysRq command return still waits for delayed ADB transport loss;
- persistent ADB remains a fail-closed no-panic result.

## Unchanged Safety Ceiling

- Existing V3440 MID result/log/preamble hashes remain exact pins.
- HIGH and MID use the exact verified V3442 setter.
- RDX permits only one `PrEaMbLe\0`; positive ACK still stops before probe.
- Source has no binary `PrObE` or `DaTaXfEr` payload and no probe parser.
- Failed evidence collection cannot bypass the mandatory MID restore attempt.
- Emergency modes verify all V3441/Magisk/stock recovery artifacts first.

## Static Validation

```text
helper_sha256   8d66d9e1766eac674589ac77b0ea7c82b5243274cc502b3cbd20bcfb09e8192c
focused_tests   11/11 PASS
policy          DRAFT_INACTIVE
device_actions  0
```

Next: run the complete related regression set and offline check, commit the
corrected source-ready checkpoint, then require a fresh explicit operator
approval. The consumed V3443 approval cannot authorize V3443R.
