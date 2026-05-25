# Native Init V863 pm_proxy_helper.rc Capture Plan

## Goal

Capture and classify `/vendor/etc/init/pm_proxy_helper.rc` read-only before
modelling or starting `vendor.per_proxy_helper`.

## Rationale

V862 found that Android starts `vendor.per_proxy_helper` during `post-fs-data`,
but V210 had only listed `pm_proxy_helper.rc`; its content was not captured in
the target init rc evidence. Modelling this service blindly would repeat the
direct-exec mismatch exposed by V861.

## Scope

1. Read the current `/sys/class/block/sda29/dev` major/minor dynamically.
2. Create a temporary block node under `/tmp/a90-v863-*`.
3. Mount that node as ext4 `ro,noload` under the same temporary directory.
4. Capture only `vendor/etc/init/pm_proxy_helper.rc`.
5. Unmount and remove the temporary node/path.
6. Record post-cleanup mounts and selftest.

## Hard Gates

- No daemon, `mdm_helper`, `ks`, Wi-Fi HAL, supplicant, or hostapd start.
- No scan/connect/link-up, credential use, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO write, sysfs/debugfs/subsystem write, module load,
  boot image write, or partition write.
- No hardcoded `sda29` minor number; use current sysfs major/minor.

## Success Criteria

- `pm_proxy_helper.rc` is captured read-only.
- `vendor.per_proxy_helper` service fields are parsed.
- Temporary vendor mount cleanup is proven by post-cleanup `/proc/mounts`.
- Device selftest passes after cleanup.

