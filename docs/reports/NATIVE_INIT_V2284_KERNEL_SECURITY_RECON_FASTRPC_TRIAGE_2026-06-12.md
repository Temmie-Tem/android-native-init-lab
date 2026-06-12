# V2284 Kernel Security Recon: FastRPC-first triage check

Date: 2026-06-12
Scope: host-only source and firmware metadata review. No device flash, no trigger, no PoC, no exploit execution.
Baseline context: WLAN/native-init observation phase is closed at the v2237 checkpoint; this report belongs to the recon-first kernel security phase described in the V2237 close checkpoint.

## Inputs checked

- Android/system SPL capture: `ro.build.version.security_patch=2023-01-01`, fingerprint/incremental `A908NKSU5EWA3` from the existing V295 property snapshot.
- Kernel build string: stock Samsung `4.14.190-25818860-abA908NKSU5EWA3`, built 2023-01-12.
- Vendor SPL: existing extracted vendor image was sparse-converted with the repo-local `simg2img`; `/build.prop` reports `ro.vendor.build.security_patch=2023-01-01` and `ro.vendor.build.version.incremental=A908NKSU5EWA3`.
- Kernel config/source: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`.
- Public references consulted:
  - Android Security Bulletins overview: `https://source.android.com/docs/security/bulletin`
  - Android February 2023 bulletin: `https://source.android.com/docs/security/bulletin/2023-02-01`
  - Qualcomm October 2024 bulletin for CVE-2024-43047: `https://docs.qualcomm.com/product/publicresources/securitybulletin/october-2024-bulletin.html`
  - CVE record for CVE-2024-43047: `https://www.cve.org/CVERecord?id=CVE-2024-43047`
  - Google Project Zero FastRPC analysis: `https://projectzero.google/2024/12/qualcomm-dsp-driver-unexpectedly-excavating-exploit.html`
  - CodeLinaro fix diff reached from the Project Zero article:
    `https://git.codelinaro.org/clo/la/kernel/msm-5.4/-/commit/c6e7698c0cf35551ab16d16ac5e21e2272644734.diff`

## Scorecard update

| Candidate | Code present | Patch absence | Device-node reachability | Current rank |
| --- | --- | --- | --- | --- |
| FastRPC / ADSPRPC CVE-2024-43047 class | Strong: `drivers/char/adsprpc.c`, `adsprpc_compat.c`, `fastrpc_mmap_*`, `get_args`, `put_args`, fdlist/free logic present | Pre-fix markers confirmed for the public `dma_handle_refs` fix: this tree lacks `dma_handle_refs` and still frees the DSP-returned fdlist map without that guard | Source registers `adsprpc-smd` and `adsprpc-smd-secure`; runtime major/minor/devnode materialization still must be verified before trigger work | 1 |
| KGSL present-ioctl class | Present: KGSL enabled and GPU command/gpuobj/gpumem/sync-cache families exist | CVE-specific | Source/config present; runtime `/dev/kgsl-3d0` reachability still must be verified | 2 |
| Binder post-2023 UAF class | Present: standard binder driver and `binder,hwbinder,vndbinder` config | CVE-specific, exact diff required | misc devices created by binder init; runtime devnode materialization still must be verified | 3 |

## FastRPC local-source match

Confirmed local source anchors:

- `struct smq_invoke_ctx` contains `fds`, `attrs`, `maps`, scalar metadata, and context bookkeeping.
- `struct fastrpc_mmap` contains `fd`, `flags`, `phys`, `va`, `len`, `refs`, `raddr`, and `attr`.
- `fastrpc_mmap_find()` searches existing mappings by `fd`, `va`, and `len`, and increments `map->refs` when requested.
- `fastrpc_mmap_create()` first calls `fastrpc_mmap_find(... refs=1 ...)`, otherwise allocates a new `struct fastrpc_mmap`.
- `get_args()` creates mappings for buffer and handle scalar entries and records them in `ctx->maps[]`.
- `put_args()` reads the DSP-returned `fdlist` and performs `fastrpc_mmap_find(... refs=0 ...)` followed by `fastrpc_mmap_free(mmap, 0)`.
- `fastrpc_device_ioctl()` exposes invoke and mmap/munmap ioctl families, including compat support through `adsprpc_compat.c`.

This is the same broad bug class described publicly for CVE-2024-43047: map lifecycle/refcount confusion around `struct fastrpc_mmap`, DSP-returned fd list handling, and `fastrpc_mmap_free()` proximity. It is enough to keep FastRPC as the top host-only candidate.

## Exact fix-diff check

The public CodeLinaro fix reached from the Project Zero article adds a separate
`dma_handle_refs` field to `struct fastrpc_mmap` and changes the handle-map
lifecycle:

- handle maps increment `dma_handle_refs` in `get_args()`;
- `get_args()` re-validates that the map still exists before using it for
  handle page metadata;
- `put_args()` only clears/frees a DSP-returned fdlist map when
  `dma_handle_refs` is present;
- `fastrpc_mmap_free()` and `fastrpc_mmap_remove()` refuse final removal while
  the new handle reference is active.

The A90 4.14 source has the older pattern:

- no `dma_handle_refs` field in `struct fastrpc_mmap`;
- `get_args()` creates handle maps and stores them in `ctx->maps[]`, but does
  not mark them with a separate handle-use refcount;
- later handle page metadata reads `ctx->maps[i]->phys/size` directly;
- `put_args()` walks the DSP-returned `fdlist` and performs
  `fastrpc_mmap_find(... refs=0 ...)` followed by `fastrpc_mmap_free(mmap, 0)`
  without the `dma_handle_refs` guard.

This upgrades the FastRPC row from `strongly likely` to
`public-fix precondition matched`. It is still not a PoC result and does not
prove exploitability on this exact boot environment. It does prove that the
public fix-side invariant is absent in this source tree.

Precise state:

- `FastRPC code presence`: confirmed.
- `FastRPC vulnerable-area presence`: confirmed.
- `CVE-2024-43047 public fix-marker absence`: confirmed.
- `Runtime ioctl reachability`: not yet confirmed; source registration exists,
  runtime devnode major/minor and openability must be checked separately.

## Devnode reachability correction

Reachability should be worded as `registered in source/config; materialization/openability pending`, not `open`.

- ADSPRPC uses `alloc_chrdev_region`, `cdev_add`, `class_create("fastrpc")`, and `device_create()` for `adsprpc-smd` plus `adsprpc-smd-secure`.
- Binder uses misc devices for configured names `binder,hwbinder,vndbinder`.
- KGSL is enabled and built, but the exact runtime `/dev/kgsl-3d0` state must be checked through sysfs/devtmpfs/ueventd context before any trigger work.

A root `mknod` may be technically sufficient once major/minor are known, but that is a live device-state mutation. It is outside this host-only report and should be a separate, explicitly approved reachability check.

## Decision

FastRPC remains the best first candidate, with a narrower wording:

> FastRPC is the strongest first host-only recon target because this build has the relevant ADSPRPC driver, mapping lifecycle code, compat ioctls, DSP-returned fdlist free path, January 2023 system/vendor SPL, public October 2024 FastRPC UAF evidence, and the public `dma_handle_refs` fix invariant is absent locally. The next step is runtime reachability classification, not PoC execution.

## Next host-only steps

1. Perform a read-only live reachability snapshot later: sysfs class/dev
   major-minor, `/proc/devices`, devnode existence, and open-only result if
   explicitly approved. No mmap/invoke trigger in that step.
2. Classify reachability as one of:
   - `fastrpc-devnode-present-openable`
   - `fastrpc-registered-missing-devnode`
   - `fastrpc-open-denied-or-driver-unready`
3. Only after reachability is known, decide whether any further FastRPC work is
   in scope. Triggering `MMAP`/`INVOKE` paths is not part of this report.
4. Repeat the same strict host-only rubric for one KGSL present-ioctl candidate
   and one Binder candidate.
