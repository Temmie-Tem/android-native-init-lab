# V939 V938 Lower-Contract Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v939-v938-lower-contract-classifier/manifest.json` | `v939-exact-property-context-gap-not-sufficient` |

V939 classifies the V938 exact `mdm_helper` property-context gap as
co-present but not sufficient as the next blocker. The next native Wi-Fi gate
should not materialize exact property-context overrides or retry eSoC triggers
until the SDX50M queue input path is better classified.

## Implementation

- Added classifier:
  `scripts/revalidation/native_wifi_v938_lower_contract_classifier_v939.py`
- Inputs:
  - `tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json`
  - `tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json`
- Evidence:
  `tmp/wifi/v939-v938-lower-contract-classifier/summary.md`

## Findings

V938 native lower-contract evidence:

- Runtime property root is present.
- `/dev/__properties__` is present.
- Runtime `property_service` socket is present by the final snapshot.
- Private `/dev/esoc-0` is a character device with mode `0660`.
- `/sys/bus/esoc` and `/sys/bus/msm_subsys` are visible.
- `mdm_helper` reaches `/dev/esoc-0`.
- `ks` and the MHI pipe remain absent.
- Four current dmesg lines report `unable to queue event for SDX50M`.

Property-context evidence:

| Property | Exact hits |
| --- | --- |
| `arm64.memtag.process.mdm_helper` | `0` |
| `persist.vendor.mdm_helper.fail_action` | `0` |
| `persist.vendor.mdm_helper.timeout` | `0` |
| `persist.log.tag.mdm_helper` | `0` |
| `log.tag.mdm_helper` | `0` |

Generic property prefixes are present:

| Prefix | Hits |
| --- | --- |
| `log.tag` | `12` |
| `persist.log.tag` | `4` |

Android reference from V914:

- Android upper Wi-Fi path is positive: WLAN-PD, WLFW, BDF, and `wlan0`.
- Post-boot Android lower shape matches the native lower shape in the relevant
  sampled markers: `mdm_helper` holds `/dev/esoc-0`, while current `ks` and
  current MHI pipe are absent.

## Interpretation

The exact property-context misses remain useful diagnostics, but they are not a
strong enough root-cause candidate to justify a property-context override as
the next implementation unit. V938 proves the repaired runtime surface is
sufficient for `mdm_helper` to reach `/dev/esoc-0`, and V914 proves Android can
reach the upper Wi-Fi path even though the sampled post-boot lower markers do
not show current `ks` or MHI.

The remaining blocker is therefore more likely in the
`mdm_helper` / peripheral-manager SDX50M queue input contract than in exact
property-context materialization.

## Guardrails

- Host-only classifier only.
- No device command.
- No daemon start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.
- No eSoC ioctl or `/dev/subsys_esoc0` open.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v938_lower_contract_classifier_v939.py
python3 scripts/revalidation/native_wifi_v938_lower_contract_classifier_v939.py
```

## Next

V940 should classify the `mdm_helper` / peripheral-manager SDX50M queue input
contract before any new live trigger. If fresh Android timing is needed, reuse
the existing V913 Android read-only collector with a new output directory, but
do not introduce a Magisk module or property-context override as the first
response to V938.
