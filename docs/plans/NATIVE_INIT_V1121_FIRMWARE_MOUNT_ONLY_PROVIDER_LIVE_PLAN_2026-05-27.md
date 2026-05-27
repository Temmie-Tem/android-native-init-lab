# Native Init V1121 Firmware Mount-only Provider Live Plan

Date: `2026-05-27`

## Goal

Repair the V1120 provider lookup blocker by testing the smallest lower-state
change that does not pre-open `/dev/subsys_modem`: global firmware mounts only.

## Context

V1120 proved that `cnss-daemon` reaches `pm_register_connect()`, but
`getService("vendor.qcom.PeripheralManager")` returns null while the global
`/dev/subsys_modem` holder is active.

The comparison point is V1108:

- no global firmware holder,
- `vendor.qcom.PeripheralManager` visible,
- `per_proxy` skipped before CNSS,
- `pm_client_register_ret=['0x0']`,
- `pm_client_connect_ret=['0x0']`.

V1121 keeps the V1108 provider-positive/no-pre-CNSS-`per_proxy` order and adds
only the firmware mounts:

- `/vendor/firmware_mnt`
- `/vendor/firmware-modem`

It does not open a global `/dev/subsys_modem` holder.

## Live Command

```bash
python3 scripts/revalidation/native_wifi_firmware_mount_only_provider_live_v1121.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

## Success Criteria

- Firmware mounts are established.
- `vendor.qcom.PeripheralManager` is visible before CNSS PM register.
- `per_proxy_start_executed=0`.
- `child.per_proxy.start_skipped=1`.
- CNSS PM register/connect reach a classified return.
- Cleanup reboot returns to healthy native init.

## Safety

- No global `/dev/subsys_modem` holder.
- No `/dev/subsys_esoc0` open.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No DHCP, route, credentials, or external ping.
- No partition write or flash.
