# Native Init v270 QRTR Nameservice Readback Plan

## Summary

- target: v270 QRTR nameservice readback classifier
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`

v269 proved the reviewed helper can send one bounded QRTR nameservice
`NEW_LOOKUP` and cleanup `DEL_LOOKUP` packet pair. v270 extends the same helper
to keep the socket open briefly after `NEW_LOOKUP` and read nameservice
notifications, so we can classify endpoint/service visibility without sending
QMI payloads or touching Wi-Fi link state.

## Reference Model

- Linux QRTR UAPI defines `QRTR_NODE_BCAST`, `QRTR_PORT_CTRL`,
  `QRTR_TYPE_NEW_LOOKUP`, `QRTR_TYPE_DEL_LOOKUP`, and the packed
  `qrtr_ctrl_pkt` service/instance/node/port fields.
- The in-kernel QRTR nameservice registers lookups from local observers, sends
  matching `NEW_SERVER` notifications, and then sends an empty notification to
  indicate the end of the current listing.
- Therefore, v270 should not infer endpoint absence from send success alone.
  It must inspect returned notifications.

Reference sources:

- Linux QRTR UAPI: `https://codebrowser.dev/linux/linux/include/uapi/linux/qrtr.h.html`
- Linux QRTR nameservice implementation: `https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html`
- LKDDB QRTR overview: `https://cateee.net/lkddb/web-lkddb/QRTR.html`

## Scope

- Add helper options:
  - `--readback-ms <0..5000>`
  - `--max-events <1..64>`
- Approved run sequence:
  1. open/bind QRTR socket
  2. send `QRTR_TYPE_NEW_LOOKUP`
  3. poll/recv nameservice notifications for the bounded readback window
  4. send cleanup `QRTR_TYPE_DEL_LOOKUP`
  5. report structured `qrtr_ns.readback.*` counters
- Runner classification:
  - `qrtr-ns-readback-services`: one or more `NEW_SERVER` services observed
  - `qrtr-ns-readback-empty`: end-of-list observed with no matching service
  - `qrtr-ns-readback-timeout`: no end marker before timeout
  - failure only when prerequisites, helper execution, cleanup, or QMI guard
    checks fail

## Guardrails

v270 must not:

- send QMI payloads
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware paths, Android partitions, property service,
  perfd, kmsg, `/data/vendor/wifi`, or routing
- run unbounded QRTR receive loops

## Validation

Static:

```bash
scripts/revalidation/build_qrtr_ns_probe_helper.sh \
  tmp/wifi/v270-qrtr-ns-readback/build/a90_qrtr_ns_probe
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  scripts/revalidation/a90ctl.py \
  scripts/revalidation/tcpctl_host.py
git diff --check
```

Non-transmitting regression:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v270-regression-plan plan
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v270-regression-preflight --service 1 --instance 1 preflight
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v270-regression-noapproval --service 1 --instance 1 run
```

Approved live readback:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v270-qrtr-ns-readback-live-$(date +%Y%m%d-%H%M%S) \
  --service 1 \
  --instance 1 \
  --readback-ms 1000 \
  --max-events 16 \
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

- `plan`, `preflight`, and no-approval `run` stay non-transmitting.
- Approved `run` sends only QRTR nameservice `NEW_LOOKUP` and cleanup
  `DEL_LOOKUP`.
- Helper reports `qmi_attempted=0`.
- Readback result is classified as services, empty, or timeout with evidence.
- Device remains without `cnss-daemon` and without `wlan*` link surface.
