# Native Init V687 PeripheralManager Live Proof Plan

## Objective

V687 connects the V686 helper change to a bounded live proof. V686 added helper
v113 mode:

```text
wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only
```

V687 deploys/verifies helper v113 and runs one service `74` gated live window
that starts Android's PeripheralManager provider pair before a fresh
`cnss-daemon` retry.

This is still below Wi-Fi bring-up. It does not start Wi-Fi HAL, wificond,
supplicant, hostapd, scan/connect, use credentials, run DHCP, change routes, or
ping externally.

## Chain Under Test

```text
qrtr-ns
  -> rmt_storage
  -> tftp_server
  -> pd-mapper
  -> cnss_diag
  -> initial cnss-daemon
  -> service-notifier 74 gate
  -> servicemanager/hwservicemanager/vndservicemanager
  -> vndservicemanager readiness
  -> initial cnss-daemon cleanup
  -> per_mgr /vendor/bin/pm-service
  -> per_proxy /vendor/bin/pm-proxy
  -> fresh cnss-daemon retry
  -> classify WLFW/BDF/wlan0 progression
```

## Scripts

- deploy/preflight:
  `scripts/revalidation/wifi_execns_helper_v113_deploy_preflight.py`
- live proof:
  `scripts/revalidation/native_wifi_peripheral_manager_cnss_retry_v687.py`
- current-boot orchestrator:
  `scripts/revalidation/native_wifi_peripheral_manager_cnss_retry_orchestrator_v687.py`

## Required Current-boot Preconditions

- native baseline healthy;
- helper v113 deployed to `/cache/bin/a90_android_execns_probe`;
- V641 clean-DSP state refreshed;
- system mounted read-only;
- SELinuxfs visible;
- V490 policy-load proof refreshed for the current boot;
- temporary firmware mounts cleaned before the live proof;
- V535 private property root present.

## Success Labels

| label | meaning |
| --- | --- |
| `v687-peripheral-manager-cnss-retry-preflight-ready` | helper/runtime prerequisites are ready |
| `v687-peripheral-manager-provider-start-gap` | `pm-service` or `pm-proxy` did not become ready; classify provider output before retrying |
| `v687-provider-ready-cnss-retry-withheld` | provider was ready but fresh CNSS retry was not reached |
| `v687-peripheral-manager-cnss-retry-gap-persists` | provider and CNSS retry ran, but WLFW/BDF/`wlan0` remain absent |
| `v687-peripheral-manager-wifi-surface-advanced` | WLFW/BDF/firmware-ready/`wlan0` advanced; stop and classify before scan/connect |

## Guardrails

- no sysfs subsystem state writes;
- no `esoc0` open/hold;
- no direct ADSP/CDSP/SLPI boot-node writes;
- no Wi-Fi HAL/wificond/supplicant/hostapd;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no boot image or partition writes.

## Commands

Build helper v113 if the artifact is missing:

```sh
mkdir -p tmp/wifi/v686-execns-helper-v113-build
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v686-execns-helper-v113-build/a90_android_execns_probe
```

Deploy preflight:

```sh
python3 scripts/revalidation/wifi_execns_helper_v113_deploy_preflight.py \
  --out-dir tmp/wifi/v687-execns-helper-v113-deploy-preflight \
  preflight
```

Deploy, if needed:

```sh
python3 scripts/revalidation/wifi_execns_helper_v113_deploy_preflight.py \
  --out-dir tmp/wifi/v687-execns-helper-v113-deploy-live \
  --approval-phrase "approve v687 deploy execns helper v113 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Live proof:

```sh
python3 scripts/revalidation/native_wifi_peripheral_manager_cnss_retry_orchestrator_v687.py \
  --out-dir tmp/wifi/v687-peripheral-manager-cnss-retry-orchestrated-live \
  --apply \
  --assume-yes \
  run
```

## Next

If V687 reaches WLFW/BDF/`wlan0`, the next gate can move toward netdev
classification and only then scan/connect. If V687 still stops before WLFW,
the next unit should classify `pm-service`/`pm-proxy` logs, vndbinder
registration, or the remaining cnss2 pre-WLFW trigger instead of attempting
credentials or external ping.
