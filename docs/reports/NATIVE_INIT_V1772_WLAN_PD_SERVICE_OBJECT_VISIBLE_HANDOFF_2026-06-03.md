# Native Init V1772 WLAN-PD Service-object Visible Handoff

## Summary

- Cycle: `V1772`
- Type: one-run rollbackable WLAN-PD service-object visible discriminator
- Decision: `v1772-service-object-still-null-rollback-pass`
- Result: PASS
- Reason: service-object visibility did not make cnss-daemon reach asInterface/register; stop for route/helper fix
- Evidence: `tmp/wifi/v1772-wlan-pd-service-object-visible-handoff`
- Rollback attempt: `from-native`

## Gate Label

- helper label: `provider-not-visible`
- provider seen: `0`
- asInterface hits: `0`
- register/vote TX hits: `0`
- success path hits: `0`
- null branch hits: `0`
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
- WLFW start hits: `0`
- WLFW service request hits: `0`
- WLFW worker create success hits: `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1771/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not autonomously chain into PM survival or WLAN cascade gates.
