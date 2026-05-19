# v363 Plan: Wi-Fi Bring-Up Phase 0 Baseline Gate

- date: `2026-05-20`
- scope: active Wi-Fi bring-up direction accepted, but first phase is a live
  no-scan/no-connect baseline gate
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V362 bounded CNSS start-only PASS

## Summary

The operator requested Wi-Fi bring-up. The project now treats Wi-Fi bring-up as
an active goal, but the execution path remains phased:

1. Phase 0: capture current native Wi-Fi/CNSS surface and confirm no accidental
   link-up.
2. Phase 1: no-scan/no-connect service readiness gate for HAL/service-manager
   prerequisites.
3. Phase 2: bounded service start-only probes, one component at a time.
4. Phase 3: link-surface creation only if wlan/wiphy/rfkill readiness appears.
5. Phase 4: scan/connect/credential/DHCP only under a separate explicit plan.

V363 performs Phase 0 only. It does not start Wi-Fi HAL, `wificond`,
supplicant, hostapd, `cnss_diag`, or AP/network association.

## References

- Android Wi-Fi uses separate Vendor HAL, Supplicant HAL, and Hostapd HAL
  surfaces. For Android 13 and lower, the Wi-Fi interfaces are HIDL-based:
  <https://source.android.com/docs/core/connect/wifi-hal>
- This supports keeping HAL/service-manager readiness as the next gate before
  supplicant/scan/connect.

## Commands

```bash
RUN_ID=v363-bringup-preflight-$(date +%Y%m%d-%H%M%S)
mkdir -p tmp/wifi/$RUN_ID/commands

python3 scripts/revalidation/a90ctl.py version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py wifiinv full
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
python3 scripts/revalidation/a90ctl.py ls /sys/class/net
python3 scripts/revalidation/a90ctl.py ls /sys/class/rfkill
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox ps -A -o pid,stat,comm
python3 scripts/revalidation/a90ctl.py stat /sys/module/wlan
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox ls /sys/module/wlan/parameters
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox cat /sys/module/wlan/parameters/fwpath
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox cat /sys/module/wlan/parameters/con_mode
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox cat /sys/module/wlan/parameters/country_code
python3 scripts/revalidation/a90ctl.py stat /sys/devices/platform/soc/18800000.qcom,icnss
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox ls -l /sys/devices/platform/soc/18800000.qcom,icnss/driver
python3 scripts/revalidation/a90ctl.py stat /sys/devices/platform/soc/a0000000.qcom,cnss-qca6390
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox ls -l /sys/devices/platform/soc/a0000000.qcom,cnss-qca6390/driver
python3 scripts/revalidation/wifi_bringup_gate_v2.py \
  --out-dir tmp/wifi/v363-bringup-gate-v2-refresh-20260520
```

## Acceptance

- native shell remains responsive;
- current native baseline is recorded;
- no `wlan*` interface appears;
- no Wi-Fi rfkill appears;
- no CNSS daemon leak appears;
- ICNSS core state and QCA6390 bind state are captured;
- no scan/connect/link-up/credential/DHCP/routing action is performed.

## Next

If Phase 0 passes, the next step is not AP connection. The next step is a
no-scan/no-connect HAL/service-manager readiness gate that reuses the existing
Binder/property/private-namespace evidence and decides whether a bounded
`vendor.wifi_hal_*` start-only probe is defensible.
