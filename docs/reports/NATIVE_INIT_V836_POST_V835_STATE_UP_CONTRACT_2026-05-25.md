# Native Init V836 Post-V835 State-Up Contract Report

## Result

- decision: `v836-timestamped-post74-listener-hold-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py`
- evidence: `tmp/wifi/v836-post-v835-state-up-contract-classifier/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py

python3 scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py \
  --out-dir tmp/wifi/v836-post-v835-state-up-contract-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_v835_state_up_contract_classifier_v836.py run
```

V836 was host-only. It did not execute a device command and did not send any
QRTR/QMI payload.

## Evidence Summary

| Signal | Android V649 | Native V835 |
| --- | ---: | ---: |
| service `180` | `1` | `1` |
| service `74` | `1` | `1` |
| WLAN-PD / listener state | `UP` path present | `UNINIT` |
| WLFW start | `1` | `0` |
| BDF | `2` files | `0` |
| `wlan0` | present | absent |
| service `74` -> WLFW | `~1291.903 ms` | missing |
| service `74` -> WLAN-PD | `~2360.510 ms` | missing |

## Classification

V835 is not worth repeating as-is. It already proved the corrected listener can
register in the best native lower window, and the state still remains:

```text
0x7fffffff / UNINIT
```

The next uncertainty is timing/source observability, not a wider Android stack.
V835 records the service-notifier result and the post-window dmesg markers, but
it does not explicitly timestamp:

- listener send time;
- listener response time;
- listener hold interval;
- service `74` arrival time relative to the listener;
- whether the listener stayed open through Android's `~2.4s` WLAN-PD window.

## Candidate Matrix

| Candidate | Classification | Reason |
| --- | --- | --- |
| repeat V835 same-window listener replay | reject | same preconditions already returned `UNINIT` |
| wait-only extension | weak | Android timing is short, but V835 lacks listener-vs-service74 timestamps |
| service-manager / Wi-Fi HAL / scan/connect / DHCP / external ping | blocked | no WLAN-PD `UP`, WLFW, BDF, wiphy, or `wlan0` |
| `boot_wlan` / `qcwlanstate` / register-driver retry | reject | V809/V810 classify these as downstream of missing WLFW/FW_READY |
| custom OSRC diagnostic kernel flash | paused | V775 classified boot incompatibility |
| timestamped post-service74 listener hold | select-next | adds missing timing proof without widening the stack |

## Safety

- No bridge command, device command, reboot, boot image write, partition write,
  or custom kernel flash executed.
- No QRTR socket opened and no QRTR/QMI packet transmitted.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping executed.
- No Wi-Fi secret material was written to tracked output.

## Next

V837 should add a bounded timestamped listener hold around service `74`:

1. keep the V835 lower-window guardrails;
2. record monotonic timestamps for listener send/response/indication/close;
3. record service `74`, WLFW, WLAN-PD, and known ASoC-warning timestamps;
4. hold the listener through at least the Android `~2.4s` post-service74 window;
5. reboot-clean and keep HAL/connect/DHCP/external ping blocked.
