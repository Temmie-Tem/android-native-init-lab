# Native Init V1841 PM Callback/Ack Current-route Handoff

## Summary

- Cycle: `V1841`
- Type: one-run rollbackable current-route PM callback/ack hit-count discriminator
- Decision: `v1841-callback-ack-present-no-powerup-rollback-pass`
- Result: PASS
- Reason: current-route callback/transact/ack hit counts appeared, but lower PMIC/GDSC and MHI/WLFW/wlan0 state stayed static
- Evidence: `tmp/wifi/v1841-pm-callback-ack-current-route-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version ok: `True`
- Post-rollback selftest fail=0: `True`
- Post-rollback version evidence: `tmp/wifi/v1841-pm-callback-ack-current-route-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1841-pm-callback-ack-current-route-handoff/post-rollback-selftest.stdout.txt`

## Gate Label

- callback/ack label: `callback-ack-present-no-powerup`
- callback/ack registered/enabled: `True` / `True`
- callback/ack hit total: `28`
- callback/ack hit keys: `['periph_pm_callback_stub_entry', 'periph_pm_callback_write_state', 'periph_pm_callback_remote_binder', 'periph_pm_callback_transact_call', 'periph_pm_callback_transact_return', 'periph_pm_client_ack_entry', 'periph_pm_client_ack_match', 'periph_pm_client_ack_virtual_call', 'periph_pm_server_ontransact_entry', 'periph_pm_server_ack_read_state', 'periph_pm_server_ack_impl_call', 'periph_pm_server_ack_write_ret']`
- lower-continuation label: `lower-continuation-static-gap`
- PM focus change fields / mdm-status delta: `[]` / `0`
- PM focus MHI/wlan0 progress: `False`
- service-notifier / QIPCRTR labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Callback/Ack Hits

- `periph_pm_callback_stub_entry` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [002] ....     6.756798: periph_pm_callback_stub_entry: (0x7f98bdba5c)`
- `periph_pm_callback_write_state` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [002] ....     6.756812: periph_pm_callback_write_state: (0x7f98bdbadc)`
- `periph_pm_callback_remote_binder` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [002] ....     6.756816: periph_pm_callback_remote_binder: (0x7f98bdbae4)`
- `periph_pm_callback_transact_call` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [002] ....     6.756822: periph_pm_callback_transact_call: (0x7f98bdbafc)`
- `periph_pm_callback_transact_return` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [002] ....     6.756861: periph_pm_callback_transact_return: (0x7f98bdbb00)`
- `periph_pm_client_ack_entry` registered/enabled/hits: `1` / `1` / `2` first=`Binder:605_2-614   [000] ....     6.756915: periph_pm_client_ack_entry: (0x7fb15536f0)`
- `periph_pm_client_ack_match` registered/enabled/hits: `1` / `1` / `2` first=`Binder:605_2-614   [000] ....     6.756922: periph_pm_client_ack_match: (0x7fb1553754)`
- `periph_pm_client_ack_virtual_call` registered/enabled/hits: `1` / `1` / `2` first=`Binder:605_2-614   [000] ....     6.757127: periph_pm_client_ack_virtual_call: (0x7fb1553780)`
- `periph_pm_server_ontransact_entry` registered/enabled/hits: `1` / `1` / `5` first=`Binder:589_2-594   [000] ....     6.407658: periph_pm_server_ontransact_entry: (0x7f98bdb5bc)`
- `periph_pm_server_ack_read_state` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [000] ....     6.757213: periph_pm_server_ack_read_state: (0x7f98bdb750)`
- `periph_pm_server_ack_impl_call` registered/enabled/hits: `1` / `1` / `2` first=`Binder:589_2-594   [000] ....     6.757218: periph_pm_server_ack_impl_call: (0x7f98bdb760)`
- `periph_pm_server_ack_write_ret` registered/enabled/hits: `1` / `1` / `3` first=`Binder:589_2-594   [002] ....     6.757059: periph_pm_server_ack_write_ret: (0x7f98bdb814)`

## Lower State

- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1840/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The new V1841 surface only adds read-only uprobe hit counts on existing `libperipheral_client.so` offsets in the V1838 current route.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- If callback/ack is absent, classify why current PM connect/register returns without the legacy callback/ack sequence before any new live mutation.
