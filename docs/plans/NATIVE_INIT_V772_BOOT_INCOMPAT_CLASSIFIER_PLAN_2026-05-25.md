# Native Init V772 Boot Incompatibility Classifier Plan

## Goal

Classify the V771 diagnostic kernel boot failure without another flash.

## Inputs

- known-good kernel payload: `tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel`
- diagnostic kernel payload: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb`
- V771 failure report: `docs/reports/NATIVE_INIT_V771_DIAGNOSTIC_LIVE_HANDOFF_BOOT_FAIL_2026-05-25.md`

## Rules

- Host-only analysis only.
- No device command, boot partition write, flash, reboot, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- Compare payload size, hashes, Linux version strings, embedded config, instrumentation markers, and appended FDT/DTB payloads.

## Success Criteria

- Known-good and diagnostic kernel payloads are available.
- V771 failure is documented.
- The classifier identifies whether the staged diagnostic payload is structurally missing a boot-critical payload compared with v724.

## Next If Classified

If the diagnostic payload is missing appended DTBs, V773 should create a
local-only fixed payload by appending the stock v724 DTB tail to the V769
instrumented Image, then repack and verify locally. No live flash until that
staging gate passes.
