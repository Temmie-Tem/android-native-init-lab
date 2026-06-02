# Native Init V1717 CNSS pm_client_register Static Classifier

## Summary

- Cycle: `V1717`
- Type: host-only static classifier for the V1716 `pm-init-register-call-no-return` blocker
- Decision: `v1717-cnss-pm-client-register-static-pass`
- Result: PASS
- Reason: `pm_client_register` is a `libperipheral_client.so` Binder client path for `vendor.qcom.PeripheralManager` over `/dev/vndbinder`
- Evidence: `tmp/wifi/v1717-cnss-pm-client-register-static`

## Inputs

- `cnss-daemon`: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- `cnss-daemon` SHA256: `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc`
- `libperipheral_client.so`: `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so`
- `libperipheral_client.so` SHA256: `e92e05976d7c04c04c055f569d87c4f27feac2b1901cd5ef4c617e62a7f770e4`

## Symbol Ownership

- `cnss-daemon` imports `pm_client_register`: `84: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_register`
- `cnss-daemon` imports `pm_client_connect`: `81: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_connect`
- `cnss-daemon` imports `get_system_info`: `80: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND get_system_info`
- `libperipheral_client.so` exports `pm_client_register`: `142: 0000000000006ec8   756 FUNC    GLOBAL DEFAULT   14 pm_client_register`
- `libperipheral_client.so` exports `pm_client_connect`: `168: 0000000000007544   216 FUNC    GLOBAL DEFAULT   14 pm_client_connect`
- `libperipheral_client.so` exports `pm_register_connect`: `109: 000000000000612c  1492 FUNC    GLOBAL DEFAULT   14 _ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event`

## Binder Contract

- `/dev/vndbinder` string present: `True`
- `vendor.qcom.PeripheralManager` string present: `True`
- `Failed to get binder object` string present: `True`
- `Failed to get binder interface object` string present: `True`
- `Peripheral manager server alive` string present: `True`

## Static Flow

- `pm_client_register@0x6ec8` validates inputs, allocates a `PeripheralManagerClient`, creates the Binder callback object, then calls internal `pm_register_connect@0x612c` from `0x7034`.
- `pm_register_connect@0x612c` calls `ProcessState::initWithDriver('/dev/vndbinder')` at `0x6168`.
- It calls `defaultServiceManager()` at `0x6190` and constructs `String16('vendor.qcom.PeripheralManager')` at `0x61a8`.
- It then performs the service-manager virtual call at `0x61c4`; this is the first likely blocking point when the vendor Binder service-manager path is unavailable.
- If a Binder object is returned, it calls `IPeripheralManager::asInterface` at `0x6218`, then the manager register transaction at `0x6274`.
- V1716 hit `pm_client_register@0xc624` from `cnss-daemon` and did not hit the caller return check at `0xc628`; therefore the live block is inside this library path before `pm_client_connect`.

## V1718 Candidate Trace Points

- Target binary: `libperipheral_client.so`, not `cnss-daemon`.
- `pm_client_register_entry`: `0x6ec8`.
- `pm_register_connect_entry`: `0x612c`.
- `process_state_init_with_driver_call`: `0x6168`.
- `default_service_manager_call`: `0x6190`.
- `peripheral_manager_string16_call`: `0x61a8`.
- `service_manager_get_call`: `0x61c4`.
- `binder_object_present_check`: `0x620c`.
- `as_interface_call`: `0x6218`.
- `manager_register_transaction_call`: `0x6274`.
- `manager_register_transaction_retcheck`: `0x6278`.
- `success_list_insert_path`: `0x6538`.
- `pm_register_connect_return`: `0x66dc`.
- `pm_client_register_return_path`: `0x7180`.

## Interpretation

- The V1716 blocker is now a vendor Binder PeripheralManager registration path, not `get_system_info`, firmware serving, MHI, WLFW service 69, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.
- This does not justify adding service-manager or PM actors yet. First trace the `libperipheral_client.so` path with one bounded non-mutating uprobe run.
- If the next live trace blocks at `defaultServiceManager` or service lookup, the missing dependency is vendor Binder service-manager availability.
- If it reaches the manager register transaction and blocks there, the missing dependency is the actual `vendor.qcom.PeripheralManager` service endpoint.

## Safety Scope

This script performed host-side static analysis only. It did not contact the device, flash, reboot, run service-manager/PM actors, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
