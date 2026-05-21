# Native Init V517 CNSS Private Data-WiFi Readiness

## Summary

- target: bounded CNSS userspace readiness retry with private `/data/vendor/wifi/sockets`
- helper: deployed `a90_android_execns_probe v60`
- runner: `scripts/revalidation/native_wifi_cnss_userspace_private_data_v517.py`
- live decision: `v517-cnss-userspace-readiness-no-fw-marker`
- pass: `true`
- Wi-Fi bring-up: not executed

V516 proved `cnss_diag` and `cnss-daemon` could start and be cleaned, but
`cnss-daemon` reported a missing user socket path. Static `cnss-daemon` strings
pointed at `/data/vendor/wifi/sockets/cnss_user_server`, so V517 reused the
existing helper `--data-wifi-mode private-empty` path instead of changing the
real Android filesystem.

## Live Result

Evidence root:

```text
tmp/wifi/v517-cnss-userspace-private-data-wifi/
```

Key result:

```text
decision: v517-cnss-userspace-readiness-no-fw-marker
pass: True
reason: cnss_diag/cnss-daemon were observable and cleaned, but no WLFW/QMI/BDF/FW-ready marker appeared; private /data/vendor/wifi/sockets was present
next: inspect QRTR/modem/perfd/property prerequisites before qcwlanstate retry
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
```

Private data Wi-Fi surface was present inside the helper namespace:

```text
data_wifi_mode=private-empty
context.data_vendor_wifi.exists=1
context.data_vendor_wifi.uid=1000
context.data_vendor_wifi.gid=1010
context.data_vendor_wifi.mode=770
context.data_vendor_wifi_sockets.exists=1
context.data_vendor_wifi_sockets.uid=1000
context.data_vendor_wifi_sockets.gid=1010
context.data_vendor_wifi_sockets.mode=770
```

The previous `Fail to bind user socket No such file or directory` symptom did
not recur in the V517 transcript. The remaining userspace warning is:

```text
cnss-daemon Failed to become a perfd client
```

That warning is not sufficient to produce WLFW readiness by itself; V517 still
observed no QMI/BDF/FW-ready markers.

## Dmesg Delta

The runner now classifies dmesg using timestamp delta rather than the whole
ring buffer. V517 live delta counts:

| marker | count |
| --- | ---: |
| `cnss_diag_netlink` | 21 |
| `cnss_daemon_netlink` | 39 |
| `qmi_server_connected` | 0 |
| `bdf_regdb` | 0 |
| `bdf_bdwlan` | 0 |
| `wlfw_start` | 0 |
| `wlan_fw_ready` | 0 |
| `wlan0_event` | 0 |

Interpretation:

- `cnss_diag` and `cnss-daemon` reach netlink activity.
- Private `/data/vendor/wifi/sockets` removes the missing user socket blocker.
- The chain still does not reach Android-like `WLFW/QMI/BDF/FW-ready/wlan0`.
- The next blocker is earlier than scan/connect and still below Wi-Fi bring-up.

## Safety Postflight

Postflight:

- helper children observed: `cnss_diag=1`, `cnss-daemon=1`
- postflight safe: `all_postflight_safe=1`
- `qcwlanstate_write=0`
- `scan_connect_linkup=0`
- `external_ping=0`
- no residual `cnss-daemon` / `cnss_diag` / Wi-Fi HAL / supplicant / hostapd process observed
- no `wlan*`/`swlan*`/`p2p*` link surface observed
- native status remained healthy: `selftest pass=11 warn=1 fail=0`, exposure guard OK

## Validation

Commands run:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss_userspace_readiness_v516.py \
  scripts/revalidation/native_wifi_cnss_userspace_private_data_v517.py

python3 scripts/revalidation/native_wifi_cnss_userspace_private_data_v517.py plan
python3 scripts/revalidation/native_wifi_cnss_userspace_private_data_v517.py preflight
python3 scripts/revalidation/native_wifi_cnss_userspace_private_data_v517.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v517 cnss userspace private data wifi proof only; no qcwlanstate write, no scan/connect/link-up and no external ping" \
  run

python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox ps -A -o pid,stat,comm,args
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Next Gate

Recommended V518:

1. classify the remaining `perfd`/property/QRTR/modem service prerequisites
   without starting Wi-Fi HAL or scan/connect;
2. compare Android boot evidence for which service or property transition occurs
   between `cnss-daemon` netlink setup and `wlfw_start`;
3. only after that, retry the smallest bounded action that can plausibly produce
   WLFW/QMI readiness.

Do not move to credentialed Wi-Fi connect/ping until `wlan0` or an equivalent
firmware-ready marker is proven in native init.
