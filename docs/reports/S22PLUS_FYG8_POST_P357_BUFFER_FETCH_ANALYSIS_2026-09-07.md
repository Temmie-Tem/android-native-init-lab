# Post-P357: normal-buffer mapping and coherency analysis

The strongest next discriminator is to retain P357's opaque ABGR8888 magenta,
pitch, mode and one atomic commit, but select `MSM_BO_CACHED` instead of
`MSM_BO_WC` for the ordinary GEM object. This is a proposed H0 design, not an
activated candidate or an F1 approval. **The cause of the visible corruption
remains unproved.**

P355's hardware fill was operator/photo-observed clean. P356's XRGB buffer and
P357's opaque ABGR buffer remained corrupt. P357 is consumed, CLOSED/19 with
exact Magisk rollback and healthy rooted FYG8. Format/alpha alone did not resolve
the observation. P353 through P357 are never replayable.

## New evidence

| Evidence | Finding | Scope and limit |
| --- | --- | --- |
| Fresh Android D0 | The nonsecure SDE SMMU client declares `dma-coherent`; DRM's MDP node has no `memory-region`. | This reads DT/sysfs metadata, not the live native CPU PTE, SMMU PTE, device coherence bit or cache contents. |
| Qualified merged DTs | All 22 retained base/overlay combinations reverify by size/hash. All declare nonsecure SDE `dma-coherent`, lack a DMA allocator override and lack MDP `memory-region`. | These are retained input configurations, not register readback. |
| Android DMA-BUF metadata | Nine 10,313,728-byte buffers report `qcom,system`. | Allocation metadata does not identify the current active scanout layer. No buffer contents were read. |
| Exact vendor heap source | `qcom_dma_heap.c` creates `qcom,system` with uncached=false; the heap's mmap path preserves normal cached protection. | This identifies the source behavior of that heap, not every Android buffer or its active display usage. |
| Consumed display module | `msm_gem_dumb_create` selects `MSM_BO_SCANOUT | MSM_BO_CACHED`, corroborated by the actual `msm_drm.ko` instruction constant `0x10001`. | Native P357 uses GEM_NEW with WC, not this default dumb allocation path. |
| Native module and renderer | GEM mmap's WC branch selects Normal-NC. The actual renderer contains the terminal `dmb ish` after paint. | A memory-ordering barrier does not itself clean or invalidate caches. |
| Native core Image | The coherent-device early-return branch in `iommu_dma_sync_sg_for_device` is present in the exact consumed Image. | Runtime selection and state still require evidence; see the binary attribution limits below. |

## Native allocation and mapping chain

The exact `msm_gem.c` source and module support this sequence:

1. P357 asks GEM_NEW for `SCANOUT | WC`, obtains the mmap offset, maps the object
   shared, registers ABGR8888 and paints the buffer. The flags are `0x20001`.
2. `_msm_gem_new` initializes a shmem-backed object when an IOMMU is present and
   there is no VRAM carveout. The reverified DTs and Android D0 support these
   preconditions; they do not directly expose the native object's allocator.
3. On the first WC userspace page fault, `get_pages` allocates all backing pages
   through `drm_gem_get_pages` and creates their scatter/gather table. The latter
   helper obtains pages through `shmem_read_mapping_page`.
4. For WC/UNCACHED, `get_pages` calls `dma_map_sg` on the default nonsecure SDE
   address-space device with attributes zero, then sets `MSM_BO_EXTBUF`.
5. `msm_gem_mmap_obj` supplies Normal-NC protection for the userspace WC mapping.
   Paint stores occur through that mapping, followed by `dmb ish`.
6. At framebuffer preparation, `msm_gem_get_iova_locked` obtains the GEM mapping;
   `smmu_aspace_map_vma` uses the first DMA address. `msm_smmu_map_dma_buf` skips a
   second DMA map for EXTBUF. The SDE layout then supplies the framebuffer's
   address and pitch to the selected source pipe.

For the generic DMA-IOMMU path, `dma_info_to_prot` derives `IOMMU_CACHE` from
`dev_is_dma_coherent`; its sync callback returns early for a coherent device.
The SMMU DT parser defaults to the upstream allocator when `qcom,iommu-dma`
is absent. The fast allocator's setup hook requires DOMAIN_ATTR_FAST and does
not unconditionally replace the default allocator. Its own sync path also
skips cache maintenance for coherent mappings. Neither observation substitutes
for a native live page-table or DMA-ops capture.

The WC allocation helper describes its initial map as cleaning newly allocated
pages, but a map through a coherent client need not perform that clean. This
creates a concrete hypothesis: shmem's cached initialization, the later Normal-NC
CPU writes and a coherent/cacheable device mapping may not have the required
cache-state handoff. The exact Qualcomm uncached heap explicitly documents and
performs an initial cache flush using its heap device; it is not interchangeable
with this GEM helper's map through the display client.

Arm's memory model requires appropriate handling when agents access a location
with mismatched cacheability attributes. That supports examining this handoff;
it does not establish that stale cache lines caused this particular picture.
[Arm mismatched memory attributes](https://developer.arm.com/documentation/ddi0487/mc/-Part-B-The-AArch64-Application-Level-Architecture/-Chapter-B2-The-AArch64-Application-Level-Memory-Model/-B2-11-Mismatched-memory-attributes?lang=en).

The generic DMA API also requires checking map results and managing ownership
transitions. A sync call is meaningful only in the actual exporter/device path.
[Linux DMA mapping API](https://www.kernel.org/doc/html/latest/core-api/dma-api.html).

## What the analysis does not establish

- No native PTE, physical-page content, live IOVA, cache-line state or SDE
  register was read. The coherence mismatch is a source/binary-supported
  hypothesis, not a measured runtime fault.
- The first DMA-map return in `get_pages` is ignored before EXTBUF is set. Both
  source and actual module confirm that weakness, but no mapping failure was
  observed. It must not be reported as the cause.
- The 4352-byte pitch, four-byte format and bounded allocation still agree with
  the inspected layout calculations. Physical noncontiguity alone is not an
  error: DMA-IOMMU can map scatter/gather pages into a contiguous IOVA span.
- `qcom,iommu-earlymap` is declared, but `_sde_kms_mmu_init` explicitly disables
  it and propagates errors before successful initialization. There is no basis
  for assuming the normal path simply forgot to enable translation.
- CPU_PREP/FINI contain cache-maintenance TODOs, and generic DRM PRIME export
  has no begin/end CPU-access implementation here. Adding an ioctl by name
  would not demonstrate a flush. Preserve the earlier P357 finding.
- Hardware fill also overrides source/scaler behavior. It does not exclude
  bandwidth, scaler, fetch, mode/DSC, handoff or downstream causes. The opaque
  ABGR result likewise does not eliminate every format-related interaction.
- Debugfs is not mounted in the observed Android state. No debugfs mount,
  register access, arbitrary memory access or new diagnostic device capability
  was added merely to obtain more detail.

## Smallest proposed next comparison

Change only the GEM allocation cache selection from WC to CACHED. Preserve
ABGR8888, opaque magenta/white padding, size 1080x2340, pitch 4352, mode 30HS,
noise_layer_v1=0, color_fill=0, primary/inherited-plane handling, one blocking
atomic request, privilege drop, dispatch/child bounds and exact attended rollback.

The driver already accepts CACHED and uses it in its dumb-buffer constructor.
This avoids a new heap, PRIME import, module patch, DMA API addition or second
commit. However, one flag selects a different internal path: cached mmap uses
the shmem file and zero page offset while retaining the same GEM fault callback.
Backing pages are still obtained on the first CPU fault, but CACHED skips the
WC/UNCACHED early DMA map and EXTBUF assignment; the checked DMA-map path then
runs during framebuffer preparation. **This is a mapping-path comparison,
not an experiment that isolates only cache coherency.**

A clean result would qualify the proposed ordinary-buffer path and strengthen
that group of hypotheses. A corrupt, absent or unobserved result would leave
clean output unproved. Neither outcome permits replay or infers automatic
recovery. Creating this candidate still requires fresh identities, appropriate
static qualification, independent changed-closure review, connected preparation
and a separately returned F1 approval. No new candidate was built or transferred
in this analysis.

## Attribution and validation

The prior 31 source/evidence inputs were reverified unchanged. Twenty-two source
and binary inputs for this investigation have private size/hash receipts. The
P357 renderer and `msm_drm.ko` match their retained build result; disassembly was
made from those exact artifacts. Existing paint/layout evidence was reused.

The retained P310 vmlinux was used as a symbol-location reference against P357's
raw Image. `dma_map_sg_attrs` matches in full. Other examined functions have
some differing data/address instructions, so whole-function equality is not
claimed. The sync function's entry, coherent-flag load/branch and return block
match; its one differing instruction is a later data load outside that return
path. Raw Image disassembly and the complete differences are preserved. P300
was also checked and did not supply whole-function matches. These are host
binary observations, not proof of live hardware execution.

One bounded D0 invocation, `post-p357-android-buffer-metadata-d0-1`, passed exact
selection, rooted FYG8/original boot and supporting-hash health before and after,
with unchanged boot/selection. Its 4,405-byte metadata capture has SHA-256
`fd1442adeb23ef13cbf35246866f261ff150c50aa114ee1aef13a841bfc8ba05`;
result SHA-256 is
`f1b2d0fae4e422642086fdcbe17bcde260302b3f315672634cc75020eeb663c5`.
A host-only quoting check first detected a NUL escape before any device command;
the original source and correction are preserved. No connected failure occurred.
No D1 was needed. A90/S20+ received no command.

Private receipts and disassembly are under
`workspace/private/outputs/s22plus_fyg8_post_p357_buffer_fetch_h0/`; raw D0 output
is under its exact private run. This report and GOAL change no device contract,
runner, consumed source closure, approval or journal.
