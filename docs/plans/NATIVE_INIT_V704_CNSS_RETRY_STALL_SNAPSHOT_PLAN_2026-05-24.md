# Native Init V704 CNSS Retry Stall Snapshot Plan

- date: `2026-05-24 KST`
- cycle: `v704`
- type: host-only classifier over V700/V703 evidence

## Goal

V703 classified the next target as the ICNSS/WLFW readiness edge rather than a
`qca6390` child-node bind. V704 narrows the live failure mode one step further:

```text
Does the provider-first cnss-daemon retry crash/fail Binder, or does it stay
alive below WLFW with missing stall-point observability?
```

## Inputs

- `tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json`
- `tmp/wifi/v703-android-native-binding-compare/manifest.json`
- `tmp/wifi/v700-provider-first-cnss-orchestrated-run/arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt`
- `tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt`

## Guardrails

V704 must not:

- contact the device;
- mount or bind mount filesystems;
- start daemons, service managers, Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan, connect, link up, use credentials, DHCP, route changes, or external
  ping;
- write sysfs/debugfs, boot images, or partitions.

## Implementation

Add `scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py`.

The classifier parses:

- V700 counts for post-provider `cnss-daemon` netlink, Binder failure, WLFW,
  ICNSS-QMI, BDF, firmware-ready, and `wlan0`;
- V700 helper stdout for the `cnss-daemon` retry pid and proc/fd capture;
- `/proc/<pid>/status` and `/proc/<pid>/attr/current` captured while the retry
  process was alive;
- retry fd targets, including socket count and `/dev/vndbinder`;
- Android dmesg markers proving the reference path reaches WLFW/BDF/fw-ready.

## Decision Criteria

`v704-cnss-daemon-alive-pre-wlfw-stall-classified` requires:

- V700 and V703 evidence are ready;
- provider-first retry suppressed the initial CNSS path and started one fresh
  `cnss-daemon` after provider proof;
- native reaches CNSS netlink without Binder transaction failure;
- native still has no WLFW, ICNSS-QMI, BDF, firmware-ready, or `wlan0`;
- the retry process was captured alive and sleeping before cleanup;
- retry fds include sockets and `/dev/vndbinder`;
- Android reference reaches `wlfw_start`, ICNSS-QMI, BDF, and firmware-ready.

## Validation Plan

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py

python3 scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py \
  --out-dir tmp/wifi/v704-cnss-retry-stall-snapshot-plan-check plan

python3 scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py \
  --out-dir tmp/wifi/v704-cnss-retry-stall-snapshot run
```

## Next Gate

If V704 classifies an alive pre-WLFW stall, V705 should implement helper v120
or an equivalent live gate that captures the retry process's blocking point
while it is alive:

- `/proc/<pid>/wchan`
- `/proc/<pid>/syscall`
- `/proc/<pid>/stack` if readable
- `/proc/<pid>/task/*/{status,stat,wchan,syscall}`
- socket inode mapping against available netlink/unix/QRTR tables
- a bounded observe window before cleanup

Do not start Wi-Fi HAL connect, scan/connect, credentials, DHCP, routing, or
external ping until `wlan0` exists.
