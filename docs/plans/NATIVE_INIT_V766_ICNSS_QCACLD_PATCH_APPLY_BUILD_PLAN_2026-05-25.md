# Native Init V766 ICNSS/QCACLD Patch Apply Build-readiness Plan

- date: `2026-05-25 KST`
- scope: host-only disposable source apply and bounded build-readiness check
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py`

## Goal

Prove the V765 `A90V765` ICNSS/QCACLD log patch can apply to an extracted
Samsung OSRC source tree, then run the smallest build-readiness check that does
not create a boot image or touch the device.

## Inputs

- V760: staged Samsung OSRC `Kernel.tar.gz` source targets verified.
- V763: SM-A908N target path corrected to ICNSS/QCACLD SNOC.
- V764: service180-gated `mdm_helper` closed as insufficient.
- V765: review-only ICNSS/QCACLD log patch generated under private evidence.

## Contract

- safely extract `Kernel.tar.gz` into private `tmp/wifi` evidence;
- run `patch --dry-run -p1`, then apply only if dry-run succeeds;
- verify exactly 19 `A90V765` markers in the target source files;
- run bounded `r3q_kor_single_defconfig` only after patch apply succeeds;
- classify Samsung toolchain availability before any full kernel build.

## Forbidden

- no mutation of `kernel_build`;
- no full kernel build;
- no boot image or partition write;
- no device command;
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Success Criteria

- V765 manifest is current and passing.
- Patch dry-run and apply pass in a disposable tree.
- Marker count matches the generated patch coverage.
- Defconfig/build-readiness is classified with evidence logs.
- Next full-build/package gate remains separate.
