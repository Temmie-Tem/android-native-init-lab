# Native Init V697 CNSS Binder Runtime Target Plan

- date: `2026-05-24 KST`
- cycle: `v697`
- type: host-only classifier

## Goal

V697 consumes the V666/V667/V681 causal-chain clarification and the newer
V684/V695/V696 evidence to choose the next repair target without another live
action.

The clarified lower-chain model remains valid:

```text
modem ONLINE
  -> service-notifier 180/74
  -> cnss2/QCA6390 progression
  -> WLFW service 69
  -> BDF, firmware-ready, wlan0
```

However, V667/V681 already answered the original V666 read-only question:
service-notifier `180/74` appears, but cnss2/WLFW progression does not follow.
V695 then proved `vendor.qcom.PeripheralManager` registration and a fresh
`cnss-daemon` retry. V696 ranked the remaining native-only gap as
`cnss-daemon` Binder/runtime continuation before WLFW.

V697 narrows that Binder/runtime continuation to a concrete target class:

- `cnss-daemon` and retry use `/dev/vndbinder`;
- `vndservicemanager` is ready on `/dev/vndbinder`;
- `vendor.qcom.PeripheralManager` registration is proven;
- `cnss-daemon` SELinux preexec is correct;
- native still hits transaction `29189/-22` before WLFW.

## Gate

Expected success label:

- `v697-cnss-vndbinder-transaction-framing-targeted`

Other labels:

- `v697-cnss-binder-runtime-target-classifier-blocked`
- `v697-cnss-binder-target-needs-manual-review`
- `v697-cnss-binder-runtime-target-inconclusive`

## Guardrails

V697 must not:

- contact the device;
- mount or bind mount filesystems;
- start daemons, service managers, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- scan, connect, link up, use credentials, run DHCP, change routes, or external
  ping;
- write sysfs/debugfs, boot images, or partitions.

## Implementation

Add `scripts/revalidation/native_wifi_cnss_binder_runtime_target_classifier_v697.py`
to:

1. read V684 static target classification;
2. read V695 provider-confirmed retry evidence;
3. read V696 post-provider blocker classification;
4. parse V695 helper output for Binder fd targets and child SELinux preexec;
5. parse V695 dmesg for `cnss-daemon` transaction `29189/-22`, generic
   context-manager ioctl `-22`, duplicate `pm_qos`, and `wlfw_start`;
6. demote generic `/dev/binder` and `/dev/hwbinder` ioctl `-22` when
   `/dev/vndbinder` provider registration is proven;
7. classify the next unit as a narrow `cnss-daemon`/`libperipheral_client`
   vendor Binder transaction framing capture or repair.

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_binder_runtime_target_classifier_v697.py
python3 scripts/revalidation/native_wifi_cnss_binder_runtime_target_classifier_v697.py \
  --out-dir tmp/wifi/v697-cnss-binder-runtime-target-classifier-rerun \
  run
git diff --check
```
