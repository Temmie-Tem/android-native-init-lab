# S22+ Native-Init M4T0 Live Gate Preflight - 2026-07-07

## Scope

Host-side implementation and dry-run preflight for the M4 TEST 0
instant-download direct-PID1 live gate. No live flash, Odin transfer, reboot,
partition write, Magisk module install, module load, sysfs/configfs write, or
device state change was performed.

The purpose is to make the next attended live test narrow and recoverable:
flash only the exact M4T0 boot-only AP, wait for the candidate's first-action
download reboot, immediately flash the pinned Magisk boot-only rollback AP, then
verify Android/Magisk root and collect retained evidence.

The helper explicitly avoids a false positive where Odin `--reboot` returns
while the original download-mode device is still visible: after the candidate
flash, the original Odin device must disappear first, and only a later Odin
reappearance can count as M4T0 self-download proof.

## Added Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py
```

Dry-run is the default. Live mode requires:

```text
--live --ack S22PLUS-M4T0-INSTANT-DOWNLOAD-LIVE-GATE
```

The helper gates:

- `AGENTS.md` contains the exact M4T0 SHA-pinned exception and ack token;
- candidate AP SHA256 and tar member shape;
- M4T0 manifest hashes, stock-format legacy-LZ4 ramdisk metadata, and safety
  fields;
- pinned Magisk boot-only rollback AP and stock boot-only fallback AP;
- normal Android identity for `SM-S906N` / `g0q` / `S906NKSS7FYG8`;
- Magisk root presence before the live attempt;
- a single target transport before live use.

## Candidate And Rollback Hashes

```text
M4T0 candidate AP.tar.md5:
ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904

M4T0 candidate padded boot.img:
4617a8804b93435cd0b6a5307862b4d5f55ca7e25befa0c19b2e7619284979e9

Magisk boot-only rollback AP:
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56

stock boot-only fallback AP:
1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

The candidate AP contains exactly:

```text
boot.img.lz4
```

Manifest safety fields verified by the helper:

```text
auto_reboot=download-first-action
marker_before_reboot=false
module_insertions=false
configfs_runtime_gadget=false
watchdog=not-touched
ramdisk_format=legacy-lz4
ramdisk_magic=02214c18
```

## Dry-Run Validation

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py \
  workspace/public/src/scripts/revalidation/build_s22plus_instant_download_m4t0_boot.py

python3 workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py \
  --serial <redacted>
```

Private dry-run log:

```text
workspace/private/runs/s22plus_m4t0_instant_download_live_gate_20260706T194711Z/
```

Dry-run result:

```text
dry-run ok: M4T0 candidate, rollback APs, AGENTS exception, and Android preflight verified
```

Preflight identity, redacted:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root) ... context=u:r:magisk:s0
```

Host observation found no Odin device during dry-run, which is expected because
the phone stayed in normal Android and no live reboot/flash was requested.

## Live Boundary

This preflight does not execute the live test. The exact live command shape is:

```text
python3 workspace/public/src/scripts/revalidation/s22plus_m4t0_instant_download_live_gate.py \
  --serial <redacted> \
  --live \
  --ack S22PLUS-M4T0-INSTANT-DOWNLOAD-LIVE-GATE
```

Expected interpretation:

- candidate self-enters download mode: custom `/init` executed and the download
  reboot path works; helper must immediately flash Magisk boot rollback;
- original Odin device never disconnects after candidate flash: helper may
  rollback while still in download mode, but the result is no-proof cleanup, not
  M4T0 success;
- candidate does not self-enter download mode within the bounded window: stop,
  require operator/manual download-mode recovery, and do not infer anything from
  empty pstore alone;
- after rollback, Android/Magisk root must be verified before any next unit.

The live gate does not authorize M4A, display/distro candidates, kernel rebuild,
recovery/vendor_boot/vbmeta/non-boot flash, raw host `dd`, fastboot,
multidisabler, format data, or any A90 action.
