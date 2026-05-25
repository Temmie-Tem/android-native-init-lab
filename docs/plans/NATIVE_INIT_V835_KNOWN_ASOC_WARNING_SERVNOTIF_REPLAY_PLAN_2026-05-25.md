# Native Init V835 Known-ASoC-Warning Service-notifier Replay Plan

## Goal

Run the corrected `msm/modem/wlan_pd` service-notifier listener inside the best
known native lower window selected by V834: clean-DSP plus CNSS lower companion
with only the known Android-parity ASoC warning tolerated.

## Why This Gate

V833 proved the listener payload/model is valid because Android returns
`UP` for the same `msm/modem/wlan_pd` request. V830/V831 returned native
`UNINIT`. V834 selected V835 because V792 is the strongest current native lower
window:

```text
clean-DSP + lower companions + cnss_diag/cnss-daemon
  -> service-notifier 180/74 present
  -> known ASoC pm_qos warning tolerated
  -> WLFW/BDF/wlan0 absent
```

V835 asks whether the service-notifier state becomes `UP` in that stronger
native window.

## Scope

V835 adds:

- `scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py`

It reuses:

- helper v128 service-notifier listener support;
- V787 clean-DSP arm-only proof;
- V401/V490 current-boot SELinux runtime prep;
- V792 known-ASoC-warning lower-window guard.

## Hard Guardrails

- No service-manager, Wi-Fi HAL, `wificond`, supplicant, scan/connect/link-up,
  credential use, DHCP, route change, or external ping.
- No `esoc0` open, subsystem state write, bind/unbind, driver override, module
  load/unload, partition write, boot image write, or custom kernel flash.
- Only the bounded service-notifier listener QMI payload is allowed in addition
  to no-QMI QRTR readback.
- Reboot cleanup is mandatory after the lower window.

## Success Criteria

- Helper v128 deploy/readiness passes.
- Clean-DSP inline proof passes.
- V401/V490 current-boot prep passes.
- Lower companion starts `qrtr-ns,rmt_storage,tftp_server,pd-mapper,cnss_diag,cnss-daemon`.
- Service-notifier listener request is sent to service `66/46081` and receives
  QMI result `0`, error `0`.
- If state is `UP`, next gate watches WLFW/service69/BDF/`wlan0` below
  HAL/connect.
- If state remains `UNINIT`, the lower WLAN-PD state-up trigger is still absent
  even in the best known native window.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py

python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
  --out-dir tmp/wifi/v835-known-asoc-warning-servnotif-replay-plan-check \
  plan

python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
  --out-dir tmp/wifi/v835-known-asoc-warning-servnotif-replay-preflight \
  preflight
```

## Live Command

```bash
python3 scripts/revalidation/native_wifi_known_asoc_warning_servnotif_replay_v835.py \
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
