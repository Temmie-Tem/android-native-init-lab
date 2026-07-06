# S22+ Native-Init M4T2 Live Result - 2026-07-07

## Scope

One attended S22+ M4T2 raw-park native-init live gate using the SHA-pinned
`AGENTS.md` exception and guarded helper. The action touched only the `boot`
partition through Odin AP packages. No recovery, vendor_boot, vbmeta, dtbo, BL,
CP, CSC, userdata, EFS, RPMB, keymaster, modem, or other partition payload was
flashed.

M4T2 was intentionally designed as a no-transport visual/behavioral test:
success means the device does not fast reboot or bootloop after the candidate is
flashed. A clean run parks in raw PID1 forever and therefore requires manual
download-mode entry followed by rollback-only.

## Candidate

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py
```

Run directories:

```text
workspace/private/runs/s22plus_m4t2_park_live_gate_live_20260707T0535Z
workspace/private/runs/s22plus_m4t2_park_rollback_20260707T0531Z
```

Candidate hashes:

```text
AP.tar.md5  66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24
boot.img    8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15
raw /init   b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12
base boot   2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

The AP contained exactly one member:

```text
boot.img.lz4
```

The replacement `/init` is raw AArch64 assembly, static, stripped, has no
`PT_INTERP`, has no libc/loader dependency, performs no syscalls, does not write
a marker, does not request reboot, and immediately enters an infinite
`wfe; b` park loop.

## Live Timeline

Preflight:

```text
exact M4T2 AP hash verified
rollback APs staged
current Android baseline: SM-S906N / g0q / S906NKSS7FYG8
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
```

M4T2 observation window:

```text
m4t2_transport_seen=0
m4t2_result=no-transport-after-observation-manual-download-required
helper rc=4
```

The helper's `rc=4` is expected for this test because M4T2 does not try to bring
up ADB, USB gadget configfs, or self-download. During the observation window the
host saw no ADB/Odin transport return. The operator visually confirmed the key
behavioral signal: the device stopped/parked and did not enter the prior fast
bootloop.

## Rollback

The operator manually entered download mode after the M4T2 park observation. The
rollback-only helper then flashed the known-good Magisk boot AP.

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
retained M4T2 marker found: false
```

This is expected: M4T2 intentionally writes no marker and does not panic. The
primary evidence channel for this rung is the attended behavior difference
between prior fast reboot loops and the raw PID1 park.

## Interpretation

M4T2 is the first positive S22+ native-init PID1 proof:

- the boot-only candidate was accepted and flashed;
- the candidate did not immediately return to download mode;
- the candidate did not return Android/ADB;
- the candidate did not repeat the prior fast bootloop;
- the device instead parked in the exact way the raw `/init` was designed to do.

That strongly indicates the kernel can execute a custom ramdisk `/init` on this
S22+ path, and the raw `_start` reached the infinite park loop.

This narrows the earlier M4T0/M4T1 failures away from "custom `/init` cannot run
at all" and toward the code that those probes added on top of PID1 entry:
glibc/startup, first syscall behavior, `reboot(..., "download")`, immediate
return/exit, or a PID1 panic path after the first attempted action.

## Next Unit

Do not rerun M4T2. The next unit should be host-only until a new SHA-pinned
exception and guarded helper exist. Build upward from the proven raw PID1 park
one primitive at a time:

1. M4T3: raw AArch64, no libc, first action is a single raw syscall such as
   `reboot(LINUX_REBOOT_CMD_RESTART2, "download")`, then park.
2. If raw self-download works, the M4T0/M4T1 fault is likely glibc/startup or
   C runtime packaging.
3. If raw self-download fails, keep libc out and test a safer raw marker channel
   such as `openat`/`write` to kmsg or pmsg followed by park.

Any next live boot candidate still requires a fresh SHA-pinned `AGENTS.md`
exception, guarded helper, dry-run, attended observation, and rollback plan.
