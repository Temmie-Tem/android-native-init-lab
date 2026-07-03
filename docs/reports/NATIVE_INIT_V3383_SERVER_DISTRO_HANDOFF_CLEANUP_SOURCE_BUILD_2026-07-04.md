# Native Init V3383 Server-Distro Handoff Cleanup Source Build

- Cycle: `V3383`
- Decision: `v3383-server-distro-native-handoff-cleanup-source-build`
- Init: `A90 Linux init 0.11.139 (v3383-server-distro-handoff-cleanup)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3383_server_distro_handoff_cleanup.img`
- Boot SHA256: `c2cb74e014c7a3e2121ef50d818e6225d7ab8d042eba75166c77e133f3fd012c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3381_server_distro_journaled_formatter.img`

## Change

- Carries forward the V3381 D4 journaled formatter/userdata appliance surface.
- Adds native server-distro display-owner cleanup before both D3 and D4 `switch_root` handoffs.
- The cleanup stops the tracked `A90_SERVICE_HUD` service, scans `/proc` for non-self `/init` processes holding DRM fds, terminates those owners with bounded `SIGTERM` then `SIGKILL`, and fails closed with `stop=handoff-display-owner` if cleanup cannot complete.
- Cleanup runs after the new root and init have already been validated, but before `/proc`, `/sys`, and `/dev` are moved into the new root.
- Intended live proof: `switch-root-to-userdata` should emit `handoff_display` markers and Debian firstboot should no longer need to kill a native `/init` DRM holder.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_server_distro_native_handoff_cleanup`.
- Builder regression: `tests.test_build_native_init_boot_v3383_server_distro_handoff_cleanup`.
- Live validation is a separate gate; this report is the source/build artifact record.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-d4d-handoff-cleanup`.
