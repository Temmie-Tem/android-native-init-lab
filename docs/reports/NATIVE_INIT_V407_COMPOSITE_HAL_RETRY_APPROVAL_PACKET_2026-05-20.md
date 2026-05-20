# Native Init v407 Composite Wi-Fi HAL Retry Approval Packet

## Summary

V407 approval packet is implemented and fail-closed.

The runner prepares a bounded composite Wi-Fi HAL start-only retry using helper v24 and the V406-proven `v30-to-system-ext-v30` private APEX materialization. No live HAL retry was executed in this packet.

## Evidence

- plan evidence: `tmp/wifi/v407-composite-hal-retry-plan-20260520-101054/`
- no-approval run evidence: `tmp/wifi/v407-composite-hal-retry-noapproval-20260520-101054/`
- read-only preflight evidence: `tmp/wifi/v407-composite-hal-retry-preflight-20260520-101101/`
- V406 input: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/manifest.json`

## Plan Result

```text
decision: v407-composite-hal-start-only-retry-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Planned command:

```text
run /cache/bin/a90_android_execns_probe --system-root /mnt/system/system --vendor-block /dev/block/sda29 --vendor-fstype ext4 --mode wifi-hal-composite-start-only --target-profile vendor-wifi-hal-ext --null-device-mode dev-null-selinux --data-wifi-mode private-empty --vndk-apex-alias-mode v30-to-system-ext-v30 --linkerconfig-mode copy-real --linkerconfig-source /cache/bin/a90_real_ld.config.txt --apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt --property-root /mnt/sdext/a90/private-property-v317/dev/__properties__ --timeout-sec 6
```

## No-Approval Result

```text
decision: v407-composite-hal-start-only-retry-approval-required
pass: True
reason: exact approval phrase required; no device command executed
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

## Read-Only Preflight Result

```text
decision: v407-composite-hal-start-only-retry-preflight-ready
pass: True
reason: read-only preflight is ready; live run still needs approval
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Confirmed checks:

- V406 linker-list pass input is present.
- native version and health pass.
- remote helper v24 SHA and `v30-to-system-ext-v30` mode pass.
- real linkerconfig, APEX libraries config, and private property root pass.
- `system_ext` VNDK v30 and `android.hardware.wifi@1.0.so` source pass.
- `servicemanager` and `hwservicemanager` binaries pass.
- existing manager/HAL process surface is clean.
- Wi-Fi link surface is clean.

The remaining gate is approval only:

```text
approval-gate: needs-operator
```

## Required Future Approval Phrase

```text
approve v407 composite Wi-Fi HAL start-only retry only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Not Executed

- composite HAL start-only retry.
- `servicemanager`, `hwservicemanager`, or Wi-Fi HAL daemon start.
- `wificond`, supplicant, hostapd.
- `cnss-daemon` or `cnss_diag`.
- scan/connect/link-up.
- credentials, DHCP, routing.
- rfkill, ICNSS bind/unbind, module load/unload, firmware mutation.
- Android partition writes.
- persistence or boot/autostart changes.

## Next Target

The next live step is exact-approved V407 bounded composite Wi-Fi HAL start-only retry.

That step still does not approve Wi-Fi bring-up. If V407 reaches `start-only-pass`, the next milestone should collect HAL registration and service surface evidence before any scan/connect stage.

