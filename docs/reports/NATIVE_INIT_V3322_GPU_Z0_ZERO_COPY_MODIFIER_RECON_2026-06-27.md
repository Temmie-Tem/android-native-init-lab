# Native Init V3322 GPU Z0 Zero-Copy Modifier Recon

- Date: 2026-06-27
- Cycle: `V3322`
- Track: GPU rung ④ zero-copy KMS/dmabuf scanout.
- Decision: `v3322-z0-implicit-linear-scanout-feasible-pending-shared-buffer-proof`

## Scope

This was a no-flash Z0 reconnaissance pass. It built a temporary static
AArch64 helper, installed it under `/cache/bin`, and queried `/dev/dri/card0`
for real plane formats plus atomic `IN_FORMATS` modifier blobs. The helper
does not modeset, page-flip, present, write panel controls, or touch power
domains.

## Safety

- Flash/reboot: `0`
- Partition/firmware writes: `0`
- Display mutation: `0`
- PMIC/GDSC/regulator/GPIO/backlight writes: `0`
- Probe scope: DRM resource/property/blob inventory only.

## Build

- Helper source: `workspace/public/src/native-init/helpers/a90_drm_modifier_probe_z0.c`
- Helper SHA-256: `4e79afa9d7bdb470f8038876e4973dbcf60ae6f47a6f980036709549e6bb937a`
- Helper size: `663456` bytes
- Install path: `bridge-nc`

## Live Result

- Resident version: `version: 0.11.92 build=v3321-gpu-m3-hold-timeout-budget`
- Pre selftest fail=0: `True`
- Post selftest fail=0: `True`
- DRM node: `/dev/dri/card0`
- Universal planes cap rc: `0`
- Atomic client cap rc: `0`
- ADD_FB2 modifiers cap: `1`
- PRIME cap: `0x3 import=1 export=1`
- Resources: `3 connectors=3 encoders=3 min=0x0 max=16384x8640`
- Active path: `current-plane` connector=`0` crtc=`133` current_plane=`60`
- Plane count: `16`
- Compatible active-CRTC planes: `16`
- Planes with src/dst rectangle properties: `16`
- XBGR8888 LINEAR planes: `0`
- XBGR8888 QCOM_TILED3 planes: `0`
- XBGR8888 QCOM_COMPRESSED planes: `0`
- Candidate LINEAR planes: `0`
- Candidate implicit-LINEAR planes: `16`
- Candidate QCOM_TILED3 planes: `0`
- Candidate QCOM_COMPRESSED planes: `0`
- Helper result: `z0-implicit-linear-scanout-feasible`

## Candidate Planes

- plane 0: id=`60` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 1: id=`84` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 2: id=`87` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 3: id=`90` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 4: id=`93` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 5: id=`99` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 6: id=`102` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 7: id=`105` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 8: id=`108` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 9: id=`112` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 10: id=`115` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 11: id=`118` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 12: id=`121` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 13: id=`124` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 14: id=`127` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`
- plane 15: id=`130` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,BG16,AR15,AB15,RA15,...` modifiers=`` implicit_linear=`1` XB24 linear=`0` tiled3=`0` compressed=`0`

## Freedreno / Layout Grounding

- Mesa reference: `/tmp/a90-mesa-gpu-src/src/gallium/drivers/freedreno/a6xx/fd6_resource.cc` maps `DRM_FORMAT_MOD_LINEAR` to `TILE6_LINEAR`,
  `DRM_FORMAT_MOD_QCOM_TILED3` to `TILE6_3`, and `DRM_FORMAT_MOD_QCOM_COMPRESSED` to
  UBWC plus `TILE6_3`.
- DRM UAPI reference: `/tmp/a90-mesa-gpu-src/include/drm-uapi/drm_fourcc.h` defines the Qualcomm compressed, tiled3, and tiled2
  modifiers used by the helper.
- Current A90 GPU present path: `workspace/public/src/native-init/v319/80_shell_dispatch.inc.c` renders into KGSL BO `session->linear`,
  syncs it from GPU, then `memcpy`s each line into the KMS framebuffer. That CPU copy is the
  step Z1/Z2 must remove.

## Feasibility Decision

Zero-copy is feasible enough to investigate, but only through legacy/implicit linear
scanout. The display driver exposes RGB plane formats and `ADDFB2_MODIFIERS`, but no
plane has an `IN_FORMATS` modifier blob, so Z0 cannot use an explicit tiled/UBWC
modifier contract. The already-live KMS path proves implicit linear scanout through
dumb/GEM framebuffers; zero-copy must therefore start from a scanout-shareable linear
buffer, not from a KGSL-only tiled/compressed render target.

Exact Z1 recipe:

- Format: `DRM_FORMAT_XBGR8888` (`XB24`).
- Modifier: implicit/legacy linear, not an explicit `IN_FORMATS` modifier.
- Size/stride: keep the existing 960x720 GPU output, `stride=3840`, `bytes=2764800`.
- First prove a shared linear allocation path. Preferred probe: allocate `msm` DRM GEM
  with `MSM_BO_SCANOUT | MSM_BO_WC`, get `MSM_INFO_GET_IOVA`/mmap metadata, create the
  KMS FB, and verify whether the existing GPU submit path can target the same memory.
- If KGSL cannot import or target that GEM/dma-buf, do not force this through KGSL;
  either pivot the submit path to DRM `msm` for this rung or close zero-copy as not
  feasible on the current KGSL path.
- Keep the existing CPU-copy present path as fallback until the shared-buffer proof passes.

## Remaining Z1 Proof

Z0 proves the display-side modifier choice. It does not yet prove the allocator bridge.
The next source unit must prove one shared allocation path before presenting it: either
`msm` DRM GEM with `MSM_BO_SCANOUT` exported/imported to the GPU path, or KGSL memory
exported/imported to DRM. If the available KGSL UAPI cannot import a dma-buf directly,
pivot to the MSM DRM submit path for the shared scanout BO or stop zero-copy at Z0.

## Validation

- Runner: `workspace/public/src/scripts/revalidation/native_gpu_z0_modifier_recon.py`
- Private summary: `workspace/private/runs/gpu/v3322-gpu-z0-modifier-recon-20260627-160954/summary.json`
- Pass: `True`
