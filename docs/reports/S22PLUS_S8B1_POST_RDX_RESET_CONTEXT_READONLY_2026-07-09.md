# S22+ S8B1 Post-RDX Reset Context Read-Only Capture (2026-07-09)

Host-side read-only capture only. No Odin transfer, reboot, flash, partition
write, sysfs write, module load, or rollback was performed by this report.

## Context

After the operator reported an RDX screen followed by manual Download-mode
entry, the phone was observed back in normal Android/Magisk baseline. The
S8B1 live gate is still not authorized: there is no active S8B1 `AGENTS.md`
exception and no live flash was run.

## Helper Update

Enhanced:

```text
workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py
```

The helper already captured `/proc/reset_*`, `/proc/last_kmsg`, pstore,
props, boot/vendor_boot hashes, and dmesg grep output. It now also structures
the reset context in `summary.json`:

```text
proc_reset_reason_value
proc_reset_rwc_value
proc_store_lastkmsg_value
reset_history_upload_causes
reset_history_upload_cause_count
reset_history_pmic_abnormal_count
reset_summary_pmic_abnormal_count
reset_history_oem_reset_magic_values
reset_history_oem_reset_magic_count
```

Added unit tests:

```text
tests/test_s22plus_reset_reason_readonly_probe.py
```

## Read-Only Capture

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py --serial <S22_SERIAL_REDACTED>
```

Run directory:

```text
workspace/private/runs/s22plus_reset_reason_readonly_20260709T025333Z/
```

Device/action gates:

```text
device_action=read-only-adb-root
writes_performed=false
reboots_performed=false
flashes_performed=false
result=pass
```

Baseline identity:

```text
ro.product.model=SM-S906N
ro.product.device=g0q
ro.build.version.incremental=S906NKSS7FYG8
ro.boot.verifiedbootstate=orange
sys.boot_completed=1
su_root=true
```

Partition hashes:

```text
boot SHA256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
boot_matches_magisk_baseline=true
vendor_boot SHA256=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
vendor_boot_matches_stock=true
```

Reset context:

```text
ro.boot.bootreason=reboot,download
sys.boot.reason=reboot,download
persist.sys.boot.reason.history=reboot,download,1754235202
/proc/reset_reason=MPON
/proc/reset_rwc=41
/proc/store_lastkmsg=1
/sys/module/qcom_dload_mode/parameters/download_mode=1
pstore entry_count_estimate=0
```

Samsung reset history retained PMIC abnormal reset evidence:

```text
reset_history_upload_cause_count=10
reset_history_pmic_abnormal_count=10
reset_summary_pmic_abnormal_count=1
reset_history_upload_causes[0]=0x0 / PMIC abnormal reset
reset_history_oem_reset_magic_values[0]=0x910d00f8
```

## Interpretation

The operator's RDX observation is now corroborated by read-only Android reset
surfaces: the current boot reports Download-mode boot reason, `/proc/reset_reason`
is `MPON`, reset RWC is nonzero, `store_lastkmsg=1`, and Samsung reset history
contains repeated `PMIC abnormal reset` upload-cause entries. This does not
prove an S8B1 candidate result because no S8B1 live run was performed. It does
prove the post-RDX/manual-Download recovery returned to the expected Magisk
baseline and that reset-context surfaces are more informative than pstore alone
for this recovery path.

## S8B1 Packet Integration

The S8B1 prelive packet generator now embeds this same no-write reset-context
shape as `android_reset_context_baseline` and verifies the sidecar JSON during
`--verify-prelive-packet`. The latest packet with the integrated baseline is:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T030213Z/s22plus_m34_s8b1_prelive_packet.json
```

It verified cleanly at:

```text
workspace/private/runs/s22plus_m34_s8b1_beacon_probe_live_gate_20260709T030227Z/
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_reset_reason_readonly_probe.py
Ran 2 tests, OK

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_reset_reason_readonly_probe.py tests/test_s22plus_m23_dts_qmp_reset_summary_live_gate.py tests/test_s22plus_m24_pmsg_steps_live_gate.py tests/test_s22plus_m25_hs_only_usb2_acm_live_gate.py
Ran 24 tests, OK

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py
OK

git diff --check
OK
```
