# Native Init V747 QCA6390 Driver-binding Delta Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_qca6390_binding_delta_v747.py`
- plan evidence: `tmp/wifi/v747-qca6390-driver-binding-delta-plan/`
- run evidence: `tmp/wifi/v747-qca6390-driver-binding-delta/`
- decision: `v747-qca-driver-link-gap-not-bind-target`
- status: `pass`

## Summary

V747 is host-only. It combines V746 live evidence with prior V715/V716/V703
binding evidence and confirms the current lower blocker:

```text
sysmon-gated mdm_helper starts safely
  -> QCA6390 platform child remains unbound
  -> MHI devices remain absent
  -> WLFW/BDF/wlan0 absent
  -> bind/unbind remains blocked by existing policy/evidence
```

No device command, daemon start, Wi-Fi HAL, scan/connect, DHCP/routing,
credentials, external ping, partition write, or bind/unbind action was executed.

## Key Results

| check | result |
| --- | --- |
| V746 sysmon/mdm_helper input | pass |
| V746 QCA6390 child unbound | pass |
| V746 MHI/WLFW progression | absent |
| V715 child-unbound consistency | pass |
| V715 ICNSS parent bound | pass |
| V716 bind action policy | bind/unbind remains blocked |
| Android reference usability | pass |

## Evidence

V746 marker counts:

| marker | count |
| --- | ---: |
| QRTR RX | 1 |
| QRTR TX | 1 |
| `sysmon-qmi` | 1 |
| service-notifier | 0 |
| MHI | 0 |
| QCA6390 | 0 |
| WLFW | 0 |
| BDF | 0 |
| `wlan0` | 0 |

Android reference summary:

| item | value |
| --- | ---: |
| ICNSS parent netdev lines | 4 |
| QCA bind-target rejection lines | 3 |
| WLFW/`wlan0` reference lines | 14 |

## Interpretation

The next step is not `mdm_helper` and not QCA6390 `bind`/`unbind`. V746 already
proves `mdm_helper` is safe but insufficient, and V747 keeps the QCA child
driver-link gap classified as **not a bind target**.

The remaining target is a non-bind ICNSS/QCA power-up trigger: the Android path
that gets from ICNSS parent readiness to QCA/MHI/WLFW without manually binding
the QCA6390 platform child.

## Next Gate

V748 should stay host-only or read-only first:

1. inspect Android/native evidence for ICNSS sysfs knobs and QMI trigger events;
2. map any Android init/service action that occurs between ICNSS parent netdev
   creation and WLFW/BDF readiness;
3. reject any candidate that requires generic `bind`, `unbind`, `driver_override`,
   Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
