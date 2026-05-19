# Native Init v264 QRTR/QMI Nameservice Model Plan

## Summary

- target: v264 QRTR/QMI userspace nameservice model
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- new host tool: `scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py`
- expected output: `tmp/wifi/v264-qrtr-qmi-nameservice-model/`

v262 proved that the native kernel can open and bind an `AF_QIPCRTR` socket
without sending packets. v263 proved the recurring CNSS start-only warning
surface does not block bounded start-only. v264 should not expand live behavior.
It should turn the current QRTR/QMI evidence into an explicit model for what is
still missing before any packet-transmitting QRTR nameservice or QMI probe.

## References

- Linux QRTR Kconfig states that QRTR communicates with services provided by
  other hardware blocks and service lookups require nameservice support:
  <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- `libqmi` is the userspace library for QMI protocol clients:
  <https://github.com/linux-mobile-broadband/libqmi>
- `qmicli` supports QRTR URI device paths such as `qrtr://0`, which confirms
  that QMI-over-QRTR is a userspace client path and not just a kernel socket
  open:
  <https://manpages.ubuntu.com/manpages/questing/man1/qmicli.1.html>

## Scope

- Consume the v262 no-scan QRTR/QMI manifest.
- Optionally consume the v263 CNSS warning disposition manifest.
- Produce a model with:
  - current evidence
  - missing runtime pieces
  - approval gates for any future transmit-capable probe
  - recommended next safe experiment
- Keep all device and Wi-Fi control actions out of scope.

## Guardrails

v264 must not:

- run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, or DHCP
- open QRTR for send/connect or issue QRTR nameservice packets
- issue QMI requests with `qmicli`, libqmi, or custom helpers
- scan/connect/link-up Wi-Fi
- mutate `/dev/kmsg`, property service, perfd, `/data/vendor/wifi`, rfkill,
  ICNSS, firmware, Android partitions, or routing

## Implementation

Add `scripts/revalidation/wifi_qrtr_qmi_nameservice_model.py`:

- Inputs:
  - `--v262-manifest`
  - optional `--v263-warning-manifest`
  - `--out-dir`
- Writes:
  - `manifest.json`
  - `summary.md`
- Decision labels:
  - `qrtr-qmi-userspace-model-ready`
  - `qrtr-qmi-userspace-model-incomplete`
  - `qrtr-qmi-userspace-model-blocked`

## Validation

Static:

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

## Acceptance

- Decision is `qrtr-qmi-userspace-model-ready`.
- v262 QRTR no-send/no-connect evidence is accepted.
- v263 warning disposition is accepted when provided.
- The output clearly says QRTR/QMI nameservice or QMI service queries remain
  approval-gated because they transmit packets.
- No bridge command or live daemon command is executed by the v264 tool.

## Assumptions

- v264 is host tooling/evidence only; no native init version bump or boot image
  flash is needed.
- QRTR kernel socket readiness is necessary but not sufficient for Wi-Fi bring-up.
- A future QRTR nameservice/QMI probe must be a separate explicit-approval step.
