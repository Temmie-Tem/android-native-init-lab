# Native Init V1808 PM-client Return Fetchargs Handoff

## Summary

- Cycle: `V1808`
- Type: one-run rollbackable WLAN-PD PM-client return fetcharg discriminator
- Decision: `v1808-pm-client-return-success-still-offlining-rollback-pass`
- Result: PASS
- Reason: PM client register/connect returns were zero while mdm3 remained OFFLINING with no MHI, WLFW service 69, or wlan0
- Evidence: `tmp/wifi/v1808-pm-client-return-fetchargs-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- PM-client return label: `pm-client-return-success-still-offlining`
- post-PM lower-state label: `stable-mdm3-offlining`
- PM-service projection label: `list-commit-progress`
- helper label: `provider-visible-modem-holder-regression`
- PM server label: `pm-server-register-success-return`
- return fetchargs seen/nonzero: `True` / `False`
- safety ok: `True`

## PM-client Return Values

- register rc: `0`
- connect rc: `0`
- PM init return-path rc: `0`
- `pm_init_pm_client_register_retcheck` hits/registered/enabled: `1` / `1` / `1`
- `pm_init_pm_client_register_retcheck` first hit: `cnss-daemon-613   [003] ....     6.658948: pm_init_pm_client_register_retcheck: (0x557bcbb628) rc=0x0`
- `pm_init_pm_client_connect_retcheck` hits/registered/enabled: `1` / `1` / `1`
- `pm_init_pm_client_connect_retcheck` first hit: `cnss-daemon-613   [003] ....     6.659890: pm_init_pm_client_connect_retcheck: (0x557bcbb654) rc=0x0`
- `pm_init_return_path` hits/registered/enabled: `2` / `1` / `1`
- `pm_init_return_path` first hit: `cnss-daemon-613   [003] ....     6.659897: pm_init_return_path: (0x557bcbb554) rc=0x0`

## Lower-state Samples

- sample total: `13`
- mdm3 states: `OFFLINING`
- mdm status IRQ totals/increased: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
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

- list commit hits: `2`
- PM register success hits: `1`
- requested `wlanmdsp`: `0`
- WLFW service 69 seen: `0`
- wlan0 present: `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1807/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless lower progress reaches WLFW/wlan0 readiness first.
