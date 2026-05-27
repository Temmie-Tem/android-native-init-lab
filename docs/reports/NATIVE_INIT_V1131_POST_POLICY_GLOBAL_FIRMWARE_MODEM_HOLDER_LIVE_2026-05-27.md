# Native Init V1131 Post-policy Global Firmware Modem-holder Live Report

Date: `2026-05-27`

## Result

- Decision: `v1131-modem-pre-holder-open-pending-subsys-modem-blocker-confirmed`
- Pass: `true`
- V401 evidence: `tmp/wifi/v1131-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1131-v490-policy-load-v213/manifest.json`
- Live evidence:
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live/manifest.json`
- Classifier evidence:
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/manifest.json`
- Classifier summary:
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/summary.md`
- Live runner:
  `scripts/revalidation/native_wifi_post_policy_global_firmware_modem_holder_live_v1131.py`
- Host-only classifier:
  `scripts/revalidation/native_wifi_post_policy_global_firmware_modem_holder_classifier_v1131.py`

## Summary

V1131 refreshed current-boot SELinux preconditions, ran the post-policy
provider-positive PM observer path, and enabled helper `v213` modem pre-holder
flags.

Preconditions passed:

```text
V401 decision=toybox-selinuxfs-mount-live-executor-run-pass
V490 decision=v490-selinux-policy-load-proof-pass
```

Helper and command contract passed:

```text
helper=a90_android_execns_probe v213
--allow-pm-observer-modem-pre-holder present
--pm-observer-modem-pre-holder present
```

Observed holder contract:

```json
{
  "modem_pre_holder_requested": true,
  "modem_pre_holder_allowed": true,
  "modem_pre_holder_start_attempted": true,
  "modem_pre_holder_child_chroot": true,
  "modem_pre_holder_plain_retry": "0",
  "modem_pre_holder_open_reported": false,
  "modem_pre_holder_result_reported": false,
  "modem_pre_holder_confirmed": false,
  "modem_pre_holder_cleanup_kill_sent": true,
  "modem_pre_holder_cleanup_reaped": false
}
```

This means the pre-holder child reached the private root and attempted the
`/dev/subsys_modem` path, but even the scoped `O_RDONLY | O_NONBLOCK |
O_CLOEXEC` open did not return a result inside the observer window.

Provider and CNSS PM path still worked:

```json
{
  "vndservicemanager_ready": true,
  "vndservice_provider_seen": true,
  "cnss_daemon_start_executed": true,
  "pm_client_register_ret": ["0x0"],
  "pm_client_connect_ret": ["0x0"]
}
```

The PM Binder worker also reproduced the lower blocker:

```text
syscall_probe.after_cnss_daemon.entry_05.path.value=/dev/subsys_modem
syscall_probe.after_cnss_daemon.entry_05.wchan=__subsystem_get
```

Lower state did not advance:

```text
mss=OFFLINING
mdm3=OFFLINING
QRTR service 69/74/180 = 0/0/0
WLFW/BDF/MHI/QCA6390/sysmon_qmi/wlan0 markers = 0
```

## Runner Note

The first live runner decision was:

```text
v1131-modem-holder-not-requested
```

That was a host-side parser false negative. The helper emitted
`modem_pre_holder_*` keys without the `pm_service_trigger_observer.` prefix in
the parsed contract map. The live runner was patched to accept both prefixed
and unprefixed forms, and the host-only classifier reprocessed the existing
evidence without executing device commands.

## Interpretation

The V1071 `pm-service exit 255` / broad BPF direction remains closed. The
current path is lower than provider registration and lower than successful CNSS
PM register/connect.

The active blocker is now more precise:

```text
provider-positive CNSS PM connect
  -> helper v213 tries bounded /dev/subsys_modem pre-holder
  -> O_NONBLOCK open still does not return
  -> pm-service Binder worker also blocks in __subsystem_get
  -> mss/mdm3 remain OFFLINING
  -> WLFW service 69 and wlan0 remain absent
```

This strongly suggests the subsystem `open()` path ignores or cannot honor
`O_NONBLOCK` and enters the same `__subsystem_get` wait path as the PM Binder
worker.

## Safety

V1131 did not perform:

```text
subsys_esoc0_open_attempted=0
wifi_hal_start_executed=0
scan_connect_linkup=0
credential_use_executed=false
dhcp_route_executed=false
external_ping=0
partition_write_executed=false
flash_executed=false
```

Cleanup reboot was required because the modem pre-holder was not proven reaped.
Post-reboot evidence in the live manifest showed:

```text
version: A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: ncm0=absent tcpctl=stopped
```

## Next

The next route should be host-only or read-only first:

1. inspect Samsung/Qualcomm subsystem open semantics for `subsys_modem`;
2. compare whether `/dev/subsys_modem` supports nonblocking behavior at all;
3. classify safer alternatives to direct open, such as PM service transaction
   fields, subsystem sysfs state, or Android-positive `mdm_helper`/eSoC timing;
4. continue forbidding `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect,
   credentials, DHCP/route, external ping, partition writes, boot image writes,
   and flash.
