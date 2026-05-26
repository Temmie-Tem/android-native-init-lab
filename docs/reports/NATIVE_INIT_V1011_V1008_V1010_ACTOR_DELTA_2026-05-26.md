# V1011 V1008/V1010 Actor Delta Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v1011-v1008-v1010-actor-delta/manifest.json` | `v1011-select-after-fd-cnss-service-manager-matrix` |

V1011 selects an incremental matrix live gate instead of another full
service-window retry.

## Findings

| Signal | V1008 full service-window | V1010 reduced service-defaults |
| --- | --- | --- |
| Result | `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd` | `mdm-helper-esoc-fd-observed` |
| `/dev/esoc-0` fd | `seen=0 max=0` | `window=1 final=1` |
| `per_mgr` state | observable, exited `0` | `per_mgr_light` alive |
| `mdm_helper` SELinux | `u:r:vendor_mdm_helper:s0` | `u:r:vendor_mdm_helper:s0` |
| Service-window breadth | 14 actors | property shim + `per_mgr_light` + `mdm_helper` |

The full service-window remains too broad for the next retry because it loses
the `mdm_helper` fd predicate before any subsystem trigger can safely run.
The reduced service-defaults path keeps the fd predicate and proves the issue is
not simply the `mdm_helper` SELinux domain.

## Selected Route

V1012 should use existing helper `v171` support:

- mode: `wifi-companion-mdm-helper-cnss-service-manager-matrix`;
- order: `after-mdm-helper-esoc-fd`;
- add service-manager and CNSS actors only after `mdm_helper` has opened
  `/dev/esoc-0`;
- keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
  forbidden.

This route is closer to final Wi-Fi bring-up than V1010 because it can test
whether CNSS/WLFW preconditions advance while preserving the fd-positive lower
state.

## Guardrails

V1011 was host-only:

- no device command;
- no Android boot or ADB command;
- no actor start;
- no `/dev/esoc-0`, `/dev/subsys_esoc0`, eSoC ioctl, GPIO, sysfs, or debugfs access;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes;
- no external ping;
- no boot image, partition, firmware, or filesystem mutation.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1008_v1010_actor_delta_v1011.py
python3 scripts/revalidation/native_wifi_v1008_v1010_actor_delta_v1011.py
```

Result:

```text
decision: v1011-select-after-fd-cnss-service-manager-matrix
pass: True
route: v1012-helper-v171-after-mdm-helper-esoc-fd-matrix-live
```
