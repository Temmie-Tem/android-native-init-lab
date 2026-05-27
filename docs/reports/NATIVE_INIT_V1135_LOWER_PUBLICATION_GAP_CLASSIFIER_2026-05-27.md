# Native Init V1135 Lower Publication Gap Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1135-pm-success-lower-esoc-publication-gap-classified`
- Pass: `true`
- Classifier: `scripts/revalidation/native_wifi_lower_publication_gap_classifier_v1135.py`
- Evidence: `tmp/wifi/v1135-lower-publication-gap-classifier/manifest.json`

## Summary

V1135 is a host-only classifier after V1134. It reconciles the latest
provider-positive PM/CNSS success with the remaining lower Wi-Fi blocker.

V1134 proved the upper path:

```text
global firmware mounts
outer /dev/subsys_modem holder
mss ONLINE
cnss-daemon PM register/connect returns
per_mgr and pm_proxy_helper /dev/subsys_modem fd evidence
```

But the lower publication path still did not advance:

```text
mdm3=OFFLINING
QRTR service69=0
QRTR service74=0
QRTR service180=0
WLFW=0
wlan0=0
```

## Classification

| Evidence | Result | Meaning |
| --- | --- | --- |
| V1134 upper PM/CNSS | pass | PM register/connect is no longer the immediate blocker |
| V1134 lower WLFW absent | pass | successful PM path is not sufficient for service69/WLFW |
| V968 Android path | pass | Android reaches WLFW start, eSoC get, firmware-ready, and wlan0 |
| V1093 provider-only | pass | provider visibility alone leaves mdm3 OFFLINING |
| V1108 PM connect | pass | PM connect alone leaves mdm3 OFFLINING without eSoC trigger |
| V1109 lower blocker | pass | PM connect can reach lower `__subsystem_get`/firmware wait |
| V884/V891/V895 eSoC history | pass | REQ/IMG path is partially known but MDM2AP readiness does not fire |
| V904 mdm_helper parity | pass | direct `mdm_helper` lacks Android runtime/input contract |

## Interpretation

The active blocker is now below the PeripheralManager/CNSS client success
boundary. Repeating PM provider or CNSS PM connect gates is unlikely to move
Wi-Fi forward unless the lower eSoC/MDM2AP readiness state machine also moves.

The next work should focus on the smallest safe post-PM eSoC/MDM2AP observer or
state-machine gate. It should not start Wi-Fi HAL, scan/connect, use
credentials, run DHCP/route changes, or external ping until service `69` or an
equivalent WLFW readiness marker appears.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_publication_gap_classifier_v1135.py
python3 scripts/revalidation/native_wifi_lower_publication_gap_classifier_v1135.py
```

Result:

```text
decision: v1135-pm-success-lower-esoc-publication-gap-classified
pass: True
```

## Next

V1136 should be a design/preflight step, not a blind live retry:

1. define the minimum post-PM eSoC/MDM2AP surface to observe;
2. decide whether the next live gate is read-only observer, state-machine
   preflight, or a strictly bounded eSoC request-engine action;
3. preserve the current V1134 upper path as the prerequisite;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping, boot
   image writes, and flash blocked.
