# Native Init V1908 Service-locator Domain-list Live Handoff

## Summary

- Cycle: `V1908`
- Type: one-run rollbackable native service-locator domain-list observer
- Decision: `v1908-servloc-domain-list-180-only-service74-missing-rollback-pass`
- Label: `servloc-domain-list-180-only-service74-missing`
- Result: PASS
- Reason: native service-locator live response returns only msm/modem/wlan_pd instance 180, and service-notifier 74/wlan_pd/WLFW69/wlan0 remain absent
- Evidence: `tmp/wifi/v1908-servloc-domain-list-live-handoff`
- Rollback ok: `True`

## Live Domain Edge

- service-locator result/count/name/instance: `domain-list-response-success` / `1` / `msm/modem/wlan_pd` / `180`
- service-locator endpoint/status: `1`:`16464` / `found`
- domain 180-only discriminator: `True`
- V1907 source gate: `v1907-servloc-domain-list-missing-service74-host-pass` / `servloc-domain-list-missing-service74` / `True` / single caller `True`

## Service-notifier / Lower Gates

- service180/service74/wlan_pd raw counts: `1,1,1` / `0,0,0` / `0,0,0`
- service-notifier early/late state: `uninit` / `uninit`
- native service74 absence discriminator: `True`
- WLFW69/requested-wlanmdsp/wlan0: `0` / `0` / `0`
- PM register/connect/open path: `0` / `0` / `None`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1903/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Selected Diff

- Native live confirms the current blocker as service-locator domain-list 180-only before service-notifier instance 74 publication.
- This remains on the internal modem path and keeps `/dev/subsys_modem` as a precondition, not a WLAN guest-PD start trigger.
- The next comparison should query/capture Android-good service-locator domain-list in the normal ~15s boot to verify whether Android receives instance 74 from the locator or publishes it by another kernel path.

## Safety Scope

- Rollbackable native test boot plus `stage3/boot_linux_v724.img` rollback only.
- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, restart-PD request, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, forced RC1/case, or PMIC/GPIO/GDSC/regulator writes.
