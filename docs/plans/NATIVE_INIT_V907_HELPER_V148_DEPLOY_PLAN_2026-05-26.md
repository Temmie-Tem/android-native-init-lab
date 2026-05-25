# Native Init V907 Helper v148 Deploy Plan

## Goal

Deploy the V906-built `a90_android_execns_probe v148` helper to the native init
device and prove remote checksum/mode parity. V907 is deploy-only; it must not
run the new runtime-contract actor.

## Gate

Install and verify:

```text
/cache/bin/a90_android_execns_probe
```

expected SHA-256:

```text
12633b3c21292cf547393abce972bc7b1e855144dcdaea3975a45e943228cae6
```

required marker/mode:

```text
a90_android_execns_probe v148
wifi-companion-mdm-helper-runtime-contract-capture
```

## Current Transport Choice

NCM is currently disabled on the device, so V907 uses the serial deploy path
explicitly. This is slower than NCM/HTTP but keeps the deploy-only unit narrow
and avoids starting netservice as part of the helper deploy gate.

## Forbidden In V907

- Runtime-contract actor start.
- `mdm_helper`, `ks`, `pm-service`, or `pm_proxy_helper` start.
- Live eSoC ioctl or controller `/dev/subsys_esoc0` open.
- Service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping.
- Reboot, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, module load/unload, Wi-Fi bring-up.

## Validation

Run preflight and approved deploy wrapper:

```bash
python3 scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v907 deploy execns helper v148 only; no actor start, no daemon start and no Wi-Fi bring-up" \
  run
```

Success requires:

- native `status`/`selftest` are clean;
- service-manager process surface is clean;
- Wi-Fi link surface is clean;
- remote helper SHA matches the V906 build artifact;
- helper usage exposes the `v148` marker and runtime-contract capture mode.

## Next

If V907 passes, V908 should run the bounded runtime-contract capture mode with
property shim and `per_mgr_light` ordering. V908 remains a diagnostic actor
gate, not a Wi-Fi scan/connect gate.
