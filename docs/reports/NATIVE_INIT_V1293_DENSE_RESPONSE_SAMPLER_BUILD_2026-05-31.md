# V1293 Dense Dynamic Response Sampler Build

- date: 2026-05-31
- scope: source/build-only helper support
- helper: `a90_android_execns_probe v271`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v271`
- verifier: `scripts/revalidation/native_wifi_dense_response_sampler_support_v1293.py`
- evidence: `tmp/wifi/v1293-execns-helper-v271-build/manifest.json`
- result: `v1293-dense-response-sampler-build-pass`
- pass: `true`
- sha256: `335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24`
- size: `1319408`

## Purpose

V1292 selected denser observation because V1290 sampled the PM-service eSoC
response window at `1000 ms`, while Android-positive PCIe RC1 appears `519 ms`
after `subsys_esoc0_get`.

V1293 adds source/build-only helper support for that next observation gate.

## Added Helper Surface

New opt-in flag:

```text
--pm-observer-late-per-proxy-dense-response-sampler
```

The flag is fail-closed behind the existing response sampler:

```text
--pm-observer-late-per-proxy-response-sampler
```

Dense sampler parameters:

| field | value |
|---|---|
| mode | `late-per-proxy-dense-pinctrl-irq-pcie` |
| interval | `50 ms` |
| samples | `40` |
| window | `2000 ms` |
| reader | existing `append_pm_esoc_response_sample()` |

New output keys:

```text
pm_service_trigger_observer.response_sampler.dense_enabled
pm_service_trigger_observer.response_sampler.dense_sample_interval_ms
pm_service_trigger_observer.response_sampler.dense_sample_count
pm_service_trigger_observer.response_sampler.dense_window_ms
post_pm_mdm_helper_esoc_observer.late_per_proxy_dense_response_sampler
```

## Safety Audit

- source/build-only: `true`
- device command executed: `false`
- deploy executed: `false`
- PMIC write: `false`
- userspace GPIO line request/hold: `false`
- direct eSoC ioctl: `false`
- Wi-Fi HAL start: `false`
- scan/connect/link-up: `false`
- credential use: `false`
- DHCP/route: `false`
- external ping: `false`
- boot image write / flash / partition write: `false`

The dense mode only changes sampling cadence and metadata. It reuses the
existing no-write response sample function.

## Verification

| check | result |
|---|---|
| V1292 input manifest | pass |
| source marker/string checks | pass |
| static aarch64 build | pass |
| stage3 helper exists | pass |
| no dynamic section / no interpreter | pass |
| binary marker/string checks | pass |

Build command:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_dense_response_sampler_support_v1293.py
python3 scripts/revalidation/native_wifi_dense_response_sampler_support_v1293.py run
```

## Next

V1294 should deploy helper `v271` only. V1295 should run the bounded dense
no-write response sampler live, still without PMIC write, GPIO request/hold,
direct eSoC ioctl, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
ping, flash, boot image write, or partition write.
