# Native Init V3400 D-public HUD Presenter Service Dedupe Source Build

- Cycle: `V3400`
- Decision: `v3400-dpublic-hud-presenter-service-dedupe-source-build`
- Init: `A90 Linux init 0.11.156 (v3400-dpublic-hud-presenter-service-dedupe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3400_dpublic_hud_presenter_service_dedupe.img`
- Boot SHA256: `4bc7a216b4a370bae9c5d561e022d57cc2cfcfc42e0a50152ed5bd7d5a45e260`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3399_dpublic_hud_presenter_service.img`

## Change

- Keeps the durable native HUD presenter service from V3399.
- Suppresses repeated poll logs for unchanged consumed intent content.
- Suppresses repeated poll logs for unchanged rejected intent content.
- Preserves fail-closed rejection for new stale, forbidden, unknown, or invalid intent content.
- Adds live-visible marker `A90WSTA142 status.intent_dedupe=same-content-consumed-or-rejected`.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: WSTA142 source/build tests.
- No association, DHCP, ping, public exposure, userdata mutation, switch-root, or live display action was performed by this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `dpublic-hud-presenter-service-dedupe`.
