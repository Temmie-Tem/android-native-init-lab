# Native Init V3387 Wi-Fi Uplink Service Redaction Source Build

- Cycle: `V3387`
- Decision: `v3387-wifi-uplink-service-redacted-source-build`
- Init: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3387_wifi_uplink_service_redacted.img`
- Boot SHA256: `ebebf4384f408c5cd20630b12cfd94d56d4d484664612b692de986fdecf6da5d`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3386_wifi_uplink_service_boundary.img`

## Change

- Carries forward the V3386 uplink-service command surface.
- Tightens file-response redaction: profile label values are no longer emitted.
- Replaces profile label strings with `autoconnect_profile_present`, `config_profile_present`, and `requested_profile_present` booleans.
- Keeps the `confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1` gate, public tunnel denial, external ping denial, and `secret_values_logged=0` contract.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3387_wifi_uplink_service_redacted`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-uplink-service-redacted`.
