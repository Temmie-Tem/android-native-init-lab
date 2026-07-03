# Native Init V3384 Server-Distro Hardware Contract Source Build

- Cycle: `V3384`
- Decision: `v3384-server-distro-stage0-hardware-contract-source-build`
- Init: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3384_server_distro_hardware_contract.img`
- Boot SHA256: `47890d04219837af3acb96ad8e281ad4eab0ea3a73ae2641e05633d014979178`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3383_server_distro_handoff_cleanup.img`

## Change

- Carries forward the V3383 D4 userdata appliance handoff cleanup surface.
- Adds a read-only `server-distro [status|hardware-contract]` command surface.
- The command prints the Stage0 hardware contract under the `A90DHW` prefix: default active surfaces, the Wi-Fi STA next rung, opt-in demo hardware, default-off hardware, tunnel ownership, and safety no-go lines.
- This is source/build only; live validation is a separate checked-helper flash gate.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: `tests.test_server_distro_hardware_contract`.
- Builder regression: `tests.test_build_native_init_boot_v3384_server_distro_hardware_contract`.
- No device action was performed in this source unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `server-distro-stage0-hardware-contract`.
