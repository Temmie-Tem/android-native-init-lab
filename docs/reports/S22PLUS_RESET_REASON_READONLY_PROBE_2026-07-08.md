# S22+ Reset/PON Reason Read-Only Probe (2026-07-08)

## Verdict

PASS / READ-ONLY / NO LIVE FLASH.

Codex added and ran a narrow reset/PON reason collector:

```text
workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py
```

The helper performs no flash, reboot, partition write, sysfs write, module
install, or remote file staging. It uses ADB root only to read the current
Android reset-reason surfaces and writes redacted captures under
`workspace/private/runs`.

Private run:

```text
workspace/private/runs/s22plus_reset_reason_readonly_20260707T183941Z
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py
```

Result: pass.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py
```

Result: pass.

The helper reported:

```text
device_action=read-only-adb-root
writes_performed=false
reboots_performed=false
flashes_performed=false
result=pass
```

## Current Baseline

Read-only checks still prove the current recovery baseline:

```text
model=SM-S906N
device=g0q
build=S906NKSS7FYG8
sys.boot_completed=1
ro.boot.boot_recovery=0
ro.boot.verifiedbootstate=orange
Magisk root=true
```

Current partition hashes:

```text
boot
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e

vendor_boot
096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

Interpretation:

- `boot` still matches the pinned Magisk baseline.
- `vendor_boot` still matches stock FYG8.
- The probe did not alter the device state.

## Reset/PON Surface

Key read-only values:

```text
/proc/reset_reason = NPON
/proc/reset_rwc = 0
/proc/store_lastkmsg = 0
/sys/module/qcom_dload_mode/parameters/download_mode = 1
/sys/module/ramoops/parameters/max_reason = -1
/sys/fs/pstore entry_count_estimate = 0
```

`/proc/reset_summary`, `/proc/reset_history`, `/proc/reset_klog`, and
`/proc/reset_tzlog` exist as proc entries, but their open path currently fails:

```text
sec_qc_user_reset:sec_qc_reset_summary_proc_open() failed to load reset_header (-2)
sec_qc_user_reset:sec_qc_reset_history_proc_open() failed to load reset_header (-2)
sec_qc_user_reset:sec_qc_reset_klog_proc_open() failed to load reset_header (-2)
sec_qc_user_reset:sec_qc_reset_tzlog_proc_open() failed to load reset_header (-2)
```

`/proc/last_kmsg` is readable, but its useful retained lines are Android
download-reboot and bootloader hard-reset records, not native-init crash
evidence:

```text
init: Received sys.powerctl='reboot,download'
init: ####Reboot start, reason: reboot,download, reboot_target: download
sec_qc_rbcmd:__rbcmd_write_pon_rr() power on reason: 0x00000015
samsung,qcom-qcom_reboot_reason: 0x15 is written successfully
PM: Reset by PSHOLD
PM: Reset Type: Hard Reset
PM: PON by CBLPWR
```

The retained grep did not surface `S22_NATIVE_INIT`, panic, Oops, or SError as
a useful proof for the native-init failure path.

## Interpretation

This closes the zero-flash reset/PON check from the observability steer. Current
Android can report that the last observed path was a download reboot followed by
hard reset / CBLPWR PON, but it still cannot explain the native-init bootloop.
`pstore` remains empty with stock `vendor_boot`, and Samsung reset summary/klog
proc nodes lack a loadable reset header in this state.

The next evidence-producing unit remains the policy-active
`vendor_boot` ramoops enable + M13 positive-control live gate. Another blind
native-init boot candidate would not improve observability.
