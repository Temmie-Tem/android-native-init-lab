# Native Init V792 Known-ASoC-Warning CNSS/WLFW Plan

## Goal

Run the current clean-DSP plus CNSS/WLFW readback path while tolerating only the
exact ASoC `pm_qos` warning signature classified by V791.

## Scope

- Arm the V641 clean-DSP one-shot flag and reboot.
- Refresh V401 SELinuxfs mount and V490 policy load after that reboot.
- Start only the lower companion plus `cnss_diag` and `cnss-daemon`.
- Read back service `69`, WLFW, BDF, and `wlan0` evidence.
- Treat the exact service `74` -> ASoC duplicate `pm_qos` warning as a known
  allowed signature only if sound-card registration follows.

## Hard Gates

- No service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect, credential
  use, DHCP/routes, or external ping.
- No `esoc0` open, subsystem state write, module load/unload, bind/unbind,
  boot image write, partition write, or custom kernel flash.
- Any warning other than the exact known ASoC `pm_qos` signature remains a
  blocker.
- WLFW/service `69`, BDF, or `wlan0` is required for a real Wi-Fi progression
  decision.

## Validation

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

## Expected Routing

- WLFW/service `69`, BDF, or `wlan0` appears: capture interface and BDF state
  before any scan/connect.
- MHI/QCA appears without WLFW: classify MHI-to-WLFW gap.
- CNSS starts but WLFW remains absent under the known warning: route to the
  current CNSS continuation blocker below HAL/connect.
