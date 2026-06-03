# Native Init V1857 SDX50M Bridge Artifact Plumbing

## Summary

- Cycle: `V1857`
- Type: host-only non-executing argument plumbing for the v356 SDX50M bridge skeleton
- Requested mode: `dry-run`
- Decision: `v1857-artifact-plumbing-dry-run-ready-host-pass`
- Label: `artifact-plumbing-dry-run-ready`
- Result: PASS
- Reason: Non-executing plumbing for the private SDX50M artifact and v356 test image is ready; live mode remains denied and no Wi-Fi credentials or network actions are used
- Evidence: `tmp/wifi/v1857-sdx50m-bridge-artifact-plumbing`

## Inputs

- V1220: `v1220-private-cnss-daemon-sdx50m-patch-ready` / host_only `True`
- private artifact: `tmp/wifi/v1220-cnss-daemon-sdx50m-patch/artifacts/cnss-daemon.sdx50m` exists `True` size `95112` sha `784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd`
- V1856: `v1856-bridge-v356-dry-run-ready-host-pass` / `bridge-v356-dry-run-ready` helper `a90_android_execns_probe v356`
- test image: `tmp/wifi/v1846-pm-service-open-context-test-boot/boot_linux_v1846_pm_service_open_context.img` exists `True` sha `d59877d8b162a0a3c24d764b6f6190e8a296473b58819c7d24086f7584abd411`

## Contract

- supported modes: `['dry-run']`
- plumbed arguments: `['--private-cnss-artifact', '--test-image', '--mode']`
- live/device/flash/reboot executed: `False` / `False` / `False` / `False`
- Wi-Fi/credential/network executed: `False` / `False` / `False` / `False` / `False`
- lower mutation executed: subsys_esoc0 `False`, PMIC/GPIO/GDSC `False`, eSoC ioctl/notify `False`, forced RC1/rescan `False`

## Interpretation

- V1857 adds argument-level plumbing only. It does not execute the private SDX50M artifact or flash/run the v356 image.
- The artifact and image hashes are pinned so a later reviewed unit can fail closed on drift before any device action.
- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.

## Safety Scope

Host-only. This plumbing check did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- Next candidate is a source-only preflight that validates host/device availability for a future one-run bridge gate without executing it.
