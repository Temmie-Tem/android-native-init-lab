# Native Init v266 QRTR Nameservice Runner Skeleton Report

## Summary

- status: PASS
- plan decision: `qrtr-ns-runner-plan-ready`
- preflight decision: `qrtr-ns-runner-preflight-ready`
- no-approval run decision: `qrtr-ns-runner-fail-closed`
- approved run decision: `qrtr-ns-runner-transmit-not-implemented`
- baseline input: `tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json`
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not implemented and not executed
- Wi-Fi scan/connect/link-up: not executed
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- plan: `docs/plans/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_PLAN_2026-05-19.md`
- output: `tmp/wifi/v266-qrtr-nameservice-runner-skeleton/`

v266 adds the runner entrypoint referenced by v265 but intentionally keeps it
unable to transmit QRTR packets. This validates the command surface and
fail-closed behavior before any transmit-capable helper is introduced.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_nameservice_runner.py
git diff --check
```

Host-only plan:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/plan \
  plan
```

Result:

```text
decision: qrtr-ns-runner-plan-ready
pass: True
```

Read-only device preflight:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/preflight \
  preflight
```

Result:

```text
decision: qrtr-ns-runner-preflight-ready
pass: True
```

Fail-closed no-approval run:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/run-noapproval \
  --service 1 \
  --instance 1 \
  run
```

Result:

```text
decision: qrtr-ns-runner-fail-closed
pass: True
reason: missing explicit transmit approval flags; no QRTR packet sent
```

Approved-but-not-implemented guard:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/run-approved-not-implemented \
  --service 1 \
  --instance 1 \
  --allow-qrtr-ns-transmit \
  --assume-yes \
  --i-understand-qrtr-packet-transmission \
  run
```

Result:

```text
decision: qrtr-ns-runner-transmit-not-implemented
pass: False
exit: 1
reason: approval flags are present but v266 has no transmit-capable helper
```

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| v264-model-ready | PASS | `qrtr-qmi-userspace-model-ready`, `pass=True` |
| service-instance-valid | PASS | `service=1`, `instance=1` parse as uint32 |
| wildcard-blocked | PASS | `service=0 instance=0` is not default |
| transmit-not-implemented | PASS | runner cannot send QRTR packets in v266 |
| expected-version | PASS | preflight saw `A90 Linux init 0.9.60 (v261)` |
| required-readonly-captures | PASS | no required capture failed |
| cnss-daemon-absent | PASS | `pidof cnss-daemon` returned absent |
| no-wlan-link-surface | PASS | no `wlan*` in `/proc/net/dev` |

## Interpretation

- The command surface for v267 can now be built against a real runner.
- No QRTR socket is opened and no QRTR/QMI packet is transmitted in v266.
- No-approval `run` is a positive fail-closed proof.
- Even with approval flags, v266 fails because transmit support is not
  implemented. This prevents accidental packet transmission before the helper
  design is reviewed.

## Guardrails Preserved

- no QRTR socket open
- no QRTR send/connect/nameservice packet
- no QMI request command
- no `cnss-daemon` or `cnss_diag`
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, or reboot

## Next Step

v267 can either:

1. design the transmit-capable QRTR nameservice helper without executing it, or
2. request explicit approval for a bounded `QRTR_TYPE_NEW_LOOKUP` no-scan run
   after the helper design is reviewed.
