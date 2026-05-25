# Native Init V832 Post-V831 Route Classifier Report

## Result

- decision: `v832-android-service-notifier-positive-control-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py`
- evidence: `tmp/wifi/v832-post-v831-route-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py

python3 scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py \
  --out-dir tmp/wifi/v832-post-v831-route-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_v831_route_classifier_v832.py run
```

V832 was host-only. It did not execute any device command or send any QMI
payload.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V829 service-locator | `wlan/fw -> msm/modem/wlan_pd`, instance `180` |
| V829 implication | pd-mapper DB empty hypothesis closed |
| V830 listener | registered, current state `uninit` |
| V831 early listener | registered, current state `uninit`, no indication |
| V750/V752 | `boot_wlan` / CNSS ordering still stop at HDD/qcwlanstate |
| V764 | `mdm_helper` starts but does not move mdm3/WLAN-PD/WLFW |
| V775 | custom OSRC diagnostic kernel flashing remains paused |

## Classification

The user-provided V829 direction is already complete in the current codebase
and evidence set. The important branch result was not `domain_list_len=0`; V829
returned one WLAN domain:

```text
msm/modem/wlan_pd instance 180
```

V830 and V831 then followed that result with a bounded service-notifier
`REGISTER_LISTENER` query. Both timing windows registered successfully, but
native still returned:

```text
current_state = uninit
```

Therefore the active blocker is no longer:

- pd-mapper DB population;
- service-locator endpoint reachability;
- encoded service-notifier endpoint reachability;
- listener registration timing;
- unchanged `boot_wlan`, `qcwlanstate`, CNSS companion ordering, or
  `mdm_helper`.

The next missing proof is a positive control: what the same bounded
service-notifier listener query returns on an Android-success runtime.

## Candidate Matrix

| Candidate | Classification | Reason |
| --- | --- | --- |
| repeat V829 service-locator domain-list | reject | V829 already returned `msm/modem/wlan_pd` instance `180` |
| repeat V830/V831 listener timing | reject | late and early native windows both return `uninit` |
| repeat `boot_wlan` / `qcwlanstate` | reject | V750/V752 already stop before WLFW/BDF/`wlan0` |
| repeat `mdm_helper` | reject | V764 started it but lower state did not progress |
| raw `esoc0`, subsystem writes, bind/unbind, module load | forbidden | outside current safety contract |
| custom OSRC diagnostic kernel flash | paused | V775 classified boot incompatibility |
| service-manager / Wi-Fi HAL / scan/connect / DHCP / external ping | blocked | WLAN-PD state-up and `wlan0` are still absent |
| Android service-notifier positive control | select-next | needed to distinguish native lower-state gap from listener payload/model gap |

## Safety

- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash executed.
- No QRTR socket opened and no QRTR/QMI packet transmitted.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No `esoc0` open, subsystem state write, bind/unbind, driver override, or
  module load/unload executed.
- No Wi-Fi secret material was written to tracked output.

## Next

V833 should define a bounded Android reference positive-control for the same
`msm/modem/wlan_pd` service-notifier listener request. The outcome should decide
between:

1. Android returns `up` or emits an indication: native genuinely lacks the lower
   WLAN-PD state transition;
2. Android also returns `uninit`: the request payload, endpoint model, or state
   interpretation needs correction before more native retries.
