# S22+ Observable Native-Init M3 v0.2 Download-Reboot Preflight - 2026-07-07

## Scope

Revised the M3 observable direct native-init candidate after the operator noted
that the rooted Android/Magisk baseline can enter download mode in software.

This was a host-side rebuild and no-flash dry-run only. No live Odin transfer,
candidate boot, partition write, recovery action, Android service change,
Magisk module install, or running-device sysfs/configfs write was performed.

## Reason

The operator observation is correct while Android/Magisk is running: before the
M3 candidate flash, the host can use `adb reboot download` and Magisk root is
available for preflight checks.

After M3 boots, however, Android/Magisk/adbd are intentionally gone because M3
is a direct PID1 native `/init`. To reduce physical-button dependency in that
post-M3 phase, v0.2 now attempts a software `download` reboot after the bounded
observation window. If that reboot syscall returns, M3 parks and keeps emitting
failure heartbeats.

## Implementation

Updated:

```text
workspace/public/src/native-init/s22plus_init_observable_m3.c
workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py
workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py
AGENTS.md
GOAL.md
```

M3 v0.2 still:

- emits `S22_NATIVE_INIT_OBSERVABLE_M3` through kmsg/pmsg;
- inserts only the bundled M2 26-module USB-first vendor `.ko` list;
- creates only the runtime configfs `ncm.0` link-only gadget;
- does not assign committed MAC/IP values in public source;
- does not mount persistent partitions, write block devices, start Android, or
  install Magisk modules.

New v0.2 behavior:

- heartbeat observation runs for about 90 seconds;
- then M3 calls `reboot(..., "download")`;
- if the syscall returns, it parks forever with `download_reboot_failed=1`.

The live helper now gates the v0.2 manifest field:

```text
auto_reboot=download-after-observation
```

It also extends the default candidate observation window to 110 seconds so the
software download reboot attempt can be observed before rollback handling.

## Built Candidate

Generated AP package:

```text
workspace/private/outputs/s22plus_native_init/observable_m3_v0_2/odin4/AP.tar.md5
```

Tar member gate:

```text
boot.img.lz4
```

Sizes:

```text
boot_unpadded=48168960
boot_img=100663296
boot_img_lz4=100663699
ap_tar_md5=100669481
ramdisk_cpio=6672384
observable_init=663456
module_bundle_total=2854024
```

Hashes:

```text
source=b615b011941e2f01838caf3453cdda449ad6da8f0342f5ae13380f34f876a1a5
stock_kernel=027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d
module_bundle_manifest=1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05
observable_init=cc55deaa6b69a2abd8ac1a7d68bbfb5a97e961e7407c0359157d7ef48cffec52
ramdisk_cpio=abd134f936af8c18d4f27b3d727bfc5e3a118d03bf1833413a338e291b9b38df
boot_img=aa66602e49045de5666b390ef7b434e07cd234d59a4503f9bac021d11383f6d0
boot_img_lz4=1bd5e9d25e1a4543f0a60f35220e9f0fc66bf752faa683d2b96a58a935f720f8
ap_tar_md5=4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b
```

## Validation

Commands:

```text
git diff --check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py

aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror \
  -o /tmp/s22plus_init_observable_m3_v02_final \
  workspace/public/src/native-init/s22plus_init_observable_m3.c

aarch64-linux-gnu-strip /tmp/s22plus_init_observable_m3_v02_final

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py
```

Results:

```text
git diff --check: pass
py_compile: pass
AArch64 static compile: pass
ELF: 64-bit LSB executable, ARM aarch64, statically linked, stripped
required string gate: S22_NATIVE_INIT_OBSERVABLE_M3, ncm.0, link_only=1,
  download_reboot_after_sec=90, download_reboot_return
live helper dry-run: pass
```

Dry-run summary:

```text
agents_exception_missing=[]
m3_candidate_sha256=4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b
m3_candidate_members=['boot.img.lz4']
m3_manifest_auto_reboot=download-after-observation
magisk_boot_rollback_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock_boot_fallback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
android_preflight=model SM-S906N, device g0q, bootloader S906NKSS7FYG8,
  boot_completed 1, verified boot orange, Magisk root uid 0
```

Private dry-run log:

```text
workspace/private/runs/s22plus_m3_observable_live_gate_20260706T181509Z/
```

## Live Boundary

Live M3 remains gated and was not executed in this unit.

The expected live flow is now:

1. Helper verifies rooted Android preflight and uses `adb reboot download`.
2. Helper flashes the exact boot-only M3 v0.2 AP.
3. M3 boots as direct PID1 and emits observable kmsg/pmsg/USB evidence.
4. M3 attempts its own `download` reboot after about 90 seconds.
5. Helper rolls back with the pinned Magisk boot-only AP when download mode
   appears.
6. If the software `download` reboot is not honored, physical download-mode
   entry is still required for rollback.

Residual risk is unchanged except for the improved rollback path: M3 v0.2 may
still park if Samsung does not honor `reboot(..., "download")` from this direct
PID1 context.
