# Native Init V740 MDM Helper/Baseband Contract Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py`
- evidence: `tmp/wifi/v740-mdm-helper-baseband-contract/`
- decision: `v740-mdm-helper-post-notifier-gated-proof-selected`
- pass: `true`

## Summary

V740 was host-only. It reconciled the older V621/V622 `mdm_helper` evidence
with the current V739 native blocker and selected a narrower next gate:

```text
Do not blind-start mdm_helper.
Only consider mdm_helper as a bounded post-notifier candidate.
```

Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain
blocked.

## Key Results

| check | result |
| --- | --- |
| inputs | pass; V621/V622/V735/V738/V739 and V614 snapshot present |
| active blocker | pass; Android `mdm3=ONLINE`, native V738 `mdm3=OFFLINING` |
| static contract | pass; `vendor.mdm_helper` exists as disabled core service |
| launcher contract | pass; `vendor.mdm_launcher` is a `ro.baseband` wrapper |
| same-boot timing | pass; Android starts `mdm_helper` after service `180`, before WLAN-PD |
| live safety | review; helper is `shutdown critical` and fail action includes `panic` |

## Evidence Summary

Android V622 timing:

```text
service_notifier_180_ms=6915.578
mdm_launcher_boottime_ms=7920.193
mdm_helper_boottime_ms=8098.546
wlan_pd_ms=9342.940
helper_after_service180_ms=1182.968
helper_before_wlan_pd_ms=1244.394
```

Vendor init contract:

```text
service vendor.mdm_helper /vendor/bin/mdm_helper
  class core
  group system wakelock shell
  shutdown critical
  disabled

service vendor.mdm_launcher /vendor/bin/sh /vendor/bin/init.mdm.sh
  class main
  oneshot

init.mdm.sh:
  baseband=`getprop ro.baseband`
  if baseband is mdm/mdm2 -> start vendor.mdm_helper
```

Current native contrast:

```text
V735: service_notifier=1, but wlan_pd=0, wlfw=0, bdf=0, wlan0=0
V738: mss=ONLINE, mdm3=OFFLINING, MHI=0, service69=0, wlan0=0
V739: Android mdm3 ONLINE vs native mdm3 OFFLINING remains the active blocker
```

## Interpretation

`mdm_helper` is not the first lower trigger because Android service-notifier
`180` appears before `mdm_helper` starts. But it still starts before WLAN-PD and
before the final WLFW/BDF/`wlan0` continuation, so it remains a plausible
post-notifier candidate for the native `mdm3`/WLAN-PD gap.

That means the next live unit must be gated:

1. reproduce the safe native lower window first;
2. require observed lower service publication before starting `mdm_helper`;
3. start only `mdm_helper`, not Wi-Fi HAL or scan/connect;
4. observe `mdm3`, WLAN-PD, service `69`, MHI/QCA6390, BDF, and `wlan0`;
5. use bounded runtime, transcript capture, and reboot cleanup.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py

python3 scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py \
  --out-dir tmp/wifi/v740-mdm-helper-baseband-contract-plan plan

python3 scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py \
  --out-dir tmp/wifi/v740-mdm-helper-baseband-contract run
```

Final V740 output:

```text
decision: v740-mdm-helper-post-notifier-gated-proof-selected
pass: True
device_commands_executed: False
daemon_start_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V741 should be a bounded live proof, still below HAL/connect:

1. refresh V401/V490 prerequisites if needed;
2. enter the firmware-mounted modem holder + lower companion/CNSS-only window;
3. gate `mdm_helper` start on observed native lower service publication;
4. do not use `vendor.mdm_launcher` unless an Android-init-compatible `start`
   path is explicitly provided;
5. do not scan/connect, use credentials, run DHCP/routes, or external ping.
