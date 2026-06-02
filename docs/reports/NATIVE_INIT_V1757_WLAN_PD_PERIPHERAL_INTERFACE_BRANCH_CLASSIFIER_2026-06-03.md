# Native Init V1757 WLAN-PD Peripheral Interface Branch Classifier

## Summary

- Cycle: `V1757`
- Type: host/source-only `libperipheral_client.so` branch classifier
- Decision: `v1757-peripheral-manager-service-get-null-host-pass`
- Label: `peripheral-manager-service-object-null`
- Result: PASS
- Reason: Static branch at 0x620c is cbz x8 to the `%s get service fail` path; V1736 hits that check, skips asInterface, returns from pm_register_connect, and never requests wlanmdsp.mbn
- Evidence: `tmp/wifi/v1757-wlan-pd-peripheral-interface-branch-classifier`

## Static Branch Evidence

| Point | Offset | Instruction / String | Meaning |
| --- | ---: | --- | --- |
| service-manager get call | `0x61c4` | `61c4:	d63f0120 	blr	x9` | lookup `vendor.qcom.PeripheralManager` |
| returned binder load | `0x6208` | `6208:	f94013e8 	ldr	x8, [sp, #32]` | load returned binder strong pointer from stack |
| null branch | `0x620c` | `620c:	b4000488 	cbz	x8, 629c <_ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event@@Base+0x170>` | branch away from `asInterface` when returned pointer is null |
| asInterface call | `0x6218` | `6218:	94000cf6 	bl	95f0 <_ZN7android18IPeripheralManager11asInterfaceERKNS_2spINS_7IBinderEEE@plt>` | only reachable when returned pointer is non-null |
| get-service-fail log | `0x629c` | `629c:	f9400663 	ldr	x3, [x19, #8]` | null-service failure path |
| log tag | `0x4a78` | `PerMgrLib` | Android log tag |
| fail format | `0x4a82` | `%s get service fail` | branch target message |
| interface fail format | `0x4a96` | `%s get interface fail` | not reached in V1736 |
| service name | `0x4c2d` | `vendor.qcom.PeripheralManager` | requested service object |

## Retained V1736 Trace Alignment

| Event | Hit Count | Interpretation |
| --- | ---: | --- |
| `periph_service_manager_get_call` | `1` | service-manager lookup was attempted |
| `periph_binder_object_present_check` | `1` | code reached the `0x620c` returned-binder null check |
| `periph_as_interface_call` | `0` | skipped because the branch condition was true |
| `periph_manager_register_tx_call` | `0` | no PeripheralManager register transaction occurred |
| `periph_pm_register_connect_return` | `1` | function returned after failure path |
| `wlfw_service_request` | `1` | CNSS still reaches the WLFW worker/request path |
| requested `wlanmdsp.mbn` | `0` | modem still does not request WLAN-PD firmware |

## Interpretation

- V1756's broad `interface-conversion-gap` is now narrowed to a null service-object lookup.
- `libperipheral_client.so` calls service-manager lookup for `vendor.qcom.PeripheralManager`, then loads the returned binder pointer and immediately tests it at `0x620c`.
- The only path that skips `IPeripheralManager::asInterface` at `0x6218` is `cbz x8, 0x629c`, which logs `%s get service fail`.
- Because V1736 hits the check, does not hit `asInterface`, and returns, the native route has no visible `vendor.qcom.PeripheralManager` binder service object in that service-manager context.
- This does not justify adding broad PM actors. The next target is the narrow service-object registration/visibility contract for `vendor.qcom.PeripheralManager`.

## Next Candidate

- V1758 should stay host/source-only first: classify how `/vendor/bin/pm-service` registers `vendor.qcom.PeripheralManager`, which service manager/context it uses, and why prior native PM-trio attempts did not expose that object to `libperipheral_client.so`.
- A later live gate, if approved, should repair only the service-object visibility/registration condition and measure PM vote plus `wlanmdsp.mbn` request.
- Keep blocked: broad PM actor march, eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping until `wlanmdsp.mbn` request or WLFW service 69 appears.

## Safety Scope

This classifier is host/source-only. It reads retained V1756 evidence, a staged vendor library, existing disassembly, and constant strings. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.
