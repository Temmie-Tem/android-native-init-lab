# S22+ M34 S11P0 Live Result

Date: 2026-07-10 KST / 2026-07-09 UTC

## Verdict

S11P0 live result is a predicate MISS, not a HIT.

The candidate flashed and booted far enough to leave the original Odin endpoint,
but no new Download beacon appeared during the bounded observation window. That
means the S11P0 predicate did not reach its true-action path:

```text
(direct cmd-db.ko finit accepted) && (/proc/modules shows qcom_wdt_core or gh_virt_wdt)
```

The S11P0 one-shot live exception is consumed and must not be reused for another
S11P0/S11P1/S10 repeat or any other boot candidate.

## Evidence

Primary live run:

```text
run_dir=workspace/private/runs/s22plus_m34_s11p0_proc_modules_positive_control_live_gate_20260709T164647Z
result=download-beacon-miss-parked-manual-download-required
rc=1
stage=S11P0
candidate_ap_sha256=dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45
candidate_boot_sha256=3ac8b8a5dde2ef6c3f7170c258a4dc6f3a3f9a4bb4575b5af5cf3380952d7881
module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible
positive_control_proc_names=qcom_wdt_core,gh_virt_wdt
```

The primary run observed no Odin device through the 90s candidate window, then
waited for manual Download. Manual Download appeared as `/dev/bus/usb/003/010`,
but rollback failed:

```text
manual_after_miss_magisk_rollback_odin_rc=1
ioctl bulk write Fail : Protocol error 71
manual_after_miss_stock_rollback_odin_rc=1
No such file or directory
usb device Fail
```

The fallback failure was a host-side stale USB path issue: after the protocol
error the helper immediately reused `/dev/bus/usb/003/010`, which no longer
existed.

Rollback-only recovery run:

```text
run_dir=workspace/private/runs/s22plus_m34_s11p0_proc_modules_positive_control_live_gate_20260709T164946Z
rollback_target=magisk
rollback_device=/dev/bus/usb/002/010
rollback_only_magisk_rollback_odin_rc=0
```

This run transferred the pinned Magisk boot-only AP successfully. It also saw a
transient Android/root proof at `2026-07-09T16:50:27Z`:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
su_root_rc=0
su_root_out=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

However the helper later timed out and returned:

```text
result=rollback-only-no-s11p0-proof
rc=5
```

The helper result remained non-zero because ADB did not stay available until
the helper timeout. Subsequent host checks proved that the Magisk boot flash did
land and that the rooted measurement baseline recovered.

## Final Recovery State

Current post-recovery verification:

```text
adb device=RFCT519XWGK usb:2-1.3 product:g0qksx model=SM_S906N device=g0q
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
su=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
/debug_ramdisk/su -> ./magisk
/product/bin/su -> ./magisk
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

A 30s stability loop saw ADB remain in `device` state with
`boot_completed=1` throughout. Final state is the rooted Magisk measurement
baseline, not stock recovery.

## USB Transport Instability

Host kernel log shows Android USB enumerated briefly:

```text
2026-07-10 01:50:25 KST idVendor=04e8 idProduct=6860 Product=SAMSUNG_Android
2026-07-10 01:50:25 KST cdc_acm ... ttyACM0
2026-07-10 01:50:29 KST USB disconnect
```

Later Android USB returned as `04e8:6860` with an ADB-looking vendor interface,
but ADB initially failed at the USB transport layer:

```text
adb opened /dev/bus/usb/002/012
transport registered RFCT519XWGK
remote usb: write terminated: Protocol error
read failed: Protocol error
errno=71
```

After a disconnect/re-enumeration at `2026-07-10 02:10:51` to `02:10:53` KST,
ADB stabilized and final recovery verification succeeded.

If this recurs, use this discriminator:

```text
Download mode enumerates as 04e8:685d -> Android USB gadget/settings/state issue.
Download mode also absent           -> physical cable/port/hub/host path first.
```

Because the observed failure was USB bulk `errno 71` on a SuperSpeed path,
prefer a direct cable or USB2 path for the next flash/recovery loop if the issue
repeats.

## Host Fix

The common Odin device listing now filters stale `/dev/bus/usb/...` paths by
actual device-node existence before returning them to rollback code. This
prevents a failed rollback from immediately reusing a dead path reported by a
stale `odin4 -l` result.

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py \
  tests/test_s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py \
  --offline-check \
  --run-dir /tmp/s22_s11p0_offline_check_after_stale_filter
```

All three validations passed.

## Next Step

The next native-init design should continue S11 with a stronger direct
per-module result channel. S11P0 proved that the combined true-action beacon is
not enough to distinguish watchdog `/proc/modules` invisibility from loader
state or observation-channel failure.
