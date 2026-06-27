# Native Init V3323 GPU Z1 Shared Linear Preflight

- Date: 2026-06-27
- Cycle: `V3323`
- Track: GPU rung ④ zero-copy KMS/dmabuf scanout.
- Decision: `v3323-z1-drm-msm-shared-linear-preflight-pass-no-iova`

## Scope

This was a no-flash Z1 allocator-bridge preflight. It built a temporary
static AArch64 helper, installed it under `/cache/bin`, then checked whether
`/dev/dri/card0` can allocate one msm DRM GEM buffer with
`MSM_BO_SCANOUT | MSM_BO_WC`, mmap it, PRIME export/import it, and create
an `XBGR8888` KMS framebuffer object from it. The helper creates no CRTC
state, performs no pageflip, and does not present the framebuffer.

## Safety

- Flash/reboot: `0`
- Partition/firmware writes: `0`
- Display mutation: `0` (FB object creation/removal only; no present/modeset/pageflip)
- PMIC/GDSC/regulator/GPIO/backlight writes: `0`
- Probe scope: DRM allocation/import/export metadata only.

## Build

- Helper source: `workspace/public/src/native-init/helpers/a90_drm_msm_shared_linear_probe_z1.c`
- Helper SHA-256: `d5e86d6b2ab180374977c14817867894d42538bf26ffe8817f41ba422950a4d2`
- Helper size: `663456` bytes
- Install path: `bridge-nc`

## Live Result

- Resident version: `A90 Linux init 0.11.92 (v3321-gpu-m3-hold-timeout-budget)`
- Pre selftest fail=0: `True`
- Post selftest fail=0: `True`
- DRM node: `/dev/dri/card0`
- Target: `960`x`720` stride=`3840` bytes=`2764800` format=`XB24` flags=`MSM_BO_SCANOUT|MSM_BO_WC`
- Dumb-buffer cap: `1`
- ADD_FB2 modifiers cap: `1`
- PRIME cap: `0x3` import=`1` export=`1`
- MSM GEM new: rc=`0` handle=`1` flags=`0x20001`
- GEM offset: rc=`0` value=`0x1013ec000`
- GEM IOVA: rc=`-22` value=`0x0`
- GEM flags: rc=`-22` value=`0x0`
- mmap: rc=`0` sample=`first=0xff112233 middle=0xff445566 last=0xff778899 words=691200`
- PRIME export: rc=`0` fd_valid=`1`
- PRIME import: rc=`0` handle=`1` same_handle=`1`
- ADDFB2: rc=`0` fb_id=`30`
- Cleanup: rmfb=`0` close_import=`0` close_handle=`0`
- Helper result: `z1-drm-msm-shared-linear-preflight-pass`

## Interpretation

The display-side shared-linear allocation path is proven: msm GEM allocation,
mmap, PRIME export/import, and KMS FB creation all passed. The helper did
not get an IOVA, so this does not yet prove that the current KGSL command
submit path can directly target the same memory. The next step should first
find a KGSL import/target route for this dma-buf/GEM, or pivot the rendering
submit path to DRM msm for this rung.

## Current Source Grounding

- Z1 helper: `workspace/public/src/native-init/helpers/a90_drm_msm_shared_linear_probe_z1.c`
- Existing KMS path: `workspace/public/src/native-init/a90_kms.c` already proves implicit linear scanout through
  KMS framebuffer objects.
- Existing GPU present path: `workspace/public/src/native-init/v319/80_shell_dispatch.inc.c` renders into a KGSL linear BO, syncs it,
  then line-copies into the KMS framebuffer. Z2 must replace only that final copy after
  a shared-buffer path is proven.

## Validation

- Runner: `workspace/public/src/scripts/revalidation/native_gpu_z1_shared_linear_preflight.py`
- Private summary: `workspace/private/runs/gpu/v3323-gpu-z1-shared-linear-preflight-20260627-162019/summary.json`
- Pass: `True`
