# V1113 Global Firmware PM Connect Live Report

Date: `2026-05-27`

## Result

- Decision: `v1113-global-holder-cnss-pm-connect-not-reproduced`
- Pass: `true`
- Evidence: `tmp/wifi/v1113-global-firmware-pm-connect-live/manifest.json`
- Collector: `scripts/revalidation/native_wifi_global_firmware_pm_connect_live_v1113.py`

## Summary

V1113 combined the V1061 lower prerequisite with the V1111 CNSS-first PM
observer. After tightening the runner so helper sha/usage checks use serial
instead of NCM/TCP, the stable run showed the lower prerequisite succeeds but
the V1111 CNSS PM-connect return path is not reproduced in the same window.

Observed state:

```text
firmware_mounts_executed=true
global_modem_holder_opened=true
mounted_hits=/vendor/firmware_mnt:true,/vendor/firmware-modem:true
mss=OFFLINING->ONLINE->ONLINE
mdm3=OFFLINING->OFFLINING->OFFLINING
qrtr_rx_seen=true
tracefs_result=tracefs-uprobe-pass
cnss pm_client_register_ret=[]
cnss pm_client_connect_ret=[]
cnss_daemon_hit_count=0
pm_server_event_hit_count=56
per_proxy_start_executed=0
per_proxy_start_skipped=1
cnss_daemon_start_executed=1
service69=0
wifi_hal_start_executed=false
scan_connect_executed=false
external_ping_executed=false
```

The important change versus V1111 is that the combined lower precondition no
longer reproduces the previous CNSS PM-connect path. The prior blocked path:

```text
openat("/dev/subsys_modem") -> __subsystem_get
```

was not captured under the combined global firmware + modem holder precondition,
but this run also did not capture CNSS `pm_client_register/connect` returns.

## Interpretation

This narrows the blocker differently than the first attempt suggested. The
lower global prerequisite is stable:

- firmware mounts are visible;
- the global modem holder opens;
- `mss` reaches `ONLINE`;
- QRTR RX is observed;
- cleanup reboot returns native healthy.

However, the stable observer window shows `pm-service` PM-server activity
without CNSS PM client return hits. The next blocker is therefore not Wi-Fi HAL
and not scan/connect. It is whether `pm-service` is alive/ready long enough for
CNSS under the global holder, or whether the CNSS trigger needs a different
ordering/window after the holder is established.

The next question is therefore smaller:

1. Did `pm-service` exit or become unobservable before CNSS reaches PM client
   register/connect?
2. Does the global holder change PM actor timing enough that the old V1111
   trigger no longer reaches the client path?
3. Or did the current observer window miss a short-lived CNSS client call?

WLFW/service 69 still did not appear, and `mdm3` stayed `OFFLINING`, so this is
not yet a Wi-Fi HAL or scan/connect point.

## Safety

- `/dev/subsys_modem` holder: executed, bounded, global proof node only
- `/dev/subsys_esoc0`: not opened
- eSoC ioctl/control: not executed
- Wi-Fi HAL: not started
- scan/connect: not executed
- credentials: not used
- DHCP/routes: not executed
- external ping: not executed
- flash/boot image/partition writes: not executed
- cleanup: reboot executed; native returned healthy

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_global_firmware_pm_connect_live_v1113.py
python3 scripts/revalidation/native_wifi_global_firmware_pm_connect_live_v1113.py plan
python3 scripts/revalidation/native_wifi_global_firmware_pm_connect_live_v1113.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

Live result:

```text
decision: v1113-global-holder-cnss-pm-connect-not-reproduced
pass: True
```

Post-cleanup checks:

```text
selftest: pass=11 warn=1 fail=0
bootstatus: BOOT OK
netservice: disabled flag; NCM/tcpctl stopped after cleanup reboot
```

## Next

V1114 should focus on PM-service readiness/lifetime under the global holder:

- capture `pm-service` process lifetime and exit reason inside the combined
  holder window;
- keep helper sha/usage checks on serial/cmdv1, not NCM/TCP;
- only then extend the post-CNSS tagged syscall sampling window.

Do not move to Wi-Fi HAL, scan/connect, DHCP, credentials, or external ping
until the PM-connect-to-WLFW/service69 gap is explained.
