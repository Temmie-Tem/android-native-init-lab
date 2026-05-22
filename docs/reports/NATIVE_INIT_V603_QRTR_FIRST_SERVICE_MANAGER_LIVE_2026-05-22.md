# Native Init V603 QRTR-First Service-Manager Live Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_qrtr_first_service_manager_v603.py`
- evidence: `tmp/wifi/v603-qrtr-first-service-manager-live/`

## Scope

V603 live proof deployed helper v101, refreshed the current boot SELinux runtime
surface, ran a bounded `subsys_modem` holder window, started the companion stack
with QRTR-first service-manager ordering, performed WLFW QRTR nameservice
readback, and reboot-cleaned the device.

It did not start Wi-Fi HAL, `wificond`, supplicant, or hostapd. It did not write
`qcwlanstate`, scan, connect, use credentials, run DHCP, change routes, ping
externally, write a boot image, or perform persistent partition writes.

## Preconditions

```text
helper_v101_deploy_decision: execns-helper-v101-deploy-pass
helper_v101_sha256: a2a089110106a9c2eb6b33eb2c5f0c382fb4fda0e0c7f32e80dbabb9dd281372
v401_selinuxfs_decision: toybox-selinuxfs-mount-live-executor-run-pass
v490_policy_load_decision: v490-selinux-policy-load-proof-pass
v603_preflight_decision: v603-qrtr-first-service-manager-preflight-ready
```

## Result

```text
decision: v603-qrtr-first-service-notifier-regressed
pass: True
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
qrtr_first_order_executed: True
service_manager_start_executed: True
copy_real_linkerconfig_executed: True
```

Observed order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon
```

## Key Counts

```text
qrtr_rx: 1
qrtr_tx: 1
sysmon_qmi: 1
service_notifier_180: 0
service_notifier_74: 0
wlan_pd: 0
wlfw_start: 0
qmi_server_connected: 0
bdf: 0
wlan_fw_ready: 0
wlan0: 0
binder_transaction_failed: 0
binder_ioctl_unsupported: 2
perfd_client_failed: 1
wl_fw_qrtr_service_events: 0
```

WLFW QRTR nameservice readback:

```text
send_attempted: 1
service_events: 0
end_of_list: 2
timeouts: 0
qmi_attempted: 0
```

## Interpretation

V603 preserved the service-manager/binder improvement from V601:

- `servicemanager`, `hwservicemanager`, and `vndservicemanager` were observed.
- `cnss-daemon` binder transaction failures stayed at `0`.
- copy-real linkerconfig mode was used.
- cleanup/postflight remained safe.

V603 did not preserve the lower service-notifier marker from V598:

- QRTR RX, QRTR TX, and `sysmon-qmi` appeared.
- service-notifier `180` did not appear.
- WLFW service `69` readback returned end-of-list for both checked instances.

That means the blocker is not a plain binder runtime gap anymore. It is an
ordering/timing gap around when CNSS enters relative to service-manager and the
lower modem/service-notifier publication path.

## Cleanup State

The live proof used reboot cleanup. The reboot command lost the final END marker
because the device restarted, but post-reboot verification saw the expected
native version and healthy status.

```text
post_reboot_version_seen: true
post_reboot_status_healthy: true
post_reboot_wifi_bringup_executed: false
```

## Next Gate

Recommended V604:

1. Keep helper v101 deployed.
2. Refresh current-boot V401/V490 prerequisites after reboot.
3. Add a bounded delayed-CNSS or delayed-service-manager proof:
   - start `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`;
   - wait for QRTR TX/`sysmon-qmi` and a longer publication window;
   - start service-manager trio;
   - then start `cnss_diag` and `cnss-daemon`.
4. Continue blocking Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP,
   routing, and external ping until service-notifier `180` plus binder-clean are
   observed together, or WLFW/BDF/FW-ready/`wlan0` appears.
