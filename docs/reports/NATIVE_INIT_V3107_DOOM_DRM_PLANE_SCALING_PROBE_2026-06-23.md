# Native Init V3107 DOOM DRM Plane Scaling Probe

- Date: 2026-06-23
- Cycle: `V3107`
- Track: DOOM large-frame scale-path optimization.
- Decision: `v3107-drm-plane-scaling-candidate-live-pass`

## Scope

This was a no-flash live probe on the installed V3104 resident. It
built and installed a temporary read-only helper under `/cache/bin`, then
queried DRM plane resources and plane properties through ioctls. No boot
image was built, flashed, or rebooted.

## Safety

- Flash/reboot: `0`
- Partition/firmware writes: `0`
- Display mutation: `0`
- Probe scope: DRM resource/property inventory only.

## Build

- Helper source: `workspace/public/src/native-init/helpers/a90_drm_plane_probe_v3107.c`
- Helper SHA-256: `10530af8289b27ee8caab95dd4c6819f150e521a4c3671ab1518685cd25bf6a7`
- Helper size: `663456` bytes
- Install path: `serial-base64`

## Live Result

- Resident version check: `True`
- Pre selftest fail=0: `True`
- Post selftest fail=0: `True`
- DRM node: `/dev/dri/card0`
- Universal planes cap rc: `0`
- Atomic client cap rc: `0`
- Resources: `crtcs=3 connectors=3 encoders=3 min=0x0 max=16384x8640`
- Active source: `current-plane`
- Active connector scan rc: `-19`
- Active fallback current-plane rc: `0`
- Active path: connector=`0` encoder=`0` crtc=`133` crtc_index=`0` current_plane=`60`
- Plane count: `16`
- Compatible active-CRTC planes: `16`
- Planes with src/dst rectangle properties: `16`
- Hardware scale candidate count: `16`
- Hardware scale exposed: `1`

## Plane Summary

- plane 0: id=`60` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,...`
- plane 1: id=`84` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,...`
- plane 2: id=`87` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,...`
- plane 3: id=`90` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,BX24,AB24,BA24,XR24,XB24,RX24,XB24,RG24,BG24,...`
- plane 4: id=`93` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 5: id=`99` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 6: id=`102` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 7: id=`105` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 8: id=`108` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 9: id=`112` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 10: id=`115` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 11: id=`118` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 12: id=`121` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 13: id=`124` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 14: id=`127` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`
- plane 15: id=`130` compatible=`1` rect_props=`1` XBGR=`1` XRGB=`1` candidate=`1` formats=`AR24,AB24,RA24,AB24,BA24,XR24,RX24,BX24,XB24,RG24,BG24,RG16,...`

## Interpretation

The device exposes at least one active-CRTC-compatible plane with
source/destination rectangle properties and an RGB8888 format compatible
with the current DOOM frame path. This is enough to proceed to a bounded
visual `drmModeSetPlane`/pageflip experiment for large DOOM scaling, still
without GPU/GL, panel re-init, or power writes.

## Next Step

If `Hardware scale exposed` is `1`, implement a bounded V3108 plane-scaling
visual candidate: allocate the DOOM-sized dumb buffer, attach it to the
compatible plane with source 640x400 and destination demo rectangle, then
restore the existing full-screen path on exit. If it is `0`, skip directly
to the pre-scaled-producer fallback.
