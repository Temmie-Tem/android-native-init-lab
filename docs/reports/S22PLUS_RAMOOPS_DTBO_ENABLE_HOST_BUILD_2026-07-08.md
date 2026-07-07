# S22+ Ramoops DTBO Enable - Host Build and Target Correction (2026-07-08)

## Scope

Host-only. No device action, no reboot, no flash, and no partition write.

This unit responds to the operator-observed M18 bootloop by stopping blind USB
module permutations and preparing the next observability path: enable ramoops so
the native-init kernel console can survive the failing boot.

## Correction

The prior steer pointed at `vendor_boot` DTB as the patch target. Local FDT
inspection corrected that:

- `vendor_boot` DTB contains 4 concatenated FDT blobs.
- All checked vendor DTBs have the `ramoops_region` node available with no
  `status` property under `/reserved-memory/ramoops_region`.
- The disabling overlay is in `dtbo.img`, not in `vendor_boot`.
- Stock `dtbo.img` contains 11 FDT blobs.
- DTBO blobs 9 and 10 contain `__fixups__/ramoops_mem` pointing at
  `/fragment@116:target:0` and a `/fragment@116/__overlay__/status =
  "disabled"` property.

## Implementation

Added:

`workspace/public/src/scripts/revalidation/build_s22plus_ramoops_dtbo_enable.py`

The builder is fail-closed and DT-aware:

- verifies the stock FYG8 raw `dtbo.img` SHA256 before patching;
- parses concatenated FDT blobs instead of raw string replacing;
- patches only overlays whose `__fixups__/ramoops_mem` target
  `/fragment@116:target:0`;
- changes `disabled\0` to same-length `okay\0\0\0\0`;
- verifies exactly 2 patch targets and exactly 16 changed bytes;
- produces both candidate and stock rollback Odin AP packages;
- records AVB hash descriptor status in the manifest.

## Output

Private output:

`workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1`

Candidate AP:

`workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/candidate_odin4/AP.tar.md5`

Stock rollback AP:

`workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/stock_rollback_odin4/AP.tar.md5`

Hashes:

```text
stock_dtbo_raw      97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
patched_dtbo_raw    1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab
candidate_ap_tar_md5 4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00
rollback_ap_tar_md5  6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
vendor_boot_dtb_checked 2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e
```

Patch evidence:

```text
blob 9  offset 0x6757e3  64697361626c656400 -> 6f6b61790000000000
blob 10 offset 0x722684  64697361626c656400 -> 6f6b61790000000000
changed_byte_count=16
tar_members=["dtbo.img.lz4"]
```

## AVB status

Stock DTBO AVB hash descriptor:

```text
partition=dtbo
image_size=7777749
salt=cd2e0e500c8eba1677c63ef2336da873c0d18d0c4cfc7f7166828b1e73086a2b
descriptor_digest=fc4274765cb8e785d1d88c974a5a6ef7119961a66fac452c305ba0dc2fbd3ed1
stock_recomputed_digest=fc4274765cb8e785d1d88c974a5a6ef7119961a66fac452c305ba0dc2fbd3ed1
patched_recomputed_digest=fb2c5caf7654daa8485cb98db5f004b011a72a73633bc85bb3602e392e8867a7
```

The stock image matches its AVB descriptor. The patched image deliberately does
not, because the DTBO payload changed and this host-only unit did not re-sign it.
Any live attempt therefore requires the existing disabled-vbmeta state to be
explicitly accepted as part of the gate, or a separate signing/repacking design.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_ramoops_dtbo_enable.py

python3 workspace/public/src/scripts/revalidation/build_s22plus_ramoops_dtbo_enable.py --force

tar -tvf workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/candidate_odin4/AP.tar.md5
tar -tvf workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/stock_rollback_odin4/AP.tar.md5

python3 workspace/private/tools/aosp_avb/avbtool.py info_image \
  --image workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img

python3 workspace/private/tools/aosp_avb/avbtool.py info_image \
  --image workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/build/dtbo.img
```

The Odin invalid-device parse gate saw both AP packages as files and then failed
only on the intentionally nonexistent USB device path.

## Live gate

Not live-authorized yet.

The current `AGENTS.md` default still authorizes only boot-image flashing via the
checked helper. This DTBO candidate is not a forbidden partition, but it is not
boot-only. Before any live attempt, add a narrow SHA-pinned `dtbo`-only exception
covering exactly:

- candidate AP SHA256
  `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`;
- stock rollback AP SHA256
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`;
- no other AP members beyond `dtbo.img.lz4`;
- attended operator ack;
- stock boot/Magisk rollback remains staged;
- immediate restore path for stock DTBO after capture.

Until that exception exists, this output is only a prepared observability
candidate.
