# Native Init V1801 PM-service Devnode Projection Handoff

## Summary

- Cycle: `V1801`
- Type: one-run rollbackable WLAN-PD PM-service private-dev projection discriminator
- Decision: `v1801-list-commit-progress-rollback-pass`
- Result: PASS
- Reason: PM-service reached supported-list commit after private-dev projection
- Evidence: `tmp/wifi/v1801-pm-service-devnode-projection-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- PM-service projection label: `list-commit-progress`
- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-register-success-return`
- safety ok: `True`

## Early Private Nodes

- sdx50m exists/char: `1` / `1`
- sdx50m major:minor mode uid:gid: `236:9` `0640` `1000:1000`
- sdx50m path/error: `/tmp/a90-v231-546/root/dev/subsys_esoc0` / ``
- modem exists/char: `1` / `1`
- modem major:minor mode uid:gid: `236:0` `0640` `1000:1000`
- modem path/error: `/tmp/a90-v231-546/root/dev/subsys_modem` / ``
- expected flags: sdx50m `True`, modem `True`

## Final No-open Devnode Status

- sdx50m name/path: `subsys_esoc0` / `/tmp/a90-v231-546/root/dev/subsys_esoc0`
- sdx50m access/lstat: `1` errno `0` / `1` errno `0`
- sdx50m char major:minor mode uid:gid: `1` `236:9` `0640` `1000:1000`
- modem name/path: `subsys_modem` / `/tmp/a90-v231-546/root/dev/subsys_modem`
- modem access/lstat: `0` errno `2` / `0` errno `2`
- modem char major:minor mode uid:gid: `0` `0:0` `0000` `-1:-1`

## PM-service Correlation

- first/second count: `2` / `0`
- first add names/devnodes: `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem`
- entry/init-fail/list-commit hits: `2` / `0` / `2`
- init-fail names/devnodes: `` / ``
- register no-peripheral requested: ``
- loop/match/success/no-peripheral hits: `2` / `1` / `1` / `0`

## Route Health

- provider seen: `1`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`
- `pm_proxy_helper` ready: `1`
- `pm-service` ready: `1`
- `tftp_server` running: `1`
- `cnss-daemon` running: `1`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1800/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The route projected private char nodes but did not open `/dev/subsys_esoc0` and did not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
- Forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, and `boot_wlan` were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; choose the next source/build-only step from the projection result.
