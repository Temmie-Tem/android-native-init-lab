# Native Init V1296 Dense Window Early-Exit Classifier

- generated: 2026-05-31
- cycle: V1296
- command: host-only classification
- classifier: `scripts/revalidation/native_wifi_dense_window_early_exit_classifier_v1296.py`
- evidence: `tmp/wifi/v1296-dense-window-early-exit-classifier/manifest.json`
- result: `v1296-dense-window-limited-by-helper-stdout-cap`
- pass: true

## Result

V1296 classified the V1295 `14/40` dense sample result against the raw helper
transcript. The sample window did not prove a real 14-sample runtime stop.
Instead, helper stdout was capped at `1048576` bytes while `poll_13` was being
printed.

| field | value |
| --- | --- |
| V1295 decision | `v1295-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required` |
| dense mode | `late-per-proxy-dense-pinctrl-irq-pcie` |
| intended dense samples | `40` |
| intended interval | `50 ms` |
| manifest parsed samples | `14` |
| transcript sample begin occurrences | `55` |
| unique parsed phases | `14` |
| stdout truncation | `true` |
| truncation cap | `1048576` bytes |
| truncation point | during `late_per_proxy_poll_13` |
| `response_sampler.end` | absent |
| helper exit | `A90_EXECNS_END rc=0` |
| cmdv1 run result | `rc=0 status=ok` |
| PM-service `/dev/subsys_esoc0` attempt | true |

## Interpretation

V1295 still proves the negative lower Wi-Fi signal inside the captured window:
PM-service reached `/dev/subsys_esoc0`, but GPIO142, PCIe, MHI, WLFW, the MHI
pipe, and `wlan0` stayed absent. However, the missing `poll_13` through
`poll_39` response samples are an evidence-output problem, not a proven runtime
observer stop.

The helper's response sampler is too verbose for the current stdout capture
contract. It prints repeated fd/syscall/kmsg/debugfs blocks and reaches the
`1 MiB` helper stdout cap before completing the dense window.

## Safety

V1296 is host-only. It executed no device command, live actor, PMIC write,
userspace GPIO line request/hold, direct eSoC ioctl, Wi-Fi HAL, scan/connect,
credential use, DHCP/route change, external ping, flash, boot image write, or
partition write.

## Verification

```bash
python3 -m py_compile scripts/revalidation/native_wifi_dense_window_early_exit_classifier_v1296.py
python3 scripts/revalidation/native_wifi_dense_window_early_exit_classifier_v1296.py run
```

## Next

V1297 should be source/build-only and add a compact dense response sampler or a
file-backed evidence path that stays below the helper stdout cap. The next live
gate should not widen behavior; it should rerun the same bounded PM-service
observer path with full 40-sample visibility and the same exclusions.
