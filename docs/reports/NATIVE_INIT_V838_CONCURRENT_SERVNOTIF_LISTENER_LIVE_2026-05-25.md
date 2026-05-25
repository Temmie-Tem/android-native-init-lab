# Native Init V838 Concurrent Service-notifier Listener Live Report

## Result

- decision: `v838-held-through-post74-no-indication`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_concurrent_servnotif_listener_v838.py`
- helper: `a90_android_execns_probe v130`
- evidence: `tmp/wifi/v838-concurrent-servnotif-listener-live-retry2-20260525-143057/`

## What Ran

```bash
python3 scripts/revalidation/native_wifi_concurrent_servnotif_listener_v838.py \
  --out-dir tmp/wifi/v838-concurrent-servnotif-listener-live-retry2-20260525-143057 \
  --allow-arm-clean-dsp \
  --allow-reboot \
  --allow-cleanup-umount \
  --allow-system-mount \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cnss-start-only \
  --allow-cleanup-reboot \
  --allow-known-asoc-warning \
  --allow-concurrent-listener \
  --assume-yes \
  run
```

## Timing Evidence

| Signal | Value |
| --- | ---: |
| listener process begin | `85589.000 ms` |
| listener register send | `85781.000 ms` |
| listener first response | `85782.000 ms` |
| service `74` timestamp | `86417.576 ms` |
| listener close | `100796.000 ms` |
| listener begin before service `74` | `828.576 ms` |
| listener register before service `74` | `636.576 ms` |
| listener close after service `74` | `14378.424 ms` |
| listener open at service `74` | `true` |
| held through service `74` + `5s` | `true` |
| WLAN-PD indication | `false` |

## Service-notifier Result

- endpoint: service-notifier `66/46081`, node `0`, port `2`
- endpoint wait attempts: `2`
- request: bounded `REGISTER_LISTENER` for `msm/modem/wlan_pd`
- response: QMI success, current state `0x7fffffff` / `uninit`
- indication: none
- hold: `15015 ms`, poll timeout reached

## Lower Window

- order: `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`
- service `180`: present
- service `74`: present
- exact known ASoC warning: present and accepted
- WLFW/service `69`: absent
- BDF: absent
- MHI/QCA6390: absent
- wiphy/`wlan0`: absent

## Safety

- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No `esoc0` open.
- No module load/unload.
- No boot image write, partition write, or custom kernel flash.
- Cleanup reboot restored healthy native v724; follow-up `version` and `status`
  were responsive.

## Notes

- Two earlier V838 attempts exposed helper-side probe bugs:
  - QRTR empty/POLLERR handling caused listener output truncation.
  - The final helper v130 uses bounded fresh lookup retries and avoids the
    repeated `POLLERR` flood.
- Helper deploy used serial fallback because host-side NCM `192.168.7.1/24` was
  not active during deploy preflight.

## Conclusion

V838 rules out the primary timing explanation. The listener was registered
before service `74`, remained open through service `74` + `5s`, and still saw no
WLAN-PD `UP` indication. The next gate should classify the Android-only explicit
WLAN-PD state-up trigger below service-manager/HAL and before any scan/connect
or external network activity.
