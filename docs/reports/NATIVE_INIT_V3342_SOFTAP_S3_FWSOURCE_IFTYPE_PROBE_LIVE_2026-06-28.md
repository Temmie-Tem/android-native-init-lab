# Native Init V3342 SoftAP S3 Firmware Source IfType Probe Live

- Cycle: `V3342`
- Decision: `v3342-softap-s3-fwsource-iftype-probe-live-pass`
- Init: `A90 Linux init 0.11.106 (v3342-softap-s3-fwsource-iftype-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3342_softap_s3_fwsource_iftype_probe.img`
- Boot SHA256: `836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Source/build report: `docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md`

## Flash And Health

- Reconfirmed rollback images before flashing:
  - V2321: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - V2237: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - V48: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Reconfirmed TWRP recovery image SHA256:
  - `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flashed only through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flash helper verified the local V3342 marker/SHA, wrote only the boot partition, read back the boot image, and matched the V3342 SHA256 above.
- Post-flash `version` reported `0.11.106 build=v3342-softap-s3-fwsource-iftype-probe`.
- Post-flash and follow-up health stayed clean: `selftest pass=12 warn=1 fail=0`.
- Current resident after this iteration is V3342 with `selftest fail=0`.

## Firmware Source Fix

The V3342 helper reached the QCACLD firmware request and sourced the requested
payload from the mounted read-only vendor firmware route:

```text
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.source_policy=qcacld-fwsource-mounted-vendor-first
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.label=WCNSS_qcom_cfg_ini
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.firmware=wlan/qca_cld/WCNSS_qcom_cfg.ini
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.seen=1
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.source_rc=0
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.source_bytes=13343
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_0.fed=1
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.seen_count=1
qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count=1
wlan_pd_service_object_visible_trigger.wlan0_present=1
```

Supervisor summary:

```text
wlan0_present=1
helper_wait_rc=0
helper_timed_out=0
helper_status_raw=0
baseline_ready=1
supervisor_result=wlan0-ready
helper_exited=1
helper_exit_code=0
helper_signaled=0
```

## Functional Probe

Command:

```text
hide
wifi softap iftype-probe 220000
```

Observed result:

```text
version=a90-native-wifi-softap-v2
scope=s3-ap-iftype-add-delete-probe-no-ap-start
iface=wlan0
ap_probe_iface=a90ap0
ap_iftype=AP
credentials=0
ssid_psk_logged=0
config_write_attempted=0
wpa_supplicant_mode2_start_attempted=0
dhcp_server_start_attempted=0
listener_start_attempted=0
address_assign_attempted=0
server_exposure_attempted=0
wlan0_wait_timeout_ms=220000
wlan0_wait_rc=0
wlan0_wait_elapsed_ms=91456
wlan0_present=1
link_up_attempted=1
link_up_rc=0
link_up_errno=0
sta_supplicant.process_count_before=0
sta_supplicant.stop_attempted=0
sta_supplicant.terminate_wait_rc=0
sta_supplicant.kill_attempted=0
sta_supplicant.process_count_final=0
sta_supplicant.stoppable=1
sta_supplicant.stop_rc=0
ifindex=9
netlink_open=1
family_id=19
ap_iftype_preexisting=0
ap_iftype_precleanup_attempted=0
ap_iftype_precleanup_rc=0
ap_iftype_precleanup_errno=0
ap_iftype_add_attempted=1
ap_iftype_add_rc=0
ap_iftype_add_errno=0
ap_iftype_iface_created=1
ap_iftype_created_ifindex=12
ap_iftype_cleanup_attempted=1
ap_iftype_cleanup_rc=0
ap_iftype_cleanup_errno=0
ap_iftype_cleanup_ok=1
decision=softap-iftype-probe-pass
```

The S3 lower gate is now proven: `wlan0` surfaced, the STA supplicant conflict
gate is stoppable, AP iftype add/delete works, cleanup succeeds, and the no-start
contract held. This run did not start `wpa_supplicant mode=2`, `udhcpd`, a local
listener, AP address assignment, WAN routing, NAT, or any transfer server.

## Next Unit

Proceed to the bounded AP bring-up unit:

```text
wpa_supplicant mode=2 SoftAP start
2.4GHz channel 1/6/11 only
BusyBox udhcpd on private local subnet
no WAN/NAT/default-route export
softap cleanup kills workers and removes address/route residue
selftest fail=0
```

