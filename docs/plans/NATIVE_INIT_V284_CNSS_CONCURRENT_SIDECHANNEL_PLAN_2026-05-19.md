# Native Init v284 CNSS Concurrent Side-Channel Plan

- date: `2026-05-19`
- scope: host-side Wi-Fi bring-up feasibility observer
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py`

## Summary

v283 proved that a bounded serial-only `cnss-daemon -n -l` start-only run is
safe but does not expose a visible ICNSS/WLFW readiness delta after completion.
The serial bridge is a single foreground control path, so repeating the same
serial-only test cannot observe transient state while the helper is running.

v284 tests the next required prerequisite: whether the existing NCM/tcpctl
control path can act as a concurrent read-only side-channel while serial ACM is
busy running the bounded CNSS start-only helper.

## Design

The observer keeps the two paths separate:

1. serial ACM bridge:
   - one bounded `run /cache/bin/a90_android_execns_probe ... cnss-start-only`
     command;
   - no retry of the live start command;
   - helper-side cleanup and postflight process check still required.
2. NCM/tcpctl:
   - `ping`, `status`, and read-only `run /cache/bin/toybox ...` probes;
   - samples `/proc/net/dev`, `/sys/class/net`, and `dmesg`;
   - no Wi-Fi scan/connect/link-up/credential/DHCP/routing.

If tcpctl is not already running, the live mode may start native `netservice`
temporarily to provide the background tcpctl side-channel, then stop it again
unless `--keep-netservice` is explicitly used.

Some verified native images keep `a90_tcpctl` in `/cache/bin` while the running
netservice policy expects `/bin/a90_tcpctl`.  v284 may create a temporary
rootfs-only helper alias with `--allow-runtime-helper-alias`, and removes it
after cleanup unless `--keep-runtime-helper-alias` is explicitly used.  This is
not an Android partition write and does not persist across reboot.

USB re-enumeration can also make the host-side NCM interface lose its manual
`192.168.7.1/24` address.  v284 may repair that host-only state through
NetworkManager with `--allow-nmcli-host-setup`; this does not write to the
device.

## Guardrails

- No QMI payload.
- No QRTR nameservice packet.
- No `cnss_diag`.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or `driver_override`.
- No reboot/recovery/poweroff.
- No Android partition write.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  scripts/revalidation/wifi_cnss_start_only_runner.py \
  scripts/revalidation/wifi_icnss_wlfw_start_delta_observer.py \
  scripts/revalidation/tcpctl_host.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Preflight:

```bash
python3 scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  --out-dir tmp/wifi/v284-cnss-concurrent-sidechannel-preflight \
  preflight
```

Live, only after explicit approval:

```bash
python3 scripts/revalidation/wifi_cnss_concurrent_sidechannel_observer.py \
  --out-dir tmp/wifi/v284-cnss-concurrent-sidechannel-live-$(date +%Y%m%d-%H%M%S) \
  --allow-runtime-helper-alias \
  --allow-nmcli-host-setup \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Expected PASS decisions:

- `cnss-sidechannel-preflight-ready`
- `cnss-sidechannel-no-readiness-delta`
- `cnss-sidechannel-readiness-lines-observed`

Expected blocked decisions:

- `cnss-sidechannel-blocked`: NCM/tcpctl is not reachable.
- `cnss-sidechannel-host-ncm-blocked`: host NCM IP/ping is not ready.
- `cnss-sidechannel-unproven`: no NCM/tcpctl sample completed while serial was
  busy.

## Acceptance

- At least one NCM/tcpctl sample completes while serial CNSS start-only is still
  active.
- CNSS helper reports `start-only-pass`.
- Postflight has no `cnss-daemon` or `cnss_diag` process leak.
- No `wlan*`/wiphy surface appears as a side effect.
- Evidence is stored in private host output under `tmp/wifi/...`.

## Next

If v284 proves the side-channel works but still shows no readiness delta, the
next useful direction is not another start-only repetition. Candidate next steps:

1. make the side-channel sampler more specific to ICNSS/QCA6390 driver state;
2. compare Android/TWRP dmesg timing around ICNSS/WLFW readiness;
3. only then consider a separately approved, still no-scan, minimal WLFW/QMI
   handshake probe.
