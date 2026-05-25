# Native Init V837 Timestamped Service-notifier Hold Live Report

## Result

- decision: `v837-listener-not-open-at-service74`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_timestamped_servnotif_hold_v837.py`
- helper: `a90_android_execns_probe v129`
- evidence: `tmp/wifi/v837-timestamped-servnotif-hold-live-20260525-134510/`

## What Ran

```bash
python3 scripts/revalidation/native_wifi_timestamped_servnotif_hold_v837.py \
  --out-dir tmp/wifi/v837-timestamped-servnotif-hold-live-20260525-134510 \
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
  --allow-timestamped-listener-hold \
  --assume-yes \
  run
```

## Timing Evidence

| Signal | Value |
| --- | ---: |
| service `74` timestamp | `86470.953 ms` |
| listener send timestamp | `87084.000 ms` |
| listener response timestamp | `87084.000 ms` |
| listener close timestamp | `102090.000 ms` |
| listener send after service `74` | `613.047 ms` |
| listener close after service `74` | `15619.047 ms` |
| listener open at service `74` | `false` |
| WLAN-PD indication | `false` |

The listener stayed open long after service `74`, but it was not yet open when
service `74` arrived. V837 therefore cannot rule out a missed state transition
at service `74` publication time.

## Service-notifier Result

- endpoint: service-notifier `66/46081`, node `0`, port `2`
- request: bounded `REGISTER_LISTENER` for `msm/modem/wlan_pd`
- response: QMI success, current state `0x7fffffff` / `uninit`
- indication: none
- hold: `15006 ms`, poll timeout reached

## Lower Window

- order: `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`
- service `180`: present
- service `74`: present
- exact known ASoC warning: present and accepted
- WLFW/service `69`: absent
- BDF: absent
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
- Cleanup reboot restored healthy native v724; follow-up `version`, `status`,
  and `selftest verbose` were responsive.

## Conclusion

V837 shows the current listener placement is too late by about `613 ms` relative
to service `74`. The next gate should make listener registration earlier or
concurrent with service-notifier publication, then repeat the same no-HAL,
no-connect lower-window proof.
