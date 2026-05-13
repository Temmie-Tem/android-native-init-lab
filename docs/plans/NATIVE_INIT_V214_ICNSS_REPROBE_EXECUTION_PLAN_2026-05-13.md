# v214 Plan: ICNSS Reprobe Execution / Firmware Request Evidence

## Summary

v214 follows the v213 `path-only-pass` result. The goal is to run the first
controlled ICNSS driver reprobe under the guarded firmware path policy and
capture whether the kernel produces firmware request evidence, WLAN netdev,
rfkill, wiphy, or a clear failure signal.

This is still not Wi-Fi connection work. It must not start Android Wi-Fi
framework, Wi-Fi HAL, `wificond`, `wpa_supplicant`, `hostapd`, `cnss-daemon`,
scan/connect, rfkill writes, or WLAN link-up.

- baseline runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v213 PASS, `baseline-only` and `path-only-pass`
- helper source: `stage3/linux_init/helpers/a90_icnssctl.c`
- helper target: `/cache/bin/a90_icnssctl`
- collector: `scripts/revalidation/native_firmware_request_probe.py`
- evidence output: `tmp/wifi/v214-icnss-reprobe`
- report after execution:
  `docs/reports/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_2026-05-13.md`

## Reference Notes

- Linux firmware lookup searches the optional `firmware_class.path` before the
  default `/lib/firmware...` paths. Runtime writes are available through
  `/sys/module/firmware_class/parameters/path`; newline characters become part
  of the value, so fixed-target helpers should write without a newline:
  <https://docs.kernel.org/driver-api/firmware/fw_search_path.html>
- The Linux driver model exposes driver sysfs directories under the bus driver
  hierarchy. Driver callbacks include `probe()` for binding and `remove()` for
  unbinding. Reprobe must therefore be treated as a real driver lifecycle event,
  not as a read-only query:
  <https://docs.kernel.org/6.7/driver-api/driver-model/driver.html>
- sysfs attributes forward reads/writes to kernel show/store methods. Writable
  attributes are kernel ABIs and should be written only through exact, bounded
  operations:
  <https://www.kernel.org/doc/html/latest/filesystems/sysfs.html>

## Current Evidence Chain

- v209: temporary `sda29` ext4 `ro,noload` mount exposes vendor assets.
- v210: Wi-Fi firmware assets are present under native-visible vendor.
- v211: `/mnt/vendor/firmware` is the preferred firmware lookup policy.
- v212: `firmware_class.path=/mnt/vendor/firmware` applies, reads back, and
  rolls back safely.
- v213: read-only ICNSS baseline and path-only apply/readback/rollback pass,
  but no real firmware request evidence exists because reprobe was not run.

## Core Question

> With `/mnt/vendor/firmware` temporarily applied as `firmware_class.path`, does
> fixed-target `icnss` unbind/bind produce firmware request evidence, WLAN
> device state, or a clear failure reason, and can all state roll back cleanly?

## Execution Scope

Allowed:

- build static ARM64 `a90_icnssctl`
- deploy only to `/cache/bin/a90_icnssctl`
- validate deployed SHA256
- enable temporary USB NCM only for helper transfer if needed
- run `native_firmware_request_probe.py` with:
  - `--apply-path`
  - `--reprobe`
  - `--i-understand-icnss-reprobe`
- capture before/after:
  - `dmesg`
  - `/sys/class/net`
  - `/sys/class/rfkill`
  - `/sys/class/ieee80211`
  - `/sys/devices/platform/soc/18800000.qcom,icnss`
  - `/sys/bus/platform/drivers/icnss`
  - `firmware_class.path`
  - `/proc/mounts`

Forbidden:

- Wi-Fi scan/connect
- `rfkill block` / `rfkill unblock`
- `ip link set wlan* up`
- `svc wifi`, `cmd wifi`, `dumpsys wifi`
- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`,
  `hostapd`
- module load/unload
- firmware copy or mutation
- persistent mount or bind mount
- boot image or PID1 change

## Step Plan

1. Commit v213 before starting v214.
2. Build local helper:

   ```sh
   scripts/revalidation/build_icnssctl_helper.sh
   ```

3. Prepare NCM only for transfer:

   ```sh
   python3 scripts/revalidation/ncm_host_setup.py setup --allow-auto-interface
   ```

4. Install helper:

   ```sh
   python3 scripts/revalidation/tcpctl_host.py \
     --device-binary /cache/bin/a90_icnssctl \
     install \
     --local-binary stage3/linux_init/helpers/a90_icnssctl
   ```

5. Verify helper:

   ```sh
   python3 scripts/revalidation/a90ctl.py stat /cache/bin/a90_icnssctl
   python3 scripts/revalidation/a90ctl.py run /cache/bin/a90_icnssctl status
   ```

6. Run opt-in reprobe:

   ```sh
   python3 scripts/revalidation/native_firmware_request_probe.py \
     --native-bridge \
     --apply-path \
     --reprobe \
     --i-understand-icnss-reprobe \
     --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
     --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
     --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
     --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
     --out-dir tmp/wifi/v214-icnss-reprobe
   ```

7. Confirm cleanup:

   ```sh
   python3 scripts/revalidation/a90ctl.py cat /sys/module/firmware_class/parameters/path
   python3 scripts/revalidation/a90ctl.py cat /proc/mounts
   ```

8. Return USB to ACM-only unless NCM is intentionally still needed:

   ```sh
   python3 scripts/revalidation/ncm_host_setup.py off
   ```

## Decision Model

- `request-evidence-captured`
  - ICNSS reprobe produced dmesg delta or net/rfkill/wiphy evidence.
- `request-evidence-missing`
  - unbind/bind completed and rolled back, but no useful request/state delta was
    visible.
- `icnss-rebind-failed`
  - bind did not restore the ICNSS driver-bound state.
- `path-rollback-failed`
  - `firmware_class.path` did not restore to the saved original.
- `cleanup-failed`
  - `/mnt/vendor` or `/tmp/a90-v213-*` mount remained.
- `manual-review-required`
  - prerequisite evidence is inconsistent.

## Acceptance

- Deployed helper hash matches local static helper.
- Reprobe collector exits cleanly and writes manifest/summary.
- Final `firmware_class.path` is `/vendor/firmware_mnt/image`.
- No `/mnt/vendor` or `/tmp/a90-v213-*` mount remains.
- ICNSS driver is bound again after the probe.
- No active Wi-Fi connection/scan/framework command was run.
- Report records captured request evidence or the exact missing-evidence/failure
  decision.

## Next Step

If v214 captures request evidence and ICNSS returns to a safe state, v215 can
map exact firmware request names to the already discovered vendor assets and
rerun read-only nl80211/wiphy probes. If v214 fails to rebind or leaves unclear
state, stop Wi-Fi work and plan recovery/observability first.
