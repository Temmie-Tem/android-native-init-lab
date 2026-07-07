# S22+ M21A Raw Nanosleep-Download Host Build (2026-07-08)

## Verdict

HOST-ONLY BUILD PASS. No flash, reboot, Odin live action, or device write was
run for this unit.

M21A is the timed floor discriminator that follows the M20A manual-download
correction. It keeps the candidate below C/libc/fs/modules/configfs while
adding a 90 second raw `nanosleep(2)` dwell before `reboot(..., "download")`.
The dwell is the proof separator for a future attended live gate.

Live flashing is not authorized by this report.

## Candidate

Source:

`workspace/public/src/native-init/s22plus_init_raw_nanosleep_download_m21a.S`

Builder:

`workspace/public/src/scripts/revalidation/build_s22plus_m21a_raw_nanosleep_download.py`

Private output:

`workspace/private/outputs/s22plus_native_init/m21a_raw_nanosleep_download_v0_1`

Runtime shape:

```text
raw AArch64 PID1
no C runtime / libc / PT_INTERP
no filesystem setup
no marker write
no module load
no configfs or USB role force
nanosleep({90,0}, NULL)
reboot(LINUX_REBOOT_CMD_RESTART2, "download")
wfe park if reboot returns
```

## Hashes

```text
source              300ed990c8ea476c3744e18327ae08277c0d27dc443e99245aeecba457968c4f
base_boot           2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
nochange_repack     2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
original_magisk_init 383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
kernel              bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
init                10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30
boot_img            61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5
boot_img_lz4        ef0503c5c29288dd9963ca4aba2afdceef656c0c686f81205b039e9f06c74e7f
AP.tar.md5          d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79
```

AP member list:

```text
boot.img.lz4
```

## Static Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m21a_raw_nanosleep_download.py

aarch64-linux-gnu-gcc -nostdlib -static -Wl,--build-id=none \
  -Wl,-e,_start -Wl,-z,noexecstack \
  -o /tmp/s22plus_m21a_init_check \
  workspace/public/src/native-init/s22plus_init_raw_nanosleep_download_m21a.S

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m21a_raw_nanosleep_download.py \
  --force
```

Results:

- `py_compile`: pass.
- Raw init compile: pass.
- Raw init ELF: AArch64, statically linked, stripped in final output, no
  interpreter.
- Final `/init` disassembly loads `x8=#0x65` for arm64 `__NR_nanosleep`
  (101), then `x8=#0x8e` for arm64 `__NR_reboot` (142).
- Final `/init` contains exactly two `svc #0` instructions.
- Required strings present:
  `S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD`,
  `nanosleep_sec=90`, and `download`.
- Forbidden strings absent: dynamic loader/libc, `/dev/kmsg`, `/lib/modules`,
  `finit_module`, module lists, `ttyGS0`, `ss_acm.0`, `usb_gadget`, and
  `/config`.
- Magiskboot no-change repack is byte-identical to the rooted Magisk base boot.
- Patched boot remains boot-partition sized and changes only through the
  intended ramdisk `/init` replacement path.
- Odin parse gate with an intentionally invalid device parsed the AP and failed
  only on the nonexistent USB path.

## Safety State

The manifest records:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
base_is_known_booting_magisk_boot=true
module_insertions=false
module_binary_injection=false
configfs_runtime_gadget=false
udc_binding=false
usb_role_force=false
block_device_writes=false
kmsg_marker_write=false
pre_reboot_dwell_sec=90
pre_reboot_syscalls=["nanosleep"]
auto_reboot=download
on_reboot_syscall_return=infinite-park
```

## Future Live Interpretation

A future M21A live gate is meaningful only if it enforces the M21 redesign
rules:

- PASS requires no visible fast loop before the 90 second dwell, no operator key
  intervention, Odin/download mode only after dwell+grace, and rollback to the
  pinned Magisk boot baseline.
- Any Odin endpoint before dwell is no proof.
- Any operator manual download-mode entry is recovery-only / no proof.
- No download after dwell+grace means the candidate did not prove the reboot
  syscall; manual rollback is required.

## Next

Do not flash M21A yet. The next unit, if live testing is selected, must add a
fresh SHA-pinned M21A-only `AGENTS.md` exception and a guarded helper that
records monotonic timing and refuses early Odin/manual-intervention as PASS.
