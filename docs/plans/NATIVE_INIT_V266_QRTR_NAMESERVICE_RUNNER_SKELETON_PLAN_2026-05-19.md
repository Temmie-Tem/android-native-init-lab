# Native Init v266 QRTR Nameservice Runner Skeleton Plan

## Summary

- target: v266 QRTR nameservice runner skeleton
- boot image change: none
- daemon start: not executed
- QRTR/QMI packet transmission: not implemented and not executed
- new host tool: `scripts/revalidation/wifi_qrtr_nameservice_runner.py`
- expected output: `tmp/wifi/v266-qrtr-nameservice-runner-skeleton/`

v265 produced the approval contract for a future QRTR nameservice lookup. v266
adds the runner entrypoint and validates all non-transmit behavior first:
`plan`, read-only `preflight`, and no-approval fail-closed `run`.

## Scope

- Implement the command-line surface that v265 referenced.
- Keep actual QRTR packet transmission out of the code path.
- Validate:
  - v264 model prerequisite
  - service/instance parsing
  - wildcard lookup block
  - approval flag checking
  - read-only bridge preflight
  - no-approval fail-closed run

## Guardrails

v266 must not:

- open QRTR sockets
- send QRTR nameservice packets
- issue QMI requests
- run `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP, or
  routing commands
- scan/connect/link-up Wi-Fi
- mutate rfkill, ICNSS, firmware, Android partitions, property service, perfd,
  kmsg, `/data/vendor/wifi`, or routing

Read-only bridge captures are allowed for `preflight`:

- `version`
- `status`
- `netservice status`
- `pidof cnss-daemon`
- `/proc/net/dev`
- `wifiinv full`

## Commands

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py plan
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py preflight
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py --service 1 --instance 1 run
```

The `run` command without approval flags must return a PASS fail-closed
decision. The approval flags may be parsed, but actual transmission remains
unimplemented in v266.

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

Read-only device preflight:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/preflight \
  preflight
```

Fail-closed no-approval run:

```bash
python3 scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  --out-dir tmp/wifi/v266-qrtr-nameservice-runner-skeleton/run-noapproval \
  --service 1 \
  --instance 1 \
  run
```

## Acceptance

- `plan` decision is `qrtr-ns-runner-plan-ready`.
- `preflight` decision is `qrtr-ns-runner-preflight-ready`.
- no-approval `run` decision is `qrtr-ns-runner-fail-closed`.
- No QRTR/QMI transmission is possible through v266.
- The next transmit-capable implementation remains explicit-approval-gated.
