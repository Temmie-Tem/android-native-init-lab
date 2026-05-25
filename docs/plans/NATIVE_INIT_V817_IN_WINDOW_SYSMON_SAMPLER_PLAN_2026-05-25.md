# Native Init V817 In-Window Sysmon Sampler Plan

## Goal

Sample the V815 subsystem/sysmon/service-locator surfaces inside the existing
bounded lower-trigger window selected by V816.

V816 showed that the lower trigger advances mss/QRTR/sysmon but not
mdm3/service-publication. V817 captures the same surfaces at before-holder,
after-holder, and after-companion checkpoints to prove where the gap remains.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py`
- Inputs:
  - V816 idle-vs-trigger delta manifest.
  - V401 SELinuxfs mount proof.
  - V490 native SELinux policy-load proof.
  - Existing lower-window firmware mount, `subsys_modem` holder, and
    companion/CNSS diagnostic stack harness.

## Hard Gates

- Stock v724 only; no custom kernel flash or boot image write.
- No partition write outside established temporary runtime/evidence paths.
- No `esoc0` open, `qcwlanstate on/off`, bind/unbind, driver override, or
  module load/unload.
- No service-manager start, Wi-Fi HAL start, wificond, scan/connect/link-up,
  credential use, DHCP, route change, or external ping.
- Live actions are bounded to current-boot prep, firmware mounts,
  `subsys_modem` holder, lower companion/CNSS diagnostic stack, read-only
  sampling, and cleanup reboot.

## Success Criteria

- V817 compiles and plan-only manifest passes.
- V816 manifest is present and passed.
- Current-boot prep passes V401 and V490.
- Firmware mounts and `subsys_modem` holder open successfully.
- Snapshots are captured at before-holder, after-holder, and after-companion.
- mss advances to `ONLINE` while mdm3 remains `OFFLINING`.
- service74/WLAN-PD/WLFW/BDF/`wlan0` remain absent below HAL/connect.
- Cleanup reboot restores healthy stock v724.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py

python3 scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py \
  --out-dir tmp/wifi/v817-in-window-sysmon-sampler-plan-check \
  plan

python3 scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py run

git diff --check
```
