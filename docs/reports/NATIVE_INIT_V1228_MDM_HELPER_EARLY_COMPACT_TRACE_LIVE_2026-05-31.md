# V1228 mdm_helper Early Compact Trace Live Gate

- date: 2026-05-31
- helper: `a90_android_execns_probe v255`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v255_deploy_preflight_v1228.py`
- live runner: `scripts/revalidation/native_wifi_mdm_helper_early_compact_trace_live_v1228.py`
- deploy evidence: `tmp/wifi/v1228-execns-helper-v255-deploy/manifest.json`
- live evidence: `tmp/wifi/v1228-mdm-helper-early-compact-trace-live/manifest.json`
- result: `v1228-early-wait-for-req-observed-no-ks-mhi`
- pass: `true`

## Purpose

V1227 proved that even focused pre-gate `ptrace` stops `mdm_helper` before it
opens `/dev/esoc-0`. V1228 therefore avoids pre-gate ptrace and adds read-only
compact `/proc` sampling during the existing early `mdm_helper` `/dev/esoc-0`
polling window.

## Evidence Summary

| field | value |
|---|---|
| early trace emitted | `true` |
| early sample count | `10` |
| max `/dev/esoc-0` fd count | `1` |
| max MHI pipe fd count | `0` |
| `ESOC_WAIT_FOR_REQ` samples | `10` |
| observed syscall | `ioctl(fd=3, request=0x8004cc02)` |
| observed ioctl name | `ESOC_WAIT_FOR_REQ` |
| observed wchan | `esoc_dev_ioctl` |
| `pm-service` `/dev/subsys_esoc0` attempt | `true` |
| `ks` or MHI present | `false` |
| `mdm3` state transitions | `OFFLINING` |
| WLFW / `wlan0` | absent |

## Interpretation

V1228 resolves the V1226/V1227 instrumentation ambiguity. The native path can
now be observed without ptrace perturbation:

1. `mdm_helper` owns `/dev/esoc-0`.
2. `mdm_helper` is blocked inside `ESOC_WAIT_FOR_REQ`.
3. `pm-service` attempts `/dev/subsys_esoc0`.
4. No `ks`, `/dev/mhi_0305_01.01.00_pipe_10`, WLFW, BDF, FW-ready, or `wlan0`
   appears before modem-down/crash markers.

The active blocker is no longer whether `mdm_helper` starts or whether it opens
the eSoC device. The active blocker is the ESOC request handling / image-link
handoff after `ESOC_WAIT_FOR_REQ`: native does not reach Android's `ks` + MHI
transfer path.

## Safety Audit

- Wi-Fi HAL start: `false`
- scan/connect/link-up: `false`
- credential use: `false`
- DHCP/route: `false`
- external ping: `false`
- boot image write / flash / partition write: `false`
- postflight selftest: `pass=11 warn=1 fail=0`
- postflight netservice: disabled, `ncm0=absent`, `tcpctl=stopped`

## Next Gate

V1229 should classify the ESOC request contract around `ESOC_WAIT_FOR_REQ` and
why native does not launch or reach the Android `ks`/MHI image-link path. The
next useful evidence should capture the request value/result and the missing
transition to `/vendor/bin/ks` and `/dev/mhi_0305_01.01.00_pipe_10`, still
without Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
