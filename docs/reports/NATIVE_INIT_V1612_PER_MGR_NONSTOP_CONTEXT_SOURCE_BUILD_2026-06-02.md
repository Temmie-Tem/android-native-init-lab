# Native Init V1612 per_mgr Non-stopping Context Source Build

## Summary

- Cycle: `V1612`
- Type: source/build-only rollbackable Wi-Fi test boot artifact
- Decision: `v1612-per-mgr-nonstop-context-test-boot-source-build-pass`
- Result: PASS
- Reason: built the V1604 route with helper v300 and non-stopping `per_mgr` context snapshots
- Manifest: `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/manifest.json`
- Boot image: `tmp/wifi/v1612-per-mgr-nonstop-context-test-boot/boot_linux_v1612_wifi_test.img`
- Boot SHA256: `0c2d70855faeb841d9622e4dd87df0f4b13b532abc4cf83047f2a988ec73ece8`
- Init: `A90 Linux init 0.9.108 (v1612-per-mgr-nonstop-context)`
- Init SHA256: `7f51f923b45b7d80d466669e423a897dd9613e69cc0dd493d07012989ca2a7ec`
- Helper marker: `a90_android_execns_probe v300`
- Helper SHA256: `f6915085d26e8505d4407c810e4e0cc7729e435cf42c132091d5dd8ca8826373`

## Delta From V1608/V1610

- Bumps `a90_android_execns_probe` to v300.
- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.
- Retires `--capture-mode ptrace-lite` for `/vendor/bin/pm-service`.
- Keeps the V1604 startup sampler and adds `--allow-android-wifi-service-window-per-mgr-nonstop-context-trace`.
- Captures registry/property/socket/runtime snapshots before and after the `per_mgr` startup sampler without stopping the process.

## Test-Boot Contract

- Log path: `/cache/native-init-wifi-test-boot-v1612.log`
- Summary path: `/cache/native-init-wifi-test-boot-v1612.summary`
- Helper result path: `/cache/native-init-wifi-test-boot-v1612-helper.result`
- Supervisor timeout sec: `130`
- Helper runtime mode: `wifi-companion-android-wifi-service-window-subsys-trigger-capture`
- Firmware mounts: `True`
- Android service window: `True`

## Safety Scope

This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.

## Next

V1613 should run local artifact sanity over this exact manifest. If it passes, a later rollbackable live handoff can collect the non-stopping `per_mgr` context snapshots and roll back to `stage3/boot_linux_v724.img`.
