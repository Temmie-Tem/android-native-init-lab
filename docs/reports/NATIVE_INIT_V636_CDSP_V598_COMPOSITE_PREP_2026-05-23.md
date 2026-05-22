# Native Init V636 CDSP + V598 Composite Prep Report

- date: `2026-05-23 KST`
- status: `prep/plan-ready`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_cdsp_v598_composite_v636.py`
- plan evidence: `tmp/wifi/v636-cdsp-v598-plan-20260523-054048/`
- decision: `v636-cdsp-v598-composite-plan-ready`

## Scope

V636 prepares the next bounded live gate after V635. It combines:

- V635: read-only firmware mounts plus CDSP-only bounded write, which brings
  CDSP to PIL/reset/power-clock/ONLINE without `pm_qos` warnings;
- V598/V625/V627: modem-holder companion/readback path, which reproducibly
  reaches QRTR RX/TX, modem `sysmon-qmi`, and service-notifier `180`.

The intended live proof tests whether those two proven-safe pieces together
advance service `74`, WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0`.

## Prep Result

```text
decision: v636-cdsp-v598-composite-plan-ready
pass: True
reason: plan-only; no device command executed
next: run fresh V490 then V636 preflight
device_commands_executed: False
device_mutations: False
cdsp_write_executed: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Runner Contract

| item | contract |
| --- | --- |
| baseline | requires native v319 health and fresh V490 for current boot |
| initial CDSP | blocks if CDSP is already `ONLINE`; reboot first for clean evidence |
| CDSP trigger | V635 bounded child writes only `/sys/kernel/boot_cdsp/boot` |
| V598 replay | reuses helper v100 modem-holder companion and WLFW QRTR readback |
| cleanup | V635 unmount cleanup plus V598 reboot cleanup |
| Wi-Fi bring-up | explicitly disabled |

## Guardrails

- no ADSP/SLPI/`boot_wlan`/`qcwlanstate`/`shutdown_wlan` write;
- no service-manager or Wi-Fi HAL start;
- no scan/connect/link-up, credentials, DHCP, routes, or external ping;
- no partition writes or boot image changes.

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_cdsp_v598_composite_v636.py`
  passed.
- V636 `plan` command passed and executed no device command.
- `git diff --check` passed.
- Sensitive-output scan passed for the V636 plan, runner, and docs index.

## Next Gate

Run a fresh current-boot V490 policy-load proof, then V636 preflight. If
preflight passes, the bounded live command should execute V636 with its exact
approval phrase. Wi-Fi connection credentials remain unused until service `74`,
WLAN-PD, WLFW/BDF, firmware-ready, or `wlan0` advances.
