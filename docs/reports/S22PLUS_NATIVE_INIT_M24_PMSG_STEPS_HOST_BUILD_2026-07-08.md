# S22+ M24 PMSG-Step Native-Init Host Build - 2026-07-08

## Summary

Built the M24 pmsg-step native-init candidate. This is a host-only build and
readiness unit: no M24 flash, reboot, partition write, sysfs write, or live
candidate execution was performed.

M24 keeps the same 43-module DTS-exact QMP/DWC3/HS-PHY/provider closure as M23
and adds retained progress markers to `/dev/pmsg0` before risky phases and
before each module insertion attempt. The intended next live discriminator is:
if the candidate loops again, rollback, then inspect retained pmsg/pstore/reset
surfaces for the last `A90_STEP:M24:` marker.

## Files

- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_inplace_m24_pmsg_steps_park.py`
- Tests:
  `tests/test_s22plus_m24_pmsg_steps_build.py`
- Output directory:
  `workspace/private/outputs/s22plus_native_init/inplace_m24_pmsg_steps_v0_1`

## Pinned Candidate

- AP SHA256:
  `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`
- boot SHA256:
  `0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df`
- `/init` SHA256:
  `4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341`
- generated-source SHA256:
  `f9a060f7804571c036631c954b3e88c064aa33176d7d8ec6abe9da8b8bf84bdd`
- module-list SHA256:
  `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`
- AP tar members:
  `boot.img.lz4` only

## Runtime Delta From M23

- Same module list as M23: 43 DTS-derived QMP/DWC3/HS-PHY/provider modules.
- Same EUD policy: EUD/extcon is excluded because retail TrustZone-gated EUD
  attach is closed.
- Same watchdog/reset blocklist: `gh_virt_wdt.ko`, `qcom_wdt_core.ko`,
  `sec_debug.ko`, `sec_debug_region.ko`, `minidump.ko`, and `abc.ko`.
- New pmsg markers:
  - `A90_STEP:M24:pid1_start`
  - `A90_STEP:M24:mounts_done`
  - `A90_STEP:M24:modules_call`
  - `A90_STEP:M24:modules_start`
  - `A90_STEP:M24:module_prepare index=N name=<module>`
  - `A90_STEP:M24:module_finit index=N name=<module>`
  - `A90_STEP:M24:modules_done`
  - `A90_STEP:M24:usb_role_call`
  - `A90_STEP:M24:acm_gadget_call`
  - `A90_STEP:M24:park_loop`

The builder creates `/dev/pmsg0` as a fallback char node with major 507, minor 0,
mode 0222 before emitting the first pmsg marker. If the kernel already exposes a
valid pmsg device through devtmpfs, the node creation is harmless.

## Safety Properties

- Boot-only AP; exactly one tar member, `boot.img.lz4`.
- Built by `magiskboot unpack/repack` from the known-booting Magisk boot.
- No `mkbootimg` from scratch.
- No boot/vendor_boot/dtbo/vbmeta/recovery/BL/CP/CSC/super/userdata/EFS writes.
- No module binaries are injected into boot ramdisk.
- Exactly one module-list text file is injected into boot ramdisk.
- No Android or Magisk handoff.
- No reboot syscall and no self-download path.
- No persistent partition mount.
- No block-device writes.
- Manifest keeps `live_flash_authorized=false`.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m24_pmsg_steps_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m24_pmsg_steps_build

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m24_pmsg_steps_park.py \
  --force
```

Results:

- `py_compile`: pass
- unit tests: `Ran 2 tests ... OK`
- host build: pass
- generated AP members: `['boot.img.lz4']`
- generated module count: 43
- pmsg markers: present
- manifest live authorization: false

A separate read-only Android/root baseline check after the operator reported a
bootloop/manual entry showed the phone currently back on the clean Magisk
baseline:

- run directory:
  `workspace/private/runs/s22plus_reset_reason_readonly_20260708T110353Z`
- result: pass
- `sys.boot_completed=1`
- verified boot: `orange`
- Magisk root: uid0
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Next Step

M24 is not live-authorized. Any live run needs a fresh SHA-pinned `AGENTS.md`
exception and an attended helper that pins the exact M24 AP and rollback APs.
The helper must preserve the existing manual-download rollback discipline and
capture pstore, pmsg, `/proc/last_kmsg`, and Samsung reset-context surfaces
after rollback.
