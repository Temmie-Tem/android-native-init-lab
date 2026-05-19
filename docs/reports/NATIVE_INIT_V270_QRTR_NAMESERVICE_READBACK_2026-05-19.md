# Native Init v270 QRTR Nameservice Readback Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- runner: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- helper device path: `/cache/bin/a90_qrtr_ns_probe`
- helper sha256: `375c30c21e5715218698a67832bf31d8052be95d4933d2ab98c198d73a45076a`
- primary live evidence: `tmp/wifi/v270-qrtr-ns-readback-live-20260519-103623/`
- long readback evidence: `tmp/wifi/v270-qrtr-ns-readback-live-long-20260519-103732/`
- decision: `qrtr-ns-readback-timeout`

v270 extends the QRTR nameservice helper from send-only to bounded readback. The
helper sent `NEW_LOOKUP`, waited for nameservice notifications, then sent cleanup
`DEL_LOOKUP`. Both 1s and 3s readback windows completed without any returned
nameservice event.

## Reference Model

- `QRTR_TYPE_NEW_LOOKUP` and `QRTR_TYPE_DEL_LOOKUP` are QRTR nameservice control
  packet types, not QMI payloads.
- The Linux QRTR nameservice can respond to a local lookup with matching
  `NEW_SERVER` notifications and an empty notification to indicate end-of-list.
- v270 therefore treats no returned notification as a classifier result, not as
  proof that the send path failed.

Reference sources:

- Linux QRTR UAPI: `https://codebrowser.dev/linux/linux/include/uapi/linux/qrtr.h.html`
- Linux QRTR nameservice implementation: `https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html`
- LKDDB QRTR overview: `https://cateee.net/lkddb/web-lkddb/QRTR.html`

## Implementation

- helper marker bumped to `a90_qrtr_ns_probe v2`
- helper options added:
  - `--readback-ms <0..5000>`
  - `--max-events <1..64>`
- runner default evidence dir moved to `tmp/wifi/v270-qrtr-nameservice-readback`
- runner now classifies:
  - `qrtr-ns-readback-services`
  - `qrtr-ns-readback-empty`
  - `qrtr-ns-readback-timeout`
  - `qrtr-ns-readback-complete`

## Validation

Static validation:

```bash
scripts/revalidation/build_qrtr_ns_probe_helper.sh \
  tmp/wifi/v270-qrtr-ns-readback/build/a90_qrtr_ns_probe
python3 -m py_compile \
  scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  scripts/revalidation/a90ctl.py \
  scripts/revalidation/tcpctl_host.py
git diff --check
```

Build result:

```text
tmp/wifi/v270-qrtr-ns-readback/build/a90_qrtr_ns_probe: ELF 64-bit LSB executable, ARM aarch64, statically linked
375c30c21e5715218698a67832bf31d8052be95d4933d2ab98c198d73a45076a  tmp/wifi/v270-qrtr-ns-readback/build/a90_qrtr_ns_probe
There is no dynamic section in this file.
```

Non-transmitting regression:

- `plan`: `qrtr-ns-runner-plan-ready`
- `preflight`: `qrtr-ns-runner-preflight-ready`
- no-approval `run`: `qrtr-ns-runner-fail-closed`

## Live Readback

Primary 1s run:

```text
decision: qrtr-ns-readback-timeout
pass: True
reason: readback timed out after 0 event(s)
out_dir: tmp/wifi/v270-qrtr-ns-readback-live-20260519-103623
```

Key helper output:

```text
qrtr_ns.version=a90_qrtr_ns_probe v2
qrtr_ns.send_attempted=1
qrtr_ns.qmi_attempted=0
qrtr_ns.new_lookup_send.rc=0
qrtr_ns.new_lookup_send.bytes=20
qrtr_ns.readback.rc=0
qrtr_ns.readback.timeout_ms=1000
qrtr_ns.readback.events=0
qrtr_ns.readback.new_server=0
qrtr_ns.readback.service_events=0
qrtr_ns.readback.end_of_list=0
qrtr_ns.readback.timeout=1
qrtr_ns.del_lookup_send.rc=0
qrtr_ns.del_lookup_send.bytes=20
qrtr_ns.status=lookup-readback-complete
```

Long 3s retry:

```text
decision: qrtr-ns-readback-timeout
pass: True
reason: readback timed out after 0 event(s)
out_dir: tmp/wifi/v270-qrtr-ns-readback-live-long-20260519-103732
```

The 3s retry used `--skip-deploy` after the 1s run had already deployed and
hash-checked the v2 helper.

## Postflight

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed
- `/cache/bin/a90_qrtr_ns_probe`: sha256 matched v270 helper

## Interpretation

- QRTR nameservice control send still works.
- No QMI payload was attempted.
- No matching QRTR nameservice response was received for service `1`, instance
  `1`, even with a 3s readback window.
- This points away from basic QRTR send mechanics and toward one of:
  - no userspace-visible service announcement for the selected service/instance
  - QRTR endpoint/service not present until a separate CNSS/runtime step happens
  - selected service/instance does not correspond to a currently announced Wi-Fi
    control service on this device

## Guardrails Preserved

- no QMI payload
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, property service mutation, perfd mutation, kmsg mutation, or reboot

## Next Step

v271 should not jump directly to QMI request payloads. The next safer step is a
QRTR service/instance selection plan: correlate Android/TWRP/native evidence,
kernel QRTR naming behavior, vendor binary strings, and any non-transmitting
service IDs before another explicit-approval live packet run.

