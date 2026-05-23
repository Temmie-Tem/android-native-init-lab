# Native Init V671 Service74 Android Userspace-order Plan

- date: `2026-05-24 KST`
- cycle: `V671`
- status: planned
- helper: `a90_android_execns_probe v111`
- runner: `scripts/revalidation/native_wifi_service74_android_order_v671.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v111_deploy_preflight.py`

## Goal

V670 selected the next live mutation: keep the V668 service `74` positive lower
path, then add the Android-observed userspace order before a fresh
`cnss-daemon` retry. V671 tests whether Wi-Fi HAL legacy/ext plus `wificond`
are the missing pre-CNSS runtime surface needed to advance WLFW/BDF/`wlan0`.

## Scope

V671 uses this bounded helper order:

```text
qrtr_ns -> rmt_storage -> tftp_server -> pd_mapper
  -> cnss_diag -> cnss_daemon -> service74_gate
  -> servicemanager -> hwservicemanager -> vndservicemanager
  -> vndservicemanager_ready -> cnss_daemon_initial_cleanup
  -> wifi_hal_legacy -> wifi_hal_ext -> wificond -> cnss_daemon_retry
```

The helper adds only start-only child processes inside the private namespace.
It observes dmesg, QRTR readback, focused cnss2/sysfs capture, process
postflight state, and cleanup after reboot.

## Guardrails

V671 does not authorize:

- supplicant or hostapd start;
- IWifi.start, qcwlanstate, or sysfs driver-state writes;
- Wi-Fi scan/connect/link-up, credentials, DHCP, routing, or external ping;
- direct ADSP/CDSP/SLPI boot-node writes;
- `esoc0` open/hold;
- boot image or partition writes.

## Success Criteria

The proof passes if:

- helper v111 is deployed and exposes the V671 mode;
- current-boot V641/V401/V490 prerequisites are ready;
- service `74` opens again;
- service-manager trio becomes ready and initial `cnss-daemon` cleanup is safe;
- Wi-Fi HAL legacy/ext, `wificond`, and retry `cnss-daemon` start in the
  expected order;
- all started children are postflight safe after bounded cleanup.

Decision labels distinguish:

| decision | meaning |
| --- | --- |
| `v671-android-userspace-wifi-surface-advanced` | WLFW/BDF/firmware-ready/`wlan0` markers advanced |
| `v671-android-userspace-no-wlfw-advance` | HAL/wificond/CNSS retry executed but WLFW/BDF/`wlan0` remained absent |
| `v671-service74-gate-timeout` | Android userspace services were withheld because lower service `74` did not open |
| `v671-helper-order-contract-gap` | helper did not execute the expected V671 order |
| `v671-cleanup-review` | bounded cleanup was not proven safe |

## Commands

Build helper:

```bash
mkdir -p tmp/wifi/v671-execns-helper-v111-build
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v671-execns-helper-v111-build/a90_android_execns_probe
```

Plan:

```bash
python3 scripts/revalidation/native_wifi_service74_android_order_v671.py \
  --out-dir tmp/wifi/v671-service74-android-userspace-plan \
  plan
```

Deploy preflight/deploy:

```bash
python3 scripts/revalidation/wifi_execns_helper_v111_deploy_preflight.py \
  --out-dir tmp/wifi/v671-execns-helper-v111-deploy-preflight \
  preflight

python3 scripts/revalidation/wifi_execns_helper_v111_deploy_preflight.py \
  --out-dir tmp/wifi/v671-execns-helper-v111-deploy-live \
  --approval-phrase 'approve v671 deploy execns helper v111 only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run
```

Live proof:

```bash
python3 scripts/revalidation/native_wifi_service74_android_order_v671.py \
  --out-dir tmp/wifi/v671-service74-android-userspace-live \
  --approval-phrase 'approve v671 service74 Android userspace-order start-only proof only; no supplicant, no scan/connect/link-up, no DHCP and no external ping' \
  --apply --assume-yes run
```

## Next

If V671 advances WLFW/BDF/`wlan0`, the next gate should classify the exact
firmware/netdev state before any supplicant or scan/connect attempt. If it does
not advance, inspect HAL/wificond runtime output and binder/`pm_qos` deltas
before enabling IWifi.start or supplicant.
