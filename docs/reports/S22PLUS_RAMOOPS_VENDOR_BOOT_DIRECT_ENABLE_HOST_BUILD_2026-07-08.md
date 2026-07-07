# S22+ Ramoops Vendor-Boot Direct Enable Host Build (2026-07-08)

## Verdict

HOST-ONLY BUILD PASS, REPACK DRIFT ELIMINATED, LIVE NOT AUTHORIZED.

Codex built a new `vendor_boot`-only private AP that enables ramoops by directly
patching the embedded stock FYG8 vendor DTB inside `vendor_boot.img`. This
supersedes the earlier `magiskboot repack -n` candidate for future live-gate
planning because it avoids the no-change repack drift.

No flash, reboot, Odin live action, or device write was run in this unit.

## Builder

Source:

`workspace/public/src/scripts/revalidation/build_s22plus_ramoops_vendor_boot_direct_enable.py`

Private output:

`workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1`

The builder:

- verifies the stock FYG8 `vendor_boot.img` SHA256 before patching;
- parses vendor_boot v4 layout directly;
- verifies the embedded DTB appears at offset `0x14cf000`;
- verifies the stock DTB page padding has 2988 zero bytes;
- adds `status = "okay"` to all 4 `/reserved-memory/ramoops_region` DTB nodes;
- updates only the 4-byte vendor_boot header `dtb_size` field plus the allocated
  DTB page region;
- verifies `changed_outside_allowed_count=0`;
- builds a candidate Odin AP with one member, `vendor_boot.img.lz4`;
- builds a stock vendor_boot rollback AP with one member,
  `vendor_boot.img.lz4`;
- runs the Odin invalid-device parse gate for both APs.

## Hashes

```text
stock_vendor_boot       096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
source_dtb              2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e
patched_dtb             b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec
patched_vendor_boot     d62f2da241e1104db9e4b72aa0ba1927c0e85afd22fe380bff62c8df52bd3245
candidate AP.tar.md5    0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3
rollback AP.tar.md5     2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb
```

AP members:

```text
candidate: vendor_boot.img.lz4
rollback:  vendor_boot.img.lz4
```

## Direct Patch Evidence

Parsed stock layout:

```text
header_version=4
page_size=4096
vendor_ramdisk_size=21813545
dtb_offset=0x14cf000
dtb_size_before=1721428
dtb_allocated_end=0x1674000
dtb_padding_before=2988
vendor_ramdisk_table_offset unchanged
bootconfig_offset unchanged
tail/footer bytes unchanged
```

Patch result:

```text
dtb_size_after=1721508
dtb_size_delta=80
dtb_padding_after=2908
changed_byte_count=1189012
changed_range_count=185735
changed_outside_allowed_count=0
```

The large changed-byte count is expected because inserting FDT properties shifts
bytes inside the DTB. The critical bound is that every changed byte is inside
one of these spans:

```text
vendor_boot header dtb_size: 0x834..0x838
allocated DTB page region:  0x14cf000..0x1674000
```

No vendor ramdisk, vendor ramdisk table, bootconfig, AVB/footer/tail, or other
partition-image bytes changed.

## Ramoops Status Evidence

The stock DTB had no `status` property on the target nodes. The patched DTB has:

```text
blob 0: status = "okay"
blob 1: status = "okay"
blob 2: status = "okay"
blob 3: status = "okay"
```

Independent extraction with `magiskboot unpack -n -h` from the direct-patched
vendor_boot re-read the same patched DTB SHA256
`b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec` and confirmed
the four `okay` status values.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_ramoops_vendor_boot_direct_enable.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_ramoops_vendor_boot_direct_enable.py \
  --force
```

Additional extraction check:

```bash
workspace/private/tools/magisk-v30.7/magiskboot unpack -n -h \
  workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/build/vendor_boot.ramoops_status_okay.direct.img
```

Results:

- `py_compile`: pass.
- Host build: pass.
- Candidate and rollback APs have exactly one `vendor_boot.img.lz4` member.
- Direct patch changed no bytes outside the header `dtb_size` field and the
  allocated DTB page region.
- Patched vendor_boot extraction confirms all 4 ramoops nodes have
  `status = "okay"`.
- Odin invalid-device parse gate parsed both APs and failed only on the
  intentionally nonexistent USB path.

## Safety State

The manifest records:

```text
host_only=true
touches_connected_device=false
live_flash_authorized=false
partition_scope_if_later_authorized=vendor_boot only
requires_new_sha_pinned_vendor_boot_exception_before_flash=true
current_agents_does_not_authorize_this_live_flash=true
magiskboot_repack_used=false
byte_preserving_layout=true
changed_outside_allowed_count=0
```

## Next

Use this direct candidate, not the earlier repack candidate, for the next
vendor_boot live-gate preflight.

If live is later authorized, it must be a new SHA-pinned vendor_boot-only
exception with:

- candidate AP SHA256
  `0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3`;
- stock vendor_boot rollback AP SHA256
  `2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb`;
- attended ack;
- M13 positive-control capture first;
- stock vendor_boot restore when done.
