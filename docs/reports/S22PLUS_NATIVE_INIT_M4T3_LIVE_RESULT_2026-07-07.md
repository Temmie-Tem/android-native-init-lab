# S22+ Native-Init M4T3 Live Result - 2026-07-07

## Scope

One attended S22+ M4T3 raw-reboot native-init live gate using the SHA-pinned
`AGENTS.md` exception and guarded helper. The action touched only the `boot`
partition through Odin AP packages. No recovery, vendor_boot, vbmeta, dtbo, BL,
CP, CSC, userdata, EFS, RPMB, keymaster, modem, or other partition payload was
flashed.

M4T3 was the one bounded post-M4T2 syscall discriminator: raw static PID1, no
libc, no marker write, first action is a direct arm64
`reboot(..., "download")` syscall, and syscall-return falls into an infinite
park.

## Candidate

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m4t3_raw_reboot_live_gate.py
```

Run directory:

```text
workspace/private/runs/s22plus_m4t3_raw_reboot_live_gate_live_20260706T204804Z
```

Candidate hashes:

```text
AP.tar.md5  f0a26bb95a091070713f8d736419cbe60974195bb59509cb1fd7cc28a0b1a907
boot.img    d5e0371c6cb68af8990ce3ac4701ad4e0e487dbe54f4702dae29e21d86f4b92a
base boot   2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
raw /init   e975a973395fd1bfe2fee0dccb9d47400e6746d62b508cd139b49c551b9aa67c
```

The AP contained exactly:

```text
boot.img.lz4
```

## Live Timeline

Preflight:

```text
agents_exception_missing=[]
current Android: SM-S906N / g0q / S906NKSS7FYG8
boot_completed=1
verifiedbootstate=orange
Magisk root available
```

Transition to download mode:

```text
adb_reboot_download_rc=0
candidate Odin wait: one download-mode device appeared
```

Candidate flash:

```text
candidate_odin_rc=0
boot.img.lz4 reached 100%
post-candidate-disconnect_odin_absent=1
```

M4T3 self-download observation:

```text
after_candidate_flash timestamp 2026-07-06T20:48:18Z
m4t3_self_download_seen=1
self-download device=/dev/bus/usb/002/086
self-download timestamp 2026-07-06T20:49:02Z
elapsed from original Odin disconnect to self-download: about 44 seconds
```

During this window the operator observed a bootloop-like screen sequence. The
host result still resolved to a new Odin/download-mode device within the
bounded observation window.

Rollback:

```text
rollback AP.tar.md5 sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
rollback AP members=['boot.img.lz4']
rollback Odin rc=0
boot.img.lz4 reached 100%
```

Post-rollback Android verification:

```text
boot_completed=1
bootanim=stopped
model=SM-S906N
device=g0q
build=S906NKSS7FYG8
verifiedbootstate=orange
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Rollback restored the known-good Magisk boot baseline.

## Retained Evidence

After rollback:

```text
/sys/fs/pstore files: none
/proc/last_kmsg bytes: 2097136
retained M4T3 marker found: false
```

This is expected: M4T3 intentionally writes no marker, and the successful proof
channel is the host-observed download-mode return.

## Interpretation

M4T3 is a live pass for the raw `reboot(..., "download")` syscall path from a
custom static PID1:

- the boot-only candidate was accepted and flashed;
- the original Odin/download-mode device disconnected after flash;
- a later Odin/download-mode device appeared within the observation window;
- the helper immediately rolled back to the pinned Magisk boot-only AP;
- Android/root and the known-good boot hash were restored.

The operator-visible loop during the 44 second observation window means the
path is not instant or visually clean. It does not overturn the host proof:
the device did re-enter download mode without manual key input.

This confirms the GOAL steering: continue no more broad micro-syscall probing.
The next useful milestone is the M5 USB-ACM control channel, using the existing
M2 USB-first module order as the host-only build input.

## Next Unit

Stop M4T3 here. The next bounded unit should be host-only:

1. build/design M5 native `/init` around `/proc` + `/sys` mounts;
2. insmod the M2 USB-first chain in order;
3. set up a minimal configfs ACM gadget;
4. park with no Android handoff;
5. add a fresh SHA-pinned live gate only after host build and dry-run pass.

Any M5 live flash still requires the same attended operator ack, boot-only Odin
AP path, and rollback plan discipline.
