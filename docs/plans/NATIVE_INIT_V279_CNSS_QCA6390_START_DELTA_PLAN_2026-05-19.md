# Native Init v279 CNSS QCA6390 Start-Only Delta Plan

## Summary

- target: v279 bounded CNSS start-only QCA6390/WLAN delta observer
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py`
- daemon execution: bounded `cnss-daemon` start-only through the existing guarded helper
- packet transmission: none
- QMI payload: none
- sysfs/control writes: none from the observer

v278 proved that the concrete `qcom,cnss-qca6390` node is visible, but its
`driver` symlink is absent in native init. v279 performs a bounded start-only
observation and compares QCA6390/WLAN read-only state before and after the run.
The goal is to learn whether the already-approved CNSS start-only path changes
driver binding or WLAN module parameters without scanning, connecting, link-up,
QRTR nameservice transmission, or QMI payloads.

## Scope

The observer records:

- before/after QCA6390 `uevent`, `modalias`, and `driver` symlink state
- before/after selected `/sys/module/wlan/parameters/*` values
- before/after `/sys/class/net`, `/proc/net/dev`, `/sys/class/ieee80211`, and
  Wi-Fi rfkill visibility
- before/after CNSS process-table cleanliness
- nested evidence from `wifi_cnss_start_only_runner.py`

The start-only run remains delegated to the existing guarded runner and helper.
The observer only decides whether a driver/parameter/readiness delta appeared
and whether postflight remained clean.

## Guardrails

v279 must not:

- send QRTR nameservice packets
- send QMI request payloads
- run Wi-Fi scan/connect/link-up/credential/DHCP/routing commands
- run `cnss_diag`, HAL, supplicant, wificond, hostapd, or hostapd-like services
- run ICNSS bind/unbind, driver override, rfkill unblock, recovery, ramdump, or
  assert controls
- mutate firmware paths or Android partitions
- reboot automatically

The only live execution is the previously planned CNSS `start-only` helper path,
bounded by runtime timeout and postflight process cleanup checks.

## Decision Model

Expected likely decision:

```text
cnss-qca6390-no-driver-delta
```

This means the bounded start-only run completed safely, but QCA6390 driver-link
state and WLAN parameters did not change.

Alternative decisions:

- `cnss-qca6390-start-delta-observed`: QCA6390 driver-link or WLAN parameters
  changed after start-only.
- `cnss-qca6390-start-readiness-delta-cleaned`: a readiness surface changed but
  postflight cleaned up safely.
- `cnss-qca6390-start-delta-blocked`: runner plan/preflight gate failed.
- `cnss-qca6390-start-delta-start-failed`: start-only runner failed its cleanup
  or safety gate.
- `cnss-qca6390-start-delta-postflight-failed`: after snapshot failed critical
  postflight checks.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/wifi_qca6390_driver_param_classifier.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Plan mode:

```bash
python3 scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py \
  --out-dir tmp/wifi/v279-cnss-qca6390-start-delta-plan \
  plan
```

Live bounded run:

```bash
python3 scripts/revalidation/wifi_cnss_qca6390_start_delta_observer.py \
  --out-dir tmp/wifi/v279-cnss-qca6390-start-delta-live-$(date +%Y%m%d-%H%M%S) \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- start-only execution is bounded and uses the existing approval runner.
- no QRTR nameservice packet or QMI payload is sent.
- postflight has no `cnss-daemon`, no `cnss_diag`, and no `wlan*` interface.
- QCA6390 driver-link and WLAN parameter before/after state is captured.
- evidence is written under `tmp/wifi/v279-*` with private output handling.
