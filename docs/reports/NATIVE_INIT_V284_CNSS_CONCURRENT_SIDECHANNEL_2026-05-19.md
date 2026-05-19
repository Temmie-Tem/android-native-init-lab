# Native Init v284 CNSS Concurrent Side-Channel Report

- date: `2026-05-19`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- result: PASS
- decision: `cnss-sidechannel-no-readiness-delta`

## Summary

v284 adds and validates a host-side concurrent side-channel observer for the
Wi-Fi/CNSS bring-up investigation.

The test separates the two control paths:

- serial ACM: runs exactly one bounded CNSS start-only helper command;
- NCM/tcpctl: concurrently samples read-only device state while serial is busy.

This proves the observation architecture works.  However, the live run still
did not expose an ICNSS/WLFW readiness delta: no `wlan*`/wiphy surface appeared,
no CNSS process leaked, and no readiness-related dmesg/state line was observed
through the concurrent side-channel.

## Implemented

- Added plan:
  - `docs/plans/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_PLAN_2026-05-19.md`
- Added tool:
  - `scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py`
- Updated queue/next-work docs:
  - `docs/plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md`
  - `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`

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
  scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  scripts/revalidation/tcpctl_host.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Result: PASS.

## Plan Gate

```bash
python3 scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  --out-dir tmp/wifi/v284-cnss-concurrent-sidechannel-plan \
  plan
```

Result:

```text
decision: cnss-sidechannel-plan-ready
pass: True
```

## Live Validation

Final PASS run:

```bash
python3 scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  --out-dir tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404 \
  --allow-runtime-helper-alias \
  --allow-nmcli-host-setup \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Result:

```text
decision: cnss-sidechannel-no-readiness-delta
pass: True
out_dir: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404
```

Evidence:

```text
tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404/manifest.json
tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404/summary.md
tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404/commands/
tmp/wifi/v284-cnss-concurrent-sidechannel-live-20260519-130404/samples/
```

## Key Evidence

From the final manifest:

```text
daemon_start_executed: true
serial helper result: start-only-pass
serial child pid/pgid: 1258/1258
postflight_safe: 1
reaped: 1
during_sample_ok: true
sample_count: 12
readiness_line_count: 0
wlan_surface_visible: false
postflight_process_clean: true
qmi_payload: false
wifi_packet_transmission: false
usb_ncm_control_packets: true
```

Concurrent sample result:

```text
12 samples completed while serial CNSS start-only was active.
Each sample completed 5/5 NCM/tcpctl observations.
```

Cleanup state after the run:

```text
netservice: enabled=no
netservice: ncm0=absent tcpctl=stopped
/bin/a90_tcpctl: No such file or directory
CNSS/a90_tcpctl process table: clean
```

## Interpretation

v284 confirms the control architecture needed for during-start observation:

```text
serial ACM = foreground start-only execution
NCM/tcpctl = concurrent read-only observation
```

The absence of a readiness delta means the current start-only run is not enough
to make ICNSS/WLFW readiness visible even when sampled during execution.  The
next step should use this proven concurrent path to sample more specific
ICNSS/QCA6390 state while the daemon is running, rather than repeating the same
generic dmesg/netdev sampling.

## Guardrails

- No QMI payload.
- No QRTR nameservice packet.
- No `cnss_diag`.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind.
- No reboot/recovery/poweroff.
- No Android partition write.

## Next

Recommended v285:

```text
ICNSS/QCA6390 focused during-start sampler
```

Use the v284 side-channel pattern, but sample more targeted read-only state:

- ICNSS platform device `uevent`, driver link, and modalias;
- QCA6390 node driver link and `uevent`;
- `/sys/module/wlan/parameters/*`;
- `/proc/modules`;
- `/proc/interrupts` filtered for WLAN/CNSS/ICNSS;
- dmesg tail filtered for `icnss`, `cnss`, `wlfw`, `qmi`, `qca6390`, `wlan`.

Still keep QMI payloads and Wi-Fi link-up actions blocked.
