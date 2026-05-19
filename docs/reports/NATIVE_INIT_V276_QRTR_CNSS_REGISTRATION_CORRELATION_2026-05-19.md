# Native Init v276 QRTR/CNSS Registration Correlation Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_qrtr_cnss_registration_correlator.py`
- evidence: `tmp/wifi/v276-qrtr-cnss-registration-correlation/`
- decision: `qrtr-cnss-platform-surface-visible`
- packet transmission: none
- daemon execution: none

v276 correlated prior QRTR nameservice readback evidence with current native
read-only QRTR/CNSS state. The result is not an active registration success:
there are static CNSS/WLAN/QRTR platform surfaces, but no active QRTR service
notifications, no `cnss-daemon`, and no `wlan*` network interface.

## Prior Evidence Correlated

| source | result |
| --- | --- |
| v273 WDS/DMS matrix | service `1` and `2`, instances `0/1`, all timeout, events `0`, qmi_attempted `0` |
| v274 WLFW locator | WLFW service id `69` / `0x45`, source-backed, local cnss-daemon strings matched |
| v275 WLFW matrix | service `69`, instances `0/1`, all timeout, events `0`, qmi_attempted `0` |

## Live Read-only Findings

| field | result |
| --- | --- |
| `QIPCRTR` protocol | present in `/proc/net/protocols` |
| no-send QRTR probe | `bind-pass`, socket rc `0`, send_attempted `0`, connect_attempted `0` |
| `/proc/net/qrtr` | absent, rc `-2` |
| `/dev` QRTR/QMI/CNSS/WLAN/DIAG/IPA matches | `0` |
| `/sys` QRTR/QMI/CNSS/WLAN/ICNSS matches | `68` |
| `cnss-daemon` / `cnss_diag` process audit | clean, `0` target processes |
| `wlan*` interface | absent from `/proc/net/dev` and `/sys/class/net` |

Notable static surfaces include:

- `/sys/devices/platform/soc/18800000.qcom,icnss`
- `/sys/bus/platform/drivers/icnss/18800000.qcom,icnss`
- `/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390`
- `/sys/module/wlan`
- devicetree nodes for `qcom,icnss@18800000`, `qcom,cnss-qca6390@a0000000`,
  and QRTR transports under glink/adsp/cdsp/slpi/modem

## Checks

All critical checks passed:

- expected native init version
- required live captures
- v273 timeout evidence
- v274 WLFW source-backed evidence
- v275 timeout evidence
- QIPCRTR protocol presence
- no-send/no-connect QRTR probe
- clean CNSS process table
- no `wlan*` interface

## Interpretation

- QRTR socket availability is not the current blocker.
- The WLFW service id candidate is now concrete, but native-state nameservice
  readback still sees no server notifications for WDS, DMS, or WLFW.
- The system exposes static CNSS/WLAN/QRTR kernel/platform surfaces. That makes
  the next useful step a read-only ICNSS/CNSS platform-state classifier, not a
  QMI request-payload escalation.
- QMI payloads remain blocked until there is active endpoint/registration
  evidence or a separately reviewed minimal request contract.

## Guardrails Preserved

- no QRTR nameservice packet transmission
- no QMI request payload
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition
  write, property service mutation, perfd mutation, kmsg mutation, or reboot

## Postflight

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed

## Next Step

v277 should classify the visible static platform surfaces with read-only sysfs
and devicetree probes:

- ICNSS driver/device bind state and exposed attributes
- QCA6390 platform node state
- `/sys/module/wlan` parameters and holders
- WLAN-related regulators, reserved memory, boot/shutdown WLAN sysfs nodes
- whether any safe read-only state suggests why QRTR nameservice has no active
  WLFW server notification
