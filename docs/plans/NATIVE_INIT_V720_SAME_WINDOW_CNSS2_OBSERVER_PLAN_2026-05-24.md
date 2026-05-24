# Native Init V720 Same-window CNSS2 Observer Plan

- date: `2026-05-24 KST`
- scope: bounded same-window CNSS2 trigger observation
- runner: `scripts/revalidation/native_wifi_same_window_cnss2_observer_v720.py`
- approval phrase: `approve v720 same-window CNSS2 observer only; no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping`

## Goal

Close the ambiguity left by V719 without attempting Wi-Fi bring-up.

V720 must reproduce a service-positive lower path and, in the same run, answer
four questions:

1. is `qrtr-ns` actually observable and postflight-safe?
2. are service-locator/SERVREG messages visible?
3. does any `SERVICE_STATE_UP` / `wlan_pd` indication reach the system?
4. does CNSS2 progress into QCA6390 power/MHI/WLFW/BDF/`wlan0`?

For SM8250, treat CNSS2 as the target kernel driver path. Legacy `ICNSS` names
remain only where existing scripts or literal log markers still use them.

## Method

V720 chains existing verified gates:

1. run V712 provider-first service-positive proof with helper v121;
2. immediately run hardened V706 current read-only capture after cleanup;
3. run V719 host-only reconciliation over those two evidence directories;
4. emit one top-level manifest that records every nested decision.

The companion runtime is bounded to `1..30s` because helper v121 rejects larger
values.

## Guardrails

Allowed:

- V712 provider-first lower stack start-only below Wi-Fi HAL;
- V706 read-only current-boot capture;
- V719 host-only reconciliation;
- runner-owned cleanup inherited from V712.

Forbidden:

- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up;
- credential use;
- DHCP, route change, or external ping;
- `qcwlanstate` or WLAN driver-state sysfs writes;
- `esoc0` open/hold;
- boot image or partition write.

## Decision Matrix

| condition | decision |
| --- | --- |
| V712 cannot reproduce service `180/74` | block on lower modem/WLAN-PD readiness |
| V706 capture is busy or incomplete | block on read-only capture hygiene |
| V719 sees WLFW/BDF/fw-ready/`wlan0` | move to wlan0 readiness gate before scan/connect |
| V719 sees service `180/74` + `qrtr-ns` but no SERVREG/WLAN-PD/CNSS2/QCA progress | classify same-window CNSS2 trigger gap |

## Success Criteria

- `python3 -m py_compile` passes.
- `plan` and `preflight` produce manifests.
- approved live run produces nested V712/V706/V719 manifests.
- final manifest states no Wi-Fi HAL, scan/connect, DHCP, external ping, or
  credential use occurred.

## Expected Next Gate

If V720 confirms service `180/74` and `qrtr-ns` are present but
`SERVICE_STATE_UP`, `wlan_pd`, CNSS2 pd-notifier, QCA power/MHI, WLFW/BDF, and
`wlan0` remain absent, V721 should compare Android and native
service-locator/SERVREG/CNSS2 kernel messages around the same lower-ready
window before any Wi-Fi HAL or connection attempt.
