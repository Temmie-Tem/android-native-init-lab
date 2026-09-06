# P357: opaque ABGR8888 framebuffer comparison

P356 produced magenta with horizontal dark gaps and severe lower-area breakup.
P355 hardware solid fill was clean, and operator-supplied Android lock/carrier
photos lack that conspicuous pattern. These observations prioritize differences
in normal framebuffer sourcing and display setup. They do not identify a cache,
address, format, scaler, bandwidth or panel-timing cause.

The operator authorized investigation and D0/D1 preparation through a fresh F1
code. Actual F1 execution still requires the separately returned exact approval.
P356 remains consumed and closed with exact rollback/final health; neither its
candidate nor its earlier failed ordinary-D1 reboot is replayable.

## Source and Android comparison

Thirty-one inputs from the retained P353 source/paint audit were reverified
unchanged. Their existing source and AArch64 module evidence is reused:

| Area | Finding | Limit |
| --- | --- | --- |
| Address/mapping | Native WC GEM allocates pages, maps them into the unsecure address space and derives the scanout address through the existing SMMU layout path. | This is source behavior, not a readback of P356's live IOVA or page contents. |
| Size/pitch/format | The 1080x2340 four-byte buffer uses pitch 4352, zero offset and linear XRGB8888; framebuffer span checks and stride programming agree. | No concrete host arithmetic defect was found; actual hardware latch was not observed. |
| Scaler | Default equal-size non-YUV QSEED3 setup returns with enable zero. | Hardware fill also overrides source/scaler state; its clean result is not a pure cache test. |
| CPU visibility | WC selects Normal-NC in the bound arm64 mapping path. GEM CPU_PREP/FINI contain cache-maintenance TODOs; generic DRM PRIME export lacks begin/end CPU-access callbacks. | Adding these ioctls or exporting the same GEM does not demonstrate an effective flush or establish a fix. |
| Bandwidth | The driver requests catalog maximum bandwidth/clock when explicit bandwidth control is absent. | This does not prove live bus votes. The twelve added display modules are not the complete native module plan; no missing-provider conclusion follows from that list alone. |

Linux documents CPU access bracketing for DMA-BUF mappings, with driver callbacks
responsible for the actual coherency work. This explains why the exporter and
its implemented callbacks must be examined; it does not make a DMA-BUF sync
ioctl a repair for the current native GEM mapping.
[Linux DMA-BUF CPU-access contract](https://www.kernel.org/doc/html/v5.15/driver-api/dma-buf.html).

Two narrowly scoped Android D0 reads were made after exact S22+ identity and
rooted health checks. The first found no exposed `/sys/kernel/debug/dri/0`
state and listed available DMA-BUF heap names. Its remote command succeeded and
retained a complete raw terminator. A host assertion incorrectly expected the
newline removed by the existing decoder's default strip=True. H0 re-decoding
with strip=False established that exact cause without replaying the read.
The first invocation did not reach its final continuity/health checks and is
not labeled D0 PASS. Its original raw capture and host error remain preserved.

The distinct SurfaceFlinger D0 used the correct decoder semantics and passed
both exact health/continuity checks. It retained 127,478 bytes privately and
reported `PASS_P357_ANDROID_SURFACEFLINGER_D0`. It lists full-screen allocated
RGBA8888 buffers with 1088-pixel / 4352-byte stride, and imported full-screen
buffers reporting FourCC 875708993 (`AB24`, ABGR8888) and modifier 0. Some metadata
also labels buffers compressed; this is retained without inferring their actual
fetch path. The dump does not expose an active SDM/HWC layer stack, so these are
allocation/configuration observations, not proof of active scanout or the
operator photo's instantaneous configuration. No device control, settings write,
framebuffer content read or other-target command was sent.

The exact driver provides another comparison: `_sde_plane_color_fill` selects
ABGR8888 internally. `sde_formats.c` declares ABGR8888 as four-byte interleaved
linear data with alpha enabled, whereas XRGB8888 disables alpha. The source
format/unpack and alpha-dependent handling can therefore differ even when both
intend magenta. Default blending uses constant plane alpha; the renderer retains
its required plane alpha 255. All new visible and padding pixels also carry
alpha 255. These facts justify a bounded format/alpha comparison, not a claim
that XRGB8888 is broken.

Private source identities, D0 receipts and findings are joined in
`workspace/private/outputs/s22plus_fyg8_p357/source-and-android-comparison.json`.
Raw dumps, private identifiers and photos are not tracked.

## Bounded candidate

P357 preserves P356's normal WC GEM allocation, pitch, size, map offset, 30HS
mode, primary/inherited-plane handling, noise_layer_v1=0, color_fill=0,
barrier, lifetime and one blocking atomic commit. Format advertisement checking
and ADDFB2 both select ABGR8888. Visible pixels become 0xffff00ff, while the eight
row-padding pixels become 0xffffffff. Both are opaque in the selected format.
No new heap, DMA-BUF ioctl, module or driver patch is introduced.

The fresh run ID is `c357f1e0a90b5e6d7c8a9b0c1d2e3f0b`. Its existing identity-only,
same-length Image transformation validates at
`41490944B/5c9af16e809e9a17de851cc2707d93d20dac3ac14df3da161fae4740e9c99541`.
No compiled kernel code changes. Design and preliminary changed-source review
found no blocking issue; final capability review follows completed A/B/static
qualification. Success requires operator-observed full clean magenta. Corruption,
white/error fill, unchanged logo or an unobserved screen is not clean-output
qualification. Dispatch and rollback remain separate machine evidence.

For H0 build space, eight owned P355/P356 packaging intermediate images were
hole-punched only in zero-filled regions. Every byte hash, logical size and
original file mode was verified unchanged; no file or evidence was deleted.
The private receipt records 457,031,680 reclaimed bytes. This changes storage
allocation only, not consumed artifacts or source identities.


## H0 qualification

Actual A/B userspace, renderer, boot image and AP match byte for byte. Candidate
AP is `30965801B/1f1da77c1a9558cb13bdc1ce0c7ce0fb7966644f948b825921b5f2242a4b650c`,
with sole member `boot.img.lz4`,
`30960280B/0a0b72e2b977654a1b36b5c338735fbd812c6a6ded5e33d1b61b3daaa7763ee7`.
The static AArch64 renderer is
`710008B/13298d7dad4f287480e668b0b933a8a1b21affe9979510e2ee2d38f61413092e`.
Actual AP/ramdisk joins pass. All 75 construction inputs remain exact. Module
bytes/plan, KMS/prerequisite receipts and child match P356.

The identical executable's --h0-paint branch under QEMU matches all 10,183,680
bytes against an independent RGBA-byte oracle, including 2,527,200 opaque magenta
pixels and 18,720 opaque white padding pixels. This exercises actual generated
instructions in host memory, not live DMA visibility or hardware scanout.
P357 focused tests and P356 regressions each pass 21 cases. The prebuild P357 run
had 20 passing tests and one missing-artifact integration case; that same full
suite passed after the required static artifact was generated. It was not an
execution failure or an assertion relaxation.

Static qualification is
`48497B/7001abb45aa9f4cccfdd0d158351d00eca2e2c3a4ce32383bbffb13cbd8faa5b`,
binding 112 source entries. No new kernel/module build was required. Final
promotion and capability review are recorded below before connected preparation.


Actual offline promotion passed with common_offline_verified=true. Ready manifest
is `4686B/50a72d4e71145324585e9d4ccc075e642a7d9096f5f031f514951d830675b87f`,
bundle `0877d8cf9508b085c9fd935b0a0fb998300999a5889e984b4256a6b2339fd680`.
Final independent capability review is PASS_GO with no open finding, receipt
SHA-256 `312e325dd83b10db8ee3ad2c755cf384bfa4e51fa8cd795f384495b73ab27554`.
The reviewed execution inputs/artifacts were reverified unchanged. Source syntax,
focused tests, repository boundary, document links and diff checks pass.
This qualifies the capability only; fresh connected preparation and exact
attended F1 approval remain separate.
