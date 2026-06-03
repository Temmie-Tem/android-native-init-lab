# Native Init V1806 Post-PM Lower-state Observer Handoff

## Summary

- Cycle: `V1806`
- Type: one-run rollbackable WLAN-PD post-PM lower-state discriminator
- Decision: `v1806-stable-mdm3-offlining-rollback-pass`
- Result: PASS
- Reason: PM vote boundary was reached, but compact lower-state samples stayed at mdm3 OFFLINING with no MHI, WLFW service 69, or wlan0
- Evidence: `tmp/wifi/v1806-post-pm-lower-state-observer-handoff`
- Reclassified existing evidence: `True`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- post-PM lower-state label: `stable-mdm3-offlining`
- PM-service projection label: `list-commit-progress`
- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-register-success-return`
- lower observer enabled/contract/safety: `1` / `True` / `True`
- safety ok: `True`

## PM Boundary

- list commit hits: `2`
- PM register success hits: `1`
- `pm_init_pm_client_register_call` hits/registered/enabled: `1` / `1` / `1`
- `pm_init_pm_client_register_call` first hit: `cnss-daemon-611   [003] ....     6.594099: pm_init_pm_client_register_call: (0x55952c6624)`
- `pm_init_pm_client_connect_retcheck` hits/registered/enabled: `1` / `1` / `1`
- `pm_init_pm_client_connect_retcheck` first hit: `cnss-daemon-611   [002] ....     6.597034: pm_init_pm_client_connect_retcheck: (0x55952c6654)`

## Lower-state Samples

- sample total: `13`
- mdm3 states: `OFFLINING`
- mdm status IRQ totals/increased: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- mdm errfatal IRQ totals/increased: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- MHI counts/pipes/present: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- wlan0 samples/present: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- WLFW service69 progress: `False`
- `after_holder_start` begin/end/count/interval: `sample-only` / `sample-only` / `` / ``
- `after_holder_start` first mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `after_holder_start` last mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `post_listener_window` begin/end/count/interval: `1` / `1` / `12` / `500`
- `post_listener_window` first mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `post_listener_window` last mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`

## Route Health

- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`
- `pm_proxy_helper` ready: `1`
- `pm-service` ready: `1`
- `tftp_server` running: `1`
- `cnss-daemon` running: `1`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1805/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; use the lower-state label to choose the next source/build-only step below Wi-Fi HAL/scan/connect.
