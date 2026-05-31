# V1240 SDX50M Response Surface Live Classifier

- report: `docs/reports/NATIVE_INIT_V1240_SDX50M_RESPONSE_SURFACE_LIVE_2026-05-31.md`
- classifier: `scripts/revalidation/native_wifi_sdx50m_response_surface_live_v1240.py`
- evidence: `tmp/wifi/v1240-sdx50m-response-surface-live/manifest.json`
- summary: `tmp/wifi/v1240-sdx50m-response-surface-live/summary.md`

- decision: `v1240-response-inputs-visible-mdm2ap-silent`
- pass: `True`
- reason: read-only SDX50M response surfaces are visible, but `mdm3` remains `OFFLINING` and the MDM status / GPIO142 interrupt count remains `0`.
- next_step: design V1241 around AP2MDM, PMIC, and PCIe prerequisites before retrying `pm-service` `/dev/subsys_esoc0`.

## Checks

| check | status | detail |
| --- | --- | --- |
| live-readonly flags | pass | `--allow-live-readonly --assume-yes` supplied |
| V1239 input | pass | `v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw` |
| runtime health | pass | version, bootstatus, selftest, post-bootstatus, post-selftest, and stopped netservice all clean |
| read-only steps | pass | version, bootstatus, selftest, sysfs, PCIe, interrupts, GPIO, regulator, devicetree, device-node metadata, and dmesg captures completed |
| MDM3 response state | pass | `mdm3=OFFLINING`, `esoc_name=SDX50M`, `esoc_link=PCIe`, `esoc_link_info=0305_01.01.00` |
| MDM status IRQ surface | pass | `/proc/interrupts` exposes `msmgpio-dc 142 Edge mdm status`, count total `0` |
| PCIe surface | pass | RC1 sysfs surface exists; no active link state was reported |
| GPIO/DT surface | finding | debug GPIO and pinctrl are not readable/present, GPIO135/142 are not exported, but DT AP2MDM/MDM2AP/soft-reset properties exist |

## Key Evidence

| field | value |
| --- | --- |
| `mdm3_state` | `OFFLINING` |
| `mss_state` | `OFFLINING` |
| `esoc_name` | `SDX50M` |
| `esoc_link` | `PCIe` |
| `esoc_link_info` | `0305_01.01.00` |
| MDM status IRQ | `290: ... msmgpio-dc 142 Edge mdm status`, count total `0` |
| PCIe runtime status | `unsupported` |
| focused regulator entries | `56` |
| dmesg `wlfw` count | `0` |
| dmesg `wlan0` count | `0` |

## Interpretation

V1240 confirms the V1239 boundary without widening live action. The device exposes
the SDX50M/eSoC metadata and the MDM status IRQ surface in native init, but the
downstream response is still absent: `mdm3` does not leave `OFFLINING`, GPIO142
does not fire, PCIe RC1 does not report a live link state, and no WLFW or `wlan0`
markers appear.

The next gate should not retry Wi-Fi HAL, scan/connect, DHCP, or external ping.
It should focus on the prerequisites that allow SDX50M to respond after
`pm-service` enters `mdm_subsys_powerup`: AP2MDM assertion observability, MDM2AP
status response, PMIC/regulator readiness, PCIe RC1 link prerequisites, and a
cleanup boundary that does not require blind raw eSoC opens.

## Safety

Read-only live classifier. No raw eSoC/subsys open, GPIO/sysfs write, daemon
start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot,
flash, boot image write, or partition write occurred. Postflight remained clean:
`selftest: pass=11 warn=1 fail=0`, `netservice enabled=no`, `tcpctl=stopped`,
and `boot: BOOT OK`.
