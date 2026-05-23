# Native Init V656 Service74 Regression Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner:
  `scripts/revalidation/native_wifi_service74_regression_classifier_v656.py`
- evidence: `tmp/wifi/v656-service74-regression-classifier/`
- decision: `v656-service74-regression-classified`

## Scope

V656 is host-only. It compares existing V644, V653, and V655 manifests plus
V653/V655 helper transcripts and V490 manifests.

No device command, sysfs write, DSP boot-node write, `esoc0` open, daemon start,
service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential, DHCP,
route change, or external ping was executed.

## Result

```text
decision: v656-service74-regression-classified
pass: True
reason: V653 reached service 74 but V655 lost service 74 despite matching QRTR/sysmon lower readiness and fresh V490; V655 withheld service-manager, so vndservicemanager readiness was not tested
next: run a bounded V657 exact V653-mode replay with helper v106 before attempting the CNSS retry mode again
```

## Evidence Matrix

| subject | V644 | V653 | V655 | interpretation |
| --- | --- | --- | --- | --- |
| service `74` | `1` | `1` | `0` | V655 regressed before service-manager |
| service `180` | `1` | `1` | `0` | same publication layer as service `74` |
| QRTR TX | `1` | `1` | `1` | lower QRTR survives |
| sibling sysmon | `4` | `4` | `4` | SSCTL layer survives |
| CNSS netlink | `0` | `5` | `5` | `cnss-daemon` still starts |
| CNSS binder transactions | `0` | `1` | `33` | V655 loops binder before service-notifier |
| kernel warning | `5` | `1` | `0` | warning absence is not enough to recover service `74` |
| Wi-Fi link | `0` | `0` | `0` | not reached |

## Helper Delta

| field | V653 | V655 | interpretation |
| --- | --- | --- | --- |
| mode | `wifi-companion-service74-gated-vnd-service-manager-start-only` | `wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only` | only intentional live-mode delta before service-manager |
| child_started | `9` | `6` | V655 stopped at gate before service-manager |
| service_manager_started | `1` | `0` | not causal for V655 loss because it was withheld |
| service74_status | `open` | `timeout` | primary regression |
| service74_wait_ms | `16` | `12232` | V655 waited full gate window |
| service74_count | `1` | `0` | V653 published service `74`; V655 never did |
| cnss_binder_transactions | `1` | `33` | V655 loops binder before service-notifier |

## Interpretation

V656 rules out several explanations for V655:

- lower QRTR/sysmon readiness was present in both V653 and V655;
- V490 policy-load passed in both runs;
- service-manager was not the cause of the V655 missing service `74`, because
  V655 never started service-manager;
- kernel warning absence did not recover service `74`.

The current blocker is therefore below the intended `vndservicemanager`
readiness proof. V655 cannot test fresh CNSS retry until service `74` is
reproduced again.

## Next Gate

Proceed to V657:

1. refresh V641 clean-DSP and V490 prerequisites as needed;
2. run helper v106 in the exact V653-compatible mode:
   `wifi-companion-service74-gated-vnd-service-manager-start-only`;
3. keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping
   blocked;
4. if V657 restores service `74`, then retry the V655
   `vndservicemanager`-readiness mode from the same prerequisite shape.
