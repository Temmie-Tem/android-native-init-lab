# P353 image corruption: H0 analysis

The consumed AArch64 renderer produces the exact intended buffer, including every
row and padding pixel. The inspected linear-format and WC-mapping paths agree
with its allocation. This substantially reduces the case for a paint-loop,
uninitialized-padding or simple pitch-calculation defect. It does **not** prove
the live mapped bytes reached the display intact. The cause of the observed
corruption remains **UNPROVED**.

The smallest useful next discriminator is the selected plane's existing hardware
`color_fill` path, with the same mode, geometry and recovery arrangement. It can
separate normal framebuffer-fetch behavior from a hardware-generated color's
output. This is a diagnostic proposal, not a fix, qualified successor, prepared
candidate or device authorization. No device command occurred in this analysis.

The later [exact Android firmware comparison](S22PLUS_FYG8_P353_ANDROID_DISPLAY_COMPARISON_H0_2026-09-07.md)
identifies explicit noise disable as a smaller first comparison with the same
pattern and mode. It prioritizes that newly supported difference; the magenta
diagnostic below remains the fallback.

## Bound evidence and observation

P353 remains consumed and CLOSED/19, with its original dispatch-only machine
verdict and verified exact rollback/final rooted FYG8 health. The operator saw
the identifiable red/blue/green and black-cross pattern, supplied a photograph
showing substantial horizontal speckles and lower-area corruption, and later
confirmed the same corruption was visible to the naked eye. A camera-only
explanation is therefore not supported by the operator evidence.

The original photograph and statements remain private and separate from the
unchanged machine result. The later naked-eye statement was appended as a new
record, not substituted into the original witness.

The host attachment timestamp is 17:55:07.464797 UTC, about 45.077 seconds after
the 17:54:22.387534 candidate-ready event. No EXIF capture timestamp is available.
This is host receipt timing, not a measured exposure time or child-exit record;
it nevertheless does not support the existing 60-second deadline as the cause
of the already-received photograph's initial corruption. Resource retention
after that deadline is not claimed.

Related closed run:
[P353 static image and rollback](S22PLUS_FYG8_P353_STATIC_FIRST_FRAME_PREPARATION_2026-09-07.md).

## Exact paint output

The renderer in the consumed A/B build is `710032B`, SHA-256
`32fe3bffddef7260671cc51ac8e3bebad2f6c7f9fac1d67f65ec112c6b5d207d`.
Both copies match the build receipt, and all 63 construction source inputs were
reverified unchanged. A byte-identical private executable copy ran its existing
`--h0-paint` entry under AArch64 user-mode QEMU. This uses ordinary allocated
host memory, not DRM, WC mappings, SMMU or display hardware.

An independent rectangle-based oracle matches **all 10,183,680 output bytes**.
It does not merely sample the four representative points used by the earlier
renderer fixture. There are exactly five intended pixel values; all eight
padding pixels on every row are white.

| Property | Verified value |
| --- | --- |
| Visible dimensions | 1080 × 2340 |
| Pitch | 4352 bytes, 1088 pixels |
| Paint allocation | 10,183,680 bytes |
| Exclusive end of last visible pixel | 10,183,648 bytes |
| Kernel page-aligned object size for this request | 10,186,752 bytes |
| White pixels, including padding | 1,416,720 |
| Red / blue pixels | 291,600 each |
| Green pixels | 366,000 |
| Black pixels | 180,000 |

The paint output SHA-256 is
`0d622524c00cfdbc72dd5996300c155a596a5e3a3533de6c6ee9d8e952f016b7`.
The actual compiled paint routine ends with `dmb ish`. This verifies emitted
ordering code, not the sufficiency of live CPU-to-display visibility.

## Buffer, format and mapping path

The renderer requests `MSM_BO_SCANOUT | MSM_BO_WC`, maps the GEM object shared,
and registers one XRGB8888 framebuffer with zero offset and modifier flags,
pitch 4352 and full-frame rectangles. There is no requested tiling or UBWC.

The source chain is consistent with that request:

- `msm_fb.c:300–317` checks `(height - 1) * pitch + width * cpp + offset`;
  the requested object covers that span.
- `sde_formats.c:237–241` declares XRGB8888 as four-byte interleaved linear
  data. Its linear layout helper at `847–918` accepts an oversized user pitch;
  the address helper at `1067–1097` checks the corresponding framebuffer pitch.
- `sde_hw_sspp.c:791–864` programs the layout's pitch. Its format setter at
  `347–456` clears old BWC enable and constructs the new linear source format.
  The visible pattern is not grounds to claim that the actual registers latched.
- `msm_gem.c:218–244` selects `pgprot_writecombine` for WC. The bound arm64
  headers identify this as `MT_NORMAL_NC`, index 2. The consumed module's
  `msm_gem_mmap_obj` disassembly corroborates the WC-bit branch and attribute
  index; it is not a readback of the live VMA or MAIR register.
- `msm_gem.c:82–136` allocates pages and attempts initial DMA mapping/cache
  preparation for noncached buffers. The IOVA path at `427–529` and
  `msm_smmu.c:235–294` remain dependent on actual address-space and mapping
  results. Their live state was not captured by P353's dispatch-only observer.

Adding GEM CPU_PREP/CPU_FINI alone is not a demonstrated repair: the inspected
implementation at `msm_gem.c:921–929` leaves cache maintenance as TODO.
Changing a CPU fence alone would likewise be a hypothesis, not a finding that
the current corruption was caused by that fence. No cache or mapping change was
made to a consumed source or candidate.

The exact consumed `msm_drm.ko` is `10534768B/f4e5e9f5`; its hash matches the
construction receipt. Retained disassembly covers the mapping, source-format,
stride and solid-fill functions. Fifteen previously inspected core/vendor
source receipts also match their earlier static-first-frame audit.

## Other plausible explanations and their limits

| Question | Finding and limit |
| --- | --- |
| Missing userspace bandwidth/clock votes? | `sde_core_perf.c:146–153` uses maximum catalog bandwidth and core clock when `bw_control` is false. The CRTC resets that flag until explicit bandwidth properties are set. Omission does not simply imply zero votes; actual hardware performance still was not measured. |
| Retained log says underrun? | One `mdp underrun: 23` line exists in the rollback observation. Its context contains Android services and a panel-off sequence. It is not bound to the P353 display child and is not candidate causal evidence. |
| Intentional hardware noise? | All 22 previously qualified merged DT identities contain the noise feature metadata. The source has a separate `noise_layer_v1` control, but P353 did not request noise. Feature presence is not evidence that hardware noise was enabled. |
| Old composition or postprocessing? | Replacing CTL plane stages does not by itself certify every mixer, postprocessing or panel state. Noise application is dirty-gated (`sde_crtc.c:7702–7744`); panel self-mask and mAFPC have separate Samsung paths. Their active state and contribution to this photo are unknown. |
| Clean host buffer means clean live framebuffer? | No. QEMU checks the actual instruction path's bytes in ordinary memory. WC visibility, page mappings, fetch, compression/transport, panel state and hardware latch remain outside that test. |

The preserved raw observation still has the original ambiguous supplemental
Carrier classification. Neither its surrounding Android text nor its Carrier
record is promoted into post-dispatch renderer diagnostics. P353 deliberately
did not capture the display child's subsequent local output.

## Proposed next diagnostic

Use a fresh candidate with the same selected primary plane, exact 30HS mode,
full-frame geometry, inherited-plane handling, one blocking atomic submission,
attended observation and exact rollback. Change the pixel source through the
existing `color_fill` property to an opaque saturated magenta fill. The selected
plane must actually expose the property; there is no fallback register access.

The source installs this property when solid fill is supported
(`sde_plane.c:3908–3910`). Bit 31 enables it. At flush, the error path takes
precedence and forces white; otherwise the requested fill goes through
`_sde_plane_color_fill` (`1484–1557`, `2771–2802`). The helper supplies a constant
color and `SDE_SSPP_SOLID_FILL` to the hardware. Magenta distinguishes the intended
diagnostic from the white-on-error path and avoids red/blue packing ambiguity.

Keep ordinary framebuffer allocation and validation in place. Solid fill does
not bypass every GEM/SMMU preparation call. It replaces the displayed pixel
source and also forces ABGR8888 and scaler/decimation setup internally. Therefore
this is a bounded branch discriminator, **not** a perfectly isolated cache-only
experiment:

- If the requested magenta output has the same corruption, ordinary framebuffer
  pixel reads become a weaker explanation; downstream composition/output/panel
  state deserves priority.
- If magenta is clean, investigate the framebuffer-fetch/format/scaler branch
  and its memory visibility. A clean result alone does not prove a cache fault.
- White, unchanged logo, missing property or failure is not a successful magenta
  diagnostic and cannot be reinterpreted as one.

Four H0 cases execute the exact source functions with stubbed kernel layouts and
hardware callbacks: ordinary no-fill, color bits without enable, enabled magenta,
and error-white precedence. They confirm the software branch, opaque color,
forced format, source geometry and scaler override. Host compilation and
execution, AArch64 object compilation and `file` inspection pass. Constants are
checked against the actual vendor headers. Full atomic validation, hardware
fetch bypass and visible output are not emulated.

No successor is implemented or qualified here. Its changed execution closure
and success criterion still need the normal scoped review and fresh binding.
No device effect, approval renewal or P353 replay follows from this proposal.

## Evidence retention

Private analysis files are under
`workspace/private/outputs/s22plus_fyg8_p353/image-corruption-h0-20260907/`.
`audit.py` and `final-audit-v2/audit.json` bind the exact paint execution,
source-function fixture, source receipts and consumed-module disassembly.
`provenance-supplement.json` records the naked-eye witness, timing limitation,
noncausal log classification and 22 merged DT identities.
The final close receipt SHA-256 is
`764babc8fee129e70474d9eeae3de5419824fc2c0e82b2d85e405d0b6c5f5c48`.

The initial QEMU invocation on the sealed non-executable file returned nonzero
without output. Its empty output is retained; a byte-identical executable copy
then succeeded. The initial source fixture used synthetic numeric constants;
the final fixture corrects and checks them against the actual headers, with
the earlier H0 files retained separately. None of those host corrections changed
a device, consumed source, approval binding or result.

P353's original evidence and final health remain unchanged. A90 and S20+ were
not contacted. This H0 unit ends with the cause unresolved and a concrete next
diagnostic.
