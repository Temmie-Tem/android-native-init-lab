# Native Init v264 QRTR/QMI Nameservice Model Report

## Summary

- status: PASS
- decision: `qrtr-qmi-userspace-model-ready`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- Wi-Fi scan/connect/link-up: not executed
- host tool: `scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py`
- plan: `docs/plans/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_PLAN_2026-05-19.md`
- output: `tmp/wifi/v264-qrtr-qmi-nameservice-model/`

v264 converts the v262 QRTR/QMI no-scan evidence and v263 warning disposition
into an explicit userspace boundary model. It does not contact the device. It
does not open QRTR sockets or transmit QRTR/QMI packets.

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py
git diff --check
```

Host-only model run:

```bash
python3 scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py \
  --v262-manifest tmp/wifi/v262-qrtr-qmi-no-scan-probe/manifest.json \
  --v263-warning-manifest tmp/wifi/v263-cnss-live-retry-20260519-091608/warning-disposition/manifest.json \
  --out-dir tmp/wifi/v264-qrtr-qmi-nameservice-model
```

Result:

```text
decision: qrtr-qmi-userspace-model-ready
pass: True
reason: QRTR/QMI userspace boundary is modeled without packet transmission
```

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| v262-manifest-pass | PASS | `qrtr-qmi-no-scan-ready`, `pass=True` |
| qipcrtr-kernel-ready | PASS | `QIPCRTR` present, `AF_QIPCRTR` bind ready |
| no-prior-qrtr-transmit | PASS | `send_attempted=0`, `connect_attempted=0` |
| cnss-process-clean | PASS | target process count `0` |
| no-wlan-link-surface | PASS | no `wlan*` link surface |
| warning-disposition-ready | PASS | v263 warning disposition present and pass |
| transmit-still-approval-gated | PASS | nameservice/QMI transmission is not authorized |

## Model

Current evidence:

- `QIPCRTR` protocol is present in `/proc/net/protocols`.
- The static QRTR helper can open and bind `AF_QIPCRTR`.
- `/dev/qrtr`, `/dev/diag`, `/dev/ipa`, and `/dev/wlan` remain absent in the
  native runtime.
- No `wlan*` interface is visible in `/proc/net/dev` or `/sys/class/net`.
- CNSS target process state is clean.

Missing before any transmit-capable experiment:

- explicit QRTR nameservice packet approval
- bounded helper that proves exactly which QRTR packet type is sent
- postflight process and `wlan*` link audit gate
- decision on perfd/property/kmsg private shim for broader Wi-Fi
- no-scan QMI service query contract before any Wi-Fi scan/connect/link-up

## Interpretation

- QRTR kernel socket readiness is necessary but not sufficient for Wi-Fi
  bring-up.
- The next QRTR/QMI step that sends any packet must be separately
  approval-gated.
- `qmicli`/libqmi-style QMI service queries are not equivalent to a harmless
  socket open; they are protocol requests and remain outside v264.
- v264 keeps `cnss_diag`, Wi-Fi scan/connect/link-up, credentials, DHCP, and
  routing blocked.

## References

- <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- <https://github.com/linux-mobile-broadband/libqmi>
- <https://manpages.ubuntu.com/manpages/questing/man1/qmicli.1.html>

## Guardrails Preserved

- no bridge command
- no `cnss-daemon` execution
- no `cnss_diag`
- no QRTR send/connect/nameservice packet
- no QMI request command
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, or reboot

## Next Step

v265 should choose one of:

1. QRTR nameservice packet design document with no execution.
2. Opt-in perfd/property/kmsg shim design document with no execution.
3. A bounded QRTR nameservice no-scan probe, but only after explicit approval
   for packet transmission.
