# Native Init V1731 WLAN-PD Service-notifier Late Listener Handoff

## Summary

- Cycle: `V1731`
- Type: one-run rollbackable WLAN-PD service-notifier late listener gate
- Decision: `v1731-late-listener-uninit-no-indication-rollback-pass`
- Result: PASS
- Reason: late listener response was success/uninit and no state indication arrived; rollback verified
- Evidence: `tmp/wifi/v1731-wlan-pd-servnotif-late-listener-handoff`
- Rollback attempt: `from-native`

## Gate Label

- late listener label: `late-listener-uninit-no-indication`
- late listener result: `listener-response-success`
- late listener endpoint found: `1`
- late listener endpoint node: `0`
- late listener endpoint port: `2`
- late listener response seen: `1`
- late listener response success: `1`
- late listener response state: `0x7fffffff` / `uninit`
- late listener indication seen: `0`
- late listener indication state: `0x00000000` / `unknown`
- late listener hold ms: `15015`
- late endpoint result: `endpoint-found`
- early listener result: `no-endpoint`
- nonlog label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- service-window label: `wlfw-start-reached`
- service-locator domain result: `domain-list-response-success`
- service-locator domain name: `msm/modem/wlan_pd`
- service_manager: `1`
- cnss-daemon running: `1`
- tftp running: `1`
- WLFW service 69 seen: `0`
- requested `wlanmdsp`: `0`

## Uprobe Fields

- tracefs available: `1` (`errno=0`)
- wlfw_start hits: `1`
- wlfw_service_request hits: `1`
- wlfw worker create success hits: `1`
- wlfw indication-register QMI hits: `0`
- wlfw capability QMI hits: `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1730/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- `late-listener-uninit-no-indication` means the service-notifier endpoint is reachable but WLAN-PD still stays UNINIT in the bounded listener window.
- `late-listener-no-response` means endpoint discovery is not enough; listener register does not get a QMI response in this namespace/window.
- Any late indication label means the next gate can move from service-notifier timing to WLFW service 69 / ICNSS QMI readiness.
