# V1129 Post-Policy Global Firmware Mount-only Report

Date: `2026-05-27`

## Result

- Decision: `v1129-global-firmware-mount-only-insufficient-subsys-modem-blocker-remains`
- Pass: `true`
- Live evidence: `tmp/wifi/v1129-post-policy-global-firmware-mount-only-cnss-pm-live/manifest.json`
- Classifier evidence: `tmp/wifi/v1129-post-policy-global-firmware-mount-only-classifier/manifest.json`
- Classifier summary: `tmp/wifi/v1129-post-policy-global-firmware-mount-only-classifier/summary.md`
- Classifier: `scripts/revalidation/native_wifi_post_policy_global_firmware_mount_only_classifier_v1129.py`

## Evidence Inputs

- V401 selinuxfs mount: `tmp/wifi/v1129-v401-selinuxfs-mount/manifest.json`
- V490 policy load: `tmp/wifi/v1129-v490-policy-load-v212/manifest.json`
- Global firmware mount-only live replay:
  `tmp/wifi/v1129-post-policy-global-firmware-mount-only-cnss-pm-live/manifest.json`
- Post-reboot process check: `tmp/wifi/v1129-post-reboot-ps.txt`

## Summary

V1129 replayed the firmware mount-only provider gate after the V490 policy
refresh and with helper `v212` overrides.

Preconditions:

```text
V401 decision=toybox-selinuxfs-mount-live-executor-run-pass
V490 decision=v490-selinux-policy-load-proof-pass
V490 result=policy-load-pass
```

Global firmware visibility:

```json
{
  "/vendor/firmware_mnt": true,
  "/vendor/firmware-modem": true
}
```

Provider and CNSS PM path:

```text
vndservicemanager_readiness.ready=1
vndservice_provider_seen=1
cnss_daemon_start_executed=1
pm_client_register_ret=["0x0"]
pm_client_connect_ret=["0x0"]
```

Lower modem/Wi-Fi state:

```text
mss: OFFLINING -> OFFLINING
mdm3: OFFLINING -> OFFLINING
QRTR service 69/74/180: 0/0/0
WLFW/BDF/MHI/QCA6390/sysmon_qmi/wlan0 markers: 0
/dev/subsys_modem open remains pending in __subsystem_get
```

## Interpretation

V1129 proves that global firmware mount visibility alone is not enough.

Closed:

1. V490 plus global firmware mount-only still preserves provider visibility.
2. CNSS PM client register/connect still returns `0x0`.
3. The previous V1128 result was not simply missing global firmware mount
   visibility.

Remaining blocker:

```text
post-policy provider-positive CNSS PM connect
  -> global firmware mounts visible
  -> no global /dev/subsys_modem first opener
  -> /dev/subsys_modem open still blocks in __subsystem_get
  -> mss/mdm3 remain OFFLINING
  -> WLFW service 69 and wlan0 remain absent
```

The next gate should therefore add a bounded `/dev/subsys_modem` first-opener
contract to the post-policy provider-positive CNSS order. Moving to Wi-Fi HAL,
scan/connect, credentials, DHCP/route, or external ping remains premature.

## Safety

V1129 did not perform:

```text
global_modem_holder_opened=false
subsys_esoc0_open_attempted=0
wifi_hal_start_executed=0
scan_connect_linkup=0
external_ping=0
credential_use_executed=false
dhcp_route_executed=false
partition_write_executed=false
flash_executed=false
```

The V1121-based live runner performed cleanup reboot after the global firmware
mount window. Post-reboot verification:

```text
version: A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: ncm0=absent tcpctl=stopped
residual PM/service-manager/CNSS actors: none matched
```

## Next

V1130 should add a bounded `/dev/subsys_modem` first-opener contract to the
V1128/V1129 post-policy provider-positive CNSS order:

1. keep V490 policy load as a hard precondition;
2. keep global firmware mounts visible;
3. open `/dev/subsys_modem` in a bounded holder before the CNSS PM request;
4. prove whether CNSS PM connect still occurs and whether mss/mdm3/WLFW advance;
5. continue forbidding `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect,
   credentials, DHCP/route, external ping, partition writes, and flash.
