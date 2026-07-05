# Native Init V3401 D-public HUD Shared Run Bind Source Build

- Cycle: `V3401`
- Decision: `v3401-dpublic-hud-shared-run-bind-source-build`
- Init: `A90 Linux init 0.11.157 (v3401-dpublic-hud-shared-run-bind)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3401_dpublic_hud_shared_run_bind.img`
- Boot SHA256: `d9496d565af554f4fb30a9064c1998356b27396163b7cc67fd693db8a3a8e418`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3400_dpublic_hud_presenter_service_dedupe.img`

## Change

- Keeps the durable native HUD presenter service and stale-intent dedupe from V3400.
- Mounts `/run/a90-dpublic` as a small tmpfs owned `root:a90hud` mode `1770`.
- Binds that same run directory into the userdata Debian root before `switch_root`.
- Fails closed before handoff if the shared run-dir bind cannot be established.
- Adds live-visible marker `A90WSTA144 shared_run_dir=shared-run-dir-bind-before-switch-root`.

## Validation

- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.
- Static source checks: WSTA144 source/build tests.
- No association, DHCP, ping, public exposure, userdata format/populate, switch-root, or live display action was performed by this source build.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `dpublic-hud-shared-run-bind`.
