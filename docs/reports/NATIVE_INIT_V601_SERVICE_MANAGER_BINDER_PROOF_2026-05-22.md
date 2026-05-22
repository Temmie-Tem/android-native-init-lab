# Native Init V601 Service-Manager Binder Proof Report

- date: `2026-05-22 KST`
- status: `validated`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_service_manager_v601.py`
- evidence: `tmp/wifi/v601-modem-holder-service-manager/`

## Scope

V601 preserved the V598 lower-readiness path and added only a bounded
service-manager runtime around the companion stack.

Executed:

- current-boot V490 SELinux policy load;
- global firmware mount materialization inside the V601 proof;
- `subsys_modem` holder only, with no `esoc0` open;
- QRTR RX gate before companion start;
- `servicemanager`, `hwservicemanager`, and `vndservicemanager /dev/vndbinder`
  inside the private namespace;
- `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`, `cnss_diag`, and
  `cnss-daemon` start-only window;
- WLFW QRTR nameservice readback for service `69` instances `0` and `1`;
- reboot cleanup.

Not executed:

- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- `qcwlanstate` or sysfs driver-state write;
- scan/connect/link-up, credentials, DHCP, routing, or external ping;
- boot image or persistent partition write.

## Result

```text
decision: v601-service-manager-binder-cleared-wlfw-missing
pass: True
reason: service-manager binder transaction gap cleared but WLFW/service-notifier 74 remains absent
next: classify missing service registry/sysmon sibling or WLAN-PD trigger before qcwlanstate/HAL retry
```

## Key Findings

- `servicemanager`, `hwservicemanager`, and `vndservicemanager` were all
  observable and cleaned up safely.
- V601 used Android-captured `copy-real` linkerconfig successfully.
- `cnss-daemon` again reached CNSS netlink activity.
- V600's repeated binder transaction failures disappeared.
- The only binder-related dmesg residue was two service-manager
  `ioctl ... returned -22` lines; these are not binder transaction failures.
- `cnss-daemon` still printed `Failed to become a perfd client`.
- WLFW service `69` readback remained end-of-list for instances `0` and `1`.
- No `service-notifier 74`, WLAN-PD, WLFW start, BDF, FW-ready, or `wlan0`
  marker appeared.

## Counts

```text
qrtr_rx=1
qrtr_tx=1
sysmon_qmi=1
service_notifier_180=0
service_notifier_74=0
wlan_pd=0
wlfw_start=0
wlfw_thread=0
qmi_server_connected=0
bdf=0
wlan_fw_ready=0
wlan0=0
cnss_daemon_binder_mentions=0
binder_transaction_failed=0
binder_ioctl_unsupported=2
perfd_client_failed=1
wl_fw_qrtr_service_events=0
```

WLFW readback:

```text
service=69 instance=0 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
service=69 instance=1 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
```

## Interpretation

V601 removes one incorrect assumption: the V600 binder transaction failures were
real, but clearing them is still not sufficient to publish WLFW service `69` or
trigger WLAN-PD.

The current blocker is now narrower:

```text
QRTR RX/TX and modem sysmon are present.
Service-manager binder transaction failure is gone.
WLFW/QMI registration is still absent.
```

This means the next useful test should not retry `qcwlanstate`, Wi-Fi HAL,
scan/connect, or external ping. The next test should classify what Android does
between modem `sysmon-qmi` readiness and WLAN-PD/WLFW registration that native
still lacks.

## Next Gate

Recommended V602:

1. Compare Android and native companion windows for service-registry/sysmon
   sibling surfaces, especially SLPI/CDSP/ADSP and service-notifier instance
   publication.
2. Preserve the V601 service-manager path, but add only read-only observation of
   perfd/service-registry inputs before adding any new daemon.
3. Keep Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP, routing, and
   external ping blocked until WLFW service `69`, BDF, FW-ready, or `wlan0`
   appears.
