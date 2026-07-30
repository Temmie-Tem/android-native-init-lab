# Native Init V3404 D3 Resolved Owner Timeout Source Build

- Cycle: `V3404`
- Decision: `v3404-d3-resolved-owner-timeout-source-build`
- Init: `A90 Linux init 0.11.160 (v3404-d3-resolved-owner-timeout)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3404_d3_resolved_owner_timeout.img`
- Boot SHA256: `0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3403_d3_immutable_handoff.img`
- Source contract: `workspace/public/src/scripts/revalidation/a90_d3_resolved_owner_timeout_v3404.py`

## Change

- Keeps V3403's immutable-source ordering, work-copy policy, and failure cleanup.
- Defers only a strict-D3 per-owner `-EBUSY` to the existing authoritative final DRM-owner rescan.
- Continues only when that scan succeeds with zero remaining non-preserved owners.
- Preserves service failures, scan failures, non-timeout owner errors, and any nonzero final owner count.
- Emits a bounded resolution marker without process identifiers.

## Validation

- Host-only error model covers resolved timeout, remaining owner, service, scan, and non-timeout owner failures.
- Static source gate binds the narrow timeout branch before the final zero-owner decision.
- Build performs the inherited AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot pack, and SHA256 capture.
- No device, flash, mount, switch-root, network, userdata, or public-exposure action was performed by this H0 build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `d3-resolved-owner-timeout`.
- Rollback baseline remains `v2321-usb-clean-identity-rodata`; no live authority is created by this build.
