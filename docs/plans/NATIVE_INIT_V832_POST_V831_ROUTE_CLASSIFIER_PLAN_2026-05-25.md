# Native Init V832 Post-V831 Route Classifier Plan

## Goal

Reconcile the completed V829/V830/V831 service-locator and service-notifier
proofs with earlier rejected trigger paths, then select the next non-duplicative
Wi-Fi gate.

## Current Basis

- V829 already sent the bounded `GET_DOMAIN_LIST wlan/fw` payload and received
  `msm/modem/wlan_pd` instance `180`.
- V830 registered a service-notifier listener for that domain, but native
  current state remained `uninit`.
- V831 moved the listener into the early lower companion window, but native
  current state still remained `uninit` and no indication arrived.
- V750/V752 rejected unchanged `boot_wlan`, `qcwlanstate`, and CNSS-before-
  `boot_wlan` retries.
- V764 rejected `mdm_helper` as the missing lower trigger.
- V775 paused custom OSRC diagnostic kernel flashing until boot compatibility is
  explained.

## Scope

V832 is host-only. It reads existing manifests and reports, writes private
evidence, and does not contact the device.

## Hard Guardrails

- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash.
- No QRTR socket, QMI payload, service-manager, Wi-Fi HAL, scan/connect,
  credential use, DHCP, route change, or external ping.
- No `esoc0` open, subsystem state write, bind/unbind, driver override, or
  module load/unload.

## Implementation

Add `scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py`.

The classifier must:

1. validate the expected V750, V752, V764, V775, V817, V818, V819, V826, V829,
   V830, and V831 decisions;
2. extract the V829 service-locator domain result;
3. extract the V830/V831 service-notifier listener state result;
4. classify duplicate or unsafe candidates;
5. select a next gate that answers a missing question rather than repeating a
   disproven native trigger.

## Success Criteria

- `manifest.json` records `decision=v832-android-service-notifier-positive-control-selected`.
- The candidate matrix rejects duplicate V829, listener timing, `boot_wlan`,
  `qcwlanstate`, `mdm_helper`, raw `esoc0`, and custom-kernel retries.
- The selected next gate is an Android-success positive control for the same
  `msm/modem/wlan_pd` service-notifier state query.
- Host-only guardrails remain false in the manifest.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py

python3 scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py \
  --out-dir tmp/wifi/v832-post-v831-route-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py run
```

## Next If Passing

V833 should define a bounded Android reference positive-control for the exact
service-notifier listener query. The point is to distinguish:

- native lower stack genuinely leaves WLAN-PD `uninit`; versus
- the listener payload/model is incomplete even on an Android-success runtime.
