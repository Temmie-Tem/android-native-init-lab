# Native Init v268 QRTR NS Helper Source Report

## Summary

- status: PASS
- boot image change: none
- helper deployment: not executed
- helper execution: not executed
- QRTR/QMI packet transmission: not executed
- helper source: `stage3/linux_init/helpers/a90_qrtr_ns_probe.c`
- build script: `scripts/revalidation/build_qrtr_ns_probe_helper.sh`
- plan: `docs/plans/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_PLAN_2026-05-19.md`
- build output: `tmp/wifi/v268-build/a90_qrtr_ns_probe`

v268 adds reviewable transmit-capable helper source but only validates local
static build properties. The helper is not deployed and not executed.

## Validation

Static build:

```bash
scripts/revalidation/build_qrtr_ns_probe_helper.sh \
  tmp/wifi/v268-build/a90_qrtr_ns_probe
```

Result:

```text
tmp/wifi/v268-build/a90_qrtr_ns_probe: ELF 64-bit LSB executable, ARM aarch64, statically linked
c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a  tmp/wifi/v268-build/a90_qrtr_ns_probe
There is no dynamic section in this file.
```

Static checks:

```bash
file tmp/wifi/v268-build/a90_qrtr_ns_probe
aarch64-linux-gnu-readelf -l tmp/wifi/v268-build/a90_qrtr_ns_probe
aarch64-linux-gnu-readelf -d tmp/wifi/v268-build/a90_qrtr_ns_probe
strings tmp/wifi/v268-build/a90_qrtr_ns_probe | rg "a90_qrtr_ns_probe|allow-qrtr-ns-transmit|send_attempted|wildcard-blocked|lookup-sent"
git diff --check
```

Marker strings:

```text
a90_qrtr_ns_probe v1
qrtr_ns.send_attempted=0
--allow-qrtr-ns-transmit
qrtr_ns.reason=wildcard-blocked
qrtr_ns.reason=missing-allow-qrtr-ns-transmit
qrtr_ns.send_attempted=1
qrtr_ns.status=lookup-sent
```

## Helper Behavior

Default behavior:

- missing service/instance: blocked
- wildcard `service=0 instance=0`: blocked unless `--allow-wildcard-lookup`
- missing `--allow-qrtr-ns-transmit`: blocked
- prints `qrtr_ns.send_attempted=0` before any possible send path

Approval-gated behavior in source:

- opens `AF_QIPCRTR` datagram socket
- sends one `QRTR_TYPE_NEW_LOOKUP`
- sends one cleanup `QRTR_TYPE_DEL_LOOKUP` unless `--no-del-lookup`
- never sends QMI payloads

## Interpretation

- v268 is source/build validation only.
- Static ARM64 build is ready for review.
- The helper source contains a transmit path, but no helper deployment or
  execution occurred.
- Actual deployment/run remains explicit-approval-gated.

## Guardrails Preserved

- no helper deployment
- no helper execution
- no bridge command
- no QRTR socket open during validation
- no QRTR send/connect/nameservice packet during validation
- no QMI request command
- no `cnss-daemon` or `cnss_diag`
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, or reboot

## Next Step

v269 should either:

1. integrate this helper into `wifi_qrtr_nameservice_runner.py` as an
   approval-gated deploy/run path, but stop before execution, or
2. ask for explicit approval to deploy and run one bounded nameservice lookup.
