# Native Init V1799 PM-service Devnode Access Handoff

## Summary

- Cycle: `V1799`
- Type: one-run rollbackable WLAN-PD PM-service devnode access discriminator
- Decision: `v1799-both-devnodes-absent-rollback-pass`
- Result: PASS
- Reason: both PM-service candidate devnodes are absent from the private Android dev tree
- Evidence: `tmp/wifi/v1799-pm-service-devnode-access-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- PM-service devnode access label: `both-devnodes-absent`
- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-no-peripheral`
- devnode observer source: `private-android-root`
- observer open/mknod attempted: `0` / `0`
- safety ok: `True`

## Devnode Status

- sdx50m name/path: `subsys_esoc0` / `/tmp/a90-v231-549/root/dev/subsys_esoc0`
- sdx50m access/lstat: `0` errno `2` / `0` errno `2`
- sdx50m char major:minor mode uid:gid: `0` `0:0` `0000` `-1:-1`
- modem name/path: `subsys_modem` / `/tmp/a90-v231-549/root/dev/subsys_modem`
- modem access/lstat: `0` errno `2` / `0` errno `2`
- modem char major:minor mode uid:gid: `0` `0:0` `0000` `-1:-1`
- present flags: sdx50m `False`, modem `False`
- absent flags: sdx50m `True`, modem `True`
- mismatch flags: sdx50m `False`, modem `False`

## PM-service Correlation

- first/second count: `2` / `0`
- first add names/devnodes: `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem`
- entry/init-fail/list-commit hits: `2` / `2` / `0`
- init-fail names/devnodes: `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem`
- register no-peripheral requested: `modem`
- loop/match/success/no-peripheral hits: `0` / `0` / `0` / `1`

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

- Remote root: `/mnt/sdext/a90/private-property-v317/v1798/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0` was not opened, no PM-service devnode repair was attempted, and no private devnode was created by the V1798 observer.
- Forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, restart-PD request, full `pm-proxy`, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; use the devnode access label to choose the next source/build-only repair or parity observer.
