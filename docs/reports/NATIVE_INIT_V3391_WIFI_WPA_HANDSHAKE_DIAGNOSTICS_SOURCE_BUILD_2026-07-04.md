# Native Init V3391 Wi-Fi WPA Handshake Diagnostics Source Build

- Cycle: `V3391`
- Decision: `v3391-wifi-wpa-handshake-diagnostics-source-build`
- Init: `A90 Linux init 0.11.147 (v3391-wifi-wpa-handshake-diagnostics)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3391_wifi_wpa_handshake_diagnostics.img`
- Boot SHA256: `11a2685964a93271bac9d2ef34348f2a74a2aa079a3ca46941b731d5f4ed76b3`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3390_wifi_cache_enospc_fallback.img`

## Change

- Carries forward the V3390 uplink-service surface, response redaction, scan recovery, connect diagnostics, and cache ENOSPC fallback.
- Adds a bounded WPA completion wait after carrier-up so native autoconnect does not fail on the first transient 4-way-handshake STATUS sample.
- Adds a WPA control monitor that records only event categories and counters; raw WPA events, SSID, BSSID, MAC, IP, and credentials remain unlogged.
- Keeps confirmed-autoconnect gating, public tunnel denial, external ping denial, and `secret_values_logged=0`.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-wpa-handshake-diagnostics`.
