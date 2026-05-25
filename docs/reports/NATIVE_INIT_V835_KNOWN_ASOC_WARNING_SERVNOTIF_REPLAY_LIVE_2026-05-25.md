# Native Init V835 Known-ASoC-Warning Service-notifier Replay Live Report

## Result

- decision: `v835-native-servnotif-still-uninit`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py`
- evidence: `tmp/wifi/v835-known-asoc-warning-servnotif-replay-live-20260525-131408/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py

python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
  --out-dir tmp/wifi/v835-known-asoc-warning-servnotif-replay-plan-check \
  plan

python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
  --out-dir tmp/wifi/v835-known-asoc-warning-servnotif-replay-preflight \
  preflight

python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
  --out-dir tmp/wifi/v835-known-asoc-warning-servnotif-replay-live-20260525-131408 \
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
  --allow-service-notifier-listener-replay \
  --assume-yes \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| helper | v128 deployed by serial appendfile; sha matched |
| clean-DSP | inline V787 proof passed |
| SELinux prep | V401 and V490 passed |
| lower companion | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| service-notifier endpoint | service `66`, instance `46081`, node `0`, port `2` |
| listener response | QMI result `0`, error `0`, state `uninit` |
| state indication | not observed |
| QRTR readback | service-notifier event present, WLFW service `69/1` absent |
| lower markers | QRTR RX/TX and sysmon present; service-notifier `2`; WLFW/BDF/`wlan0` absent |
| warning guard | exact known ASoC `pm_qos` warning matched |
| cleanup | reboot cleanup; post-cleanup native v724 status and selftest healthy |

## Interpretation

V835 is a stronger negative than V830/V831. The listener no longer ran only in
the basic native lower window. It ran inside the V792-derived best native lower
window where service-notifier `180/74` are present and the known ASoC warning is
tolerated.

The service-notifier listener still returned:

```text
current_state = uninit
```

Therefore the missing condition is not:

- pd-mapper domain-list population;
- service-notifier endpoint visibility;
- listener payload/model;
- early/late listener timing;
- clean-DSP plus CNSS companion ordering;
- known ASoC warning handling.

The remaining blocker is a lower native WLAN-PD state-up trigger that Android
has but this native path still lacks.

## Safety

- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No `esoc0` open, subsystem state write, bind/unbind, driver override, module
  load/unload, boot image write, partition write, or custom kernel flash
  executed.
- The only QMI payload was the bounded service-notifier listener request.
- Cleanup reboot restored healthy native v724.
- No Wi-Fi secret material was written to tracked output.

## Next

V836 should be host-only first. It should compare Android and native evidence
around the remaining `msm/modem/wlan_pd` state-up contract and identify what
Android does after service-notifier `180/74` that native V835 still lacks.

Do not widen to Wi-Fi HAL, scan/connect, DHCP, routes, external ping, or custom
kernel flashing until native can produce WLAN-PD `UP`, WLFW service `69`, BDF,
wiphy, or `wlan0`.
