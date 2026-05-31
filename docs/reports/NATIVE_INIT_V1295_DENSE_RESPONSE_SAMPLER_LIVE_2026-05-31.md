# Native Init V1295 Dense Response Sampler Live

- generated: 2026-05-31
- cycle: V1295
- command: bounded live observation
- decision: `v1295-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- pass: true
- helper: `a90_android_execns_probe v271`
- helper sha256: `335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24`
- runner: `scripts/revalidation/native_wifi_dense_response_sampler_live_v1295.py`
- evidence: `tmp/wifi/v1295-dense-response-sampler-live/manifest.json`

## Result

V1295 reran the bounded PM-service `/dev/subsys_esoc0` response sampler with
helper v271 and the dense late-`per_proxy` sampler enabled. The helper command
included both sampler flags, and the helper output emitted dense metadata:

| field | value |
| --- | --- |
| sampler mode | `late-per-proxy-dense-pinctrl-irq-pcie` |
| intended interval | `50 ms` |
| intended dense samples | `40` |
| intended dense window | `2000 ms` |
| parsed samples | `14` |
| phases | `pre_late_per_proxy`, `late_per_proxy_poll_00`..`late_per_proxy_poll_12` |
| PM-service `/dev/subsys_esoc0` attempt | true |
| `mdm3` state | `OFFLINING` -> `OFFLINING` |
| GPIO142 IRQ count | `0` |
| PCI devices | `0` |
| MHI bus devices | `0` |
| PCIe kmsg markers | `0` |
| MHI kmsg markers | `0` |
| WLFW kmsg markers | `0` |
| SDX50M kmsg markers | `0` |
| MHI pipe | absent |
| `wlan0` | absent |
| postflight health | v724 selftest `pass=11 warn=1 fail=0` |

The parsed sample count stops at 14 rather than the intended 40-sample dense
window. This is not a flag-injection failure: the child script and helper
transcript prove the dense flag and dense metadata were active. The run still
entered the same reboot-required classification because the PM-service eSoC
trigger did not produce GPIO142, PCIe RC1, MHI, WLFW, or `wlan0` progress, and
cleanup was not proven safe inside the live window.

Postflight evidence was captured after native recovery:

- `tmp/wifi/v1295-dense-response-sampler-live/postflight/version.json`
- `tmp/wifi/v1295-dense-response-sampler-live/postflight/selftest-verbose.json`

## Interpretation

V1295 strengthens the negative result from V1290/V1291/V1292: even with a
50 ms intended cadence around the first two seconds after late `per_proxy`, the
native path still shows no dynamic SDX50M response. The remaining open question
is why the dense sampler exits after 14 samples in this reboot-required path;
that should be classified from V1295 evidence before adding any wider live
mutation.

The next shortest gate is a host-only early-exit classifier for the V1295
dense window. It should explain why only 14 samples were parsed despite
`dense_sample_count=40`, using the helper transcript, PM actor states, and
wrapper parser behavior.

## Safety

No PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, Wi-Fi HAL
start, scan/connect/link-up, credential use, DHCP/route change, external ping,
flash, boot image write, or partition write was executed. The live actor stayed
within the existing bounded PM-service observer path.

## Verification

```bash
python3 -m py_compile scripts/revalidation/native_wifi_dense_response_sampler_live_v1295.py
python3 scripts/revalidation/native_wifi_dense_response_sampler_live_v1295.py run
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json selftest verbose
```

## Next

V1296 should be host-only and classify the V1295 dense-window early exit before
any new live power, GPIO, eSoC, HAL, scan/connect, or network action.
