# Native Init V705 Execns Helper v120 Stall Capture Prep Report

- date: `2026-05-24 KST`
- status: `prep-pass`; helper deploy is **not** executed in this report
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py`
- build evidence: `tmp/wifi/v705-execns-helper-v120-build/`
- deploy preflight evidence:
  `tmp/wifi/v705-execns-helper-v120-deploy-preflight-check/`

## Scope

V705 prep added read-only observability to the helper and prepared deployment.
It did not start daemons, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP, change routes, ping externally, write boot images/partitions, or perform
the helper deployment.

## Changes

The helper marker is now:

```text
a90_android_execns_probe v120
```

When `cnss_daemon` or `cnss_daemon_retry` is observable, the helper now captures
the pre-cleanup stall surface:

```text
/proc/<pid>/wchan
/proc/<pid>/syscall
/proc/<pid>/stack
/proc/<pid>/stat
/proc/<pid>/sched
/proc/<pid>/task/*/{status,stat,wchan,syscall}
/proc/net/{netlink,unix,qrtr,protocols}
```

The helper also emits:

```text
wifi_companion_start.child.<name>.stall_snapshot_captured=<0|1>
```

## Build Result

Static helper build passed:

```text
artifact: tmp/wifi/v705-execns-helper-v120-build/a90_android_execns_probe
size: 969K
sha256: acc43d21f948c88350099e1a652a26c7a5f4f0352e06396c6d30dd6908d1ba28
dynamic section: none
```

## Preflight Result

Executed:

```bash
python3 scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py \
  --out-dir tmp/wifi/v705-execns-helper-v120-deploy-plan-check plan

python3 scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py \
  --out-dir tmp/wifi/v705-execns-helper-v120-deploy-preflight-check preflight
```

Results:

```text
execns-helper-v120-deploy-plan-ready
execns-helper-v120-deploy-preflight-ready
```

## Interpretation

V705 is ready for a deploy-only live step. The next live action should deploy
helper v120 and then run a provider-first CNSS start-only proof that consumes
the new stall snapshot fields.

The final Wi-Fi goal is still incomplete. No Wi-Fi HAL connect, scan/connect,
credential use, DHCP, route change, or external ping has been attempted in this
prep unit.
