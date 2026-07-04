# Native Init V3392 Wi-Fi Tmp Ctrl Dir Source Build

- Cycle: `V3392`
- Decision: `v3392-wifi-tmp-ctrl-dir-source-build`
- Init: `A90 Linux init 0.11.148 (v3392-wifi-tmp-ctrl-dir)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3392_wifi_tmp_ctrl_dir.img`
- Boot SHA256: `da2f39b60300497d8957abff77a97764864fd8a6d3de3018bb8e837837c9861c`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3391_wifi_wpa_handshake_diagnostics.img`

## Change

- Carries forward V3391 WPA handshake diagnostics and V3390 cache ENOSPC fallback.
- Moves the WPA control socket directory from full `/cache/a90-wifi/sockets` to volatile `/tmp/a90-wifi/sockets`.
- Keeps the generated supplicant config under `/cache/a90-wifi/wpa_supplicant.conf` and keeps all credential/raw-value redaction contracts.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wifi_cache_enospc_fallback_source` and `tests.test_native_wifi_uplink_service_source`.
- Builder regression: `tests.test_build_native_init_boot_v3392_wifi_tmp_ctrl_dir`.
- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wifi-tmp-ctrl-dir`.
