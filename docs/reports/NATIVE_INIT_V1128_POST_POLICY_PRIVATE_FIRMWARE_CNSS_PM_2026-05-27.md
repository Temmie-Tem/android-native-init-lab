# V1128 Post-Policy Private Firmware CNSS PM Report

Date: `2026-05-27`

## Result

- Decision: `v1128-post-policy-cnss-pm-connect-reaches-subsys-modem-blocker`
- Pass: `true`
- Live evidence: `tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-observer-live/manifest.json`
- Classifier evidence: `tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-classifier/manifest.json`
- Classifier summary: `tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-classifier/summary.md`
- Classifier: `scripts/revalidation/native_wifi_post_policy_private_firmware_cnss_pm_classifier_v1128.py`

## Evidence Inputs

- V401 selinuxfs mount: `tmp/wifi/v1128-v401-selinuxfs-mount/manifest.json`
- V490 policy load: `tmp/wifi/v1128-v490-policy-load-v212/manifest.json`
- Post-policy private-firmware CNSS PM replay:
  `tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-observer-live/manifest.json`
- Post-pass process surface: `tmp/wifi/v1128-post-policy-post-pass-ps.txt`
- Post-reboot process check: `tmp/wifi/v1128-post-reboot-ps-r2.txt`

## Summary

V1128 applied the V490 policy-load precondition and replayed the
private-firmware CNSS PM observer path.

Preconditions:

```text
V401 decision=toybox-selinuxfs-mount-live-executor-run-pass
V490 decision=v490-selinux-policy-load-proof-pass
V490 result=policy-load-pass
```

Post-policy live replay:

```text
decision=v1124-private-firmware-provider-preserved-cnss-connect-reached
private_firmware_mounts_requested=1
private_firmware_mnt_mounted=1
private_firmware_modem_mounted=1
vndservicemanager_readiness.ready=1
vndservice_provider_seen=1
cnss_daemon_start_executed=1
```

CNSS PM client path:

```json
{
  "pm_client_register_ret": ["0x0"],
  "pm_client_connect_ret": ["0x0"]
}
```

PM server Binder side:

```json
{
  "pm_server_register_ret": ["0x0"],
  "pm_server_connect_ret": ["0x0"]
}
```

Remaining lower blocker:

```text
post_provider_surface.after_cnss_daemon.mdm3_state=OFFLINING
post_provider_surface.after_cnss_daemon.wlan0_exists=0
syscall_probe.after_cnss_daemon.entry_05.path.value=/dev/subsys_modem
syscall_probe.after_cnss_daemon.entry_05.wchan=__subsystem_get
```

## Interpretation

V1128 closes two previously active blockers:

1. service-manager policy/provider registration is repaired by V490;
2. CNSS PM client register/connect now succeeds with the private firmware
   mount surface.

The active blocker has moved lower:

```text
V490 policy loaded
  -> vendor.qcom.PeripheralManager provider visible
  -> cnss-daemon PM client register/connect returns 0
  -> PM server Binder register/connect returns 0
  -> Binder worker attempts open("/dev/subsys_modem")
  -> thread blocks in __subsystem_get
  -> mdm3 remains OFFLINING
  -> wlan0 remains absent
```

This means Wi-Fi HAL or scan/connect is still premature. The next gate must
target the lower modem/eSoC state transition.

## Safety

V1128 did not perform:

```text
wifi_hal_start_executed=0
scan_connect_linkup=0
external_ping=0
subsys_esoc0_open_attempted=0
credential_use_executed=false
dhcp_route_executed=false
partition_write_executed=false
flash_executed=false
```

The live observer reported `observer-reboot-required` because
`pm_proxy_helper` remained in D-state after the window. Cleanup reboot was
performed after evidence capture.

Post-reboot verification:

```text
version: A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: ncm0=absent tcpctl=stopped
residual PM/service-manager/CNSS actors: none matched
```

## Next

V1129 should classify the lower `/dev/subsys_modem` path:

1. confirm which PM server Binder worker opens `/dev/subsys_modem`;
2. capture its blocking state and related mdm3/eSoC sysfs state;
3. compare the expected safe trigger with earlier eSoC research;
4. avoid Wi-Fi HAL, scan/connect, credentials, and external ping until mdm3 can
   leave `OFFLINING`.
