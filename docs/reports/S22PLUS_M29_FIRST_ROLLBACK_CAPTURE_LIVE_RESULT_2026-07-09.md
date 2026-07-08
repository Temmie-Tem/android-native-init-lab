# S22+ M29 First-Rollback Capture Live Result (2026-07-09 KST)

## Verdict

CONSUMED / MANUAL-DOWNLOAD CONTAMINATED / NO CANDIDATE EVIDENCE / BASELINE CLEAN.

M29 did not produce a clean S24 self-download proof. The host observed no ADB
and no Odin for the bounded post-candidate window; the operator observed a
bootloop and manually entered Download mode. The checked M29 rollback-from-
download path restored Magisk boot, captured retained surfaces before stock
DTBO restore, restored stock DTBO, and returned the device to the known
Android/Magisk baseline.

The first post-M29 rollback capture still did not contain native-init evidence.
It retained an Android reboot/download boot, so the M29 collection-timing
hypothesis is weakened and must not be used as a reason to repeat S24.

## Runs

Live run:

```text
workspace/private/runs/s22plus_m29_first_rollback_capture_live_gate_20260708T150223Z/
```

Rollback-from-download run:

```text
workspace/private/runs/s22plus_m29_first_rollback_capture_live_gate_20260708T150539Z/
```

## Candidate Observation

M29 reused the existing M28 dependency-complete S24 candidate:

```text
S24 AP.tar.md5 SHA256  c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f
S24 boot.img SHA256    a1459931001bfd6e17593dd329fc682f00ab61f4841b6543791f5349dd012cd0
S24 /init SHA256       5c04a2023b2b56ef98746da6f7168121b62d7859cee81c756b80d1a382c1964e
```

Host-side result after candidate flash:

```text
m29_S24_self_download_seen=0
m29_S24_result=no-self-download-manual-download-required
m29_S24_final_rc=4 result=manual-download-required
```

Timeline:

```text
candidate_flash_done  2026-07-08T15:03:56Z
self-download poll    2026-07-08T15:03:57Z..15:04:41Z
live_session_end      2026-07-08T15:04:42Z
```

No clean Odin reappearance was observed during the helper window. The later
Download mode was operator-entered and is not proof of candidate self-download.

## First Rollback Capture

The recovery path flashed the pinned Magisk boot rollback AP, waited for rooted
Android, and captured retained evidence before stock-DTBO rollback.

First-capture fingerprint:

```text
last_kmsg_bytes=2097136
last_kmsg_sha256=5306bb56ddd5f73f75921dea18c17fa5b07fffba30262b858647e27c302704da
m29_marker_count=0
s22_native_count=0
android_really_probe_count=49
android_reboot_download_count=1
watchdog_count=30
kernel_panic_count=0
unknown_symbol_count=0
pstore_files=[]
```

The retained log contains Android init handling `sys.powerctl='reboot,download'`
from `/system/bin/reboot`; it does not contain the M28/M29 native marker or any
S22 native-init line. Reset surfaces reported NPON / reboot,download and no
retained marker.

## Final Baseline

Independent post-run verification:

```text
sys.boot_completed=1
init.svc.bootanim=stopped
ro.boot.verifiedbootstate=orange
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot_sha=096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

## Interpretation

M29 answered the narrow collection-order question negatively. Capturing earlier
than stock-DTBO rollback did not recover S24 candidate evidence after a manual
Download recovery. The retained channel remains alive, but the available blob is
still an Android boot, not the native-init candidate.

Do not run F43 or repeat S24 under this gate. The next unit should be host-only:
explain why S24 becomes host-invisible and why retained evidence still resolves
to Android. A future live attempt needs a fresh, narrower exception and should
either create a more durable pre-rollback observation path or reduce the first
fault discriminator further.

