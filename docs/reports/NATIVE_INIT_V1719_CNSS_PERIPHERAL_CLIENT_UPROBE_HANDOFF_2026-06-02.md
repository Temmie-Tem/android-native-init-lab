# Native Init V1719 CNSS Peripheral Client Uprobe Handoff

## Summary

- Cycle: `V1719`
- Type: one-run rollbackable CNSS `libperipheral_client.so` tracefs uprobe classifier
- Decision: `v1719-peripheral-default-service-manager-call-no-return-rollback-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1719-cnss-peripheral-client-uprobe-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- output label: `cnss-output-still-invisible`
- non-log label: `peripheral-default-service-manager-call-no-return`
- legacy firmware-serve label: `firmware-not-requested`
- peripheral target: `/tmp/a90-v231-547/root/vendor/lib64/libperipheral_client.so`
- peripheral hit count: `4`
- peripheral first hit: `cnss-daemon-561   [002] ....     3.629173: periph_pm_client_register_entry: (0x7fb8428ec8)`
- cnss-daemon running: `1`

## Peripheral Trace Targets

- `periph_pm_client_register_entry` offset `0x6ec8` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.629173: periph_pm_client_register_entry: (0x7fb8428ec8)`
- `periph_pm_register_connect_entry` offset `0x612c` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.629214: periph_pm_register_connect_entry: (0x7fb842812c)`
- `periph_vndbinder_init_call` offset `0x6168` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.629219: periph_vndbinder_init_call: (0x7fb8428168)`
- `periph_default_service_manager_call` offset `0x6190` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.629348: periph_default_service_manager_call: (0x7fb8428190)`
- `periph_manager_name_string16_call` offset `0x61a8` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_service_manager_get_call` offset `0x61c4` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_binder_object_present_check` offset `0x620c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_as_interface_call` offset `0x6218` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_manager_register_tx_call` offset `0x6274` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_manager_register_tx_retcheck` offset `0x6278` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_success_path` offset `0x6538` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_pm_register_connect_return` offset `0x66dc` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `periph_pm_client_register_common_return` offset `0x7184` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This classifier distinguishes `/dev/vndbinder` initialization, default service-manager lookup, `vendor.qcom.PeripheralManager` service lookup, and the manager register transaction.
- It still does not add service-manager or PM actors.
- The live result reaches `ProcessState::initWithDriver('/dev/vndbinder')` and `defaultServiceManager()`.
- It does not reach `String16('vendor.qcom.PeripheralManager')` or the service-manager get call.
- Therefore the current blocker is default vendor service-manager acquisition, before looking up the concrete `vendor.qcom.PeripheralManager` service.
