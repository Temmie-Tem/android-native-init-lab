# Native Init V843 Current-Window CNSS Stall Classifier Report

## Result

- decision: `v843-cnss-retry-poll-futex-prewlfw-event-gap`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_current_window_cnss_stall_classifier_v843.py`
- evidence: `tmp/wifi/v843-current-window-cnss-stall-classifier/`

## Scope

V843 was host-only. It did not contact the device, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, ping externally, write sysfs/debugfs, write boot images, write
partitions, or flash a custom kernel.

## Key Signals

| Signal | Value |
| --- | --- |
| Retry PID | `992` |
| Main wait channel | `do_sys_poll` |
| Main syscall | `73` / `ppoll` |
| Worker wait channels | `do_sys_poll: 2`, `futex_wait_queue_me: 2` |
| FD surface | `16` fds, `10` sockets, vndbinder present |
| CNSS user socket | present at `/data/vendor/wifi/sockets/cnss_user_server` |
| Netlink surface | retry PID present in `/proc/net/netlink` |
| QRTR proc surface | unavailable in helper namespace |
| Positive lower markers | service `180/74`, QRTR RX/TX, `sysmon-qmi`, CNSS netlink/CLD80211 |
| Missing Wi-Fi markers | no `wlfw_start`, no WLAN-PD, no BDF, no FW-ready, no `wlan0` |

## Interpretation

The current provider-first `cnss-daemon` retry is alive and waiting in
`poll`/`futex` paths with the expected CNSS socket and netlink surfaces. That
rules against another broad launcher-contract retry as the next useful step.

The remaining blocker is the missing event source below Wi-Fi HAL: native still
does not publish the ICNSS/WLFW/WLAN-PD progression that Android reaches before
full Wi-Fi bring-up.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_window_cnss_stall_classifier_v843.py
python3 scripts/revalidation/native_wifi_current_window_cnss_stall_classifier_v843.py \
  --out-dir tmp/wifi/v843-plan-check \
  plan
python3 scripts/revalidation/native_wifi_current_window_cnss_stall_classifier_v843.py \
  --out-dir tmp/wifi/v843-current-window-cnss-stall-classifier \
  run
```

Result:

```text
decision: v843-cnss-retry-poll-futex-prewlfw-event-gap
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V844 should classify the source-backed ICNSS/WLFW event publication
prerequisite. Do not advance to Wi-Fi HAL, scan/connect, DHCP/routes,
credentials, external ping, `esoc0`, subsystem writes, module load/unload, or
boot image writes from this result alone.
