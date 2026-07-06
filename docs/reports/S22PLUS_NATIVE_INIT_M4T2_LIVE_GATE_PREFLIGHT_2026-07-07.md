# S22+ Native-Init M4T2 Live Gate Preflight - 2026-07-07

## Scope

Prepared and dry-ran the guarded M4T2 raw-park native-init live gate. No live
flash, reboot, Odin transfer, partition write, recovery action, or rollback
action was performed.

M4T2 is different from the M4T0/M4T1 self-download probes: if the raw PID1
runs correctly, it parks forever. Therefore the helper includes a separate
rollback-only mode for after the operator manually enters download mode.

## Public Changes

Added:

```text
workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py
```

Updated `AGENTS.md` with the SHA-pinned M4T2 boot-only live exception and
matching Odin path exception.

## Candidate

Exact candidate hashes:

```text
AP.tar.md5  66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24
boot.img    8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15
base boot   2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
raw /init   b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12
```

The AP contains exactly:

```text
boot.img.lz4
```

No recovery, vendor_boot, vbmeta, vbmeta_system, dtbo, BL, CP, CSC, super,
persist, userdata, EFS, RPMB, keymaster, modem, or any other partition payload
is present.

## Dry-Run

Command:

```bash
python3 workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py \
  --run-dir workspace/private/runs/s22plus_m4t2_park_live_gate_dryrun_20260707T0528Z
```

Result:

```text
dry-run ok: M4T2 candidate, rollback APs, AGENTS exception, and Android preflight verified
```

Dry-run gates:

```text
agents_exception_missing=[]
m4t2_candidate_sha256=66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24
m4t2_candidate_members=['boot.img.lz4']
magisk_boot_rollback_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
magisk_boot_rollback_members=['boot.img.lz4']
stock_boot_fallback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
stock_boot_fallback_members=['boot.img.lz4']
```

Manifest safety gates:

```text
construction=magiskboot unpack/repack; replace only ramdisk /init
mkbootimg_from_scratch=false
first_candidate_action=infinite-park
libc=false
syscalls=false
reboot_request=false
marker_write=false
module_insertions=false
configfs_runtime_gadget=false
watchdog=not-touched
replaced_entry=init
```

Current Android preflight, redacted:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

## Live Boundary

The live command is now gated but was not executed:

```bash
python3 workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py \
  --live \
  --ack S22PLUS-M4T2-RAW-PARK-LIVE-GATE
```

If the phone remains with no ADB/Odin transport after the observation window,
that may be the intended raw park behavior or an earlier dark hang; either way
the helper stops and requires manual download-mode entry. Rollback is then:

```bash
python3 workspace/public/src/scripts/revalidation/s22plus_m4t2_park_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M4T2-ROLLBACK-FROM-DOWNLOAD
```

M4T2 live should not be run unattended. Its useful signal is visual/behavioral:
whether the fast reboot loop stops.
