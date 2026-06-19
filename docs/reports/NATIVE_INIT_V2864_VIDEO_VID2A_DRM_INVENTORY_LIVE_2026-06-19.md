# NATIVE_INIT V2864 — Video VID-2A DRM/display inventory live validation

Date: 2026-06-19
Scope: device live inventory on resident rollback baseline
Device action: serial-bridge commands only; no flash
Decision: `v2864-video-vid2a-drm-inventory-pass`
Private evidence: `workspace/private/runs/video/v2864-video-vid2a-drm-inventory-20260619-183804`

## Summary

VID-2A performs the first device-side Video frontier check after the VID-0/VID-1
host-only reports. It intentionally stays on the resident `v2321` rollback baseline and
runs only bounded native-init inventory commands through the existing ACM serial bridge.
No boot image was built, flashed, or rolled back.

Result: native init sees an operational DRM/KMS display path:

- Resident image: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Health: `selftest fail=0` before and after the inventory.
- Timeline: `display-splash`, `early-nodes`, and `resource-drm` all completed at boot.
- DRM node: `/dev/dri/card0` is present and usable.
- KMS capability: `DRM_CAP_DUMB_BUFFER=1`.
- Connected output: DSI connector `28`, encoder `27`, CRTC `133`.
- Mode: `1080x2400@60`.
- `drminfo`: `card0-DSI-1` is `connected`, `enabled`, and `dpms=On`.
- `fbinfo`: returned `rc=0` with no framebuffer entries printed, so the fbdev path is
  not the useful live surface in this baseline.

This validates the VID-1 decision: proceed with the existing DRM/KMS dumb-buffer display
path for the first video/demo frame work. There is no evidence here requiring raw DSI panel
bring-up, backlight control, PMIC/PWM/regulator/GDSC writes, GPU/KGSL, or Venus.

## Commands executed

Through `workspace/public/src/scripts/revalidation/a90ctl.py` over the serial bridge:

1. `version`
2. `status`
3. `selftest verbose`
4. `timeline`
5. `hide` to clear the active autohud/menu busy guard before display inventory
6. `kmsprobe`
7. `drminfo`
8. `fbinfo`
9. `autohud 2` to restore the prior display HUD state
10. final `status`
11. final `selftest verbose`

A host-side quoting mistake initially sent `selftest verbose` as a single token and failed
inside `a90ctl.py`; this was a host invocation error, not a device failure. The first
`kmsprobe` / `drminfo` / `fbinfo` attempts then returned `status=busy` because autohud
was active. The command output itself instructed to send `hide`; after `hide`, all DRM
inventory commands completed with `status=ok`.

## Evidence excerpts

### Version / display line

`version` reported:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
display: 1080x2400 connector=28 crtc=133 fb=208
```

### KMS probe

`kmsprobe` after `hide` reported:

```text
kmsprobe: node=/dev/dri/card0
kmsprobe: DRM_CAP_DUMB_BUFFER=1
kmsprobe: DRM_CAP_DUMB_PREFERRED_DEPTH=0
kmsprobe: crtcs=3 connectors=3 encoders=3 size=0x0..16384x8640
kmsprobe: connector=28 type=16 status=connected encoders=1 modes=1 current_encoder=27
kmsprobe: selected connector=28 encoder=27 crtc=133 mode=1080x2400x60x184032
kmsprobe: chosen connector=28 encoder=27 crtc=133 mode=1080x2400x60x184032 1080x2400@60
```

### DRM sysfs inventory

`drminfo` after `hide` reported:

```text
renderD128  dev=226:128  node=/dev/dri/renderD128
card0-DSI-1
  status=connected
  enabled=enabled
  dpms=On
  modes=1080x2400x60x184032
card0  dev=226:0  node=/dev/dri/card0
card0-Virtual-1
  status=unknown
  enabled=disabled
  dpms=On
  modes=
card0-DP-1
  status=unknown
  enabled=disabled
  dpms=On
  modes=
```

### Timeline

`timeline` reported the boot display/DRM resources:

```text
02     1562ms display-splash     rc=0 errno=0 boot splash applied
03     1562ms early-nodes        rc=0 errno=0 display/input/graphics nodes prepared
04     1562ms resource-drm       rc=0 errno=0 /sys/class/drm/card0 ready
```

### Health

Final `selftest verbose` reported:

```text
selftest: pass=11 warn=1 fail=0 duration=41ms entries=12
07 PASS      kms      rc=0 errno=0 0ms 1080x2400 fb=207 crtc=133
```

## Safety

- No build.
- No flash.
- No rollback was needed.
- No forbidden partition was touched.
- No Wi-Fi connect/DHCP/ping was run.
- No ADSP, audio, mixer, PCM, speaker, Venus, KGSL, DSI panel init, backlight, PMIC,
  PWM, regulator, GPIO, or GDSC action was run.
- The only runtime state adjustment was `hide` to clear the active menu guard, followed
  by `autohud 2` to restore the display HUD state.

## Decision

Proceed to VID-2B: add a small native Video command surface over existing KMS primitives:

- `video status`: read-only display/KMS state derived from `a90_kms_info()` and/or
  existing DRM inventory helpers.
- `video frame` or `video demo`: one bounded frame or short CPU-rendered animation using
  `a90_kms_begin_frame()`, `a90_kms_framebuffer()`, and `a90_kms_present()`.

Keep the same safety boundary: no Venus, no GPU/KGSL, no raw DSI, no panel/backlight/power
writes. Bad Apple / Nyan Cat / DOOM remain downstream until the single-frame command is
implemented and validated.

## Validation

- Live serial bridge inventory on resident `v2321`.
- Final `status` returned `autohud: running` and `selftest fail=0`.
- Public report contains metadata and redacted excerpts only; full raw command output stays
  under `workspace/private/runs/video/`.
- `git diff --cached --check` passed before commit.
