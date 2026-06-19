# NATIVE_INIT V2863 — Video VID-1 display path analysis

Date: 2026-06-19
Scope: host-only source / docs / prior live-evidence analysis
Device action: none
Decision: `v2863-video-vid1-kms-path-ready`

## Summary

VID-1 re-checks the display side of the new Video frontier after VID-0. The original
host-only question was whether native init can inherit a writable continuous-splash
surface through `/dev/dri/card0` or `/dev/fb0` before teardown, and then region-blit
without re-initializing the panel.

The practical answer is stronger and slightly reframes the next step:

- The legacy fbdev path is not the primary route. The project evidence says the stock
  config enables Qualcomm DRM/MSM/SDE and disables the MSM/simple fbdev routes; VID-0
  also found no pinned public `cont_splash` property in the indexed source.
- Native init already contains a driver-mediated KMS dumb-buffer path over
  `/sys/class/drm/card0/dev` -> `/dev/dri/card0` and has repeatedly validated display-only
  `screenapp` routes on hardware.
- Therefore the first display/video demo path should use the existing native KMS API,
  not chase a speculative raw `/dev/fb0` or low-level DSI/panel bring-up path.
- This path does **not** directly write backlight, PMIC, PWM, regulator, GPIO, or GDSC
  state. It uses the kernel DRM driver through standard KMS ioctls.

This does not prove the bootloader continuous-splash handoff details. It means the
make-or-break drawable surface for Bad Apple / Nyan Cat / DOOM-style demos is already
represented by a proven DRM/KMS abstraction in native init, so VID-2 should verify the
current device-visible DRM state first and then add a minimal KMS-frame demo on top of
that API.

## Evidence

### Active charter

`GOAL.md` now marks Video as the active frontier and explicitly prioritizes a drawable
display framebuffer over Venus hardware decode. It also keeps the hard display safety
boundary: use an inherited/display-driver surface only, and do not run from-scratch DSI
panel init or write backlight, PMIC, PWM, regulator, or GDSC state.

### VID-0 inventory baseline

`docs/reports/NATIVE_INIT_V2862_VIDEO_VID0_HOST_INVENTORY_2026-06-19.md` established:

- `CONFIG_DRM_MSM=y`
- `CONFIG_DRM_MSM_DSI_STAGING=y`
- `CONFIG_DRM_SDE_WB=y`
- `CONFIG_DRM_SDE_RSC=y`
- `CONFIG_FB_MSM is not set`
- `CONFIG_FB_SIMPLE is not set`
- The exact Samsung panel and `cont_splash` / `qcom,cont-splash` strings were not found
  in the currently indexed source tree.

Implication: `/dev/dri/card0` / `/sys/class/drm` is the primary native path. `/dev/fb0`
remains a secondary live check, not the design center.

### Existing native KMS path

`workspace/public/src/native-init/a90_kms.c` already does the work needed for a bounded
CPU-rendered framebuffer demo:

- Creates `/dev/dri/card0` from `/sys/class/drm/card0/dev` when needed.
- Opens the DRM node `O_RDWR` and attempts `DRM_IOCTL_SET_MASTER` best-effort.
- Enumerates resources with `DRM_IOCTL_MODE_GETRESOURCES`.
- Reads connectors and modes with `DRM_IOCTL_MODE_GETCONNECTOR`.
- Selects a connected connector, encoder, CRTC, and preferred mode.
- Requires `DRM_CAP_DUMB_BUFFER`.
- Allocates two dumb buffers with `DRM_IOCTL_MODE_CREATE_DUMB`.
- Publishes them with `DRM_IOCTL_MODE_ADDFB2` using `DRM_FORMAT_XBGR8888`.
- Maps them with `DRM_IOCTL_MODE_MAP_DUMB` + `mmap(PROT_READ|PROT_WRITE, MAP_SHARED)`.
- Presents through `DRM_IOCTL_MODE_SETCRTC`.
- Exposes the active mapped buffer through `a90_kms_framebuffer()`.

This is a kernel-driver-mediated KMS path. It is not a raw DSI sequence and not a
userspace power-domain/backlight path.

### Existing command surface

The current native shell already exposes display/KMS commands:

- `kmsprobe`
- `kmssolid`
- `kmsframe`
- `displaytest`
- `screenapp ...`

Multiple screen applications use `a90_kms_begin_frame()` and `a90_kms_present()`:
`a90_hud.c`, `a90_app_displaytest.c`, `a90_app_wifi.c`, `a90_app_network.c`,
`a90_app_audio.c`, `a90_app_about.c`, and related app surfaces.

### Prior live display evidence

The historical runbook records a live display surface:

```text
display: 1080x2400 connector=28 crtc=133 fb=207
```

`docs/overview/PROGRESS_LOG.md` also records repeated display regressions passing,
including `displaytest`, `displaytest colors/font/safe/layout`, `kmsprobe`, `kmsframe`,
`statushud`, `cutoutcal`, and `autohud 2`.

The latest audio productization validations also exercise the same display-only KMS
surface:

- V2860 validated `screenapp about-changelog` and `screenapp audio-status` on hardware.
- V2861 validated `screenapp about-version`, `about-changelog`, `audio-status`,
  `audio-profile`, `audio-stages`, `audio-map`, and `audio-chime` on hardware.
- These V2860/V2861 screen validations intentionally avoided ADSP boot, `/dev/snd`, mixer
  writes, speaker writes, playback, and stop-execute actions. Their relevance here is only
  that the display/KMS route worked on the latest `0.10.19` candidate.

## Interpretation

### What VID-1 answers

The low-risk display route for the first video demos should be the existing KMS dumb-buffer
path. It is already integrated, command-exposed, and hardware-validated through display-only
screen routes. It gives native init a mapped CPU-writeable frame buffer and a present call,
which is exactly what the demo ladder needs for pre-decoded frames.

### What VID-1 does not claim

VID-1 does **not** prove:

- the exact Samsung panel node in public source;
- the exact continuous-splash property;
- that `/dev/fb0` exists;
- that the current KMS path preserves the bootloader scanout object rather than replacing it
  with a driver-managed dumb buffer;
- that Venus/VIDC is ready or needed.

Those are no longer blocking for a first framebuffer demo, because native init already has
a working driver-mediated DRM surface. If a future operator specifically wants the original
bootloader scanout preserved, that needs a separate live read-only inventory and probably
DTBO/vendor extraction. It should not block the practical display demo path.

## VID-2 reviewable device plan

VID-2 should stay display-first and read-only before any new render command.

### VID-2A: DRM/display inventory

Run on a rollbackable test image only if needed, otherwise on the current validated image:

1. `a90ctl version`
2. `a90ctl status`
3. `a90ctl 'selftest verbose'`
4. `a90ctl kmsprobe`
5. `a90ctl fbinfo` or equivalent `/proc/fb` / `/dev/fb0` check if available
6. Record whether `/sys/class/drm/card0/dev` exists and whether KMS reports a connected
   connector and mode.

Expected pass condition: `kmsprobe` finds the same class of connected display path already
used by `screenapp` validations.

Abort conditions:

- no `/sys/class/drm/card0/dev`;
- no connected connector/mode;
- DRM open/ioctl errors that indicate the display driver path is unavailable;
- any need to write backlight, PMIC, PWM, regulator, GPIO, or GDSC state.

### VID-2B: minimal frame/demo scaffold

Only after VID-2A passes, add a small native display demo surface that reuses
`a90_kms_begin_frame()`, `a90_kms_framebuffer()`, and `a90_kms_present()`:

- `video status`: read-only state using existing KMS info.
- `video frame` or `video demo`: one bounded frame/short animation into the mapped KMS dumb
  buffer.
- No Venus, no GPU/KGSL, no raw DSI, no power-domain/backlight writes.

The first useful demo can be CPU-rendered test bars or a tiny pre-decoded monochrome frame.
Bad Apple / Nyan Cat / DOOM should remain downstream until this single-frame path is
validated.

## Decision

Proceed to a KMS-based VID-2 plan. Do not spend the next unit on Venus or on fbdev-only
cont-splash archaeology unless the KMS inventory unexpectedly fails.

Recommended next unit: implement a tiny host-side `video status` / `video frame` design over
the existing `a90_kms` primitives, or run the minimal `kmsprobe`/screenapp display inventory
if a device checkpoint is required before adding the command surface.

## Validation

- Host-only source and public report review.
- No build.
- No flash.
- No device access.
- No private/raw payload committed.
- `git diff --cached --check` passed before commit.
