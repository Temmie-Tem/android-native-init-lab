# Native Init V795 Lower-Window mdm3/esoc Observer Plan

## Goal

Observe mdm3/esoc, ICNSS, QRTR/service `69`, WLFW, BDF, and `wlan0` surfaces
inside the proven firmware-backed `subsys_modem` holder window.

## Scope

- Use V794 as the idle-surface prerequisite.
- Prepare read-only firmware mounts for `/vendor/firmware_mnt` and
  `/vendor/firmware-modem`.
- Open only the proven `subsys_modem` holder path.
- Read modem/esoc0, ICNSS, QRTR/service `69`, WLFW/BDF markers, and `wlan0`
  state.
- Cleanup with reboot and prove v724 health.

## Hard Gates

- No lower companion start.
- No `cnss_diag` or `cnss-daemon` start.
- No service-manager, Wi-Fi HAL, `boot_wlan`, qcwlanstate write, scan/connect,
  credential use, DHCP/routes, or external ping.
- No `esoc0` open/hold, module load/unload, bind/unbind, boot image write,
  partition write, or custom kernel flash.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py
python3 scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py --out-dir tmp/wifi/v795-static-plan-check plan
python3 scripts/revalidation/native_wifi_lower_window_mdm3_esoc_observer_v795.py run \
  --assume-yes \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-cleanup-reboot
git diff --check
```

## Expected Routing

- If WLFW/BDF/`wlan0` appears, stop before credentials and capture interface
  state.
- If `subsys_modem` only brings `mss` online while mdm3 remains offlining, route
  V796 to the mdm3/esoc trigger contract or Android vendor-init delta.
- Do not widen to HAL, scan/connect, DHCP, or external ping until service `69`,
  BDF, and `wlan0` are proven.
