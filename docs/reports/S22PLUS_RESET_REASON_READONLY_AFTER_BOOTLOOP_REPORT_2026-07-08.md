# S22+ Reset-Reason Read-Only Probe After Bootloop Report - 2026-07-08

## Summary

After the operator reported a bootloop followed by manual Download entry, the
host later observed the phone back in normal Android ADB mode.  Codex ran the
read-only reset-reason probe to capture the Samsung reset-context surfaces
without flashing, rebooting, writing partitions, writing sysfs, or changing the
device.

Result: current Android baseline is clean, but the current boot did not retain a
useful watchdog reset-context payload.  The reset-summary family exists, but
opens as an empty/no-header surface on this normal boot.

## Run

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py`
- Private run directory:
  `workspace/private/runs/s22plus_reset_reason_readonly_20260708T001814Z`
- Device action:
  read-only ADB root collection
- Writes/reboots/flashes:
  none

## Baseline Checks

All helper checks passed:

```text
target_model=true
target_device=true
target_build=true
android_booted=true
normal_boot=true
root_available=true
boot_hash_baseline=true
vendor_boot_hash_stock=true
```

Pinned live hashes:

- boot:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- vendor_boot:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

Android boot properties reported `reboot,userrequested` rather than a native
candidate watchdog/reset reason.

## Reset Surfaces

Current values:

```text
/proc/reset_reason     RPON
/proc/reset_rwc        0
/proc/store_lastkmsg   0
pstore entries         0
```

The Samsung reset-context files were present but did not expose a retained
payload on this boot:

```text
/proc/reset_summary    failed to load reset_header (-2)
/proc/reset_klog       failed to load reset_header (-2)
/proc/reset_history    failed to load reset_header (-2)
/proc/reset_tzlog      failed to load reset_header (-2)
```

`dmesg` still shows the normal `msm_watchdog_data` pet cadence and the
`sec_qc_user_reset` reset-header failures when those proc nodes are opened.

## Interpretation

This run confirms the reset-summary reader path is available and safe to use,
but it does not retroactively recover a useful M23/M18 native-init hang payload
from the current Android boot.  The reset-summary capture must be run
immediately after the next attended candidate rollback, which is now wired into
the M23 reset-summary live gate.
