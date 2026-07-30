# Native Init V3403 D3 Immutable Handoff Source Build

- Cycle: `V3403`
- Decision: `v3403-d3-immutable-handoff-source-build`
- Init: `A90 Linux init 0.11.159 (v3403-d3-immutable-handoff)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3403_d3_immutable_handoff.img`
- Boot SHA256: `2b2b458b4f021825e0567c239ef86996d482a7b55baccc4e4a8cd9e670a2e2b9`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Source contract: `workspace/public/src/scripts/revalidation/a90_d3_immutable_handoff_v3403.py`

## Change

- Keeps V3402's native services and restart policy while replacing the D3 handoff ordering.
- Stops autohud and the D-public presenter, terminates all native-init DRM owners, and requires zero remaining owners before any loop attachment or rw mount.
- Rechecks the manifest-bound source SHA after display cleanup, copies it to a fixed absent-only work image, and loop-mounts only that work image rw.
- On every pre-`switch_root` failure, restores moved mounts, unmounts the work root, detaches the loop, removes the owned work image, and rechecks the original source SHA.
- Refuses a preexisting work image rather than overwriting or deleting an unowned path.

## Validation

- Host-only model injects every pre-switch failure and a multi-owner `-EBUSY` fault.
- Static source-order gate binds cleanup, source recheck, work-copy, loop, mount, init validation, mount moves, exec, and failure cleanup.
- Build performs the inherited AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot pack, and SHA256 capture.
- No device, flash, mount, switch-root, network, userdata, or public-exposure action was performed by this H0 build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `d3-immutable-handoff`.
- Rollback baseline remains `v2321-usb-clean-identity-rodata`; no live authority is created by this build.
