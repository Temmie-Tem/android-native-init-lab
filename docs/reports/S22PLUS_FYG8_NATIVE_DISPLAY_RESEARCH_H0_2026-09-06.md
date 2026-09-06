# S22+ native PID1 display witness: H0 research

Date: 2026-09-06. Target: SM-S906N / g0q / S906NKSS7FYG8 only.
Scope: host source, retained artifact/configuration and metadata analysis.
No device read, display ioctl, module load, candidate change, preparation or
new device authority occurred. P349 remains paused and untransferred.

## Finding

**A small DRM/KMS renderer is the preferred investigation path for the current
kernel configuration. It is not yet a qualified native display capability.**
The vendor driver contains modesetting, atomic, CPU-buffer allocation and mmap
interfaces. A full Android compositor or GPU renderer is not the proposed
first dependency. Whether the exact native environment can bind the display
and present a CPU-drawn buffer remains unproved.

The current P349 Image has DRM core/helpers enabled, but framebuffer support,
fbdev emulation and VT disabled. Its declared 73-module USB plan includes the
display clock controller but no `msm_drm.ko`. Thus adding a drawing command to
the existing isolated shell is insufficient. That shell has no display device
view or display-ioctl authority, and remains unchanged.

## Evidence and provenance

The actual retained P349 `inputs/fixed-Image` was hash-checked before extracting
IKCONFIG: 41,490,944 bytes, SHA-256
`de36995ad644cde3df79ea18a0ce1b0cc6ffac3aa8d0e6ec6532d5834cfe155d`.
Its relevant configuration is:

```text
CONFIG_DRM=y
CONFIG_DRM_KMS_HELPER=y
# CONFIG_DRM_MSM is not set
# CONFIG_DRM_FBDEV_EMULATION is not set
# CONFIG_FB is not set
# CONFIG_VT is not set
# CONFIG_DEVTMPFS is not set
```

`CONFIG_DRM_MSM` here is the Image's configuration, not evidence that the
separately built vendor display module is unavailable. The retained
[vendor_dlkm inventory](../module-map/s22plus-fyg8-super/inventory.tsv) records
`msm_drm.ko`, 11,733,384 bytes, SHA-256
`7b790074a73cd457d1f483c93e9abec040bca0b0cb07d9c71283b8d6bd396ec9`.
This turn verified that metadata entry, not a newly extracted module binary
or its compatibility with the current native kernel.

The five inspected worktree source files were compared byte-for-byte with
members of the retained Samsung base `Kernel.tar.gz`. All five matched. The
FYG8 delta archive has 52 entries and no `display-drivers` member. This supports
source provenance for these files, not a complete binary-to-source proof of
the shipped `msm_drm.ko`.

Paths below are relative to `vendor/qcom/opensource/display-drivers/msm/` in
the private Samsung source tree:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `msm_drv.c` | 59358 | `848e8731f5c649a77b361acdc1b1a4e85606a4e449e3dcfc338cda50d525344b` |
| `msm_gem.c` | 35165 | `c6b08c30bb8395df31645dfd77fe77cbf2cca7df114980c4ed900b9f60c6d91f` |
| `sde/sde_kms.c` | 135547 | `99c990ebb538a8e6112157633ecb93df266348dfb62faec865abbb9c9a793b6c` |
| `dsi/dsi_display.c` | 248483 | `f63285d79fbee0749c5ab8d83848551df8045ecf7e4db8eebd9fe99f074fdebb` |
| `samsung/S6E3FAC_AMB655AY01/ss_dsi_panel_S6E3FAC_AMB655AY01.c` | 88764 | `1743b7754cb323d1e98ba31c8fb8f863aa06fd7894289ce379f803c3ad75d602` |

Private analysis receipts: `workspace/private/outputs/s22-display-source-provenance.json`
and `s22-display-current-capability.json`; archive member listing is retained
alongside them. No source archive, module binary or raw device data is published.

## Three possible routes

| Route | Current assessment | Reason |
| --- | --- | --- |
| `/dev/fb0` or fbcon | Not available through the current configuration | `CONFIG_FB`, fbdev emulation and VT are disabled. `msm_drv.c:917` conditionally initializes fbdev only under its config. |
| Directly modify a retained splash buffer | Not selected | A surviving logo does not prove a known writable scanout buffer. Pitch, format, ownership, cache coherence and panel refresh are not established. No raw memory/MMIO access is proposed. |
| DRM/KMS, CPU-drawn buffer | Preferred H0 path | `msm_drv.c:1803` declares GEM, render, atomic and modeset features, with dumb allocation/map callbacks; `msm_drv.c:1789` exposes DRM ioctl and GEM mmap. Driver/DT/module qualification remains necessary. |

The vendor driver handles continuous-splash handoff (`msm_drv.c:909` and
`sde_kms.c`), but this is managed driver behavior, not permission to treat a
boot logo's memory as an application framebuffer. Generic KMS object and atomic
validation semantics are documented in the [Linux 5.10 KMS guide](https://docs.kernel.org/5.10/gpu/drm-kms.html).
That guide does not prove the Samsung driver satisfies a proposed mode request.

## Concrete unresolved dependencies

1. **Exact module bytes and provider closure.** Locate/rederive the inventoried
   display module, then check required symbol versions and transitive providers
   against the actual rebuilt kernel and retained vendor modules. Do not reuse
   the USB plan as a display dependency proof. The historical
   [P257 display closure](S22PLUS_FYG8_P257_DISPLAY_CLOSURE_IMPLEMENTATION_H0_2026-07-24.md)
   explicitly added no DRM, panel or framebuffer stack.
2. **Selected panel and mode.** The retained g0q r12 DT representation contains
   multiple panel/display alternatives. Its `S6E3FAC_AMB655AY01_FHD` node has
   command mode, DCS brightness control and 1080x2340 DSC timings, including
   120/96/60-Hz entries. `qcom,dsi-display@1` carries that label. These are
   declared alternatives, not proof of the installed panel, selected board
   overlay or active mode. `dsi_display.c:9533` exposes the `dsi_display0`
   selection parameter. Selection must be traced through the actual boot inputs;
   do not hardcode this panel or a resolution from a marketing specification.
3. **Power, clock, interconnect and IOMMU suppliers.** Trace the selected
   display component graph and deferred-probe requirements, including panel
   supplies, DSI PHY/controller, display clocks and memory mapping. Existing
   display-clock bind evidence does not prove the panel can display a frame.
4. **CPU-write visibility.** `msm_gem.c:700` allocates dumb buffers with
   `MSM_BO_SCANOUT | MSM_BO_CACHED`. The CPU prepare/fini paths around lines
   921/928 contain cache-maintenance TODOs. This is a concrete question for
   mapping/export/synchronization review; it is not proof that all CPU rendering
   fails. A successful mmap or ioctl alone must not count as visible output.
5. **Device-node and owner setup.** Devtmpfs is disabled in the retained Image;
   identify the existing native device-node mechanism and actual DRM sysfs
   identity. Do not assume `/dev/dri/card0` exists or is the intended device.
   Resolve DRM ownership before commit; keep display handles out of the
   caller-selected P349 shell.

## Proposed first visible witness

The intended screen is deliberately different from the boot logo:

```text
NATIVE PID1
RUN <fresh public test identifier>
FRAME 0001 -> 0002 -> 0003
```

Use a dark background, a modest-brightness contrasting rectangle and a changing
counter. A later separately designed experiment should pair at least two
visible updates with the same boot's authenticated host witness, actual process
identity and completed display commits. A static label or successful commit
receipt alone is not sufficient evidence of visible changing output.

Distinguish two implementations before making a PID1 claim:

- PID1 itself performs display ioctls: direct ownership, but an ioctl stall can
  also stall the existing PID1/USB path.
- PID1 launches a fixed supervised display helper: isolates ordinary userspace
  work from the USB owner, but proves **PID1-managed output**, not that the
  renderer process has PID 1. A kernel stall is not solved merely by forking.

The user's objective is a visible witness that the native PID1 environment is
running. The supervised-helper design is worth evaluating first; its process
relationship must be explicit in both the screen label and retained evidence.
This is a proposal, not a change to the active runtime or safety contract.

## Next bounded H0 unit

Produce a display-module/provider/selected-DT dependency map and settle the
CPU-buffer cache path before implementing a renderer. The completion criterion
is a source-backed minimum configuration, named unresolved bindings and a
small userspace ioctl sequence with explicit ownership and failure behavior.
Only then design a separate reviewed attended display experiment. No display
work is inserted into the paused, already-qualified P349 candidate.
