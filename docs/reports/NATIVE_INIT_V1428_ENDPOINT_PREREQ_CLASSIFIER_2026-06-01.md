# Native Init V1428 Endpoint Prerequisite Classifier

## Summary

- Cycle: `V1428`
- Type: host-only/read-only classifier over existing reports and manifests
- Decision: `v1428-rc1-retry-closed-pre-rc1-endpoint-prereq-next`
- Result: PASS
- Reason: timing, ordering, GPIO135, PON, and retry-count branches are closed enough; the next useful work is endpoint prerequisite parity around PERST release
- Evidence: `tmp/wifi/v1428-endpoint-prereq-classifier/manifest.json`

## Inputs

| Input | Path | Pass |
| --- | --- | --- |
| `v1353_pcie1_static_contract` | `docs/reports/NATIVE_INIT_V1353_PCIE1_RC_STATIC_CONTRACT_CLASSIFIER_2026-06-01.md` | `True` |
| `v1354_current_route_rc_off` | `docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md` | `True` |
| `v1355_pon_parity` | `docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md` | `True` |
| `v1368_rc1_status_read` | `docs/reports/NATIVE_INIT_V1368_PCI_MSM_CORRECTED_RC1_STATUS_LIVE_2026-06-01.md` | `True` |
| `v1370_corrected_rc1` | `docs/reports/NATIVE_INIT_V1370_PCI_MSM_CORRECTED_RC1_ENUMERATE_LIVE_2026-06-01.md` | `True` |
| `v1372_provider_held` | `docs/reports/NATIVE_INIT_V1372_PROVIDER_HELD_PCIE1_ENUMERATE_LIVE_2026-06-01.md` | `True` |
| `v1423_gpio135` | `docs/reports/NATIVE_INIT_V1423_GPIO135_PARITY_CLASSIFIER_2026-06-01.md` | `True` |
| `v1424_timing` | `docs/reports/NATIVE_INIT_V1424_RC1_TIMING_PARITY_CLASSIFIER_2026-06-01.md` | `True` |
| `v1427_retry_handoff` | `docs/reports/NATIVE_INIT_V1427_WIFI_TEST_BOOT_RC1_RETRY_HANDOFF_2026-06-01.md` | `True` |

## Closed Branches

| Branch | Result | Meaning |
| --- | --- | --- |
| static pcie1 contract | `True` | RC1 GPIO/clock/GDSC surfaces are known from DTS |
| current-route RC off | `True` | older current-route run observed pcie1 RC off before corrected enumerate work |
| PM8150L PON blind write | `True` | PON parity is closed enough to avoid direct PMIC mutation |
| corrected RC1 status surface | `True` | status-read case can expose PERST/WAKE without enumeration |
| corrected RC1 entry | `True` | corrected RC1 reaches PHY/LTSSM but not L0 |
| provider-held ordering | `True` | holding the provider path still does not reach L0 |
| GPIO135/AP2MDM low | `True` | GPIO135 low alone does not justify a direct GPIO/PMIC write |
| RC1 timing parity | `True` | V1424 put native RC1 assert within the Android timing window |
| RC1 INT mask parity | `True` | native and Android share the same RC1 INT mask path |
| single attempt hypothesis | `True` | V1427 executed initial plus two retries |
| retry widening | `True` | all retry attempts failed before L0 with no MHI/WLFW/`wlan0` |

## Classification

V1427 closes the simple test-boot retry branch. Three corrected-RC1
attempts produced the same reset/release/LTSSM path and failed before
L0. V1424 already made the timing close enough to Android, so adding
more retries is lower value than proving the endpoint prerequisites at
the exact PERST-release boundary.

- Downstream still blocked: `True`
- The next proof point is not Wi-Fi scan/connect. It is whether SDX50M
  sees the expected RC1 preconditions when PERST is released.

## V1429 Candidate

Build a source/build-only test boot that keeps the V1425 rollbackable
shape but replaces retry expansion with read-only endpoint-prerequisite
sampling around the corrected-RC1 window.

| Surface | Required observation |
| --- | --- |
| `perst_gpio102` | read around RC1 release |
| `clkreq_gpio103` | read around RC1 release |
| `wake_gpio104` | read around RC1 release |
| `pcie_1_gdsc` | read immediately before and after corrected RC1 |
| `pcie1_refclk_pipe_clocks` | read immediately before and after corrected RC1 |
| `gpio142_mdm2ap_irq` | read across the RC1 window |
| `ltssm_terminal_state` | classify post-release endpoint response |

The sampler should capture these states before the corrected RC1 write,
immediately after PERST release, and after the terminal LTSSM result.
It should not add new PMIC/GPIO/GDSC writes and should not start any
connect-side Wi-Fi work until L0/MHI/WLFW/`wlan0` progress exists.

## Safety Scope

This cycle was host-only. It did not run device commands, flash, reboot,
write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,
ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/
`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_endpoint_prereq_classifier_v1428.py
python3 scripts/revalidation/native_wifi_endpoint_prereq_classifier_v1428.py --write-report
```
