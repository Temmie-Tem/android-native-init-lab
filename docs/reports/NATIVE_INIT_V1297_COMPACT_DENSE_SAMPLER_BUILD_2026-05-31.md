# V1297 Compact Dense Response Sampler Build

- date: 2026-05-31
- scope: source/build-only helper support
- helper: `a90_android_execns_probe v272`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v272`
- verifier: `scripts/revalidation/native_wifi_compact_dense_response_sampler_support_v1297.py`
- evidence: `tmp/wifi/v1297-execns-helper-v272-build/manifest.json`
- result: `v1297-compact-dense-sampler-build-pass`
- pass: `true`
- sha256: `1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885`
- size: `1319408`

## Purpose

V1296 proved the V1295 dense sampler shortfall was not a confirmed runtime
observer stop. The helper stdout cap truncated output at `1048576` bytes during
`late_per_proxy_poll_13`, before `response_sampler.end`.

V1297 adds a compact dense sampler path so the same bounded PM-service response
window can be sampled without emitting the full verbose per-sample blocks.

## Added Helper Surface

New opt-in flag:

```text
--pm-observer-late-per-proxy-compact-response-sampler
```

The flag is fail-closed behind the existing response sampler:

```text
--pm-observer-late-per-proxy-response-sampler
```

It can be combined with the existing dense flag:

```text
--pm-observer-late-per-proxy-dense-response-sampler
```

Compact dense mode:

| field | value |
|---|---|
| mode | `late-per-proxy-dense-compact-pinctrl-irq-pcie` |
| interval | `50 ms` |
| samples | `40` |
| window | `2000 ms` |
| reader | `append_pm_esoc_response_sample_compact()` |

The compact path preserves the no-write status counters needed for the response
window: GPIO142 IRQ count, `mdm3` state/crash count, PCIe state, MHI pipe/path
counts, `ks` process count, `wlan0` presence, selected kmsg marker counts,
PMIC/TLMM line visibility, and explicit zero-action safety fields.

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

## Verification

| check | result |
|---|---|
| V1296 input manifest | pass |
| source marker/string checks | pass |
| static aarch64 build | pass |
| stage3 helper exists | pass |
| no dynamic section / no interpreter | pass |
| binary marker/string checks | pass |

Build command:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_compact_dense_response_sampler_support_v1297.py
python3 scripts/revalidation/native_wifi_compact_dense_response_sampler_support_v1297.py run
```

## Next

V1298 should deploy helper `v272` only. V1299 should run the bounded compact
dense no-write response sampler live, still without PMIC write, GPIO
request/hold, direct eSoC ioctl, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, flash, boot image write, or partition write.
