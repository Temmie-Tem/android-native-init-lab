# Native Init V1791 PM-service Devnode String Handoff

## Summary

- Cycle: `V1791`
- Type: one-run rollbackable WLAN-PD PM-service devnode string discriminator
- Decision: `v1791-pm-devnode-missing-esoc-or-other-rollback-pass`
- Result: PASS
- Reason: PM-service rejects discovered candidate SDX50M at /dev/subsys_esoc0; classify before any live devnode repair
- Evidence: `tmp/wifi/v1791-pm-service-devnode-string-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-no-peripheral`
- PM-service devnode label: `pm-devnode-missing-esoc-or-other`
- candidate name: `SDX50M`
- candidate devnode: `/dev/subsys_esoc0`
- provider seen: `1`
- asInterface hits: `1`
- register/vote TX hits: `1`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`

## PM-service Devnode Uprobes

- entry hits: `2`
- entry fetchargs: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`
- entry first hit: `pm-service-573   [002] ....     5.356458: pm_service_add_peripheral_entry: (0x5557f0a5ec) record=0x7fdb94aea0 name="SDX50M" devnode="/dev/subsys_esoc0"`
- entry parsed name/devnode: `SDX50M` / `/dev/subsys_esoc0`
- known-name hits: `2`
- known-name fetchargs: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`
- known-name first hit: `pm-service-573   [002] ....     5.356467: pm_service_add_peripheral_known_name: (0x5557f0a63c) record=0x7fdb94aea0 name="SDX50M" devnode="/dev/subsys_esoc0"`
- known-name parsed name/devnode: `SDX50M` / `/dev/subsys_esoc0`
- init-fail hits: `2`
- init-fail fetchargs: `name=+0(%x21):string devnode=+0(%x25):string`
- init-fail first hit: `pm-service-573   [002] ....     5.357156: pm_service_add_peripheral_init_fail: (0x5557f0a68c) name="SDX50M" devnode="/dev/subsys_esoc0"`
- init-fail parsed name/devnode: `SDX50M` / `/dev/subsys_esoc0`
- list commit hits: `0`

## PM-service Init-discovery Uprobes

- get_system_info call/fail hits: `1` / `0`
- first add-peripheral call/fail hits: `2` / `2`
- second add-peripheral call/fail hits: `0` / `0`
- pre-Binder init-done hits: `1`

## Route Health

- policy-load result: `policy-load-pass`
- `pm_proxy_helper` ready: `1`
- `pm-service` ready: `1`
- `pm-service` state/zombie: `S` / `0`
- `tftp_server` running: `1`
- `cnss-daemon` running: `1`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1790/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not repair PM-service devnodes, chase WLAN-PD cascade, start Wi-Fi HAL, scan/connect, DHCP/routes, or external ping in this run.
