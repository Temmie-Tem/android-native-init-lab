# Native Init V3393 Wi-Fi Ctrl Socket Unique Source Build

- Cycle: `V3393`
- Decision: `v3393-wifi-ctrl-socket-unique-source-build`
- Init: `A90 Linux init 0.11.149 (v3393-wifi-ctrl-socket-unique)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3393_wifi_ctrl_socket_unique.img`
- Boot SHA256: `ee9d185e831265c47b11939a929ce361d70efc770e746f65d7b2c65884162f79`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3392_wifi_tmp_ctrl_dir.img`

## Change

- Carries forward V3392 tmp-backed WPA control socket directory and V3391 WPA diagnostics.
- Makes native WPA control local abstract socket names monotonic-unique by adding a process-local sequence to the existing pid/time tuple.
- Targets the V3392 live `-98` control-command artifact after monitor attach, without changing credential handling, DHCP, external ping, or public tunnel policy.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3393_wifi_ctrl_socket_unique`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-ctrl-socket-unique`.
