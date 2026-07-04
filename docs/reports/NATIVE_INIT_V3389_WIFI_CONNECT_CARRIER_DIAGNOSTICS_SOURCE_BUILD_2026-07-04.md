# Native Init V3389 Wi-Fi Connect Carrier Diagnostics Source Build

- Cycle: `V3389`
- Decision: `v3389-wifi-connect-carrier-diagnostics-source-build`
- Init: `A90 Linux init 0.11.145 (v3389-wifi-connect-carrier-diagnostics)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3389_wifi_connect_carrier_diagnostics.img`
- Boot SHA256: `e9eca0744848f51a44690768c4c6335e2867d718acb2cd1afc010c4cb1dc5b4c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3388_wifi_autoconnect_scan_recovery.img`

## Change

- Carries forward the V3388 uplink-service command surface, response redaction, and scan recovery.
- Adds redacted native connect/carrier diagnostics for the confirmed autoconnect path.
- Records carrier wait, control-socket, WPA state, supplicant, and cleanup summaries in `autoconnect.result` and the uplink-service response.
- Keeps the confirmed-autoconnect gate, public tunnel denial, external ping denial, and `secret_values_logged=0` contract.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3389_wifi_connect_carrier_diagnostics`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-connect-carrier-diagnostics`.
