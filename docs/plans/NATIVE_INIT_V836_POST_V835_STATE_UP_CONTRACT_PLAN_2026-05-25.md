# Native Init V836 Post-V835 State-Up Contract Plan

## Goal

Classify the remaining Android/native WLAN-PD state-up gap after V835 proved
that native still reports `UNINIT` in the best known lower window.

## Why This Gate

V835 closed the simple repeat path:

```text
clean-DSP + lower companions + cnss_diag/cnss-daemon
  -> service-notifier 180/74 present
  -> corrected listener request succeeds
  -> msm/modem/wlan_pd still UNINIT
```

Android V649 reaches WLFW and WLAN-PD quickly after service `74`:

```text
service74 -> WLFW start: ~1.292s
service74 -> WLAN-PD:    ~2.361s
```

V836 compares those facts host-only before designing another live gate.

## Scope

V836 adds:

- `scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py`

Inputs:

- V649 Android full audio/Wi-Fi reference
- V650/V651/V696 post-warning and CNSS continuation classifiers
- V701/V811 pre-WLFW/WLAN-PD classifiers
- V835 native known-ASoC-warning service-notifier replay

## Hard Guardrails

- Host-only: no bridge command, device command, reboot, bootloader handoff, boot
  image write, or partition write.
- No QRTR socket and no QRTR/QMI payload.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping.
- No custom kernel flash.

## Expected Result

V836 should reject another identical V835 replay. If Android timing is strong
and V835 remains `UNINIT`, the next useful live gate should add timing/source
observability: timestamp listener send/response/hold against service `74` and
keep the listener alive through the Android-equivalent post-service74 window.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py

python3 scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py \
  --out-dir tmp/wifi/v836-post-v835-state-up-contract-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py \
  run
```
