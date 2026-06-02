# Native Init V1789 PM Add-peripheral Init-fail Classifier

## Summary

- Cycle: `V1789`
- Type: host-only static classifier
- Decision: `v1789-pm-add-peripheral-devnode-access-gap-host-pass`
- Label: `pm-add-peripheral-devnode-access-gap`
- Result: PASS
- Reason: V1788 passed known-name validation, but every add-peripheral object failed before list commit because pm-service checks access(F_OK) on the libmdmdetect devnode field at record+0x44
- Evidence: `tmp/wifi/v1789-pm-add-peripheral-init-fail-static`

## Inputs

- pm_service: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- libmdmdetect: `tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so`
- v1788_manifest: `tmp/wifi/v1788-pm-service-init-discovery-handoff/manifest.json`
- v1788_helper: `tmp/wifi/v1788-pm-service-init-discovery-handoff/test-v1393-helper-result.stdout.txt`

## V1788 Baseline

- V1788 decision: `v1788-pm-service-discovery-zero-list-commit-rollback-pass`
- V1788 rollback ok: `True`
- PM-service discovery label: `pm-service-discovery-zero-list-commit`
- get_system_info call / fail hits: `1` / `0`
- first add-peripheral call / fail-log hits: `2` / `2`
- second add-peripheral call / fail-log hits: `0` / `0`
- add-peripheral entry / known-name / init-fail / list-commit hits: `2` / `2` / `2` / `0`
- PM server label: `pm-server-no-peripheral`
- register TX / requested wlanmdsp / WLFW 69 / wlan0: `1` / `0` / `0` / `0`

## Static Add-peripheral Branch

- `pm-service` SHA256: `0ef4d72ab242e2e3d2708c6590d0b6caf0e3ec47c5b342a57d66b90dfba21bb8`
- `libmdmdetect.so` SHA256: `abb807a879b0124b837c546612a42f86ff900e9df04328872ac817a602740fc1`
- add-peripheral entry: `pm-service+0x65ec`
- known-name validation checkpoint: `pm-service+0x663c`
- object constructor: `pm-service+0x8d60`
- init/access check: `pm-service+0x8eb0`
- init-fail log branch: `pm-service+0x668c`
- supported-list commit: `pm-service+0x6758..0x6788`
- init-fail log string: `Failed to add/init structure for %s`
- device-file access-fail string: `%s can not access device file %s: %s`
- add-peripheral calls `access(F_OK)` on constructor path: `True`
- `libmdmdetect` record devnode offset: `0x44`
- `libmdmdetect` devnode format: `/dev/subsys_%s`

## Static Peripheral Table

- `modem`: index `0`, file offset `0xc0b8`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`
- `slpi`: index `1`, file offset `0xc140`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX50M`: index `2`, file offset `0xc1c8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `spss`: index `3`, file offset `0xc250`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX55M`: index `4`, file offset `0xc2d8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `SDXPRAIRIE`: index `5`, file offset `0xc360`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`

## Interpretation

- V1788 is no longer a service-object or CNSS client TX problem: the provider is visible and CNSS reaches register/vote TX.
- V1788 also is not a candidate-name mismatch: add-peripheral reaches the known-name checkpoint twice.
- Both attempted candidates fail inside the Peripheral object init path before the supported-list node is committed.
- Static control flow shows that path calls `access(<record+0x44 devnode>, F_OK)` and logs `%s can not access device file %s: %s` on failure.
- `libmdmdetect` fills record `+0x44` as `/dev/subsys_<discovered-entry>`, so the current blocker is private devnode discovery/parity for the discovered PM-service candidates.
- V1788's second/internal subsystem add-peripheral path did not run; the immediate observed failures are first-loop discovery candidates, not the later CNSS register traversal.

## Next

- V1790 should remain source/build-only first: add a bounded PM-service discovery argument/string observer or private namespace preflight that records the exact candidate names and devnode strings before any repair.
- A future live repair must be separately scoped and must not blindly open `/dev/subsys_esoc0` or restart eSoC/RC1. The current evidence justifies classifying devnode path parity, not executing power paths.
- Keep hard stops: no `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, or platform bind/unbind.

## Safety Scope

This classifier is host-only. It executed local `objdump`, `strings`-equivalent byte reads, and manifest parsing. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.
