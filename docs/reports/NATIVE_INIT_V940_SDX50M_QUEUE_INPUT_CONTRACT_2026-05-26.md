# V940 SDX50M Queue Input Contract Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v940-sdx50m-queue-input-contract/manifest.json` | `v940-pm-provider-queue-timing-instrumentation-selected` |

V940 classifies the next useful work as source/build-only helper
instrumentation for `mdm_helper` queue timing against PeripheralManager
provider/lifetime state. It does not select property-context override, Magisk
module work, `/dev/subsys_esoc0` retry, Wi-Fi HAL, or scan/connect as the next
step.

## Implementation

- Added classifier:
  `scripts/revalidation/native_wifi_sdx50m_queue_input_contract_v940.py`
- Inputs:
  - `tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json`
  - `tmp/wifi/v939-v938-lower-contract-classifier/manifest.json`
  - `tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json`
  - V857/V860/V861/V867 PM reports
- Evidence:
  `tmp/wifi/v940-sdx50m-queue-input-contract/summary.md`

## Findings

Current native V938 actor surface:

| Marker | Value |
| --- | --- |
| `mdm_helper` final `/dev/esoc-0` fd | `true` |
| `mdm_helper` window `/dev/esoc-0` fd | `false` |
| `ks` absent | `true` |
| MHI pipe absent | `true` |
| `per_mgr` observable | `true` |
| `per_mgr` pre-cleanup safe | `false` |
| service-manager started | `false` |
| `pm_proxy_helper` started | `false` |
| SDX50M queue failures | `4` |

PM evidence already closes these first-response blockers:

- V857: shutdown-critical property writes were allowed.
- V860: PM property denials reached zero.
- V861: direct exec still ran with runtime `attr/current=kernel` and no
  Android-equivalent subsystem holds.
- V867: init-contract markers and `ioprio rt 4` executed, but
  `pm_proxy_helper` hit D-state and `per_mgr` still did not retain subsystem
  fds.

## Interpretation

The remaining correlated gap is not exact `mdm_helper` property context and not
the basic existence of `/dev/esoc-0`. Native reaches `/dev/esoc-0`, but the
SDX50M event queue path still fails while the PM/provider lifetime model is
known incomplete.

The next implementation should therefore add narrow observability around:

- `per_mgr` lifetime at the moment `mdm_helper` queues SDX50M;
- provider/voter readiness markers visible to `mdm_helper`;
- ordering of `/dev/esoc-0` fd acquisition versus queue failure;
- fresh-pid attribution for the queue failure lines.

## Guardrails

- Host-only classifier only.
- No device command.
- No actor start.
- No service-manager, CNSS, Wi-Fi HAL, wificond, supplicant, or hostapd.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl.
- No GPIO/sysfs/debugfs write.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_sdx50m_queue_input_contract_v940.py
python3 scripts/revalidation/native_wifi_sdx50m_queue_input_contract_v940.py
```

## Next

V941 should be helper `v156` source/build-only work. It should add
queue-timing diagnostics to the existing runtime-contract path without opening
`/dev/subsys_esoc0`, without sending eSoC notifications, and without starting
Wi-Fi HAL or scan/connect.
