# Native Init v285 ICNSS/QCA6390 During-Start Report

- date: `2026-05-19`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- result: PASS
- decision: `icnss-qca6390-focused-no-during-delta`

## Summary

v285 adds and validates a focused ICNSS/QCA6390 during-start sampler.

It reuses the v284 control split:

- serial ACM: runs exactly one bounded CNSS start-only helper command;
- NCM/tcpctl: concurrently samples read-only focused kernel state while serial
  is busy.

The focused sampler observed ICNSS/QCA6390 sysfs, WLAN module parameters,
module state, interrupts, netdev/wiphy surfaces, rfkill class, and dmesg while
`cnss-daemon -n -l` was running.  The side-channel worked, but no focused
ICNSS/QCA6390 state delta appeared.

## Implemented

- Added plan:
  - `docs/plans/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_PLAN_2026-05-19.md`
- Added tool:
  - `scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py`

The tool supports:

- `plan`
- `preflight`
- `run`
- temporary rootfs-only `/bin/a90_tcpctl` aliasing from `/cache/bin/a90_tcpctl`
  when the running netservice policy expects the ramdisk path;
- NetworkManager host-side NCM repair after USB re-enumeration.

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/tcpctl_host.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Result: PASS.

## Plan Gate

```bash
python3 scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  --out-dir tmp/wifi/v285-icnss-qca6390-during-start-plan \
  plan
```

Result:

```text
decision: icnss-qca6390-focused-plan-ready
pass: True
```

## Live Validation

Final PASS run:

```bash
python3 scripts/revalidation/wifi_icnss_qca6390_during_start_sampler.py \
  --out-dir tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119 \
  --allow-runtime-helper-alias \
  --allow-nmcli-host-setup \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Result:

```text
decision: icnss-qca6390-focused-no-during-delta
pass: True
out_dir: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119
```

Evidence:

```text
tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119/manifest.json
tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119/summary.md
tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119/commands/
tmp/wifi/v285-icnss-qca6390-during-start-live-20260519-132119/samples/
```

## Key Evidence

From the final manifest:

```text
daemon_start_executed: true
serial helper result: start-only-pass
serial child pid/pgid: 1731/1731
postflight_safe: 1
reaped: 1
during_sample_ok: true
sample_count: 19
focused_delta_count: 0
new_focus_line_count: 0
wlan_surface_visible: false
postflight_process_clean: true
qmi_payload: false
qrtr_nameservice_packet: false
wifi_packet_transmission: false
usb_ncm_control_packets: true
```

Cleanup state after the run:

```text
netservice: enabled=no
netservice: ncm0=absent tcpctl=stopped
/bin/a90_tcpctl: No such file or directory
CNSS/a90_tcpctl process table: clean
```

## Tool Correction

An initial live run over-classified tcpctl wrapper output such as
`OK authenticated`, `[pid ...]`, and `[exit ...]` as observed device state.
The sampler now strips those wrapper lines before hashing focused signals or
classifying wiphy/netdev visibility.

## Interpretation

v285 confirms that even focused ICNSS/QCA6390 side-channel sampling does not
show a state transition during bounded `cnss-daemon -n -l` start-only execution.

The current evidence chain is now:

```text
ICNSS core bound
QCA6390 compatible/modalias visible
WLAN module sysfs present
cnss-daemon start-only safe and observable
no QCA6390 driver link change
no WLAN parameter change
no new dmesg/interrupt/netdev/wiphy readiness line
```

This points away from another identical start-only retry.  The next useful
direction is to compare Android/TWRP/native ICNSS boot timing or to design a
separately approved minimal WLFW/QMI handshake probe that still avoids scan,
connect, credential, DHCP, and routing actions.

## Guardrails

- No QMI payload.
- No QRTR nameservice packet.
- No `cnss_diag`.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind.
- No debugfs mount.
- No reboot/recovery/poweroff.
- No Android partition write.

## Next

Recommended v286:

```text
Android/TWRP/native ICNSS boot-log timing comparison
```

Purpose:

- identify which Android/TWRP boot-time event is missing in native init;
- keep the next step read-only before considering any QMI payload or Wi-Fi
  link-up experiment.
