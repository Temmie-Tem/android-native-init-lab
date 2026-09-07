# P358: cached ABGR8888 ordinary framebuffer preparation

P358 compares GEM `MSM_BO_CACHED` with P357's `MSM_BO_WC`, retaining opaque
ABGR8888 magenta and the same display request. P357 is consumed and closed with
exact rollback/final health; its corrupt visual result is unchanged. P358 has now completed one separately approved F1, with operator-observed clean
magenta and exact healthy rollback. The cause of the earlier corruption remains
unproved.

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
with exact artifact/AP/ramdisk joins. Promotion/review, connected preparation and
the later separately approved F1 are recorded below.

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


## Connected preparation

First preparation in `p358-ready1-prepared-20260907-1` passed exact initial health
then preserved the expected retained-baseline stop. The non-reusable stop receipt
is `3252B/68d277bdd490a64ea9864f1258545be31b5121734aea86b0dd2f4f26d5356a6d`.
Actual bundle/stop-result validation passed; no candidate/Download effect occurred.

Under the current D0/D1 preapproval, the existing reviewed one-normal-reboot
primitive was invoked once with fresh P358 metadata and the closed P357 health
binding. Its host self-test passed. Actual result is
`2963B/796a27333bde83c6c876d8bff9ea68307ef3ef4cbb1a753f68379e020c4bbc03`,
`PASS_P358_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`. One reboot returned with a new
boot ID and exact rooted FYG8/original boot and supporting hashes/Android health.
Linked invocation and primitive receipts reverify. No retry or manual recovery
was needed. P356's historical failure and every consumed F1 result are unchanged.

Fresh D0 in `p358-ready1-prepared-20260907-2` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`, result
`3261B/2f54c9632a193e83276c26837bba7141d3e51925dc1916f81d098b994d8c80a7`.
Prepared record is
`30321B/32d4c08d38096ffff46511aec68122ef8b86bc57a26bf6e7501baefe3e0b5aec`.
It issues a fresh exact F1 token, excluded from tracked documents and supplied
directly to the operator.
Device-write, reboot, partition-transfer, live/F1 authority and Odin flags in
that prepared record are false. At preparation completion no P358 candidate had
transferred, and the separate F1 approval was pending. A90/S20+ received no
command from this task. GOAL/report are outside the prepared execution closure.

Actual `load_prepared` reopening passed. Final document content/link/privacy and
diff checks passed. The preparation-through-code unit completed before the
separately approved F1 below.


## Consumed F1: observed clean cached-buffer magenta

After the operator returned the exact fresh approval, run
`p358-ready1-prepared-20260907-2` transferred one candidate and one exact Magisk
rollback. The operator explicitly reported **full clean magenta**. This is
operator-observed clean ordinary CACHED-buffer output; no photograph was supplied
for this run. WC P356/P357 remained corrupt in their separate retained observations.
The comparison supports choosing the CACHED path for the next bounded display
capability, but does not isolate cache coherency from mmap/DMA-map timing or
other consequences of the flag. No native PTE/cache/register readback was added.

The machine verdict is
`PASS_F1_V2_P358_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`, proving authenticated
host dispatch and rollback, not renderer completion or panel output. Live result
is `22805B/f6467449af7e16dcbcac61b76ce078c94161273ba5f4f2fd6f79e81991c3dea5`.
The independent private `operator-visual-witness.json` retains the visual report.

The original execute stopped with `measured USB endpoint evidence failed` while
waiting for physical Download after observation, before any rollback intent or
transfer. Its error and raw evidence remain preserved; its cause is unproved.
One same-journal preauthorized recovery invocation obtained the exact rollback
endpoint and completed the sole rollback. Candidate and observation were never
replayed, and no topology-rebind exception was used.

Final rooted FYG8, original boot/supporting hashes, Android health and absent
Download passed. The journal is CLOSED/19, recovery_required=false, with no
active later-action lease. P358 is consumed and never replayable. A90/S20+
received no command from this task. No successor F1 or standing native session
is activated by this result.

Canonical timeline, UTC:

| Event | Timestamp |
| --- | --- |
| live_session_start | 2026-09-07T08:49:12.552574Z |
| candidate_flash_start | 2026-09-07T08:49:29.693436Z |
| candidate_flash_done | 2026-09-07T08:49:31.315356Z |
| candidate_boot_ready | 2026-09-07T08:49:43.787356Z |
| rollback_flash_start | 2026-09-07T08:51:35.080671Z |
| rollback_flash_done | 2026-09-07T08:51:36.638188Z |
| rollback_boot_ready | 2026-09-07T08:52:24.392260Z |
| live_session_end | 2026-09-07T08:52:24.412296Z |
