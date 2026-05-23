# Native Init V685 PeripheralManager Provider Plan

## Objective

V685 follows V684 by proving the provider side of
`vendor.qcom.PeripheralManager`.

V684 showed that native `cnss-daemon` maps `libperipheral_client.so` and hits a
vendor Binder `-22` before WLFW. V685 identifies the Android provider contract
for that client and checks whether current native init already materializes or
runs it.

## Inputs

- `tmp/wifi/v684-cnss-daemon-vndbinder-target/manifest.json`
- `tmp/wifi/v210-vendor-asset-classifier/native/commands/cat-etc-init-hw-init.target.rc.txt`
- `tmp/wifi/v209-vendor-ro-mount-probe/native/commands/mounted-find-shallow.txt`
- `stage3/linux_init/helpers/a90_android_execns_probe.c`
- optional current device read-only captures through the serial bridge

## External References

- Android `device/huawei/angler` sepolicy change records
  `vendor.qcom.PeripheralManager` and `pm-service` as the peripheral manager
  provider surface:
  `https://android.googlesource.com/device/huawei/angler/+/44b4be09a24ef3f1a920043b465ed07f701919e2`
- Android `device/lge/bullhead` sepolicy labels `/system/bin/pm-service` and
  `/system/bin/pm-proxy` as `per_mgr_exec`:
  `https://android.googlesource.com/device/lge/bullhead/+/c15ba1c^!/`
- Android `device/google/marlin` vendor sepolicy has
  `vendor.qcom.PeripheralManager` in `vndservice_contexts`:
  `https://android.googlesource.com/device/google/marlin/+/9fa458369707a6bbc34eb8caedb5ba46ed41de25^2..9fa458369707a6bbc34eb8caedb5ba46ed41de25`

## Method

Run the host+read-only live classifier:

```sh
python3 scripts/revalidation/native_wifi_peripheral_manager_provider_v685.py \
  --out-dir tmp/wifi/v685-peripheral-manager-provider-live-verify \
  --apply \
  run
```

The classifier:

1. verifies V684 passed;
2. parses A90 vendor init for `vendor.per_mgr` and `vendor.per_proxy`;
3. confirms previous mounted-vendor evidence saw `pm-service`/`pm-proxy`;
4. checks the current helper source lacks provider start support;
5. captures current native global namespace read-only for
   `pm-service`, `pm-proxy`, `/dev/vndbinder`, init rc visibility, and process
   state;
6. classifies whether current native boot already materializes/runs the provider
   or whether helper private namespace support is needed.

## Success Criteria

- V684 target candidate is passing;
- A90 vendor init defines:
  - `service vendor.per_mgr /vendor/bin/pm-service`;
  - `service vendor.per_proxy /vendor/bin/pm-proxy`;
  - `vendor.per_proxy` starts after `init.svc.vendor.per_mgr=running`;
- previous mounted-vendor evidence contains both provider binaries;
- current helper source has no `pm-service`/PeripheralManager mode;
- live read-only capture proves current native global namespace does not already
  run `pm-service` or `pm-proxy`;
- no daemon, service-manager, Wi-Fi HAL, scan/connect, DHCP, route, external
  ping, sysfs/debugfs write, boot image write, or partition write occurs.

## Next Gate

If V685 passes, V686 should add helper support for a bounded
`vendor.per_mgr`/`vendor.per_proxy` start-only proof inside the private Android
namespace. Only after provider availability is proven should a fresh
`cnss-daemon` retry be attempted. Wi-Fi HAL, scan/connect, DHCP, routes, and
external ping remain blocked.
