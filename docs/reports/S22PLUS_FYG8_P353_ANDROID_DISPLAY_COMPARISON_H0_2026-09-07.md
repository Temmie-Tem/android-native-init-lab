# P353 versus Android: firmware and source comparison

The shipped FYG8 display stack provides a concrete additional comparison:
Android's noise-configuration path can submit `noise_layer_v1=0` when noise is
disabled. P353 submits no value for this property. The kernel treats omission
and an explicit zero differently. This is a verified software-path difference,
**not proof that hardware noise caused P353's corruption**.

The next proposed experiment is therefore smaller than the earlier magenta
diagnostic: retain the same pattern, buffer, mode and one-commit structure,
and explicitly disable the supported noise property in that atomic request.
If corruption persists, the hardware solid-fill discriminator remains useful.
Neither successor is implemented, prepared, reviewed as a capability or
authorized by this H0 report.

## Scope and evidence

The operator supplied an Android comparison photo and reported that the lower
touch area does not respond, while Android does not show the P353 corruption.
The photo shows the lock-screen image and lower text without the earlier missing
pixel pattern. It is retained privately. This establishes an operator-observed
working display condition; it does not diagnose the touch hardware, exclude a
condition-dependent physical fault, or measure the photo's active display mode.

All work here is host-only: web research, existing firmware-image reads, selected
file extraction, source inspection, disassembly and source-function tests.
No phone was contacted, rebooted, configured or flashed. P353 remains consumed,
CLOSED/19 and rolled back with its existing final health. The original dispatch
receipt, visual witness and corruption qualification remain unchanged.

### Firmware identity and extraction

The retained FYG8 logical `vendor.img` is 2,175,606,784 bytes, SHA-256
`a885cb219d3d21aea87aacb514650857d46f9e2d3b2bfa2fb7a7f1754c5dacf2`.
Its full digest matches the earlier firmware extraction. The shipped properties
identify `S906NKSS7FYG8`, board platform `taro`, and vendor SDK 31 / release 12.
These vendor properties are not a claim that the current Android system is 12.

Thirty-nine selected files were read from the F2FS image without mounting it:
display services, init scripts, properties, configuration and calibration files,
and the relevant libraries. Their total size is 8,086,254 bytes. Large firmware
images and unrelated partitions were not duplicated.

| Exact shipped library | Bytes | SHA-256 |
| --- | --- | --- |
| `libsdmcore.so` | 820624 | `610752c3bb9970dd9ac077ade5bc167e04bbb85dbc50cf9ee02cd83fa06c7125` |
| `libsdedrm.so` | 403968 | `97ac885254a5c34d213ed6363ad8e18e8375d7efa352daf83546e6c810fa85ce` |
| `libsdmextension.so` | 1255640 | `3f5728b81c32cd65b3bcb8bbd0dfa0f8e2b96a2be56b3d46709036663bf6accc` |

All 19 selected ELF headers/section tables and 11 XML files parse. Nine files
match the earlier independent read-only mounted extraction byte for byte. The
panel-specific 2,127,056-byte QDCM JSON parses and identifies
`ss_dsi_panel_S6E3FAC_AMB655AY01_FHD`.

The existing module-oriented F2FS reader did not handle inline file data. The
private adapter uses the kernel's extra-attribute-plus-one-reserved-word offset
(`fs/f2fs/f2fs.h:3484–3489`). Initial unsupported inline outputs were retained
separately and are excluded from the final extraction. Both available direct
`dump.f2fs` inline dumps included 36 extra-attribute bytes before the content;
they were not accepted as an inline oracle. The kernel offset, complete parses
and prior mounted-file matches validate the corrected path. A block-backed
script independently matches `dump.f2fs` output. No shared reader was changed.

## What the web sources establish

AOSP describes HWC as device-specific composition policy and Gralloc as an
allocator whose usage flags can select different layouts. Consequently a normal
Android frame is not an automatic control for P353's CPU-painted linear GEM
buffer. These are architectural references, not evidence of FYG8's active
allocation or register state. [AOSP HWC](https://source.android.com/docs/core/graphics/hwc),
[AOSP BufferQueue and Gralloc](https://source.android.com/docs/core/graphics/arch-bq-gralloc).

AOSP's refresh-rate documentation distinguishes available configurations from
active configuration and transition timing. The older public Qualcomm SDM845
source illustrates atomic setup of planes, performance votes and connector
controls, but is not the shipped FYG8 implementation. Exact conclusions below
come from the FYG8 files and bound kernel sources.
[AOSP multiple refresh rates](https://source.android.com/docs/core/graphics/multiple-refresh-rate),
[public SDM845 HWDeviceDRM source](https://android.googlesource.com/platform/hardware/qcom/sdm845/display/+/refs/heads/android10-dev/sdm/libs/core/drm/hw_device_drm.cpp).

A December 2025 panel-driver submission also reports artifacts and
brightness-change corruption on different Samsung panels in Sony devices, with
command-mode transfer timing and sequencing still under investigation. This is
a primary developer report showing why display corruption need not imply panel
damage. It is not the S6E3FAC/FYG8 driver or evidence that its patches apply here.
[Panel developer's original submission, archived by Patchew](https://patchew.org/linux/20251222-drm-panels-sony-v2-0-82a87465d163%40somainline.org/).

## Exact noise-property chain

Disassembly of the shipped libraries establishes the following chain:

1. `HWDeviceDRM::SetupAtomic` initializes its noise configuration disabled.
   An explicitly supplied noise layer can enable it later. A guarded path
   submits operation 41 with that configuration.
2. The actual `DRMCrtc::Perform` jump-table entry for operation 41 reaches
   the noise configuration branch. When the configuration is disabled, its
   property value becomes zero.
3. `DRMPropertyManager::GetPropertyEnum` maps `noise_layer_v1` to enum 144.
   The property parser stores the discovered ID at `328 + 144 * 4 = 904`,
   the same member consumed by the noise branch.
4. The branch adds that property to the atomic request, except when its cache
   already records the same value. This is explicit disabled-state handling,
   not an assertion that every Android frame writes the register anew.

The source consumer is equally specific. `_sde_crtc_set_noise_layer(NULL)` sets
`noise_layer_en=false` and marks the noise state dirty. The dirty-gated
`sde_cp_crtc_apply_noise` invokes the mixer disable callback.
`sde_hw_clear_noise_layer` clears the noise bits and writes the noise control
register to zero. With no property update and no dirty bit, that application
function returns without programming the noise state.

These functions are present in the exact consumed `msm_drm.ko`; their source
identities and disassembly are retained. All 22 already-qualified merged DT
images contain the noise capability metadata. Runtime exposure, the guarded
Android call site's actual execution, and the noise register's P353 value
remain unmeasured. The word "noise" in a function name is not itself a diagnosis.

Three tests execute the actual source functions using synthetic kernel objects
and register storage: omitted property, explicit zero, and cleared-dirty/null
owner behavior. They verify that zero programs the disable, preserves unrelated
bits, and needs no userspace payload copy. Host compilation/execution, AArch64
object compilation and `file` checks pass. The fixture does not simulate visible
hardware output or prove a previously enabled noise layer.

## Mode, DSC and Android initialization differences

| Area | Verified comparison | Remaining uncertainty |
| --- | --- | --- |
| Refresh mode | P353 selects exact 30HS. Preserved Android-origin log text contains 120HS ↔ 60PHS transitions. | Those historical transitions do not identify the new photo's mode or P353's actual panel state. |
| DSC | All 13 modes across the 22 bound DT combinations declare DSC, 8 bpc / 8 bpp, 540×117 slices and two encoders. | Hardware PPS programming and panel acceptance were not captured by P353. |
| Transfer timing | 30HS declares 9616 µs; 120HS and 60PHS declare 7533 µs. All declare a 1,362,080,000 Hz panel clock. | These DT values are not measured link clocks or transfer durations. |
| Buffer allocation | The Waipio boot-script branch enables DMA-BUF heaps; Gralloc permits UBWC. P353 explicitly uses native linear WC GEM. | Android's actual lock-screen buffer format/modifier is unknown; permitted UBWC is not proven use. |
| Postprocessing | The exact panel calibration has nine named profiles, including Native, sRGB and OEM_VIVID, with gamut/gamma/PCC/dither-related payloads. | File presence does not prove the selected profile or applied hardware coefficients. |
| Initialization | Composer, allocator, color and demura services are declared; Samsung init primarily sets access permissions. | Permissions and service declarations do not prove each feature is active. |

The DSC settings are not missing merely because P353 lacks Android userspace.
The bound `dsi_bridge_mode_fixup` finds the cached panel mode and propagates its
private DSC settings (`dsi_drm.c:480–500`). It also has Samsung-specific VRR and
splash/active-change branches. Correct nominal DRM timing alone does not prove
the panel handoff, but blindly supplying separate PPS bytes is not justified.

The firmware also demonstrates why a single property listing is insufficient:
`build.prop` has `vendor.display.enable_rc_support=0`, while
`init.qti.display_boot.sh` sets it to 1 for the matching `taro` / SoC 457 branch.
Both applicable base DTs identify 457. The branch also enables DMA-BUF heaps,
posted-start and speculative-fence features. This is a configuration-level
override chain, not a fresh runtime property measurement.

Similarly, `vendor.display.disable_dynamic_fps=1` does not justify saying Android
never changes panel refresh mode: the retained Android text demonstrates Samsung
mode switches. The `init.samsung.display.rc` permissions for panel controls are
not writes of their values, so copying those permission changes would not
reproduce Android's display state.

Self-mask, mAFPC, gamma and first-frame display-on work have separate Samsung
driver paths. Their existence deserves preservation in the comparison, but no
specific failure in those paths was proved. The historical Android underrun
line remains noncausal for P353, as explained in the
[earlier corruption analysis](S22PLUS_FYG8_P353_IMAGE_CORRUPTION_H0_2026-09-07.md).

## Next bounded unit

Prefer a fresh same-pattern successor that explicitly submits supported
`noise_layer_v1=0` in the same existing atomic request. Keep the mode, buffer,
pixel data, inherited-plane handling, observation window and exact recovery
unchanged. This tests a specific shipped-software difference without combining
a cache change, a refresh-mode change and a postprocessing change.

If runtime property lookup does not find it, the renderer must stop before
atomic submission and use ordinary rollback; there is no alternate register
interface. If the image becomes clean, that is evidence
supporting the omitted noise-disable path, not a retrospective register read.
If it remains corrupted, retain the result and move to the previously described
magenta solid-fill discriminator. A later 120HS comparison must be a separate
candidate so its meaning is not mixed with noise disable.

No candidate or execution-critical source was changed in this unit. Any
successor still needs its normal scoped review, qualification and fresh
execution binding. This report grants no D0/D1/F1 authority or replay.

## Private evidence

Evidence resides under
`workspace/private/outputs/s22plus_fyg8_p353/android-display-comparison-h0-20260907/`:
`extraction-v2.json`, its two-library supplement, extraction validation,
`noise-binary-chain.json`, `noise-off-h0/`, `dt-display-comparison.json`,
historical mode provenance, web-source references and the operator's Android
comparison photo. Firmware files, photos, raw logs and disassembly remain private.
The final close receipt is SHA-256
`60c87ed569229d5e983968f02abf40d7ee3a9473606d420a82228cbda00cda88`;
the full vendor-image digest was rechecked unchanged at closure.

The prior proposal remains documented as the fallback discriminator. The new
priority follows the newly inspected FYG8 binary path; it is not a promotion of
the consumed P353 feature result or a diagnosis of physical panel damage.
