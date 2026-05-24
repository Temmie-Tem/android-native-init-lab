# Native Init V746 Sysmon-gated MDM Helper Plan

- date: `2026-05-24 KST`
- native build on device: `A90 Linux init 0.9.68 (v724)`
- helper target: `a90_android_execns_probe v124`
- runner: `scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py`

## Goal

Start `/vendor/bin/mdm_helper` only after the lower native Wi-Fi stack reaches
the reproducible `sysmon-qmi` marker. This tests whether `mdm_helper` can move
the current blocker past `mdm3=OFFLINING` toward MHI/WLFW/BDF/`wlan0`.

## Basis

V745 deployed helper v123 and ran the service `180` gated proof safely, but the
service-notifier `180` gate did not open in that boot. The same run still
reached QRTR RX/TX and `sysmon-qmi`, so service `180` is too narrow as the next
gate. V746 lowers the gate to `sysmon-qmi` while preserving the same safety
boundary.

## Scope

Allowed:

- deploy static helper v124 to `/cache/bin/a90_android_execns_probe`
- mount vendor/firmware partitions read-only inside the private namespace
- hold `subsys_modem` only; do not raw-open `esoc0`
- start `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`, `cnss_diag`, `cnss-daemon`
- wait for `sysmon-qmi`
- start `/vendor/bin/mdm_helper` after that gate only
- capture dmesg, QRTR, sysfs, process, and post-reboot health evidence

Forbidden:

- service-manager / hwservicemanager / vndservicemanager start
- Wi-Fi HAL start
- scan/connect/link-up
- credentials, DHCP, routing, external ping
- persistent writes to `/system`, `/vendor`, `/data`, `/apex`
- raw `esoc0` open

## Success Criteria

Minimum pass:

- helper v124 is static ARM64 and exposes `wifi-companion-sysmon-gated-mdm-helper-start-only`
- deploy preflight is clean
- live run opens the `sysmon-qmi` gate or reports a bounded gate miss
- postflight reboot cleanup returns native init to healthy state
- no service-manager/HAL/scan/connect/external ping happens

Forward progress:

- `mdm_helper_start_executed=True`
- and any of `mdm3 ONLINE`, WLAN-PD, MHI/QCA6390, WLFW service `69`, BDF, or `wlan0`
  appears.

Stop condition:

- kernel warning, helper crash, cleanup failure, service-manager/HAL/connect crossing,
  or persistent state mutation outside the declared boundary.

## Validation Commands

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v746-execns-helper-v124-build/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py \
  scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py

python3 scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py \
  --out-dir tmp/wifi/v746-mdm-helper-sysmon-live-plan-final \
  plan

python3 scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py \
  --out-dir tmp/wifi/v746-execns-helper-v124-deploy-preflight-final \
  --transfer-method serial \
  --serial-chunk-size 1850 \
  preflight
```

## Next Gate

Deploy helper v124, refresh current-boot SELinuxfs/policy-load prep, then run
V746 live. If `mdm_helper` starts and lower markers still do not move, route
away from `mdm_helper` and classify the remaining modem/WLAN-PD trigger.
