# NATIVE_INIT V2862 — Video VID-0 host inventory and decision

Date: 2026-06-19
Scope: host-only source / DTS / stock-firmware-file inventory
Device action: none
Decision: `v2862-video-vid0-display-first`

## Summary

Audio is now a closed core feature and `GOAL.md` marks Video as the active frontier. VID-0
re-checked the starting assumptions before any device work:

- Display support is present through Qualcomm DRM/SDE with DSI staging; legacy `FB_MSM`
  is not enabled.
- The kernel source exposes SDE KMS, DSI controller/PHY nodes, and broad DSI display
  definitions.
- The exact Samsung panel name and `cont_splash` / `qcom,cont-splash` property were **not**
  found in the currently indexed kernel/Platform source tree.
- VIDC/Venus support is also present and registers V4L2 M2M `/dev/video*` nodes, but its
  boot path is firmware/PIL plus clocks/regulators/GDSC inside the kernel driver.

The lower-risk next sub-target is still the display path, specifically an inherited
bootloader/cont-splash framebuffer probe, because the demo ladder needs a drawable surface
and does not require hardware video decode. VID-1 should analyze the display handoff path and
prepare a read-only-first device plan for `/dev/dri/card0` / `/sys/class/drm` / possible
`/dev/fb0` presence. It must not re-initialize the panel or write backlight, PMIC, PWM,
regulator, or GDSC state.

## Inputs inspected

- `GOAL.md` active Video charter.
- `CLAUDE.md` current project state and safety context.
- `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel`.
- `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Platform`.
- Stock firmware container listing under `workspace/private/inputs/firmware/SAMFW.COM_SM-A908N_KTC_A908NKSU5EWA3_fac`.

No proprietary image was extracted into a public path. No raw firmware, boot image, or device log is committed.

## Display inventory

### Kernel config

`arch/arm64/configs/r3q_kor_single_defconfig` confirms:

- `CONFIG_DRM_MSM=y`
- `CONFIG_DRM_MSM_DSI_STAGING=y`
- `CONFIG_DRM_SDE_WB=y`
- `CONFIG_DRM_SDE_RSC=y`
- `CONFIG_DRM_PANEL=y`
- `CONFIG_FB=y`
- `CONFIG_FB_MSM is not set`
- `CONFIG_FB_SIMPLE is not set`

Implication: the safe first display probe should expect the DRM/SDE path, not a legacy
MSM framebuffer. `/dev/dri/card0` and `/sys/class/drm` are the primary live inventory
targets; `/dev/fb0` is only a secondary check.

### SDE / DSI DTS

`arch/arm64/boot/dts/qcom/sm8150-sde.dtsi` defines:

- `mdss_mdp: qcom,mdss_mdp@ae00000`, compatible `qcom,sde-kms`.
- `qcom,sde-intf-type = "dp", "dsi", "dsi", "dp"`.
- DSI controllers:
  - `mdss_dsi0: qcom,mdss_dsi_ctrl0@ae94000`, compatible `qcom,dsi-ctrl-hw-v2.3`.
  - `mdss_dsi1: qcom,mdss_dsi_ctrl1@ae96000`, compatible `qcom,dsi-ctrl-hw-v2.3`.
- DSI PHYs:
  - `mdss_dsi_phy0: qcom,mdss_dsi_phy0@ae94400`.
  - `mdss_dsi_phy1: qcom,mdss_dsi_phy0@ae96400`.

`arch/arm64/boot/dts/qcom/sm8150-sde-display.dtsi` includes the Qualcomm panel set and
defines `qcom,dsi-display-primary` with DSI controllers/PHYs, display lists, and `sde_wb`.
The Samsung r3q overlays contain simulator DSI panel fragments but the current source search
did not expose the expected `ss_dsi_panel_S6E3FC2_AMS670TA01_FHD` label.

### Unverified display assumptions

The GOAL starting facts mention a Samsung panel node and continuous splash. Host-only
searches over both `Kernel/arch/arm64/boot/dts` and `Platform` found no direct match for:

- `cont_splash`
- `cont-splash`
- `qcom,cont-splash`
- `S6E3FC2`
- `AMS670`
- `ss_dsi`
- `ss_panel`

This does **not** disprove the live device handoff; it means the exact panel and continuous
splash property are not pinned by the currently indexed source. VID-1 must either locate the
property from DTBO/vendor extraction or treat it as a live read-only inventory question.

## Venus / VIDC inventory

### Kernel config and build path

`arch/arm64/configs/r3q_kor_single_defconfig` confirms:

- `CONFIG_VIDEO_V4L2=y`
- `CONFIG_MSM_VIDC_V4L2=y`
- `CONFIG_MSM_VIDC_GOVERNORS=y`
- `CONFIG_MSM_VIDC_3X_V4L2 is not set`

`drivers/media/platform/msm/vidc/Kconfig` defines `MSM_VIDC_V4L2` as the Qualcomm MSM
V4L2 video driver. `drivers/media/platform/msm/vidc/Makefile` builds `msm-vidc.o` from
the V4L2 core, decoder/encoder, Venus HFI, `venus_boot.o`, and related resources.

### Expected device nodes

`drivers/media/platform/msm/vidc/msm_v4l2_vidc.c` registers V4L2 M2M devices:

- `msm_v4l2_vidc_fops` uses `.unlocked_ioctl = video_ioctl2`.
- `msm_vidc_register_video_device()` calls `video_register_device(..., VFL_TYPE_GRABBER, nr)`.
- Probe registers decoder at base number, encoder at base number + 1, and CVP if present.

Expected live inventory target: `/dev/video*` plus `/sys/class/video4linux/*/name` and the
driver link under sysfs. A future device step should be open/query-only before any stream setup.

### Venus boot caution

`drivers/media/platform/msm/vidc/venus_boot.c` shows a subsystem-style Venus boot path with:

- `subsys_notif_register_notifier("venus", ...)`.
- `pil_venus_mem_setup()`.
- `pil_venus_auth_and_reset()`.
- Kernel-managed clocks, regulators, and GDSC through `venus_clock_prepare_enable()` and
  `regulator_enable(venus_data->gdsc)`.

This is a driver-mediated path. Native init must not directly write GDSC, regulators,
PMIC, GPIO, or similar power controls. If Venus is revisited, the first live unit must be
passive `/dev/video*` inventory/open/query only.

### Firmware state

The stock AP tar lists `vendor.img.ext4.lz4`, but no extracted public vendor tree was created
for this unit. A repository-wide filename search did not find a plain `venus*.mbn`,
`venus*.mdt`, or similar firmware file in the currently indexed inputs. That makes Venus a
secondary VID-1 item: useful to inventory, but not the low-risk demo-enabling path.

## Decision

Proceed to VID-1 with display-first path analysis:

1. Locate the actual display handoff source of truth:
   - DTBO/vendor extraction if needed, or
   - live read-only sysfs inventory in the later VID-2 plan.
2. Determine whether native init can observe an inherited scanout object before teardown:
   - `/dev/dri/card0`
   - `/sys/class/drm`
   - `/proc/fb` and `/dev/fb0` only as fallback
3. Draft a region-blit plan that writes only to an already-inherited framebuffer/surface.
4. Stop if the panel is blanked or the surface has been torn down; do not re-light the panel.

Venus remains secondary:

- The V4L2 driver exists and should register `/dev/video*`.
- It is not necessary for Bad Apple / Nyan Cat / DOOM-style framebuffer demos.
- It introduces firmware/PIL/power-domain complexity that should not be touched before the
  display inheritance question is answered.

## Validation

- Host-only source/DTS/firmware-container inventory.
- No build, no flash, no device access.
- `git diff --check` passed before commit.
