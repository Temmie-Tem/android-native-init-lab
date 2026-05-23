# Native Init V699 Provider-first CNSS Helper Plan

- date: `2026-05-24 KST`
- cycle: `v699`
- type: helper build prep

## Goal

V698 proved that the Binder `29189/-22` line belongs to the initial
pre-provider `cnss-daemon`, while the post-provider retry reaches CNSS netlink
without a matching Binder failure or WLFW progression.

V699 prepares a helper mode that removes that confounder:

- do **not** start the initial pre-provider `cnss-daemon`;
- still start lower QRTR/firmware companion services and `cnss_diag`;
- wait for service-notifier `74` after `cnss_diag`;
- start service managers and prove `vendor.qcom.PeripheralManager`;
- start exactly one fresh `cnss-daemon` after provider proof.

## Gate

Expected helper marker:

- `a90_android_execns_probe v119`

Expected mode:

- `wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only`

Expected order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,
servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,
per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry
```

## Guardrails

V699 helper prep must not:

- contact the device;
- deploy the helper;
- start daemons on the live device;
- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan, connect, link up, use credentials, run DHCP, change routes, or external
  ping;
- write sysfs/debugfs, boot images, or partitions.

## Implementation

Update `stage3/linux_init/helpers/a90_android_execns_probe.c` to v119:

1. add the provider-first CNSS mode to usage and mode routing;
2. include it in service-manager/private-namespace companion modes;
3. suppress only the initial pre-provider `cnss-daemon`;
4. keep `cnss_diag` before the service `74` gate;
5. move the service `74` gate index from after initial `cnss-daemon` to after
   `cnss_diag` for this mode;
6. report `wifi_companion_start.initial_cnss_daemon.suppressed=1`;
7. preserve vndservice query and post-provider single CNSS start.

## Validation Plan

```bash
mkdir -p tmp/wifi/v699-execns-helper-v119-build
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe
strings tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v119|provider-first-cnss|initial_cnss_daemon\\.suppressed'
git diff --check
```
