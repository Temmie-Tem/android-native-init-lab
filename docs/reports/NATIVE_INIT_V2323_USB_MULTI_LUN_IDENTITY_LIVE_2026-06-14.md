# Native Init V2323 USB Multi-LUN Identity Live Validation

## Summary

- Cycle: `V2323`.
- Build tag: `v2323-usb-multi-lun-identity`.
- Init version: `0.9.287`.
- Unit: named multi-LUN mass-storage identity U-B.
- Decision: `v2323-usb-multi-lun-identity-live-pass`.
- Result: PASS.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2323_usb_multi_lun_identity.img`.
- Boot SHA256: `c0d5d73ecf66fa26dd8efb1535e6ed61f3e37123ffd175663a5f8709aaf7eccb`.
- Source build report: `docs/reports/NATIVE_INIT_V2323_USB_MULTI_LUN_IDENTITY_SOURCE_BUILD_2026-06-14.md`.

## Scope

V2323 keeps the V2321 parent USB descriptor identity unchanged and changes only the native-init mass-storage persona:

- `lun.0`: SCSI model `A90-INTERNAL`, exact INQUIRY `A90-LNX A90-INTERNAL    0001`, FAT label `A90INTERNAL`.
- `lun.1`: SCSI model `A90-SD`, exact INQUIRY `A90-LNX A90-SD          0001`, FAT label `A90SD`.
- Backing storage: two `/cache` file-backed read-only FAT16 images, 8 MiB each.
- No real `/data`, internal partition, SD raw block, or forbidden partition is exposed.

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2323_usb_multi_lun_identity.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS, 996 tests.
- `git diff --check`: PASS.
- Native init cross-build: PASS, AArch64 static executable.
- Boot image build: PASS.

## Flash Gate

- Rollback image present and SHA verified: `boot_linux_v2321_usb_clean_identity_rodata.img` = `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback present and SHA verified: `boot_linux_v2237_supplicant_terminate_poll.img` = `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback present: `boot_linux_v48.img`.
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Local boot image SHA pinned with `--expect-sha256`.
- Boot block readback SHA matched the pinned SHA.
- Flash total elapsed: 64.439 s.

## Post-Flash Health

- `version`: `A90 Linux init 0.9.287 (v2323-usb-multi-lun-identity)`.
- `status`: boot OK, transport serial ready, NCM ready, TCP control ready.
- `selftest verbose`: `pass=11 warn=1 fail=0`.

## Before Expose

`usb status` showed the control-only topology:

- `gadget.bound=1`.
- `config.0.link_count=2`.
- `function.count=2`.
- `control.acm.present=1`.
- `control.ncm.present=1`.
- `control.ok=1`.

## Expose Result

Command: `usb mass-storage expose`.

- Scheduled worker PID reported.
- Expected disconnect reported.
- Watchdog retained: 8 seconds.
- Control requirement retained: `NCM+ACM`.
- Persona: `readonly-backing`.
- `usb.mass_storage.lun.count=2`.
- `lun.0.backing_file=/cache/a90-usb-mass-storage-v2323-internal.img`.
- `lun.0.model=A90-INTERNAL`.
- `lun.0.volume_label=A90INTERNAL`.
- `lun.1.backing_file=/cache/a90-usb-mass-storage-v2323-sd.img`.
- `lun.1.model=A90-SD`.
- `lun.1.volume_label=A90SD`.
- `usb.mass_storage.read_only=1`.

## Host-Side Identity Validation

Host `lsblk -S` after expose showed two USB SCSI disks:

```text
NAME TRAN VENDOR   MODEL        SERIAL       SIZE STATE
sda  usb  A90-LNX  A90-INTERNAL A90NATIVE001   8M running
sdb  usb  A90-LNX  A90-SD       A90NATIVE001   8M running
```

Host block/label view showed both FAT volume labels and read-only state:

```text
NAME TRAN VENDOR   MODEL        LABEL        FSTYPE SIZE RO MOUNTPOINT
sda  usb  A90-LNX  A90-INTERNAL A90INTERNAL  vfat    8M  1
sdb  usb  A90-LNX  A90-SD       A90SD        vfat    8M  1
```

This confirms both naming layers required by U-B:

- Per-LUN SCSI model: `A90-INTERNAL` and `A90-SD`.
- FAT volume label: `A90INTERNAL` and `A90SD`.

## Remove / Restore Result

Command: `usb mass-storage remove`.

- Remove was scheduled with the watchdog active.
- A transient serial framing loss occurred while the USB gadget re-enumerated; retry after `hide` succeeded.
- `version`: still `0.9.287`.
- `status`: boot OK, serial/NCM/TCP control ready.
- `selftest verbose`: `pass=11 warn=1 fail=0`.
- `usb status`: `control.ok=1`, NCM+ACM linked, `mass_storage.0` unlinked, both LUNs present but backing `file.present=0`.
- Host `lsblk -S`: no A90 USB mass-storage disk remained.

## Decision

`V2323` closes U-B. The host now sees two named read-only file-backed disks under the existing V2321 parent USB identity:

- `A90-INTERNAL` / `A90INTERNAL`.
- `A90-SD` / `A90SD`.

U-C remains explicitly deferred: do not expose real SD/internal storage without a new goal and a mount-conflict gate.
