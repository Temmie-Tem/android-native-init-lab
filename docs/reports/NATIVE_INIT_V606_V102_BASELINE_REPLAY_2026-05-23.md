# Native Init V606 V102 Baseline Replay Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_wlfw_readback_v598.py`
- evidence: `tmp/wifi/v606-v102-baseline-wlfw-readback-live/`
- preflight evidence: `tmp/wifi/v606-v102-baseline-wlfw-readback-preflight/`

## Scope

V606 replayed the V598 no-service-manager baseline with the current helper v102
runtime. It refreshed current-boot SELinux/runtime prerequisites, ran the
bounded `subsys_modem` holder window, started only the modem/Wi-Fi companion
stack, and performed WLFW QRTR nameservice readback without QMI payload.

It did not start `servicemanager`, `hwservicemanager`, `vndservicemanager`,
Wi-Fi HAL, `wificond`, supplicant, or hostapd. It did not write `qcwlanstate`,
scan, connect, use credentials, run DHCP, change routes, ping externally, write
a boot image, or perform persistent partition writes.

## Preconditions

```text
helper_v102_sha256: 8214098f750c77f982975f46a8b6af2a8461b6e4520962488b7daf9e013251d3
helper_marker: a90_android_execns_probe v102
v401_selinuxfs_decision: toybox-selinuxfs-mount-live-executor-run-pass
v490_policy_load_decision: v490-selinux-policy-load-proof-pass
v606_preflight_decision: v598-wlfw-readback-preflight-ready
```

The reused V598 runner still labels one helper check as `helper-v100-ready`;
the actual checked marker and SHA in this run were v102.

## Result

```text
decision: v598-wlfw-readback-empty
pass: True
reason: WLFW QRTR readback reached end-of-list; timeouts=0
helper_result: companion-window-pass
wifi_bringup_executed: False
```

Observed companion order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon
```

Service-manager flags remained disabled:

```text
with_service_manager: 0
with_vnd_service_manager: 0
```

## Key Counts

```text
qrtr_rx: 1
qrtr_tx: 1
sysmon_qmi: 1
service_notifier_180: 0
wlan_pd: 0
qmi_server_connected: 0
wlfw: 0
bdf: 0
wlan_fw_ready: 0
wlan0: 0
binder_transaction_failed: 21
```

WLFW QRTR nameservice readback:

```text
send_attempted: 1
service_events: 0
end_of_list: 2
timeouts: 0
qmi_attempted: 0
```

## Runtime Surface

```text
mss_after_holder: ONLINE
mss_after_companion: ONLINE
mdm3_after_companion: OFFLINING
firmware_class_path: /vendor/firmware_mnt/image
mounted:/vendor/firmware_mnt: True
mounted:/vendor/firmware-modem: True
visible:/vendor/firmware-modem/image/modem.b00: True
visible:/vendor/firmware_mnt/image/modem.b00: False
```

The lower modem path still reaches QRTR RX, QRTR TX, and `sysmon-qmi`.
However, unlike V598, the `service-notifier` `180` registration did not appear.

## Interpretation

V605 showed that the positive V598 `service-notifier` `180` event happened
before CNSS userspace entered. V606 then replayed the no-service-manager path
with current helper v102 and still lost `service-notifier` `180`.

That removes short service-manager ordering as the primary explanation. The
current blocker is the lower QMI service-publication boundary after
`sysmon-qmi`: native can bring the modem far enough for QRTR TX and modem SSCTL,
but the QMI service registration that triggers `service-notifier` is not
reliably reproduced.

Likely buckets:

1. helper/runtime delta between the V598-positive window and current v102;
2. current-boot precondition delta not captured by V401/V490/firmware mounts;
3. lower modem publication timing/state nondeterminism;
4. evidence gap in the service-notifier/QRTR observation window.

Direct `qcwlanstate`, HAL, scan/connect, credentials, DHCP, routing, and
external ping remain premature until service-notifier/WLAN-PD/WLFW markers move.

## Cleanup State

V606 used reboot cleanup. The reboot command lost the final END marker because
the device restarted, but post-reboot verification saw the expected native
version and healthy status.

```text
post_reboot_version_seen: true
post_reboot_status_healthy: true
selftest: pass=11 warn=1 fail=0
exposure_boundary: usb-local
```

## Next Gate

Recommended V607:

1. Run a host-only delta classifier over V598-positive and V606-negative
   evidence.
2. Compare helper version/marker, companion transcript, daemon order, wait
   windows, V401/V490 freshness, firmware mounts, subsystem states, QRTR
   readback rows, `/proc/net/qrtr`, qipcrtr socket counts, and dmesg timing.
3. Classify the gap as helper-version delta, boot/runtime delta, modem
   publication nondeterminism, or insufficient evidence.
4. Only after that, choose a bounded live follow-up such as helper v100 replay
   or a no-CNSS post-sysmon service-notifier observation window.
