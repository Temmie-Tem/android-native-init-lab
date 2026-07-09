# S22+ Magisk Boot Baseline Restore Active Exception

Date: 2026-07-10 01:19 KST / 2026-07-09 16:19 UTC

## Verdict

The Magisk boot-baseline restore gate is now mechanically ready for an explicit
operator-approved live restore. No live restore was run in this unit.

Current policy state:

```text
S10C0 live gate: consumed
Magisk boot-baseline restore gate: active
live ack token: S22PLUS-MAGISK-BOOT-BASELINE-RESTORE-GATE
```

The active exception is intentionally narrow: one bounded attended boot-only
Magisk measurement-baseline restore using only
`workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py`.

## Pre-Live Checks

AGENTS active exception verification:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py \
  --verify-agents-candidate AGENTS.md \
  --run-dir workspace/private/runs/s22plus_magisk_boot_baseline_restore_agents_verify_20260709T161907Z
```

Result:

```text
verify-agents-candidate ok: Magisk boot baseline restore exception is present
```

Host artifact offline check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py \
  --offline-check \
  --run-dir workspace/private/runs/s22plus_magisk_boot_baseline_restore_offline_20260709T161907Z
```

Result:

```text
offline-check ok: Magisk boot baseline restore artifact verified; no device action
```

Current Android identity check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py \
  --check-current-android \
  --run-dir workspace/private/runs/s22plus_magisk_boot_baseline_restore_check_android_20260709T161907Z
```

Result:

```text
check-current-android ok: S22+ stock Android identity verified; no device action
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
```

## Helper Hardening

`--live-from-android` now verifies the current Android identity before issuing
`adb reboot download`:

```text
boot_completed=1
model=SM-S906N
device=g0q
incremental=S906NKSS7FYG8
vbstate=orange
```

This prevents the helper from rebooting an unrelated, wrong-build, incomplete,
or non-orange Android session into Download mode.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py \
  tests/test_s22plus_magisk_boot_baseline_restore_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_magisk_boot_baseline_restore_gate.py
```

Result:

```text
Ran 9 tests in 0.014s
OK
```

## Next Live Command

Only after explicit operator approval:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py \
  --live-from-android \
  --ack S22PLUS-MAGISK-BOOT-BASELINE-RESTORE-GATE \
  --run-dir workspace/private/runs/<fresh-run-dir>
```

If the operator manually places the phone in Download mode first, use
`--live-from-download` instead.
