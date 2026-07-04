# Native Init V3397 WSTA Execute Gate Screen Source Build

- Cycle: `V3397`
- Decision: `v3397-wsta-execute-gate-screen-source-build`
- Init: `A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3397_wsta_execute_gate_screen.img`
- Boot SHA256: `788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3396_wsta_persistent_state_screen.img`

## Change

- Carries forward V3396 WSTA persistent-state screen validation.
- Updates the display-only WSTA screen to show the WSTA80 execute gate and WSTA58 explicit-live handoff.
- Keeps `PUBLIC_OFF`, private-run-only URL redaction, and no native public autostart.
- Does not add Wi-Fi connect, DHCP, public tunnel, native reboot, or flash behavior to the WSTA screen.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_native_wsta_operator_screenapp_source`.
- Builder regression: `tests.test_build_native_init_boot_v3397_wsta_execute_gate_screen`.
- WSTA native lineage checks include V3397 for future live gates.
- No association, DHCP, ping, public exposure, userdata, switch-root, or live display action was performed in this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `wsta-execute-gate-screen`.
