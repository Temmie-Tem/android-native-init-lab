# Native Init V1782 WLAN-PD PM Forwarding Delta Classifier

## Summary

- Cycle: `V1782`
- Type: host-only classifier
- Decision: `v1782-cnss-pm-register-return-no-success-host-pass`
- Label: `client-register-return-no-forwarding`
- Result: `PASS`
- Reason: V1781 proves service-object non-null and client register TX/return, but skips the libperipheral success path and still never requests wlanmdsp; retained V1768/V1769 evidence keeps the next blocker in PM server forwarding before WLAN-PD
- Evidence: `tmp/wifi/v1782-wlan-pd-pm-forwarding-delta-classifier`

## V1781 Client-side PM Path

- provider seen: `1`
- `asInterface` call: `True`
- manager register TX call: `True`
- manager register TX return checkpoint: `True`
- register-connect return: `True`
- client register common return: `True`
- success path: `False`
- requested `wlanmdsp`: `0`
- WLFW service 69: `0`
- late WLAN-PD listener state: `uninit`

## Retained Android-good / Server-side Model

- Android PM register seen: `True`
- Android PM vote seen: `True`
- Android `wlanmdsp` request seen: `True`
- Android WLAN-PD UP seen: `True`
- V1768 server entry-only-before-match: `True`
- V1769 pre-match list/mutex boundary: `True`

## Interpretation

- V1781 closes the previous service-object-null gap: cnss-daemon gets a non-null `vendor.qcom.PeripheralManager` object and reaches the manager-register transaction.
- V1781 does not prove functional PM forwarding: the client returns without the retained `periph_success_path`, `wlanmdsp` is still not requested, WLFW service 69 is absent, and WLAN-PD remains `uninit`.
- The next aligned unit is not Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping. It is a source/build-only PM server forwarding observer for the V1781 route, then a separately approved one-run live gate.
- The next live gate should avoid `per_proxy` positive-control side effects unless explicitly scoped, because V1769 classified the pre-match record/list boundary as sensitive to PM server ordering.

## Safety

- Host-only analysis. No live device command, flash, reboot, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PM actor start, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write was performed.
