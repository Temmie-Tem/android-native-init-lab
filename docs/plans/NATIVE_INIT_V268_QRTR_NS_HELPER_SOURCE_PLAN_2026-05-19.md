# Native Init v268 QRTR Nameservice Helper Source Plan

## Summary

- target: v268 QRTR nameservice helper source/build
- boot image change: none
- helper deployment: not executed
- helper execution: not executed
- QRTR/QMI packet transmission: not executed
- new helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- new build script: `scripts/revalidation/build_qrtr_ns_probe_helper.sh`

v267 fixed the QRTR nameservice packet byte layout. v268 adds reviewable helper
source that defaults to fail-closed and can be statically built, but it is not
deployed or executed.

## Scope

- Implement helper argument parsing and guardrails.
- Default behavior without `--allow-qrtr-ns-transmit`:
  - print `qrtr_ns.send_attempted=0`
  - print blocked status
  - exit `0`
- Approval behavior in source:
  - require explicit service and instance
  - block wildcard unless explicitly allowed
  - open/bind QRTR socket
  - send one `QRTR_TYPE_NEW_LOOKUP`
  - optionally send one `QRTR_TYPE_DEL_LOOKUP`
- v268 validation compiles and inspects only. It does not run the helper.

## Guardrails

v268 must not:

- deploy the helper to the device
- execute the helper on host or device
- run bridge commands for this helper
- send QRTR nameservice packets
- issue QMI requests
- run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP, or
  routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware, Android partitions, property service, perfd,
  kmsg, `/data/vendor/wifi`, or routing

## Validation

Static build:

```bash
scripts/revalidation/build_qrtr_ns_probe_helper.sh \
  tmp/wifi/v268-build/a90_qrtr_ns_probe
```

Static checks:

```bash
file tmp/wifi/v268-build/a90_qrtr_ns_probe
aarch64-linux-gnu-readelf -l tmp/wifi/v268-build/a90_qrtr_ns_probe
aarch64-linux-gnu-readelf -d tmp/wifi/v268-build/a90_qrtr_ns_probe
strings tmp/wifi/v268-build/a90_qrtr_ns_probe | rg "a90_qrtr_ns_probe|allow-qrtr-ns-transmit|send_attempted"
git diff --check
```

## Acceptance

- Helper builds as static ARM64 with no `INTERP` and no dynamic section.
- Source contains the explicit approval flag requirement.
- Source defaults to blocked/no-send behavior.
- No helper deployment or execution occurs.
