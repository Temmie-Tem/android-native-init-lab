# Native Init V704 CNSS Retry Stall Snapshot Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- classifier: `scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py`
- evidence: `tmp/wifi/v704-cnss-retry-stall-snapshot/`
- decision: `v704-cnss-daemon-alive-pre-wlfw-stall-classified`

## Scope

V704 consumed existing V700/V703 and Android baseline evidence only. It did not
contact the device, mount filesystems, start daemons or service managers, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, ping
externally, write sysfs/debugfs, or write boot images/partitions.

## Result

| check | result |
| --- | --- |
| V700/V703 input evidence | pass |
| provider-first CNSS retry contract | pass |
| native no-WLFW without Binder failure | finding |
| retry process alive/sleeping before cleanup | finding |
| retry runtime fds present | finding |
| Android WLFW reference | finding |

## Key Evidence

V700 removed the old Binder-failure confounder:

```text
cnss_daemon_netlink=5
cnss_daemon_cld80211=2
cnss_binder_transaction_failed=0
binder_transaction_failed=0
wlfw_start=0
qmi_server_connected=0
bdf_bdwlan=0
wlan_fw_ready=0
wlan0=0
```

The retry process was not an immediate crash. The helper captured it alive
before cleanup:

```text
pid=976
State=S (sleeping)
Threads=4
Uid=1000
Gid=1000
Groups=1010 3003 3005
SELinux=u:r:vendor_wcnss_service:s0
CapEff=0000000000001000
```

The process had active runtime fds:

```text
fd_count=16
socket_count=10
pipe_count=4
vndbinder_present=True
tty_present=True
```

Android reference reaches the path native is missing:

```text
cnss_daemon_start=1
wlfw_start=1
wlfw_service_request=1
icnss_qmi_connected=1
bdf_bdwlan=1
wlan_fw_ready=1
```

## Interpretation

V704 separates the current blocker from three older hypotheses:

- not the old initial pre-provider Binder failure;
- not a `qca6390` child bind target;
- not an immediate `cnss-daemon` crash.

The current blocker is a live pre-WLFW stall inside or below the provider-first
`cnss-daemon` retry. The process is alive and has vndbinder/socket fds, but it
does not emit `wlfw_start` and the kernel never reaches ICNSS-QMI/BDF/fw-ready.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py

python3 scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py \
  --out-dir tmp/wifi/v704-cnss-retry-stall-snapshot-plan-check plan

python3 scripts/revalidation/native_wifi_cnss_retry_stall_snapshot_v704.py \
  --out-dir tmp/wifi/v704-cnss-retry-stall-snapshot run
```

Results:

```text
v704-cnss-retry-stall-snapshot-plan-ready
v704-cnss-daemon-alive-pre-wlfw-stall-classified
```

## Next Gate

Plan V705 as a bounded live stall capture rather than another start-order retry:

- capture `wchan`, `syscall`, task status/stat, optional stack, and socket inode
  mappings for the live `cnss-daemon` retry pid;
- preserve V700 provider-first ordering;
- keep `qca6390` bind/unbind, Wi-Fi HAL connect, scan/connect, credentials,
  DHCP, routing, and external ping blocked until `wlan0` exists.
