# Native Init V908 mdm_helper Runtime Contract Capture Plan

## Goal

Run the deployed helper `v148` runtime-contract capture mode once, bounded, with
the Android-derived private property layout and `per_mgr_light` ordering. V908
is still diagnostic-only; it must not start Wi-Fi bring-up.

## Gate

Execute:

```text
wifi-companion-mdm-helper-runtime-contract-capture
```

with:

- bounded selinuxfs mount/cleanup so the helper can bind `/sys/fs/selinux`
  inside its private namespace;
- private property root:
  `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__`
- property-service shim enabled by `--property-root`
- `per_mgr_light` as `/vendor/bin/pm-service`
- `mdm_helper` as `/vendor/bin/mdm_helper`
- no `pm_proxy_helper`
- no controller `/dev/subsys_esoc0` open

## Questions

V908 should answer whether adding the missing property/peripheral-manager
runtime contract changes the native `mdm_helper` surface:

- Does `mdm_helper` become observable?
- Does `mdm_helper` open `/dev/esoc-0`?
- Does `/vendor/bin/ks` or the MHI pipe appear?
- Does GPIO142/MDM/eSoC/ICNSS/WLFW/BDF/wlan0 state change?
- Are all started actors reaped cleanly, or is reboot cleanup required?

## Forbidden In V908

- Leaving selinuxfs mounted after the run.
- `pm_proxy_helper`.
- Controller `/dev/subsys_esoc0` open.
- eSoC engine registration, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`,
  `ESOC_NOTIFY`, or `BOOT_DONE`.
- Service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping.
- Boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, module load/unload, Wi-Fi link-up.

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py plan
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-runtime-contract-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

Success requires the helper mode to begin/end, remote helper parity to pass,
forbidden flags to remain false, and postflight cleanup to be healthy.

## Next

- If `ks`/MHI appears, inspect mdm3/GPIO142/WLFW/BDF/wlan0 deltas before
  service-manager or Wi-Fi HAL work.
- If `mdm_helper` is observable but still no `/dev/esoc-0`/`ks`/MHI, compare
  Android runtime inputs beyond property/per_mgr ordering.
- If the runtime setup fails before `mdm_helper`, repair the property shim or
  `per_mgr_light` contract before retrying.
