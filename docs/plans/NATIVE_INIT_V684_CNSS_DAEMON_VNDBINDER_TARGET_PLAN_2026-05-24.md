# Native Init V684 cnss-daemon vndbinder Target Plan

## Objective

V684 narrows the V683 pre-WLFW blocker from "native `cnss-daemon`
vndbinder continuation" to a concrete Binder target candidate.

The V666/V667 direction remains valid: service-notifier `180/74` being visible
from userspace does not prove the WLAN/QCA6390 path advanced to WLFW service
`69`. V683 then showed the native-only stop occurs at `cnss-daemon` vendor
Binder transaction `-22` before WLFW/BDF/`wlan0`. V684 therefore classifies
which vendor Binder service `cnss-daemon` is most likely trying to use.

## Inputs

- `tmp/wifi/v683-cnss2-qmi-trigger-isolation/manifest.json`
- `tmp/wifi/v682-cnss2-wlfw-progression-observer-live/manifest.json`
- `tmp/wifi/v682-cnss2-wlfw-progression-observer-live/arm-v679-v112-observer/live/manifest.json`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmiservices.so`

## Method

Run a host-only classifier:

```sh
python3 scripts/revalidation/native_wifi_cnss_daemon_vndbinder_target_v684.py \
  --out-dir tmp/wifi/v684-cnss-daemon-vndbinder-target \
  run
```

The classifier:

1. verifies V683 input evidence is passing;
2. extracts bounded static strings from local exported vendor ELF files;
3. checks whether `cnss-daemon` imports `libperipheral_client.so`;
4. checks whether `libperipheral_client.so` uses `/dev/vndbinder`,
   `defaultServiceManager`, `IPeripheralManager`, and
   `vendor.qcom.PeripheralManager`;
5. checks that `libqmiservices.so` is not the static Binder target candidate;
6. correlates V682 live evidence showing `cnss-daemon` mapped
   `libperipheral_client.so` before the Binder `-22` / no-WLFW gap;
7. records that the literal live service name is not yet confirmed, so the next
   unit must prove live availability/start order rather than relying only on
   static strings.

## Success Criteria

- decision is `v684-cnss-daemon-peripheral-manager-target-candidate`;
- `cnss-daemon` static surface includes `libperipheral_client.so`;
- `libperipheral_client.so` static surface includes `libbinder.so`,
  `/dev/vndbinder`, `defaultServiceManager`, and
  `vendor.qcom.PeripheralManager`;
- V682 live evidence includes both `cnss-daemon` and `libperipheral_client.so`;
- V682 live evidence still has service-notifier `180/74`, CNSS netlink, Binder
  `-22`, and no WLFW/QMI/BDF/firmware-ready/`wlan0` markers.

## Guardrails

V684 is host-only. It must not:

- contact the device;
- mount filesystems;
- start daemons, service-manager, Wi-Fi HAL, supplicant, or hostapd;
- scan/connect/link-up;
- use credentials, DHCP, routes, or external ping;
- write sysfs/debugfs, boot image, or partitions.

## Next Gate

If V684 passes, V685 should be a narrow
`vendor.qcom.PeripheralManager` live availability/start-order proof before
another `cnss-daemon` retry. Wi-Fi HAL, scan/connect, DHCP, routes, and
external ping stay blocked until WLFW/BDF/firmware-ready/`wlan0` progresses.
