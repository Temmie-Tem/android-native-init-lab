# Native Init V3390 Wi-Fi Cache ENOSPC Fallback Source Build

- Cycle: `V3390`
- Decision: `v3390-wifi-cache-enospc-fallback-source-build`
- Init: `A90 Linux init 0.11.146 (v3390-wifi-cache-enospc-fallback)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3390_wifi_cache_enospc_fallback.img`
- Boot SHA256: `6c9101fa1e5c835e9d3ec0f828bf924089589fc7d56eff9398257f4f29ee2dbf`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3389_wifi_connect_carrier_diagnostics.img`

## Change

- Carries forward the V3389 uplink-service command surface, response redaction, scan recovery, and connect diagnostics.
- Adds a bounded supplicant config ENOSPC fallback for full `/cache` conditions.
- Falls back to `O_NOFOLLOW` in-place rewrite of the existing generated supplicant config only when atomic temp rewrite fails with storage pressure.
- Keeps the confirmed-autoconnect gate, public tunnel denial, external ping denial, and `secret_values_logged=0` contract.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_uplink_service_source` and `tests.test_native_wifi_cache_enospc_fallback_source`.
- Builder regression: `tests.test_build_native_init_boot_v3390_wifi_cache_enospc_fallback`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-cache-enospc-fallback`.
