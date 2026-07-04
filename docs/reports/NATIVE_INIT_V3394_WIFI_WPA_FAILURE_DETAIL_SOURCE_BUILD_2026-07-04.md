# Native Init V3394 Wi-Fi WPA Failure Detail Source Build

- Cycle: `V3394`
- Decision: `v3394-wifi-wpa-failure-detail-source-build`
- Init: `A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3394_wifi_wpa_failure_detail.img`
- Boot SHA256: `471ac301103e27e02bfac7faae3fee850e759218a05ffede1b596c10e5a240a7`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3393_wifi_ctrl_socket_unique.img`

## Change

- Carries forward V3393 ctrl socket uniqueness and V3392 tmp-backed WPA control socket directory.
- Adds redacted WPA failure-detail fields for the true 4-way-handshake stall: temp-disabled/disconnect/assoc-reject reason classes plus safe STATUS fields.
- Keeps SSID, PSK, BSSID, raw MAC/IP/gateway/DNS, confirm token, external ping, and public tunnel out of public/result surfaces.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3394_wifi_wpa_failure_detail`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-wpa-failure-detail`.
