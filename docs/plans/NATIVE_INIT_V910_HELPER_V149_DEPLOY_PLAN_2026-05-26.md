# Native Init V910 Helper v149 Deploy Plan

## Goal

Deploy the V909-built `a90_android_execns_probe v149` helper and prove remote
checksum/mode parity. V910 is deploy-only; it must not run the runtime-contract
actor.

## Gate

Install and verify `/cache/bin/a90_android_execns_probe`.

Expected SHA-256:

```text
b615aa127e130e8b285642b34992102fa6d0c15702479bc1265dd4c5f06dff49
```

Expected marker/mode:

```text
a90_android_execns_probe v149
wifi-companion-mdm-helper-runtime-contract-capture
```

## Forbidden In V910

- Runtime-contract actor start.
- `mdm_helper`, `ks`, `pm-service`, or `pm_proxy_helper` start.
- Live eSoC ioctl or controller `/dev/subsys_esoc0` open.
- Service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping.
- Reboot, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, module load/unload, Wi-Fi bring-up.

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v149_deploy_preflight.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v910 deploy execns helper v149 only; no actor start, no daemon start and no Wi-Fi bring-up" \
  run
```

## Next

After V910 passes, rerun the bounded runtime-contract capture with helper
`v149` so the `/dev/esoc-0` fd boundary includes fdinfo and stall snapshots.
