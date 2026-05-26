# V1028 PM Proxy Helper Modem-Get Classifier Plan

- date: `2026-05-26`
- type: host-only classifier
- inputs:
  - `tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json`
  - `tmp/wifi/v1027-pm-full-contract-live/manifest.json`
  - `tmp/wifi/v1027-pm-full-contract-live/native/post-dmesg-wifi-esoc-tail.txt`
  - `tmp/wifi/v1027-pm-full-contract-live/native/post-ps.txt`

## Objective

Classify why V1027 could not reproduce the Android PM full-contract fd
predicate before adding another live actor start or subsystem retry.

## Gate

Compare the known Android-positive contract with the native V1027 result:

```text
Android V1024:
  pm_proxy_helper -> /dev/subsys_modem
  pm-service      -> /dev/subsys_modem
  mdm_helper      -> /dev/esoc-0
  WLFW/FW-ready/wlan0 chain present

Native V1027:
  pm_proxy_helper started
  pm-service started
  pm-proxy started
  mdm_helper -> /dev/esoc-0 present
  PM full-contract fd predicate missing
```

## Guardrails

- host-only evidence parsing
- no device command
- no actor start
- no daemon start
- no Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP, route, or external ping
- no `/dev/subsys_esoc0` open
- no eSoC ioctl, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image or partition write

## Success Criteria

The classifier passes if it proves:

- V1024 contains the Android PM fd contract and WLFW-good chain.
- V1027 reproduced the PM actor order.
- V1027 kept lower/Wi-Fi guardrails closed.
- V1027 shows `pm_proxy_helper` entering modem subsystem-get but not reaching
  an observable `/dev/subsys_modem` fd.
- Cleanup reboot completed after the unsafe actor state.

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_proxy_helper_modem_get_classifier_v1028.py
python3 scripts/revalidation/native_wifi_pm_proxy_helper_modem_get_classifier_v1028.py run
```

## Next

If V1028 passes, V1029 should compare Android/native `pm_proxy_helper` runtime
inputs and service context. Repeating V1027 unchanged is not useful because the
blocker occurs before post-provider retry, CNSS, Wi-Fi HAL, or scan/connect.
