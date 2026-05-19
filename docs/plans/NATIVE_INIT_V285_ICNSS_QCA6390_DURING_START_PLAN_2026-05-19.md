# Native Init v285 ICNSS/QCA6390 During-Start Sampler Plan

- date: `2026-05-19`
- scope: host-side Wi-Fi bring-up feasibility observer
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py`

## Summary

v284 proved that the control architecture works:

- serial ACM can run one bounded `cnss-daemon -n -l` start-only command;
- NCM/tcpctl can concurrently run read-only observations while serial is busy.

The v284 sample set was intentionally generic: ping, status, netdev, class-net,
and dmesg.  It proved the side-channel but did not expose an ICNSS/WLFW
readiness delta.

v285 keeps the same safety model and changes only the observation surface.  It
samples ICNSS/QCA6390-focused read-only state while the bounded daemon command
is active.

## Design

The sampler keeps the v284 split:

1. serial ACM bridge:
   - one bounded guarded CNSS start-only helper command;
   - no live retry of the daemon command;
   - postflight process cleanup remains mandatory.
2. NCM/tcpctl:
   - read-only status and `toybox cat/ls/dmesg` commands only;
   - focused ICNSS/QCA6390/WLAN surfaces;
   - no Wi-Fi packet transmission.

Focused surfaces:

- `/sys/devices/platform/soc/18800000.qcom,icnss/{uevent,modalias,driver}`
- `/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390/{uevent,modalias,driver}`
- `/sys/module/wlan/parameters/{fwpath,con_mode,country_code}`
- `/sys/module/icnss/parameters/{quirks,dynamic_feature_mask}`
- `/proc/modules`
- `/proc/interrupts`
- `/proc/net/dev`
- `/sys/class/net`
- `/sys/class/ieee80211`
- `/sys/class/rfkill`
- `dmesg`

## Guardrails

- No QMI payload.
- No QRTR nameservice packet.
- No `cnss_diag`.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or `driver_override`.
- No debugfs mount.
- No reboot/recovery/poweroff.
- No Android partition write.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/tcpctl_host.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan gate:

```bash
python3 scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  --out-dir tmp/wifi/v285-icnss-qca6390-during-start-plan \
  plan
```

Live, only after explicit approval:

```bash
python3 scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  --out-dir tmp/wifi/v285-icnss-qca6390-during-start-live-$(date +%Y%m%d-%H%M%S) \
  --allow-runtime-helper-alias \
  --allow-nmcli-host-setup \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Expected PASS decisions:

- `icnss-qca6390-focused-plan-ready`
- `icnss-qca6390-focused-preflight-ready`
- `icnss-qca6390-focused-no-during-delta`
- `icnss-qca6390-focused-during-delta`

Expected blocked decisions:

- `icnss-qca6390-focused-sidechannel-blocked`
- `icnss-qca6390-focused-host-ncm-blocked`
- `icnss-qca6390-focused-start-failed`
- `icnss-qca6390-focused-process-leak`

## Acceptance

- At least one focused NCM/tcpctl sample completes while serial CNSS
  start-only is still active.
- CNSS helper reports `start-only-pass`.
- Postflight has no `cnss-daemon` or `cnss_diag` process leak.
- No `wlan*`, wiphy, or rfkill readiness surface appears as a side effect.
- Evidence is stored in private host output under `tmp/wifi/...`.

## Next

If v285 still shows no focused during-start delta, the next useful work is not
another identical CNSS start-only loop.  The next candidate should compare
Android/TWRP/native boot-time ICNSS log timing or plan a still no-scan,
separately approved minimal WLFW/QMI handshake probe.
