# Native Init v265 QRTR Nameservice Approval Contract Report

## Summary

- status: PASS
- decision: `qrtr-nameservice-approval-contract-ready`
- baseline input: `tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json`
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not executed
- Wi-Fi scan/connect/link-up: not executed
- host tool: `scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py`
- plan: `docs/plans/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_PLAN_2026-05-19.md`
- output: `tmp/wifi/v265-qrtr-nameservice-approval-contract/`

v265 prepares the explicit approval contract for a future QRTR nameservice
packet experiment. It does not implement or run the transmit-capable runner.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py
git diff --check
```

Host-only contract generation:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_approval_contract.py \
  --v264-manifest tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json \
  --out-dir tmp/wifi/v265-qrtr-nameservice-approval-contract
```

Result:

```text
decision: qrtr-nameservice-approval-contract-ready
pass: True
reason: future QRTR nameservice transmission requires explicit approval and bounded postflight
```

## Future Command Template

The command below was generated but not executed. The service and instance are
placeholders on purpose, so the template cannot be copied as a meaningful
live command without a deliberate service selection:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py --out-dir tmp/wifi/v266-qrtr-nameservice-no-scan-run --v264-manifest tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json --max-runtime-sec 5 run --service __SERVICE_ID__ --instance __INSTANCE_ID__ --allow-qrtr-ns-transmit --assume-yes --i-understand-qrtr-packet-transmission
```

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| v264-model-ready | PASS | `qrtr-qmi-userspace-model-ready`, `pass=True` |
| approval-flags-present | PASS | required explicit transmit flags present |
| wildcard-blocked-by-default | PASS | default template is not `service=0 instance=0` |
| qmi-payload-blocked | PASS | nameservice control packet only |
| wifi-link-actions-blocked | PASS | scan/connect/link-up remain blocked |
| no-execution-in-v265 | PASS | host-only contract generation |

## Contract

Allowed future packet scope:

- `QRTR_PORT_CTRL = 0xfffffffe`
- `QRTR_TYPE_NEW_LOOKUP = 10`
- cleanup packet: `QRTR_TYPE_DEL_LOOKUP = 11`
- QMI payload: not allowed
- Wi-Fi scan/connect/link-up: not allowed

Future runner must require:

- `--allow-qrtr-ns-transmit`
- `--assume-yes`
- `--i-understand-qrtr-packet-transmission`
- explicit `--service` and `--instance`
- bounded runtime
- postflight CNSS process audit
- postflight `wlan*` surface audit

## Interpretation

- v265 is the last safe non-transmit step before a QRTR nameservice experiment.
- The next implementation can create a bounded runner, but actual packet
  transmission still needs explicit user approval.
- Wildcard lookup remains blocked by default.
- QMI service requests remain separate from nameservice lookup and are still
  blocked.

## References

- <https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html>
- <https://codebrowser.dev/linux/include/linux/qrtr.h.html>
- <https://codebrowser.dev/linux/linux/net/qrtr/ns.c.html>

## Guardrails Preserved

- no bridge command
- no QRTR socket open
- no QRTR send/connect/nameservice packet
- no QMI request command
- no `cnss-daemon` or `cnss_diag`
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, or reboot

## Next Step

Stop before execution. The next step is to ask for explicit approval to design
and run a bounded QRTR nameservice no-scan runner, or choose a non-transmit
alternative such as perfd/property/kmsg shim design.
