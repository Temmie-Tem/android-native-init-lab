# Native Init V1788 PM-service Init-discovery Handoff

## Summary

- Cycle: `V1788`
- Type: one-run rollbackable WLAN-PD PM-service init-discovery discriminator
- Decision: `v1788-pm-service-discovery-zero-list-commit-rollback-pass`
- Result: PASS
- Reason: PM-service init reached get_system_info but no supported-list insertion was observed; stop for private sysfs discovery parity
- Evidence: `tmp/wifi/v1788-pm-service-init-discovery-handoff`
- Rollback attempt: `from-native`

## Gate Label

- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-no-peripheral`
- PM-service discovery label: `pm-service-discovery-zero-list-commit`
- provider seen: `1`
- asInterface hits: `1`
- register/vote TX hits: `1`
- client success path hits: `0`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`
- late listener state: `uninit`

## PM-service Init-discovery Uprobes

- list init hits: `1`
- init helper entry hits: `1`
- get_system_info call hits: `1`
- get_system_info fail hits: `0`
- first count/load hits: `1`
- first add-peripheral call/fail hits: `2` / `2`
- second count/load hits: `1`
- second add-peripheral call/fail hits: `0` / `0`
- add-peripheral entry hits: `2`
- known-name hits: `2`
- add-peripheral init-fail hits: `2`
- list commit hits: `0`
- pre-Binder init-done hits: `1`

## PM Server Register Uprobes

- attempted/registered/enabled: `1` / `1` / `1`
- target: `/tmp/a90-v231-546/root/vendor/bin/pm-service` (index `0`)
- register entry hits: `1`
- loop/match hits: loop=`0`, strcmp=`0`, match=`0`
- permission/add-client/success hits: `0` / `0` / `0`
- no-peripheral hits: `1`

## Route Health

- policy-load result: `policy-load-pass`
- `pm_proxy_helper` ready: `1`
- `pm-service` ready: `1`
- `pm-service` state/zombie: `S` / `0`
- `tftp_server` running: `1`
- `cnss-daemon` running: `1`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1787/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not autonomously chain into sysfs repair, functional PM forwarding repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.
