# P358: cached ABGR8888 ordinary framebuffer preparation

P358 compares GEM `MSM_BO_CACHED` with P357's `MSM_BO_WC`, retaining opaque
ABGR8888 magenta and the same display request. P357 is consumed and closed with
exact rollback/final health; its corrupt visual result is unchanged. This
preparation does not prove the cause of that corruption or activate a device run.

The operator authorized remaining analysis and preparation of the next
experiment, with D0/D1 preapproval when needed. A separately returned fresh F1
approval is still required before candidate transfer.

## Remaining analysis and selected discriminator

The [post-P357 investigation](S22PLUS_FYG8_POST_P357_BUFFER_FETCH_ANALYSIS_2026-09-07.md)
joined exact source, module/core disassembly, 22 hash-qualified DT combinations
and one bounded Android D0. They support investigating the WC/shmem/coherent-DMA
cache-state handoff. The actual driver also chooses CACHED in its default dumb
buffer constructor. No native PTE, cache, IOVA, actual bus vote, scaler register
or DSC state was captured. Those unknowns remain unknown; another Android read
or a normal reboot cannot establish them for the consumed native run.

The next request therefore keeps the existing allocation size, shared mapping,
ABGR8888 format, pixel values, pitch 4352, 1080x2340 geometry, 30HS timing,
noise_layer_v1=0, color_fill=0, inherited-plane replacement and one blocking
atomic request. Only the GEM cache flag and identifying text change. Existing
module providers, readiness checks, privilege drop, authenticated one-way
dispatch, child bounds, physical Download and exact Magisk rollback are retained.

The cached branch retains the same GEM fault callback and obtains the backing
pages on the first CPU fault. It changes protection and shmem-file mmap
bookkeeping, skips the WC early DMA map/EXTBUF assignment, and reaches the
checked DMA-map path during framebuffer preparation. Thus the experiment changes
cacheability and DMA-map timing/path together. It does not isolate cache
coherency alone and adds no heap, DMA-BUF import, cache ioctl or kernel patch.

Independent design review found no blocker but identified a relevant limit:
`msm_smmu.c:259–274` contains an unchanged Samsung DMA-map failure retry branch.
After an initial mapping return of zero, it can sleep and retry internally;
the loop breaks on zero, so a successful retry does not itself terminate that
loop. This path is not qualified here, and no such failure was observed. The
no-retry claim is strictly about userspace requests, not internal driver mapping
attempts. Existing bounds and physical rollback remain mandatory. No additional
kernel repair or new diagnostic action is included in this comparison.

Clean full magenta must be observed by the operator. Corrupt magenta, white/error
fill, unchanged logo or no observation does not qualify clean output. Host
dispatch and supplemental Carrier evidence do not prove renderer completion,
cache behavior or visible output. Every candidate outcome requires exact rollback
and final health, without candidate replay.

## Implementation and H0 evidence

Thin P358 namespace wrappers reuse seven sealed P353 producer/observer/adapter
sources. The renderer imports the sealed P357 renderer and applies one functional
flag replacement. The shared evidence registry adds only P358's existing
static-display-dispatch class. The target clause and post-close ledger family
are extended without changing permanent boundaries.

The fresh run ID is `c358f1e0a90b5e6d7c8a9b0c1d2e3f0b`. Existing same-length
post-link identity transformation changes only the declared raw marker and
IKCONFIG marker spans. Image is
`41490944B/06366eb6660e9de4c8edfac68e4baf21aae911f5b15c9220cae1cfefeee2812b`.
No kernel or module code was rebuilt or patched.

Actual A/B userspace, renderer, boot and AP agree. All 76 construction source
inputs remain exact. Candidate AP is
`30965801B/b0dff4a9eca664e6bdb71ea8a1b14e3cee14746329723124482235eac6197210`,
with sole member `boot.img.lz4`,
`30960225B/b204433f2b50d1f03861d40cdcea482938b16af417928a23541f626332464a6f`.
The static AArch64 renderer is
`710056B/5f319587fba881761e77e76d81fbc55aa7c1402d83c09b72206fbaa66def0a4a`.

Actual executable bytes under QEMU produced 10,183,680 bytes matching both an
independent byte oracle and the consumed P357 H0 paint output. All 2,527,200
visible pixels remain opaque magenta and 18,720 padding pixels opaque white.
This host-memory check is not a hardware-coherency or scanout test. The first
QEMU attempt against the non-executable mode-0400 artifact returned nonzero
with empty output; the host failure is preserved. A byte-identical mode-0500
fixture copy then completed. Original artifact bytes and mode were unchanged.

The renderer behavioral fixture checks the CACHED allocation flag, exact atomic
request, unchanged paint, one buffer/commit and failure without userspace retry.
P358's focused suite passes 21 tests, including inherited authenticated prefix,
no-replay, child-bound and evidence-separation cases. The P357 regression suite
also passes 21 tests. No old fixture or consumed candidate was edited.

Actual static qualification is
`48708B/cf390afe6181ade4bde97e77b643ac21dd74c5f850fa6f1cd560b01f7577164d`,
with exact artifact/AP/ramdisk joins. Final promotion/review and connected
preparation are recorded below when completed; no F1 candidate has transferred.

Private evidence is under `workspace/private/outputs/s22plus_fyg8_p358/`.


## Capability qualification and promotion

Final independent review is PASS_GO with no open finding, receipt SHA-256
`143dfcb8c28559446736d9e32b9b994f1a4b24c5fc57641e0e229960ee120a1a`.
Actual offline promotion passed with common_offline_verified=true. Ready manifest
is `4686B/3b8b333f7368570d805f1fc60762180123c7c0f0371b4c7cf4ddf8555ff154c6`,
bundle `e063ec8f45081df3fc8c3e47a0d06ecc654158f5b75238dcd0502a81fb3d0b77`.
Reviewed critical inputs and artifact hashes were reverified unchanged before
connected preparation. Syntax, focused/regression tests and repository boundary
checks pass. This qualifies the capability, not a device run.
