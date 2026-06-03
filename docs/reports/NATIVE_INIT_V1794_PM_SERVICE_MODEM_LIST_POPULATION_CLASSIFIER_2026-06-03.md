# Native Init V1794 PM-service Modem List Population Classifier

## Summary

- Cycle: `V1794`
- Type: host-only static/evidence classifier
- Decision: `v1794-pm-modem-primary-list-devnode-gate-host-pass`
- Label: `pm-modem-primary-list-devnode-gate`
- Result: PASS
- Reason: the missing modem record is not explained by the second count path; libmdmdetect routes modem into the primary count, and the observed primary add-peripheral attempts all fail before supported-list commit
- Evidence: `tmp/wifi/v1794-pm-service-modem-list-population-classifier`

## Inputs

- pm_service: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- libmdmdetect: `tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so`
- v1793_manifest: `tmp/wifi/v1793-pm-register-request-string-handoff/manifest.json`
- v1793_helper: `tmp/wifi/v1793-pm-register-request-string-handoff/test-v1393-helper-result.stdout.txt`
- v1789_manifest: `tmp/wifi/v1789-pm-add-peripheral-init-fail-static/manifest.json`
- v1786_manifest: `tmp/wifi/v1786-pm-server-supported-list-population-static/manifest.json`

## V1793 Baseline

- V1793 decision: `v1793-pm-register-request-modem-or-other-rollback-pass`
- V1793 rollback ok: `True`
- requested PM peripheral: `modem`
- no-peripheral branch name: `modem`
- PM server loop / strcmp / match / success hits: `0` / `0` / `0` / `0`
- first add-peripheral call/fail hits: `2` / `2`
- second add-peripheral call/fail hits: `0` / `0`
- add-peripheral entry / init-fail / list-commit hits: `2` / `2` / `0`
- first captured candidate: `SDX50M` / `/dev/subsys_esoc0`

## Static Count Model

- `pm-service` SHA256: `0ef4d72ab242e2e3d2708c6590d0b6caf0e3ec47c5b342a57d66b90dfba21bb8`
- `libmdmdetect.so` SHA256: `abb807a879b0124b837c546612a42f86ff900e9df04328872ac817a602740fc1`
- first count load: `pm-service+0x6be8`, stack field `[sp,#24]`
- first add-peripheral call: `pm-service+0x6cb4`
- second count load: `pm-service+0x6cd4`, stack field `[sp,#28]`
- second add-peripheral call: `pm-service+0x6d9c`
- first loop uses primary record base `get_system_info_output+0x8`: `True`
- second loop uses additional record base `get_system_info_output+0xe18`: `True`
- `libmdmdetect` stores `modem` into the primary count path: `True`
- `libmdmdetect` stores non-modem additional subsystems into the second count path: `True`
- `libmdmdetect` devnode format: `/dev/subsys_%s`

## Live Sysfs Inputs

- `/sys/bus/msm_subsys/devices` has `subsys0`: `True`
- `subsys0` name/state/firmware: `modem` / `ONLINE` / `modem`
- `subsys9` name/state/firmware: `esoc0` / `OFFLINING` / `esoc0`
- inferred primary candidate names: `SDX50M, modem`
- second-loop candidate source: `non-modem additional msm_subsys entries`

## Static Peripheral Table

- `modem`: index `0`, file offset `0xc0b8`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`
- `slpi`: index `1`, file offset `0xc140`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX50M`: index `2`, file offset `0xc1c8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `spss`: index `3`, file offset `0xc250`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX55M`: index `4`, file offset `0xc2d8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `SDXPRAIRIE`: index `5`, file offset `0xc360`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`

## Interpretation

- The second count/load path is not the source of the `modem` record. Static `libmdmdetect` control flow routes `name=modem` from `/sys/bus/msm_subsys/devices` into the first/primary count.
- V1793 hit the first add-peripheral call twice and hit the second add-peripheral call zero times. That shape matches primary candidates only, not a missing second-loop modem path.
- The first observed candidate was `SDX50M` at `/dev/subsys_esoc0`; the same first-loop set also includes the live `subsys0` modem record by static/sysfs reconstruction.
- Both observed add-peripheral attempts failed before `pm-service+0x6758..0x6788`, so the PM server list stayed empty and CNSS's `modem` register request took the no-peripheral branch.
- Therefore the next source/build unit should observe first/second count values and all add-peripheral hit strings before any private devnode repair.

## Next

- V1795 should stay source/build-only first: add fetchargs or direct helper logging for `[sp,#24]`, `[sp,#28]`, first-loop record names, and second-loop record names.
- Fixed outcomes should distinguish `modem-devnode-access-fail`, `sdx50m-only-first-loop`, `count-fetcharg-unavailable`, and `list-commit-progress`.
- Do not repair `/dev/subsys_esoc0`, synthesize PM records, start Wi-Fi HAL, scan/connect, configure DHCP/routes, or external ping from this classifier.

## Safety Scope

This classifier is host-only. It executed local `objdump` against extracted vendor binaries and read prior evidence. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.
