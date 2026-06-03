# Native Init V1848 CNSS PM Selection Classifier

## Summary

- Cycle: `V1848`
- Type: host-only classifier over V1847 current-route evidence plus bounded historical CNSS/mdmdetect context
- Decision: `v1848-cnss-pm-register-selects-modem-not-sdx50m-host-pass`
- Label: `cnss-pm-register-selects-modem-record`
- Result: PASS
- Reason: Current CNSS pm_client_register requests modem, PM-service selects the modem record, and the SDX50M/eSoC lower state remains static despite a successful /dev/subsys_modem open
- Evidence: `tmp/wifi/v1848-cnss-pm-selection-classifier`

## Current Evidence

- V1847: `v1847-open-context-modem-success-static-rollback-pass` / pass `True`
- rollback/post-version/post-selftest: `True` / `True` / `True`
- PM map: `{'SDX50M': '/dev/subsys_esoc0', 'modem': '/dev/subsys_modem'}`
- register rc/call/retcheck: `0` / `1` / `1`
- PM-server register/strcmp hits: `1` / `2`
- requested values: `['modem']`
- compare `0`: candidate `SDX50M` requested `modem` line=`Binder:592_2-597   [003] ....     6.816533: pm_server_register_strcmp_call: (0x5587dc50ac) candidate="SDX50M" requested="modem"`
- compare `1`: candidate `modem` requested `modem` line=`Binder:592_2-597   [003] ....     6.816563: pm_server_register_strcmp_call: (0x5587dc50ac) candidate="modem" requested="modem"`

## Post-Ack Open Context

- open-context label: `open-context-modem-success-static`
- open path/state/fd: `/dev/subsys_modem` / `0x2` / `0x7`
- post-ack/callback labels: `post-ack-open-branch-reached` / `callback-ack-present-no-powerup`
- context line: `Binder:592_2-597   [000] ....     6.818654: pm_service_post_ack_open_context: (0x5587dc7cc8) peripheral=0xb400007fb1026180 name_ptr=12970367475257524632 devnode_ptr=12970367475257467288 state=2 fd=-1 open_count=0 fail_count=0`
- path line: `Binder:592_2-597   [000] ....     6.818661: pm_service_post_ack_open_path_loaded: (0x5587dc7ccc) path="/dev/subsys_modem" peripheral=0xb400007fb1026180`
- fd line: `Binder:592_2-597   [000] ....     6.818713: pm_service_post_ack_open_fd_store: (0x5587dc7cd8) open_rc=0x7`

## Static Lower State

- lower-continuation/lower-state: `lower-continuation-static-gap` / `stable-mdm3-offlining`
- powerup threads / inferred esoc0 opens: `[0, 0]` / `[0, 0]`
- PM focus changes/status-delta/MHI-wlan0-progress: `[]` / `0` / `False`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service-notifier / QIPCRTR bound labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`

## Historical Context

- V1211: `v1211-esoc-framework-dev-node-absent`; libmdmdetect knows `SDX50M` and reported dev-node absence `True`
- V1219: `v1219-mdmdetect-entry-not-sdxprairie`; CNSS counts `{'cnss_nullname_loop_entry': 1, 'cnss_nullname_register_call': 1, 'cnss_num_modems': 2, 'cnss_pm_vote_entry': 2, 'cnss_type_compare': 1, 'mdm_get_system_info_entry': 3, 'mdm_success_return': 3, 'pm_client_connect_entry': 1, 'pm_client_connect_ret': 1, 'pm_client_register_entry': 1, 'pm_client_register_ret': 1}`
- V1220: `v1220-private-cnss-daemon-sdx50m-patch-ready`; host-only `True` executed `False` patch `SDX50M` at `0x6cd4`

## Interpretation

- PM-service already has both records: `SDX50M -> /dev/subsys_esoc0` and `modem -> /dev/subsys_modem`.
- The current CNSS registration request is `modem`; PM-service compares `SDX50M` against `modem`, then selects the `modem` record.
- The successful post-ack open is therefore expected to target `/dev/subsys_modem`; it does not create SDX50M/eSoC powerup, WLFW service 69, MHI, or `wlan0` progress.
- The next safe target is CNSS/mdmdetect selection source or a private patched-daemon gate that changes the registration request before PM-service selection.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- Next unit should be source/build-only first: decode or trace the CNSS/mdmdetect branch that supplies `modem` to `pm_client_register`, then re-evaluate the existing private SDX50M daemon patch as a separate gated step.
