# Native Init V1786 PM Server Supported-list Population Classifier

## Summary

- Cycle: `V1786`
- Type: host-only static classifier
- Decision: `v1786-pm-supported-list-sysfs-enumeration-gap-host-pass`
- Label: `pm-supported-list-sysfs-enumeration-gap`
- Result: PASS
- Reason: pm-service only populates the supported-peripheral list from libmdmdetect get_system_info sysfs enumeration; V1784 publishes the service but the list is still empty at CNSS registration time
- Evidence: `tmp/wifi/v1786-pm-server-supported-list-population-static`

## Inputs

- pm_service: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- libperipheral_client: `tmp/wifi/v1073-host-only/vendor-extract/files/libperipheral_client.so`
- libmdmdetect: `tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so`
- v1784_manifest: `tmp/wifi/v1784-pm-server-forwarding-observer-handoff/manifest.json`
- v1784_helper: `tmp/wifi/v1784-pm-server-forwarding-observer-handoff/test-v1393-helper-result.stdout.txt`
- v1785_manifest: `tmp/wifi/v1785-pm-server-no-peripheral-classifier/manifest.json`
- v1779_manifest: `tmp/wifi/v1779-pm-service-lifetime-delta-classifier/manifest.json`

## V1784 / V1785 Baseline

- V1784 decision: `v1784-service-object-nonnull-vote-sent-no-request-rollback-pass`
- V1784 PM server label: `pm-server-no-peripheral`
- V1784 provider / asInterface / register TX: `1` / `1` / `1`
- V1784 PM server entry / loop / no-peripheral hits: `1` / `0` / `1`
- V1784 requested `wlanmdsp`: `0`
- V1785 label: `pm-server-supported-list-empty`
- V1779 Android-good shutdown-list values: `SDX50M, SDX50M modem`
- V1784 shutdown-list set requests: `0` values ``

## Static Population Model

- `pm-service` SHA256: `0ef4d72ab242e2e3d2708c6590d0b6caf0e3ec47c5b342a57d66b90dfba21bb8`
- `libperipheral_client.so` SHA256: `e92e05976d7c04c04c055f569d87c4f27feac2b1901cd5ef4c617e62a7f770e4`
- `libmdmdetect.so` SHA256: `abb807a879b0124b837c546612a42f86ff900e9df04328872ac817a602740fc1`
- main initializes supported-list sentinel at object `+0x20`: `True`
- main calls init helper `pm-service+0x6b6c` before Binder service registration: `True`
- init helper calls `get_system_info@plt` at `pm-service+0x6bc0`: `True`
- init helper loops two `get_system_info` counts before registration: `True`
- add-peripheral helper commits supported-list node at `pm-service+0x6758..0x6788`: `True`
- add-peripheral helper rejects unsupported names before insertion: `True`
- `libmdmdetect:get_system_info` scans `/sys/bus/esoc/devices` and `/sys/bus/msm_subsys/devices`: `True`
- `libmdmdetect:get_system_info` accepts internal subsystem names `modem`, `slpi`, `spss`: `['modem', 'slpi', 'spss']`
- `libmdmdetect` eSoC strings include `SDX50M` and `SDXPRAIRIE`: `['SDX50M', 'SDXPRAIRIE', 'SDX55M']`

## Static Peripheral Table

- `modem`: index `0`, file offset `0xc0b8`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`
- `slpi`: index `1`, file offset `0xc140`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX50M`: index `2`, file offset `0xc1c8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `spss`: index `3`, file offset `0xc250`, enabled `0`, kind `2`, off/ack/extra `1000`/`0`/`0`
- `SDX55M`: index `4`, file offset `0xc2d8`, enabled `1`, kind `3`, off/ack/extra `1001`/`1000`/`0`
- `SDXPRAIRIE`: index `5`, file offset `0xc360`, enabled `1`, kind `4`, off/ack/extra `1001`/`1000`/`1021`

## Interpretation

- The PM server list is not populated by the CNSS vote/register transaction itself.
- The list starts empty in the `pm-service` object constructor path and is populated only during the pre-registration init helper.
- That helper delegates discovery to `libmdmdetect.so:get_system_info`, which reads sysfs under `/sys/bus/esoc/devices` and `/sys/bus/msm_subsys/devices`.
- V1784 proves the Binder provider is visible and CNSS reaches `asInterface` plus register TX, but the server-side supported-list loop never starts.
- Therefore the next useful target is not another PM actor. It is a narrow observation or repair of the `pm-service` discovery namespace before CNSS registration.

## Next

- V1787 source/build-only: add a PM service init observer for `get_system_info` return/counts and add-peripheral insert hits before Binder registration.
- If counts are zero while provider is visible, the next repair candidate is a private read-only sysfs discovery bind/parity fix for `/sys/bus/msm_subsys/devices` and, if needed, `/sys/bus/esoc/devices` inside the vendor exec namespace.
- Do not start the full PM trio, `boot_wlan`, restart-PD, eSoC, forced RC1, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping from this classifier.

## Safety Scope

This classifier is host-only. It executed local `strings`/`objdump` against extracted vendor binaries and read prior evidence. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.
