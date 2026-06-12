# V2285 Kernel Security Recon: KGSL and Binder host-only triage

Date: 2026-06-12
Scope: host-only source and public-fix marker review. No device flash, no live devnode open, no ioctl trigger, no PoC, no exploit execution.
Baseline context: V2284 confirmed FastRPC/ADSPRPC as the strongest first candidate by matching the public CVE-2024-43047 `dma_handle_refs` fix invariant absence. This iteration extends the same strict rubric to one KGSL candidate and one Binder candidate.

## Inputs checked

- Kernel source/config: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`.
- KGSL config: `CONFIG_QCOM_KGSL=y`, `CONFIG_QCOM_KGSL_IOMMU=y`.
- Binder config: `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`.
- Public references consulted:
  - Google Project Zero RCA for CVE-2023-33107:
    `https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-33107.html`
  - Android December 2023 security bulletin entry for CVE-2023-33107:
    `https://source.android.com/docs/security/bulletin/2023-12-01`
  - Android February 2023 security bulletin entry for CVE-2023-20938:
    `https://source.android.com/docs/security/bulletin/2023-02-01`
  - Android July 2023 security bulletin entry for CVE-2023-21255:
    `https://source.android.com/docs/security/bulletin/2023-07-01`
  - Android Offensive Security Binder write-up for remediation linkage:
    `https://androidoffsec.withgoogle.com/posts/attacking-android-binder-analysis-and-exploitation-of-cve-2023-20938/`
  - AOSP Binder full-mitigation commit for CVE-2023-21255:
    `https://android.googlesource.com/kernel/common/+/1ca1130ec62d`

## Scorecard update

| Candidate | Code present | Public fix-marker absence | Device-node reachability | Current rank |
| --- | --- | --- | --- | --- |
| FastRPC / ADSPRPC CVE-2024-43047 class | Confirmed in V2284 | Confirmed in V2284: public `dma_handle_refs` invariant absent | Source registration confirmed; runtime materialization/openability pending | 1 |
| KGSL CVE-2023-33107 / SVM range wrap class | Confirmed: KGSL IOMMU SVM range code plus `IOCTL_KGSL_MAP_USER_MEM` and `IOCTL_KGSL_GPUOBJ_IMPORT` paths exist | Confirmed: local `iommu_addr_in_svm_ranges()` still uses repeated `gpuaddr + size` checks without the public `end <= gpuaddr` wrap guard | Source/config present; runtime `/dev/kgsl-3d0` state pending | 2 |
| Binder CVE-2023-21255 / incomplete failed-buffer release mitigation | Confirmed: Binder driver and `binder,hwbinder,vndbinder` config exist | Confirmed: local `binder_transaction_buffer_release()` still accepts `failed_at` and failure path can release only up to `buffer_offset`; public `binder_release_entire_buffer()` mitigation absent | Source/config present; runtime devnode state pending | 3 |

## KGSL candidate: CVE-2023-33107

Public root cause and fix marker:

- The Project Zero RCA identifies the vulnerable area as `kgsl_iommu_set_svm_region()`, reached by KGSL user-memory import/map flows, where `gpuaddr + size` can wrap during SVM overlap/range checks.
- The public patch adds a local `end = gpuaddr + size` and rejects `end <= gpuaddr` in `iommu_addr_in_svm_ranges()`.
- Android's December 2023 bulletin lists CVE-2023-33107 under Qualcomm Display with security patch level later than this device's January 2023 system/vendor SPL.

Local source match:

- `include/uapi/linux/msm_kgsl.h` exposes `IOCTL_KGSL_MAP_USER_MEM` and `IOCTL_KGSL_GPUOBJ_IMPORT`.
- `drivers/gpu/msm/kgsl.c` routes `KGSL_MEM_ENTRY_USER` through `_map_usermem_addr()` and `kgsl_setup_useraddr()`.
- `drivers/gpu/msm/kgsl.c` routes `KGSL_USER_MEM_TYPE_ADDR` import through `_gpuobj_map_useraddr()` and `kgsl_setup_useraddr()`.
- `drivers/gpu/msm/kgsl_iommu.c` has the vulnerable-form SVM helper:
  - `iommu_addr_in_svm_ranges()` uses `gpuaddr + size` directly in both compat and SVM range checks;
  - no local `end` variable is introduced for the public guard;
  - no `end <= gpuaddr` guard exists before accepting the range;
  - `kgsl_iommu_set_svm_region()` then compares `gpuaddr + size <= start` and can call `_insert_gpuaddr(pagetable, gpuaddr, size)`.

This is enough to classify the KGSL candidate as:

> `kgsl-cve-2023-33107-public-fix-marker-absence-confirmed`

This is not exploitability proof. It does not establish runtime `/dev/kgsl-3d0` availability, GPU state, SELinux/device-node behavior, or successful triggerability.

## Binder candidate: CVE-2023-21255

Public root cause and fix marker:

- Android's February 2023 bulletin lists CVE-2023-20938 under Binder.
- Android's July 2023 bulletin lists CVE-2023-21255 under Binder.
- The Android Offensive Security remediation section states that CVE-2023-20938 was first addressed in February 2023, but that the initial patch did not fully mitigate the root cause and CVE-2023-21255 was assigned for the July 2023 full mitigation.
- The July 2023 AOSP full-mitigation commit changes `binder_transaction_buffer_release()` so callers release the entire buffer through a new `binder_release_entire_buffer()` wrapper instead of passing a partial `failed_at` offset through failure cleanup.

Local source match:

- `drivers/android/binder.c` registers Binder misc devices from `binder_devices_param`, with config set to `binder,hwbinder,vndbinder`.
- Local `binder_transaction_buffer_release()` still has the pre-mitigation shape:
  - function parameter `binder_size_t failed_at`;
  - local `off_end_offset = is_failure ? failed_at : off_start_offset + buffer->offsets_size`;
  - failed translation cleanup calls `binder_transaction_buffer_release(target_proc, t->buffer, buffer_offset, true)`;
  - no `binder_release_entire_buffer()` helper exists.
- The public `1ca1130ec62d` patch marker is absent from the local source.
- A separate one-line Binder guard commit that adds `object_offset > tr->data_size` is also absent, but the clearer local match for this iteration is the `1ca1130ec62d` failed-buffer release invariant.

This is enough to classify the Binder candidate as:

> `binder-cve-2023-21255-public-fix-marker-absence-confirmed`

This is not exploitability proof. It does not establish runtime `/dev/binder`/`hwbinder`/`vndbinder` availability, openability, mapped Binder buffer setup, or successful triggerability.

## Candidate ordering

Recommended order remains:

1. **FastRPC / ADSPRPC CVE-2024-43047 class** — strongest because V2284 matched the vulnerable-area code and a late public fix invariant in a Qualcomm driver with source-registered device nodes.
2. **KGSL CVE-2023-33107** — strong because code, exact public vulnerable-form range math, and public fix-marker absence all match; however runtime `/dev/kgsl-3d0` reachability is still unknown.
3. **Binder CVE-2023-21255** — strong source/fix-marker absence, but Binder is a generic Android surface and exploitability depends on runtime device-node state plus higher-complexity object/lifecycle conditions.

KGSL AUX-command candidates remain excluded for this device because `KGSL_GPU_AUX_COMMAND` / `IOCTL_KGSL_GPU_AUX_COMMAND` is absent in the local source.

## Next step

The next safe step is a read-only live reachability snapshot, if explicitly selected:

- `/proc/devices`;
- relevant `/sys/class/*/dev` entries;
- `/dev/adsprpc-smd`, `/dev/adsprpc-smd-secure`;
- `/dev/kgsl-3d0`;
- `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`;
- devnode major/minor and permission metadata.

An open-only check should be a separate sub-step from pure read-only metadata. No ioctl, mmap, invoke, Binder transaction, KGSL command, FastRPC invoke, or exploit trigger belongs in the reachability snapshot.

## Decision

Host-only A is complete:

- KGSL: `public-fix-marker-absence-confirmed` for CVE-2023-33107.
- Binder: `public-fix-marker-absence-confirmed` for CVE-2023-21255.
- FastRPC remains rank 1 from V2284.
- The live approval was not consumed by this iteration because A stayed host-only.
