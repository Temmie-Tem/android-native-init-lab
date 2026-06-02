# Native Init V1751 WLAN-PD Tracefs Mount Restore Handoff

## Summary

- Cycle: `V1751`
- Type: one-run rollbackable tracefs mount-restore live gate
- Decision: `v1751-wlfw-start-reached-downstream-block-rollback-pass`
- Result: PASS
- Reason: one tracefs mount-restore live handoff produced a fixed label and rollback verified
- Evidence: `tmp/wifi/v1751-wlan-pd-tracefs-mount-restore-handoff`
- Rollback attempt: `from-native`

## Fixed Label

- V1751 label: `wlfw-start-reached-downstream-block`
- V1751 basis: cnss-daemon reached wlfw_start by output or private tracefs/uProbe evidence
- output label: `cnss-output-still-invisible`
- `wlfw_start` source: `none`
- `wlfw_start` stdout/stderr/kmsg counts: `0` / `0` / `0`
- first init failure slug: `none`
- non-log label: `peripheral-default-service-manager-call-no-return`
- non-log contract seen: `True`
- tracefs available/path/errno: `1` / `/tmp/a90-v231-546/root/sys/kernel/debug/tracing` / `0`
- uprobe attempted/register rc/enabled/hits: `1` / `0` / `1` / `1`
- reached wlfw by non-log evidence: `True`
- route safety ok: `True`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1749/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This gate preserves the corrected premise: `boot_wlan` is not a WLFW trigger and missing native dmesg output can be a measurement artifact.
- It reuses only the V1680-style internal-modem firmware-serve route and adds no PM/service-window actors.
- One live run sets one label. Stop after this label; do not spin timing/window variants.
