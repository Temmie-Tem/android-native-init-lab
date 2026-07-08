# S22+ M31B Watchdog-Managed Park Live Result (2026-07-09 KST)

## Verdict

CONSUMED / SURVIVAL WINDOW PASS / ROLLBACK CLEAN /
MANUAL-DOWNLOAD RDX-PMIC SIDE OBSERVED.

The M31B candidate was flashed exactly once. It did not self-boot Android and it
did not expose an ADB/Odin endpoint during the observation window, which is the
expected park shape. The decisive result is that the host observed no ADB/Odin
and the operator reported no bootloop during the full 120 second park window.
This passes the survival discriminator that was intended to test whether loading
the stock watchdog dependency closure removes the prior ~30 second PMIC/PON
ceiling.

The later manual Download recovery path was not clean on the first endpoint:
the operator observed the RDX `PMIC abnormal reset` screen while trying to enter
Download mode, and the first Odin endpoint failed both Magisk and stock rollback
attempts with USB protocol error 71. After re-entering normal Download mode, the
checked rollback helper restored the pinned Magisk boot AP and Android/Magisk
returned cleanly.

No active M31B authorization remains.

## Runs

Candidate live run:

```text
workspace/private/runs/s22plus_m31b_wdt_managed_park_live_gate_20260708T162708Z/
```

Rollback-from-Download run:

```text
workspace/private/runs/s22plus_m31b_wdt_managed_park_live_gate_20260708T163308Z/
```

Post-rollback offline artifact check:

```text
workspace/private/runs/s22plus_m31b_wdt_managed_park_live_gate_20260708T163409Z/
```

## Candidate

```text
AP.tar.md5       06d1c149c7c09a284062826f21ac848220e99d552d6b91762abbfb80f3679527
boot.img         206fbb40df69a496f7fbe67e32cf862049d9258ef518db6949e1b5db2f4afdc4
/init            b01e52d3762e3cbdcba3501b00bb1dc9f9084899550ea23b92df43884bed23d0
module-list      80da959311e4a0f6bedb40da3c6f74c7fd5918017e40e0787b3e17c153cfe937
source           32d85b4aeb64e5e1615b175b93fde166795598bfa0614934a9dcfb1bb165230d
kernel           bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
base boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The AP contained exactly one tar member, `boot.img.lz4`.

Runtime shape:

```text
modules loaded: smem.ko, minidump.ko, qcom-scm.ko, qcom_wdt_core.ko, gh_virt_wdt.ko
reboot syscall: no
Download beacon: no
USB/configfs/ACM: no
Android/Magisk handoff: no
persistent partition mount: no
block write: no
```

## Live Observation

Candidate transfer:

```text
endpoint              /dev/bus/usb/002/050
candidate_odin_rc     0
post disconnect       observed, Odin absent at 2026-07-08T16:27:32Z
```

Observation window:

```text
m31b_observe_start_utc=2026-07-08T16:27:32Z
m31b_observe_sec=120
m31b_park_observe_024_elapsed_sec=117.003
m31b_survival_window_pass=1
m31b_result=survived-observation-window-manual-download-required
```

Every host snapshot through the last sample showed no ADB device and no Odin
device:

```text
adb devices -l: List of devices attached
odin4 -l: devices=[]
```

The operator reported that the device did not enter the prior bootloop pattern
during this window.

## Manual Download Recovery

After the helper reported survival and asked for manual Download rollback, the
operator observed the RDX `PMIC abnormal reset` screen. The first host-visible
endpoint was not usable for rollback:

```text
endpoint                                             /dev/bus/usb/003/025
manual_after_survival_magisk_boot_rollback_odin_rc   1
manual_after_survival_stock_boot_fallback_odin_rc    1
error                                                ioctl bulk write Fail : Protocol error 71
```

This first endpoint is treated as a recovery-path side observation, not as a
candidate survival failure. It occurred after the survival window had already
passed.

The operator then re-entered normal Download mode and the checked rollback mode
completed:

```text
endpoint                         /dev/bus/usb/002/051
manual_magisk_boot_rollback_rc   0
rollback_boot_ready              2026-07-08T16:33:54.739179Z
```

Rollback command run by the helper:

```text
/usr/bin/odin4 --reboot -a workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5 -d /dev/bus/usb/002/051
```

## Timelines

Candidate live timeline:

```text
live_session_start      2026-07-08T16:27:19.115945Z
candidate_flash_start   2026-07-08T16:27:29.861942Z
candidate_flash_done    2026-07-08T16:27:31.348791Z
candidate_boot_ready    2026-07-08T16:27:32.626228Z
rollback_flash_start    2026-07-08T16:32:31.288374Z
rollback_flash_done     2026-07-08T16:32:31.326529Z
live_session_end        2026-07-08T16:32:31.368449Z
```

The `rollback_flash_*` entries above are the failed first-endpoint attempts
after survival, not the successful final rollback.

Successful rollback timeline:

```text
live_session_start      2026-07-08T16:33:08.185768Z
rollback_flash_start    2026-07-08T16:33:08.188164Z
rollback_flash_done     2026-07-08T16:33:09.539105Z
rollback_boot_ready     2026-07-08T16:33:54.739179Z
live_session_end        2026-07-08T16:33:55.106001Z
```

## Final Baseline

Post-rollback helper verification:

```text
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Independent final read-only check:

```text
boot_sha=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot_sha=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
Android boot complete, vbstate orange, Magisk root present
```

## Retained Evidence

```text
post_m31b_manual_rollback_pstore_files=[]
post_m31b_manual_rollback_pstore_marker_found=0
post_m31b_manual_rollback_last_kmsg_rc=0
post_m31b_manual_rollback_last_kmsg_bytes=2097136
post_m31b_manual_rollback_last_kmsg_marker_found=0
post_m31b_manual_rollback_retained_marker_found=0
```

The retained log did not contain the M31B marker. That is not unexpected for
this unit: the useful proof channel was survival past the prior reset window,
not retained marker collection after a manual Download/RDX recovery path.

## Interpretation

M31B is a positive discriminator for the current PMIC/PON watchdog model. The
same family of bare PID1 candidates previously reset around the ~30 second
window; M31B loaded the stock watchdog dependency closure and stayed in the
parked state past 120 seconds. That strongly supports the direction that
native-init must manage the watchdog early rather than blocklist it.

The result does not prove USB/ACM bring-up, display, Debian handoff, or any
instruction-level marker. It proves the prior dwell ceiling is no longer the
first blocker when the watchdog closure is present.

The RDX `PMIC abnormal reset` and Odin protocol error 71 after the survival
window should be tracked as a recovery/Download-mode edge. A PC-side dump
retrieval test from RDX/S-Boot is possible as a separate read-only experiment,
but it was not run under this consumed M31B gate and needs its own fresh scope
and stop conditions.

## Next

Do not repeat M31B under the consumed authorization.

The next native-init unit should build from the M31B base and add the smallest
observable transport, preferably a watchdog-managed USB/ACM or link-only USB
substrate with no broad module replay. Success should still preserve the
survival property while adding a host-visible control path.

An alternate bounded unit is a read-only RDX/S-Boot dump retrieval rehearsal
using the PC connection path shown on the RDX screen. That would answer whether
future PMIC/RDX incidents can yield dumps directly to the host, but it should be
kept separate from boot-candidate flashing.
