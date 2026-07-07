# S22+ Sec Debug MID Set Read-Only Result (2026-07-08)

## Verdict

READ-ONLY CONFIRMATION PASS.

After the operator selected DEBUG LEVEL in the physical Samsung SysDump UI, the
phone rebooted normally back into Android. A follow-up read-only probe confirms
the retail LOW state moved to a MID-class sec_debug state.

No flash, partition write, procfs/sysfs write, sysrq trigger, Odin transfer,
Magisk module install, native-init candidate action, or intentional crash was
performed by Codex in this unit. The reboot was an operator-observed effect of
the Samsung DEBUG LEVEL UI action.

## Live Result

Android returned cleanly:

```text
adb state:          device
sys.boot_completed: 1
boot_recovery:      0
vbstate:            orange
root:               uid=0(root) ... context=u:r:magisk:s0
visible UI:         com.sec.android.app.servicemodeapp/.SysDump
```

Follow-up read-only probe:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --read-only-probe
```

Private run, not committed:

```text
workspace/private/runs/s22plus_sec_debug_mid_sysrq_20260707T210400Z
```

Public sec_debug state:

```text
debug_level decimal   18765
debug_level hex       0x494d
debug_level ascii_le  MI
debug_level ascii_be  IM
likely_low_code       false
enable                1
enable_user           0
force_upload          5
/proc/sys/kernel/sysrq still 0 before any intentional panic gate
```

Previous LOW baseline:

```text
debug_level decimal   20300
debug_level hex       0x4f4c
debug_level ascii_le  LO
likely_low_code       true
```

## Interpretation

The SysDump package restore fixed the physical `*#9900#` route, and the
operator's DEBUG LEVEL action changed the kernel sec_debug state from LOW to
MID-class. The helper only decodes the two-byte kernel parameter representation,
so it reports `MI` rather than a three-character `MID`; the important gate is
that the value is no longer `LO` and `enable` is now `1`.

This satisfies the precondition that blocked the zero-flash positive-control
panic gate. The next live-capable unit is still separate: promote the inert
sec_debug MID sysrq-panic exception, run the dry-run, then run exactly one
attended `--live-panic` only with explicit operator approval.

Expected physical involvement for the next live unit:

```text
Before live panic: none beyond keeping USB connected and watching the screen.
After live panic: operator may need to recover from Upload Mode / Download /
                  reboot state, then reconnect ADB so Codex can collect logs.
```

Do not trigger sysrq panic automatically from this report.
