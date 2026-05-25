# Native Init V906 mdm_helper Runtime Contract Helper Plan

## Goal

Implement the V905-selected helper support as a source/build-only unit. V906
must not deploy or run the new mode live.

## Gate

Add a fail-closed helper mode:

```text
wifi-companion-mdm-helper-runtime-contract-capture
```

with explicit opt-in:

```text
--allow-mdm-helper-runtime-contract-capture
```

## Required Support

- `a90_android_execns_probe v148` marker.
- Default Android exec-context mappings:
  - `/vendor/bin/mdm_helper` -> `u:r:vendor_mdm_helper:s0`
  - `/vendor/bin/ks` -> `u:r:vendor_mdm_helper:s0`
- Property-service shim enabled for the new mode when `--property-root` is set.
- Runtime order model:
  - property shim;
  - `per_mgr_light` (`/vendor/bin/pm-service`);
  - `mdm_helper` (`/vendor/bin/mdm_helper`);
  - no `pm_proxy_helper`;
  - no controller `/dev/subsys_esoc0` open.
- Late private MHI node mirror if `/dev/mhi_0305_01.01.00_pipe_10` appears
  globally during the capture window.
- Observability for `/dev/esoc-0`, `/dev/subsys_esoc0`, MHI pipe, `ks`,
  GPIO142/MDM status, `mdm3`, WLFW/BDF, and `wlan0`.

## Forbidden In V906

- Helper deployment.
- Device actor start.
- Live eSoC ioctl.
- Controller subsystem open.
- Service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping.
- Reboot, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, module load/unload, Wi-Fi bring-up.

## Validation

- Build static ARM64 helper into `tmp/wifi/v906-execns-helper-v148-build/`.
- Run source/build verifier:

```bash
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_support_v906.py
```

## Next

If V906 passes, V907 should deploy helper `v148` only and verify remote
checksum/mode support. Runtime-contract live execution must remain a separate
later gate.
