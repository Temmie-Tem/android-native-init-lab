# Native Init V3395 WSTA Screenapp Source Build

- Cycle: `V3395`
- Decision: `v3395-wsta-screenapp-source-build`
- Init: `A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3395_wsta_screenapp_live.img`
- Boot SHA256: `4d3eb72f20d8a2cf6186b81b7cdcf86c01b68bbc34d9007cc573d0bb19fb0605`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3394_wifi_wpa_failure_detail.img`

## Change

- Carries forward V3394 redacted WPA failure-detail diagnostics.
- Adds WSTA50 native operator screenapp strings to the boot-image required-string audit.
- Targets live validation of the read-only `screenapp wsta` / `screenapp dpublic` display surface.
- Does not add Wi-Fi connect, DHCP, public tunnel, native reboot, or flash behavior to the WSTA screen.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wsta_operator_screenapp_source`.
- Builder regression: `tests.test_build_native_init_boot_v3395_wsta_screenapp_live`.
- No association, DHCP, ping, public exposure, userdata, switch-root, or live display action was performed in this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wsta-screenapp-live`.
