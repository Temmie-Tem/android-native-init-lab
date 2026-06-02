# Native Init V1793 PM Register Request String Handoff

## Summary

- Cycle: `V1793`
- Type: one-run rollbackable WLAN-PD PM register request string discriminator
- Decision: `v1793-pm-register-request-modem-or-other-rollback-pass`
- Result: PASS
- Reason: CNSS PM register requested modem; classify request/candidate mismatch before any devnode repair
- Evidence: `tmp/wifi/v1793-pm-register-request-string-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-no-peripheral`
- PM register request label: `pm-register-request-modem-or-other`
- requested peripheral: `modem`
- register entry peripheral/client: `unreliable-entry-fetcharg` / `unreliable-entry-fetcharg`
- register strcmp candidate/requested: `` / ``
- no-peripheral requested: `modem`
- candidate name: `SDX50M`
- candidate devnode: `/dev/subsys_esoc0`
- provider seen: `1`
- asInterface hits: `1`
- register/vote TX hits: `1`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`

## PM Register Request Uprobes

- register entry hits: `1`
- register entry fetchargs: `peripheral=+0(%x1):string client=+0(%x2):string out_client=%x4 out_state=%x5`
- register entry first hit: `unreliable-entry-fetcharg`
- strcmp hits: `0`
- strcmp fetchargs: `candidate=+0(%x0):string requested=+0(%x1):string`
- strcmp first hit: `none`
- no-peripheral hits: `1`
- no-peripheral fetchargs: `peripheral=+0(%x26):string`
- no-peripheral first hit: `Binder:571_2-574   [000] ....     6.636998: pm_server_register_no_peripheral: (0x556f5d4148) peripheral="modem"`
- loop/match/success hits: `0` / `0` / `0`

## PM-service Devnode Uprobes

- entry hits: `2`
- entry fetchargs: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`
- entry first hit: `pm-service-571   [000] ....     5.327861: pm_service_add_peripheral_entry: (0x556f5d45ec) record=0x7fde217400 name="SDX50M" devnode="/dev/subsys_esoc0"`
- entry parsed name/devnode: `SDX50M` / `/dev/subsys_esoc0`
- known-name hits: `2`
- known-name fetchargs: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`
- known-name first hit: `pm-service-571   [000] ....     5.327871: pm_service_add_peripheral_known_name: (0x556f5d463c) record=0x7fde217400 name="SDX50M" devnode="/dev/subsys_esoc0"`
- known-name parsed name/devnode: `SDX50M` / `/dev/subsys_esoc0`
- init-fail hits: `2`
- init-fail fetchargs: `name=+0(%x21):string devnode=+0(%x25):string`
- init-fail first hit: `pm-service-571   [000] ....     5.328548: pm_service_add_peripheral_init_fail: (0x556f5d468c) name="SDX50M" devnode="/dev/subsys_esoc0"`
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

- Remote root: `/mnt/sdext/a90/private-property-v317/v1792/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not repair PM-service devnodes, chase WLAN-PD cascade, start Wi-Fi HAL, scan/connect, DHCP/routes, or external ping in this run.
