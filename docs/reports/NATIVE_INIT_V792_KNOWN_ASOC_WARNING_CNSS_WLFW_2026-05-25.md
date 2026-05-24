# Native Init V792 Known-ASoC-Warning CNSS/WLFW Report

## Result

- decision: `v792-known-warning-cnss-no-wlfw-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_known_asoc_warning_cnss_wlfw_v792.py`
- evidence: `tmp/wifi/v792-known-asoc-warning-cnss-wlfw/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_known_asoc_warning_cnss_wlfw_v792.py
python3 scripts/revalidation/native_wifi_known_asoc_warning_cnss_wlfw_v792.py plan
python3 scripts/revalidation/native_wifi_known_asoc_warning_cnss_wlfw_v792.py run \
  --assume-yes \
  --allow-arm-clean-dsp \
  --allow-reboot \
  --allow-cleanup-umount \
  --allow-system-mount \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cnss-start-only \
  --allow-known-asoc-warning \
  --allow-cleanup-reboot
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| V791 reference | pass |
| inline clean-DSP proof | pass |
| V401 SELinuxfs mount | pass |
| V490 policy load | pass |
| lower/CNSS order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| `cnss_diag` / `cnss-daemon` | started |
| service-manager / Wi-Fi HAL / scan-connect | not executed |
| service-notifier markers | `2` |
| `sysmon-qmi` | `4` |
| known ASoC warning guard | exact signature matched |
| service `74` -> `pm_qos` | `4.858 ms` |
| `pm_qos` -> sound card | `514.402 ms` |
| WLFW / BDF / `wlan0` | `0 / 0 / 0` |
| QRTR service `69` readback | `service_events=0`, `qmi_attempted=0` |
| post-cleanup health | healthy v724 |

## Classification

V792 validates the V791 route on live hardware. The exact known ASoC
`pm_qos_add_request()` warning appears, but the path continues to sound-card
registration and cleanup health is good. The warning is therefore not the first
useful Wi-Fi blocker for this gate.

The useful blocker is now narrower:

```text
clean-DSP + lower companions + cnss_diag/cnss-daemon
  -> service 180/74
  -> known ASoC warning and sound-card registration
  -> no WLFW/service69, no BDF, no wlan0
```

The next work should target the CNSS continuation gap: `cnss-daemon`
runtime/binder/service-manager parity or ICNSS/WLFW trigger evidence, still
below Wi-Fi HAL and connect.

## Safety

- Wi-Fi HAL start: not executed
- scan/connect: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed
- boot image or partition write: not executed
- custom kernel flash: not executed
- cleanup reboot: executed and post-cleanup status is healthy

## Next

V793 should be a bounded CNSS continuation classifier:

1. compare current V792 `cnss-daemon`/`cnss_diag` netlink, binder, service
   manager, and ICNSS/WLFW trigger surfaces;
2. avoid service-manager start until the preflight proves it is the smallest
   required runtime surface;
3. keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
   blocked until WLFW/service `69`, BDF, or `wlan0` exists.
