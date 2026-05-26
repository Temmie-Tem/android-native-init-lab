# Native Init V1076 PM Service Uprobe Helper Build Report

## Summary

V1076 built a static AArch64 PM-service uprobe/BPF counter helper.  The build
passed: the helper is stripped, static, has no `INTERP`, preserves explicit
tracefs/attach/child-command gates, and reuses V1075 `pm-service` entry/main/PLT
candidates as future event specs.

No deploy, tracefs write, BPF attach, PM actor start, Wi-Fi action, or network
action was executed by the V1076 build gate.

## Change

- Added `stage3/linux_init/helpers/a90_pm_service_uprobe_counter.c`.
- Added `scripts/revalidation/native_wifi_pm_service_uprobe_helper_build_v1076.py`.
- Built static helper artifact:
  `tmp/wifi/v1076-pm-service-uprobe-helper-build/a90_pm_service_uprobe_counter-aarch64-static`.
- Wrote private evidence manifest:
  `tmp/wifi/v1076-pm-service-uprobe-helper-build/manifest.json`.

## Evidence

| item | path / value |
| --- | --- |
| source | `stage3/linux_init/helpers/a90_pm_service_uprobe_counter.c` |
| build wrapper | `scripts/revalidation/native_wifi_pm_service_uprobe_helper_build_v1076.py` |
| manifest | `tmp/wifi/v1076-pm-service-uprobe-helper-build/manifest.json` |
| summary | `tmp/wifi/v1076-pm-service-uprobe-helper-build/summary.md` |
| helper artifact | `tmp/wifi/v1076-pm-service-uprobe-helper-build/a90_pm_service_uprobe_counter-aarch64-static` |
| helper size | `663456` |
| helper sha256 | `05a8b9786fdfe95de94ada2883e0ee9326df69cf8548018b05d65aef3b384d9d` |

## Build Result

```text
decision: v1076-pm-service-uprobe-helper-build-pass
pass: True
reason: static aarch64 PM-service uprobe/BPF counter helper built with explicit tracefs/attach/child gates
next: V1077 should deploy helper and run check-only; live attach remains a separate bounded gate
```

## Helper Contract

The helper defaults to no-op check-only behavior.  Active tracing requires all
relevant allow flags:

```text
--allow-tracefs-write
--allow-attach
--allow-child-command
```

The helper does not mount tracefs itself.  A future live runner must mount
tracefs under an explicit gate, register dynamic uprobe events, attach BPF
counters, then remove all created uprobe events during cleanup.

## Candidate Event Specs

V1076 extracted these V1075 callsites for a future bounded live gate:

```text
elf_entry:0x6000
libc_init_main_candidate:0x7650
android_log:0x9e60
binder_driver:0xa0a0
binder_service_manager:0xa0b0
mdmdetect_system_info:0x9f40
qmi_csi_register:0x9fb0
qmi_csi_event_loop:0x9ff0
property_set:0x9ec0
pipe:0xa040
access:0xa310
open:0xa2c0
select:0x9fd0
write:0xa170
close:0xa080
```

## Safety

V1076 build manifest records:

```text
device_commands_executed=False
tracefs_write_executed=False
bpf_attach_executed=False
child_command_executed=False
wifi_action_executed=False
scan_connect_executed=False
credential_use_executed=False
dhcp_route_executed=False
external_ping_executed=False
partition_write_executed=False
flash_executed=False
reboot_executed=False
```

## Interpretation

V1076 closes the source/build side of the lower-overhead `pm-service` observer.
It does not prove the exit-255 root cause yet.  The next step is deploy-only
parity, not live attach: first prove the reviewed helper can be installed and
run in check-only mode on v724 without touching tracefs or Wi-Fi state.

## Next Gate

V1077 should deploy the V1076 helper to `/cache/bin/a90_pm_service_uprobe_counter`
and run only:

```text
/cache/bin/a90_pm_service_uprobe_counter --check-only
/cache/bin/a90_pm_service_uprobe_counter
```

The live attach gate should wait for V1077 deploy/check-only evidence, then use
bounded tracefs mount/register/attach/cleanup around
`wifi-companion-pm-service-trigger-observer`.
