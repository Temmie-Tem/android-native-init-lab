# Native Init V1077 PM Service Uprobe Helper Deploy Check-only Report

## Summary

V1077 deployed the V1076 PM-service uprobe helper over NCM and verified both
check-only modes on the device.  The remote sha256 matched the reviewed V1076
artifact, and both `--check-only` and default no-argument execution proved no
tracefs write, no BPF attach, and no child command execution.

Device health remained good: `netservice` showed `ncm0=present` and
`tcpctl=running`, and `selftest` reported `fail=0`.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_uprobe_helper_deploy_checkonly_v1077.py`.
- Deployed V1076 artifact to `/cache/bin/a90_pm_service_uprobe_counter`.
- Wrote private evidence to
  `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/manifest.json`.

## Evidence

| item | path / value |
| --- | --- |
| runner | `scripts/revalidation/native_wifi_pm_service_uprobe_helper_deploy_checkonly_v1077.py` |
| manifest | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/manifest.json` |
| summary | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/summary.md` |
| install transcript | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/logs/install.txt` |
| remote sha transcript | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/logs/remote-sha.txt` |
| check-only transcript | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/logs/check-only.txt` |
| default transcript | `tmp/wifi/v1077-pm-service-uprobe-helper-deploy-checkonly/logs/default-no-args.txt` |
| remote helper | `/cache/bin/a90_pm_service_uprobe_counter` |
| sha256 | `05a8b9786fdfe95de94ada2883e0ee9326df69cf8548018b05d65aef3b384d9d` |

## Result

```text
decision: v1077-pm-service-uprobe-helper-deploy-checkonly-pass
pass: True
reason: helper deployed over NCM and both check-only/default modes proved no tracefs write or BPF attach
next: V1078 can run a bounded tracefs mount/register/attach cleanup proof around PM observer
```

## Remote Check-only Output

`--check-only`:

```text
a90_pm_service_uprobe_counter v1076
binary=/vendor/bin/pm-service
tracefs_root=/sys/kernel/tracing
group=a90pm1076
duration_sec=8
event_count=0
allow_tracefs_write=0
allow_attach=0
allow_child_command=0
result=check-only
tracefs_write_attempted=0
attach_attempted=0
child_command_attempted=0
```

Default no-argument mode produced the same no-attach markers.

## Health

```text
netservice: ncm0=present tcpctl=running pid=550
selftest: pass=11 warn=1 fail=0
```

## Safety

V1077 executed only deploy and no-attach helper checks.  It did not pass
`--allow-tracefs-write`, `--allow-attach`, or `--allow-child-command`; it did
not start PM actors, service-manager, CNSS, Wi-Fi HAL, `mdm_helper`, scan,
connect, DHCP, route changes, external ping, `/dev/esoc*`, `wlan.ko`, boot image
writes, partition writes, or reboot.

## Interpretation

The helper is now staged on the device and safe default behavior is proven.  The
remaining PM blocker is still unresolved: this step did not observe live
`pm-service` execution.  V1078 should be the first active bounded uprobe proof,
with explicit tracefs mount/register/attach/cleanup and the PM observer child
command gated by the helper.
