# Native Init V906 mdm_helper Runtime Contract Helper Build Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build-only verifier | `tmp/wifi/v906-mdm-helper-runtime-contract-support/manifest.json` | `v906-mdm-helper-runtime-contract-support-pass` |

V906 adds helper `v148` support for the next bounded `mdm_helper` runtime-contract capture gate. No live actor was started in this unit.

## Implemented

- Added mode `wifi-companion-mdm-helper-runtime-contract-capture`.
- Added allow flag `--allow-mdm-helper-runtime-contract-capture`.
- Added default source mappings for `/vendor/bin/mdm_helper` and `/vendor/bin/ks` to `u:r:vendor_mdm_helper:s0`.
- Added property-service shim support for the new mode.
- Added `per_mgr_light` before `mdm_helper`, while explicitly excluding `pm_proxy_helper`.
- Added late private `/dev/mhi_0305_01.01.00_pipe_10` mirroring if the global node appears.
- Preserved hard gates: no service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or controller `/dev/subsys_esoc0` open.

## Build

- artifact: `tmp/wifi/v906-execns-helper-v148-build/a90_android_execns_probe`
- sha256: `12633b3c21292cf547393abce972bc7b1e855144dcdaea3975a45e943228cae6`
- static check: `statically linked`, `There is no dynamic section`

## Guardrails

- No device contact, helper deployment, actor start, eSoC ioctl, subsystem open, daemon start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi bring-up occurred in V906.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v906-execns-helper-v148-build/a90_android_execns_probe
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_runtime_contract_support_v906.py
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_support_v906.py
```

## Next

V907 should deploy helper `v148` only and verify remote checksum/mode support. Live runtime-contract execution should remain a separate later gate.
