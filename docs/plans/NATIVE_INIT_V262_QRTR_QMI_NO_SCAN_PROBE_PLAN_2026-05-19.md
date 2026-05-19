# Native Init v262 QRTR/QMI No-Scan Probe Plan

## Summary

- target: v262 QRTR/QMI no-scan endpoint inventory probe
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- daemon start: not executed
- Wi-Fi scan/connect/link-up: not executed
- new host tool: `scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py`
- expected output: `tmp/wifi/v262-qrtr-qmi-no-scan-probe/`

v250 proved that `AF_QIPCRTR` socket creation and local ephemeral bind work in
native init. v261 then closed the CNSS zombie cleanup blocker and re-validated a
bounded start-only retry with clean postflight process state. v262 should not
repeat a broader live daemon attempt. Instead it should collect a fresh,
read-only/no-scan QRTR/QMI endpoint inventory on the clean v261 baseline and
re-run the existing no-send QRTR socket helper as a sanity check.

## References

- Linux QRTR Kconfig describes Qualcomm IPC Router as the protocol used to
  communicate with services provided by other hardware blocks, and notes that
  userspace service lookup needs a service-listing daemon:
  <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- Linux `af_qrtr.c` registers the `AF_QIPCRTR` family, accepts `SOCK_DGRAM`, and
  provides bind/connect/send/recv socket operations. v262 must avoid connect and
  send paths:
  <https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html>
- `libqmi` documents QMI as a userspace protocol/library stack for Qualcomm MSM
  Interface devices, so native Wi-Fi bring-up still needs QMI/QRTR runtime
  evidence before any scan/link-up step:
  <https://github.com/linux-mobile-broadband/libqmi>

## Scope

Collect and classify only read-only/no-scan evidence:

- v261 version/status/bootstatus/selftest baseline
- v261 post-live clean-state prerequisite from process table
- `/proc/net/protocols`, `/proc/net/netlink`, optional `/proc/net/qrtr`
- `/dev` QRTR/QMI/CNSS/diag/IPA/WLAN node inventory
- `/sys` QRTR/QMI/CNSS/WLAN/ICNSS hints
- `/sys/class/net`, `/proc/net/dev`, `/proc/net/wireless`
- existing `/cache/bin/a90_qrtr_probe` static helper hash and no-send run output
- `wifiinv full`, `wififeas full`, `netservice status`

## Guardrails

v262 must not do any of the following:

- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, or DHCP
- send QRTR payloads
- connect to QRTR services
- perform QRTR nameservice lookup packets
- run QMI client commands that transmit requests
- unblock rfkill or set `wlan*` up
- scan, connect, add credentials, DHCP, route, or expose non-USB network paths
- bind/unbind ICNSS, mutate firmware paths, write Android partitions, or reboot

## Implementation

Add `scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py`:

- Use `EvidenceStore` private output helpers.
- Validate static denied-command patterns before device access.
- Capture each command under `captures/<name>.txt` and write a manifest.
- Reuse `wifi_cnss_zombie_audit` process parsing to prove CNSS process clean.
- Reuse v250 `qrtr_probe.*` parsing to prove the helper still reports:
  - `send_attempted=0`
  - `connect_attempted=0`
  - `socket.rc=0`
  - `status=bind-pass` or `open-only`
- Classify:
  - `qrtr-qmi-no-scan-ready`: required baseline, clean-state, QIPCRTR protocol,
    helper no-send, and no WLAN link-up all pass.
  - `qrtr-qmi-no-scan-blocked`: required baseline or guardrail evidence fails.
  - `qrtr-qmi-no-scan-manual-review`: required evidence exists, but optional
    endpoint inventory is ambiguous.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py
python3 -m py_compile scripts/revalidation/wifi_qrtr_socket_probe.py scripts/revalidation/wifi_cnss_zombie_audit.py
git diff --check
```

Live no-scan probe:

```bash
python3 scripts/revalidation/wifi_qrtr_qmi_no_scan_probe.py \
  --out-dir tmp/wifi/v262-qrtr-qmi-no-scan-probe \
  --expect-version "A90 Linux init 0.9.60 (v261)"
```

Post-check:

```bash
python3 scripts/revalidation/wifi_cnss_zombie_audit.py \
  --out-dir tmp/wifi/v262-cnss-zombie-audit-post-qrtr-qmi
```

## Acceptance

- Manifest decision is `qrtr-qmi-no-scan-ready` or an explicitly documented
  `manual-review` with no guardrail breach.
- `cnss-daemon` and `cnss_diag` remain absent after the probe.
- `wlan*` is not brought up and no Wi-Fi scan/connect occurs.
- QRTR helper evidence confirms no send/connect attempts.
- Report records whether the remaining blocker is QRTR userspace nameservice,
  QMI endpoint/device-node visibility, or a different Android runtime service
  gap.

## Assumptions

- Latest verified device build is v261.
- v262 is host tooling/evidence only; no native init version bump or boot image
  flash is needed.
- The existing `/cache/bin/a90_qrtr_probe` helper is trusted if its sha256 still
  matches v250. If missing, deploy should be handled as a separate explicit
  step before running v262.
