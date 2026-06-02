# Native Init V1744 WLAN-PD Pure-route Non-log Parity Handoff

## Summary

- Cycle: `V1744`
- Type: one-run rollbackable pure-route non-log parity gate
- Decision: `v1744-tracefs-surface-unavailable-rollback-pass`
- Result: PASS
- Reason: one pure-route non-log parity run produced a fixed label and rollback verified
- Evidence: `tmp/wifi/v1744-wlan-pd-pure-nonlog-parity-handoff-retry1`
- Rollback attempt: `from-native`

## Non-log Parity Decision

- V1744 label: `tracefs-surface-unavailable`
- output label: `cnss-output-still-invisible`
- non-log label: `cnss-target-unavailable`
- non-log contract seen: `True`
- tracefs available/path/errno: `0` / `none` / `2`
- uprobe attempted/register rc/enabled/hits: `0` / `0` / `0` / `0`
- reached wlfw by non-log evidence: `False`
- route safety ok: `True`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1743/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Output-source Supplemental Fields

- stdout/stderr bytes: `269703` / `8653`
- `wlfw_start` source: `none`
- `wlfw_start` stdout/stderr/kmsg counts: `0` / `0` / `0`
- first init failure slug: `none`
- syslog available/errno/filtered: `1` / `0` / `0`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This gate uses the V1743 artifact to close the V1740 tracefs measurement gap on the pure internal-modem route.
- It does not add service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- One live run set the label `tracefs-surface-unavailable`; stop actor expansion and repair the private tracefs/uProbe path in a source/build-only V1745 gate.
