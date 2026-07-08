# S22+ M30/M21A Raw Nanosleep-Download Live Result (2026-07-09 KST)

## Verdict

CONSUMED / NO TIMED-DOWNLOAD PROOF / OPERATOR-OBSERVED PHIC ABNORMAL RESET /
ROLLBACK CLEAN.

M30/M21A did not produce the intended automatic Download-mode proof. The
candidate flash succeeded, the original Odin endpoint disconnected, and the
host observed no ADB and no Odin throughout the 90 second dwell plus 30 second
grace window. The operator reported that the device did not fall into the prior
fast bootloop pattern, then observed an RDX screen with `PHIC abnormal reset`.

After the helper returned `no-download-after-dwell-grace`, the operator entered
Download mode manually. The checked rollback helper restored the pinned Magisk
boot AP and Android/Magisk baseline returned cleanly.

## Runs

Candidate live run:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_gate_20260708T153504Z/
```

Manual Download rollback run:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_gate_20260708T154317Z/
```

Post-rollback read-only reset probe:

```text
workspace/private/runs/s22plus_m21a_post_rollback_reset_reason_20260708T154445Z/
```

Additional retained evidence copy:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_result_20260708T154424Z/
```

Operator photo artifact:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_result_20260708T154424Z/operator_photo_phic_abnormal_reset.png
SHA256 7c03abfeecd36619c2939392467747487d231987c6c173ced5b337d6a9ab942e
```

## Candidate Observation

Candidate helper result:

```text
M21A candidate flashed. Waiting 90s dwell + 30s grace.
m21a_download_seen=0
m21a_result=no-download-after-dwell-grace
```

Candidate timeline:

```text
live_session_start      2026-07-08T15:35:05.673136Z
candidate_flash_start   2026-07-08T15:35:16.231088Z
candidate_flash_done    2026-07-08T15:35:17.709879Z
candidate_boot_ready    2026-07-08T15:35:18.979645Z
live_session_end        2026-07-08T15:37:19.682779Z
```

Every host snapshot through elapsed `119.525s` showed:

```text
odin4 devices=[]
adb devices=[]
```

This is not a PASS because Download mode did not appear after dwell plus grace.
It is also not the prior fast-loop shape. The operator observed no immediate
bootloop and later reported a kernel-panic/RDX-style screen.

## Operator Visual Evidence

The photographed screen shows:

```text
RDX (without Token)
PHIC abnormal reset
... print_summary_to_lcd...
pMic init.. Done for RDX
[To PC] Connect a USB cable or
[RDX AGAIN] Press VOL_UP + POWERKEY 3 sec
[RDX EXIT] Press VOL_DOWN + POWERKEY 3 sec
```

This is treated as physical evidence that the candidate path reached an
abnormal reset/RDX state, not a clean self-Download state. The host did not see
an Odin endpoint until the operator manually entered Download mode for rollback.

## Rollback

Rollback endpoint:

```text
/dev/bus/usb/002/047
```

Rollback command run by helper:

```text
/usr/bin/odin4 --reboot -a workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5 -d /dev/bus/usb/002/047
```

Rollback result:

```text
magisk_rollback_odin_rc=0
M21A rollback-from-download completed rc=0
```

Rollback timeline:

```text
live_session_start      2026-07-08T15:43:17.608654Z
rollback_flash_start    2026-07-08T15:43:17.611272Z
rollback_flash_done     2026-07-08T15:43:18.963154Z
rollback_boot_ready     2026-07-08T15:43:54.040019Z
live_session_end        2026-07-08T15:43:54.293127Z
```

## Final Baseline

Independent post-run verification:

```text
sys.boot_completed=1
ro.boot.verifiedbootstate=orange
ro.boot.bootloader=S906NKSS7FYG8
ro.product.device=g0q
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot_sha=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

Read-only reset probe result:

```text
result=pass
android_booted=true
normal_boot=true
root_available=true
boot_hash_baseline=true
vendor_boot_hash_stock=true
ro.boot.bootreason=reboot,download
sys.boot.reason=reboot,download
/proc/reset_reason=MPON
/proc/reset_rwc=25
/proc/store_lastkmsg=1
pstore entry_count_estimate=0
```

## Retained Evidence

Post-rollback helper capture:

```text
post_rollback_pstore_files=[]
post_rollback_pstore_marker_found=0
post_rollback_last_kmsg_rc=0
post_rollback_last_kmsg_bytes=2097136
post_rollback_last_kmsg_marker_found=0
post_rollback_retained_marker_found=0
```

Additional retained last_kmsg copy:

```text
last_kmsg_bytes=2097136
last_kmsg_sha256=39dacfc2dde0e710a80b16cfb08efb1e183b9f882bc15c5fd9d65c041244a42f
S22_NATIVE=0
M21A=0
S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD=0
PHIC=1
RDX=16
abnormal=32
panic=0
download=14
reboot,download=3
watchdog=72
```

The retained log still does not contain a candidate-owned marker. It contains
Android `reboot,download` lines, so retained software evidence remains
insufficient to prove candidate instruction-level progress. The photo is the
only direct PHIC/RDX visual evidence from the candidate incident.

## Interpretation

M30/M21A answered the narrow question negatively: raw PID1
`nanosleep(90s) -> reboot(..., "download")` did not produce a host-observed
timed Download endpoint. The visual result was RDX/PHIC abnormal reset, and the
retained logs again resolved mostly to Android-side reboot/download state.

Do not repeat M21A under the consumed tokens. The next unit should be host-only
postmortem/design. It should separate at least these cases before another
boot-only live:

- Did the raw PID1 actually reach the `nanosleep` return and `reboot` syscall?
- Did Samsung's direct PID1 `reboot(..., "download")` path map to RDX/PHIC
  abnormal reset instead of Odin Download?
- Did watchdog/boot-progress policy reset the device because PID1 stayed asleep
  without Android first-stage progress?
- Is a different observation shape needed, such as a raw timed park with
  operator-held visual proof, a deliberately shorter dwell ladder, or a
  retained marker path that does not depend on Android logs?

Any next live flash requires a fresh, narrower exception and must not reuse the
M30/M21A authorization.
