# Native Init V1776 Service-object Property-contract Handoff

## Summary

- Cycle: `V1776`
- Type: one-run rollbackable WLAN-PD service-object property-contract discriminator
- Decision: `v1776-property-contract-not-materialized-rollback-pass`
- Result: PASS
- Reason: V1775 booted and rolled back, but the PM shutdown-critical-list values did not materialize in helper output
- Evidence: `tmp/wifi/v1776-service-object-property-contract-handoff`
- Rollback attempt: `from-native`

## Property Contract

- Property contract flag: `1`
- Shutdown-list allow flag: `1`
- Shutdown-list values: ``

Interpretation: the repaired V1775 route did enable the property-contract flags,
but it still did not surface the actual
`vendor.peripheral.shutdown_critical_list` values. The provider therefore
remained hidden and this is a route/helper-materialization result, not a modem
or WLAN-PD response result.

## Gate Label

- helper label: `provider-not-visible`
- provider seen: `0`
- asInterface hits: `0`
- register/vote TX hits: `0`
- success path hits: `0`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`
- late listener state: `None`
- late listener indication seen: `None`

## Route Health

- `pm_proxy_helper` ready: `1`
- `pm-service` ready: `1`
- `tftp_server` running: `1`
- `cnss-daemon` running: `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1775/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not autonomously chain into PM forwarding, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.
