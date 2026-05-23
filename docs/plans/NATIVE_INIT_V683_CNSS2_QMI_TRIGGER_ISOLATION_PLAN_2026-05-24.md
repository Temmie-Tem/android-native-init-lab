# Native Init V683 cnss2/QMI Trigger Isolation Plan

## Objective

Classify the V682 pre-WLFW gap into an actionable next trigger. V682 proved the
current live path reaches service `74`, CNSS retry, focused ICNSS/QCA6390 sysfs,
and Android userspace start-only, but still never reaches WLFW, BDF, firmware
ready, or `wlan0`.

V683 is host-only. It consumes existing V682, V651, V654, and V669 evidence to
answer whether the next gate should be direct cnss2/QCA power manipulation or a
narrow `cnss-daemon` vendor Binder continuation capture/repair.

## Inputs

- `tmp/wifi/v682-cnss2-wlfw-progression-observer-live/manifest.json`
- `tmp/wifi/v651-cnss-wlfw-continuation/manifest.json`
- `tmp/wifi/v654-binder-runtime-mismatch-classifier/manifest.json`
- `tmp/wifi/v669-android-cnss2-runtime-delta/manifest.json`

## Gate

Run `scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py` to:

1. verify V682 current live evidence still stops before WLFW;
2. verify Android reaches WLFW/QMI/BDF/`wlan0` without a CNSS Binder transaction;
3. verify native `cnss-daemon` Binder transaction failure appears before WLFW;
4. decide whether direct QCA/sysfs power writes are justified;
5. route V684 to the narrowest next capture/repair target.

## Forbidden Actions

- No device command.
- No mount or bind mount.
- No daemon or service-manager start.
- No Wi-Fi HAL start.
- No supplicant or hostapd start.
- No scan/connect/link-up.
- No credential, DHCP, route change, or external ping.
- No sysfs or debugfs write.
- No boot image or partition write.

## Success Criteria

- V683 runs host-only.
- It classifies whether the next trigger is a direct cnss2/QCA power edge or a
  `cnss-daemon` continuation edge.
- If native Binder failure remains the first native-only stop before WLFW, V684
  is routed to a narrow `cnss-daemon` vndbinder transaction target capture or
  repair gate.

## Commands

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py

python3 scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py \
  --out-dir tmp/wifi/v683-cnss2-qmi-trigger-isolation-plan \
  plan

python3 scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py \
  --out-dir tmp/wifi/v683-cnss2-qmi-trigger-isolation \
  run
```

## Expected Routing

If V683 classifies the native `cnss-daemon` vndbinder transaction as the
pre-WLFW trigger, V684 should not jump to scan/connect or direct QCA sysfs
writes. It should capture or repair the exact vendor Binder transaction target
with the least invasive primitive available. Private Binder debugfs is allowed
only as a target-identification mechanism, not as a broad debug session.
