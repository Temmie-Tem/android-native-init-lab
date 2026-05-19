# Native Init v269 QRTR Nameservice Live Retry Plan

## Summary

- target: v269 QRTR nameservice approval-gated live retry
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- helper build script: `scripts/revalidation/build_qrtr_ns_probe_helper.sh`
- helper device path: `/cache/bin/a90_qrtr_ns_probe`

v269 converts the v266 runner skeleton into an approval-gated deploy/run path
for the reviewed v268 static helper. `plan` and `preflight` remain
non-transmitting. `run` remains fail-closed unless all explicit transmit
approval flags are present.

## Scope

- Build the reviewed static ARM64 helper on the host.
- Verify host NCM reachability before deployment.
- Deploy the helper to `/cache/bin/a90_qrtr_ns_probe` using a short-lived host
  HTTP server and device-side `toybox wget`.
- Verify the deployed helper hash before moving it into place.
- Execute one bounded QRTR nameservice lookup cleanup pair:
  - `QRTR_TYPE_NEW_LOOKUP`
  - `QRTR_TYPE_DEL_LOOKUP`
- Parse `qrtr_ns.*` helper output and require:
  - `qrtr_ns.status=lookup-sent`
  - `qrtr_ns.send_attempted=1`
  - `qrtr_ns.qmi_attempted=0`

## Guardrails

v269 must not:

- execute QRTR transmission from `plan` or `preflight`
- execute `run` without all approval flags:
  - `--allow-qrtr-ns-transmit`
  - `--assume-yes`
  - `--i-understand-qrtr-packet-transmission`
- send QMI payloads
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware paths, Android partitions, property service,
  perfd, kmsg, `/data/vendor/wifi`, or routing

## Validation

Static checks:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  scripts/revalidation/a90ctl.py \
  scripts/revalidation/tcpctl_host.py
git diff --check
```

Non-transmitting regression:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v269-regression-plan plan
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v269-regression-preflight \
  --service 1 --instance 1 preflight
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v269-regression-noapproval \
  --service 1 --instance 1 run
```

Approved live retry:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v269-qrtr-nameservice-live-retry6-20260519-102134 \
  --service 1 \
  --instance 1 \
  --allow-qrtr-ns-transmit \
  --assume-yes \
  --i-understand-qrtr-packet-transmission \
  run
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py "run /cache/bin/toybox pidof cnss-daemon"
python3 scripts/revalidation/a90ctl.py "cat /proc/net/dev"
python3 scripts/revalidation/a90ctl.py "run /cache/bin/toybox sha256sum /cache/bin/a90_qrtr_ns_probe"
```

## Acceptance

- `plan`, `preflight`, and no-approval `run` preserve no-send behavior.
- Approved `run` sends exactly the reviewed QRTR nameservice lookup/delete pair.
- Helper reports `lookup-sent` and `qmi_attempted=0`.
- Device remains on the native init build with no `cnss-daemon` and no `wlan*`
  link surface.
- NCM/serial control remains usable after the run.

