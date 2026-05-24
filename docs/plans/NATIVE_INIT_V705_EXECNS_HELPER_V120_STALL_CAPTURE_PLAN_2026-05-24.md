# Native Init V705 Execns Helper v120 Stall Capture Plan

- date: `2026-05-24 KST`
- cycle: `v705`
- type: helper observability build/deploy prep

## Goal

V704 classified the current blocker as an alive provider-first
`cnss-daemon` retry stalled before WLFW. V705 adds only the missing
observability to the exec namespace helper:

```text
capture the live cnss-daemon retry blocking point before cleanup
```

## Scope

Allowed:

- bump `a90_android_execns_probe` marker from `v119` to `v120`;
- add bounded read-only proc captures for `cnss_daemon` and
  `cnss_daemon_retry` while they are alive;
- add a deploy/preflight wrapper for helper v120;
- build the static helper and verify deploy preflight.

Forbidden:

- daemon start during helper deploy/preflight;
- Wi-Fi HAL start;
- scan/connect/link-up;
- credential use;
- DHCP, route changes, or external ping;
- sysfs/debugfs writes;
- boot image or partition writes.

## Implementation

Patch `stage3/linux_init/helpers/a90_android_execns_probe.c`:

- `EXECNS_VERSION` becomes `a90_android_execns_probe v120`;
- for `cnss_daemon` and `cnss_daemon_retry`, capture:
  - `/proc/<pid>/wchan`;
  - `/proc/<pid>/syscall`;
  - `/proc/<pid>/stack` if readable;
  - `/proc/<pid>/stat` and `/proc/<pid>/sched`;
  - `/proc/<pid>/task/*/{status,stat,wchan,syscall}` for up to 16 tasks;
  - `/proc/net/{netlink,unix,qrtr,protocols}`;
- emit `wifi_companion_start.child.<name>.stall_snapshot_captured`.

Add `scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py` with:

- helper marker: `a90_android_execns_probe v120`;
- artifact path:
  `tmp/wifi/v705-execns-helper-v120-build/a90_android_execns_probe`;
- SHA-256:
  `acc43d21f948c88350099e1a652a26c7a5f4f0352e06396c6d30dd6908d1ba28`;
- same provider-first mode token as v119.

## Validation Plan

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v705-execns-helper-v120-build/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py

python3 scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py \
  --out-dir tmp/wifi/v705-execns-helper-v120-deploy-plan-check plan

python3 scripts/revalidation/wifi_execns_helper_v120_deploy_preflight.py \
  --out-dir tmp/wifi/v705-execns-helper-v120-deploy-preflight-check preflight
```

## Live Approval Boundary

Deploy only:

```text
approve v705 deploy execns helper v120 only; no daemon start and no Wi-Fi bring-up
```

The deploy gate must not start daemons or Wi-Fi.

## Next Gate

After helper v120 is deployed, rerun the provider-first CNSS start-only proof
with the v120 marker and classify whether the new stall snapshot identifies the
blocking syscall, wchan, task, or socket table edge.
