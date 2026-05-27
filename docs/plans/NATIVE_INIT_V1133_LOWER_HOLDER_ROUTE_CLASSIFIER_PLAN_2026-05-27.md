# Native Init V1133 Lower Holder Route Classifier Plan

Date: `2026-05-27`

## Goal

Reconcile the post-V1132 lower modem evidence and choose the next route toward
native Wi-Fi bring-up.

V1132 closed another helper-private `/dev/subsys_modem` nonblocking/pre-holder
retry. V1133 must decide whether the next useful work is another private holder
retry, another broad BPF/trace path, or a composite of already-proven lower and
upper preconditions.

## Evidence Inputs

- V731 firmware-mounted outer `subsys_modem` holder positive:
  `tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json`
- V1113 recent outer global holder plus PM observer attempt:
  `tmp/wifi/v1113-global-firmware-pm-connect-live/manifest.json`
- V1128 post-policy provider/CNSS PM success:
  `tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-classifier/manifest.json`
- V1131 helper-private modem pre-holder live/classifier:
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/manifest.json`
  and
  `tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live/manifest.json`
- V1132 subsystem nonblock classifier:
  `tmp/wifi/v1132-subsys-nonblock-semantics-classifier/manifest.json`
- Current helper source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`

## Success Criteria

- Prove whether an outer global holder has already advanced `mss` and QRTR.
- Prove whether the current post-policy CNSS PM path already reaches
  register/connect.
- Prove whether helper-private/nonblocking pre-holder retries are closed.
- Select one next gate that is closer to Wi-Fi bring-up than the stale V1071 BPF
  branch or another private pre-holder retry.

## Guardrails

V1133 is host-only.

Do not execute device commands, tracefs writes, PM actors, CNSS daemon, Wi-Fi
HAL, scan/connect, credentials, DHCP/route changes, external ping, partition
writes, boot image writes, or flash.

## Expected Output

- classifier:
  `scripts/revalidation/native_wifi_lower_holder_route_classifier_v1133.py`
- evidence:
  `tmp/wifi/v1133-lower-holder-route-classifier/manifest.json`
- report:
  `docs/reports/NATIVE_INIT_V1133_LOWER_HOLDER_ROUTE_CLASSIFIER_2026-05-27.md`
