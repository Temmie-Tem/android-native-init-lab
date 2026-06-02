# Native Init V1702 WLAN-PD cnss-daemon Tracefs Target-path Handoff

## Summary

- Cycle: `V1702`
- Type: one-run rollbackable WLAN-PD cnss-daemon tracefs target-path/non-log gate
- Decision: `v1702-cnss-wlfw-entry-hit-downstream-wait-rollback-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1702-wlan-pd-cnss-tracefs-target-path-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- output label: `cnss-output-still-invisible`
- non-log label: `cnss-wlfw-entry-hit-downstream-wait`
- legacy firmware-serve label: `firmware-not-requested`
- property lookup all_match: `1`
- cnss-daemon running: `1`
- tftp running: `1`
- companion order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,cnss-output-visibility-summary`

## Tracefs / Non-log Control Flow

- tracefs path/available: `/sys/kernel/debug/tracing` / `1`
- uprobe register rc/registered: `0` / `1`
- uprobe enable rc/enabled: `0` / `1`
- uprobe hit count: `1`
- first hit line: `cnss-daemon-561   [000] ....     3.572363: wlfw_start: (0x55798bac00)`
- maps text seen / runtime PC: `1` / `0x55798bac00`
- socket/kmsg fd counts: `10` / `0`
- MHI pipe fd count / ks process count: `0` / `0`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- V1702 proves stock `cnss-daemon` reaches `wlfw_start` under the internal-modem firmware-serve route.
- V1681-V1700 missing `wlfw_start` dmesg evidence is a logging/measurement gap, not proof that `cnss-daemon` skipped `wlfw_start`.
- The current blocker moves downstream of `cnss-daemon` entry: WLAN-PD/WLFW service publication remains absent, firmware request remains absent, and `wlan0` is still absent.
- Do not add PM/service-window actors or `boot_wlan` from this label; the next unit should classify the downstream WLFW wait/request path.

## V1702 Delta

- Uses V1701 test boot with helper `a90_android_execns_probe v314`.
- Verifies whether the repaired private-vendor target path lets tracefs register `cnss-daemon+0xec00`.
- Still uses only the internal-modem firmware-serve route; no PM/service-window actors, `boot_wlan`, eSoC/RC1, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
