# Native Init V773 Stock DTB Tail Repack Plan

## Goal

Create a local-only diagnostic boot image that keeps the V769 ICNSS/QCACLD
instrumented kernel payload but restores the appended DTB tail required by the
known-good v724 boot path.

## Inputs

- V772 classifier manifest: `tmp/wifi/v772-boot-incompat-classifier/manifest.json`
- known-good kernel payload: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel`
- diagnostic payload: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb`
- base boot image: `stage3/boot_linux_v724.img`

## Rules

- Local-only repack.
- No device command, partition write, flash, reboot, Wi-Fi HAL, scan/connect,
  credential use, DHCP/routes, or external ping.
- Preserve all 19 `A90V765` markers.
- Restore appended FDT/DTB payload count before any future live handoff.

## Method

1. Find the first FDT magic offset in the known-good v724 kernel payload.
2. Copy the stock v724 DTB tail from that offset to the end of the payload.
3. Append that tail to the V769 diagnostic payload.
4. Repack a boot image with v724 boot header/ramdisk metadata and the combined kernel.
5. Unpack the staged image and verify the embedded kernel hash.

## Success Criteria

- combined kernel has three FDT blobs;
- combined kernel preserves 19 `A90V765` markers;
- staged boot image is 4096-byte aligned and mode `0600`;
- staged boot image contains the native-init marker and 19 `A90V765` markers;
- unpacked staged kernel hash matches the combined kernel.
