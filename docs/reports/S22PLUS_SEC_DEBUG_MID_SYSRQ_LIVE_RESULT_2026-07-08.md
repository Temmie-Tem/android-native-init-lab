# S22+ Sec Debug MID Sysrq Live Result (2026-07-08)

## Verdict

LIVE POSITIVE CONTROL PASS. SAMSUNG `sec_debug` / DEBUG LEVEL MID RETAINS THE
KERNEL PANIC LOG.

The one-shot zero-flash Android-side sysrq panic gate was consumed after active
policy promotion and dry-run. The phone entered a Download/Upload-style state
after the intentional panic, the operator manually rebooted it back to Android,
and `--collect-after-recovery` found the control marker and panic evidence in
`/proc/last_kmsg`.

No Odin flash, partition write, boot image write, DTBO write, vendor_boot write,
recovery/vbmeta/BL/CP/CSC/super/userdata/EFS/sec_efs/RPMB/keymaster/modem/
bootloader write, raw host `dd`, fastboot, or Magisk module install was
performed.

## Live Trigger

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --live-panic \
  --ack S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE \
  --confirm-debug-level-mid DEBUG_LEVEL_MID_SET_BY_OPERATOR
```

Private run, not committed:

```text
workspace/private/runs/s22plus_sec_debug_mid_sysrq_20260707T211709Z
```

Result:

```text
live helper rc: 4
post_trigger_observed: adb_disconnected
host follow-up USB: Samsung Download mode, USB ID 04e8:685d
operator action: manual reboot back to Android
```

The `rc=4` is the helper's expected "trigger happened; recover and collect"
state, not a rollback failure.

## Post-Recovery Collection

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py \
  --collect-after-recovery
```

Private run, not committed:

```text
workspace/private/runs/s22plus_sec_debug_mid_sysrq_20260707T212156Z
```

Result:

```text
post-recovery collection rc: 0
marker_found: 1
Android returned: sys.boot_completed=1
Magisk root: OK
current boot hash: matched known-booting Magisk baseline
```

Retained evidence summary:

```text
/sys/fs/pstore files: []
/proc/last_kmsg bytes: 2097136
/proc/last_kmsg marker_found: true
S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL hits: 2
Kernel panic hits: 2
SysRq/sysrq hits: 20
panic hits: 31
ramdump hits: 15
upload hits: 14
reset hits: 97
sec_debug hits: 1
last_kmsg grep lines: 239
```

Key retained lines, paraphrased from the private log:

```text
S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL phase=before-sysrq
S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL phase=sysrq-trigger-c
sysrq: Trigger a crash
Kernel panic - not syncing: sysrq triggered crash
sec_upload_cause ... cause : sysrq triggered crash
sec_qc_upload_cause ... write cause
summary_update_upload_cause: Start
upload_cause = KERNEL PANIC
```

Final Android state sampled after recovery:

```text
sys.boot_completed=1
root=uid=0(root) ... context=u:r:magisk:s0
debug_level=18765 / 0x494d / MI
sec_debug enable=1
/proc/reset_reason=KPON
/sys/fs/pstore empty
```

## Interpretation

This closes the observability positive-control question:

```text
Samsung SysDump DEBUG LEVEL MID + sec_debug retains a real Android kernel panic
in /proc/last_kmsg on this S22+ build.
```

The earlier mainline ramoops/DTBO path and M22 mainline retained-console path
should not be the default next step. The next native-init fault-capture unit
should route the selected native candidate through this proven Samsung
sec_debug/MID retained-console path, then collect `/proc/last_kmsg` after manual
recovery.

## Policy State

The one-shot `AGENTS.md` sec_debug MID sysrq exception has been marked
consumed/retired after this run. Do not rerun the same intentional Android
sysrq panic under the same gate. A future native-init candidate capture needs a
fresh, narrower exception for the chosen boot artifact and observation path.
