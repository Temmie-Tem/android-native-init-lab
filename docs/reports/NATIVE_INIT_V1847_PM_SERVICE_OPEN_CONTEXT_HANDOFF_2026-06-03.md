# Native Init V1847 PM-Service Open-Context Handoff

## Summary

- Cycle: `V1847`
- Type: one-run rollbackable PM-service open-context discriminator
- Decision: `v1847-open-context-modem-success-static-rollback-pass`
- Result: PASS
- Reason: PM-service open context confirmed /dev/subsys_modem success while lower SDX50M/eSoC state stayed static
- Evidence: `tmp/wifi/v1847-pm-service-open-context-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version ok: `True`
- Post-rollback selftest fail=0: `True`
- Post-rollback version evidence: `tmp/wifi/v1847-pm-service-open-context-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1847-pm-service-open-context-handoff/post-rollback-selftest.stdout.txt`

## Gate Label

- open-context label: `open-context-modem-success-static`
- open-context registered/enabled: `True` / `True`
- open-context hit total: `7`
- open-context hit keys: `['pm_service_post_ack_power_state_loaded', 'pm_service_post_ack_open_context', 'pm_service_post_ack_open_path_loaded', 'pm_service_post_ack_open_fd_store', 'pm_service_post_ack_open_fd_compare', 'pm_service_post_ack_open_success_counter']`
- open-context path/state/fd: `/dev/subsys_modem` / `0x2` / `0x7`
- post-ack label/total: `post-ack-open-branch-reached` / `22`
- callback/ack label/total: `callback-ack-present-no-powerup` / `28`
- lower-continuation label: `lower-continuation-static-gap`
- PM focus change fields / mdm-status delta: `[]` / `0`
- PM focus MHI/wlan0 progress: `False`
- service-notifier / QIPCRTR labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Open-Context Hits

- `pm_service_post_ack_power_state_loaded` registered/enabled/hits: `1` / `1` / `2` first=`Binder:592_2-597   [000] ....     6.818645: pm_service_post_ack_power_state_loaded: (0x5587dc78cc) power_state=0x2`
- `pm_service_post_ack_open_context` registered/enabled/hits: `1` / `1` / `1` first=`Binder:592_2-597   [000] ....     6.818654: pm_service_post_ack_open_context: (0x5587dc7cc8) peripheral=0xb400007fb1026180 name_ptr=12970367475257524632 devnode_ptr=12970367475257467288 state=2 fd=-1 open_count=0 fail_count=0`
- `pm_service_post_ack_open_path_loaded` registered/enabled/hits: `1` / `1` / `1` first=`Binder:592_2-597   [000] ....     6.818661: pm_service_post_ack_open_path_loaded: (0x5587dc7ccc) path="/dev/subsys_modem" peripheral=0xb400007fb1026180`
- `pm_service_post_ack_open_fd_store` registered/enabled/hits: `1` / `1` / `1` first=`Binder:592_2-597   [000] ....     6.818713: pm_service_post_ack_open_fd_store: (0x5587dc7cd8) open_rc=0x7`
- `pm_service_post_ack_open_fd_compare` registered/enabled/hits: `1` / `1` / `1` first=`Binder:592_2-597   [000] ....     6.818718: pm_service_post_ack_open_fd_compare: (0x5587dc7ce0) open_fd=0x7`
- `pm_service_post_ack_open_success_counter` registered/enabled/hits: `1` / `1` / `1` first=`Binder:592_2-597   [000] ....     6.818725: pm_service_post_ack_open_success_counter: (0x5587dc7ce8)`

## Key Lines

- state line: `Binder:592_2-597   [000] ....     6.818645: pm_service_post_ack_power_state_loaded: (0x5587dc78cc) power_state=0x2`
- context line: `Binder:592_2-597   [000] ....     6.818654: pm_service_post_ack_open_context: (0x5587dc7cc8) peripheral=0xb400007fb1026180 name_ptr=12970367475257524632 devnode_ptr=12970367475257467288 state=2 fd=-1 open_count=0 fail_count=0`
- path line: `Binder:592_2-597   [000] ....     6.818661: pm_service_post_ack_open_path_loaded: (0x5587dc7ccc) path="/dev/subsys_modem" peripheral=0xb400007fb1026180`
- fd line: `Binder:592_2-597   [000] ....     6.818713: pm_service_post_ack_open_fd_store: (0x5587dc7cd8) open_rc=0x7`

## Lower State

- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1846/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The new V1847 surface only adds read-only `pm-service` open-context uprobe hit counts on the V1846 test boot image.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- If `/dev/subsys_modem` success is confirmed again, the next safe step is host-only/source classification of CNSS PM peripheral selection versus the SDX50M record.
