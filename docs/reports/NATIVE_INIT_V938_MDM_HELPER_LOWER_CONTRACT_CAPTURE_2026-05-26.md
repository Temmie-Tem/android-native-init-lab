# V938 mdm_helper Lower-Contract Capture Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| live capture | `tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json` | `v938-mdm-helper-lower-contract-captured` |

V938 ran the existing bounded `mdm_helper` runtime-contract capture with helper
`v155` lower-contract diagnostics enabled. It captured the remaining
property-context and eSoC lower surfaces without starting service-manager,
CNSS, Wi-Fi HAL, scan/connect, DHCP/routing, or external ping.

## Implementation

- Added wrapper:
  `scripts/revalidation/native_wifi_mdm_helper_lower_contract_capture_v938.py`
- Required deployed helper marker:
  `a90_android_execns_probe v155`
- Required helper sha256:
  `44d7820e7bc33ab9886ea4f5f39248b1902c404c694c48fcd00a3ecc0fb76063`
- Evidence:
  `tmp/wifi/v938-mdm-helper-lower-contract-capture-live/summary.md`

## Live Findings

- `mdm_helper` was started and became observable.
- `mdm_helper` final fd scan showed one `/dev/esoc-0` fd.
- No `/dev/subsys_esoc0` fd was observed.
- No `/dev/mhi_0305_01.01.00_pipe_10` fd was observed.
- No `ks` process was observed.
- The helper mode timed out after preserving the evidence window, but
  postflight cleanup reported all tracked actors safe.
- No cleanup reboot was required.

## Lower-Contract Findings

- Private `/dev/esoc-0` exists as a character device with mode `0660` inside
  the runtime namespace.
- Private `/dev/__properties__` is present.
- `property_service` socket is absent before actor setup and present during
  the runtime window/final snapshot.
- `/sys/bus/esoc` and `/sys/bus/msm_subsys` are visible in the runtime
  namespace.
- Exact property-context entries for these `mdm_helper` keys are absent across
  `plat`, `system_ext`, and `vendor` property contexts:
  - `arm64.memtag.process.mdm_helper`
  - `persist.vendor.mdm_helper.fail_action`
  - `persist.vendor.mdm_helper.timeout`
  - `persist.log.tag.mdm_helper`
  - `log.tag.mdm_helper`
- Generic `log.tag` / `persist.log.tag` prefixes exist in platform property
  contexts, so this is a specific-key gap, not a total property-context mount
  absence.

## Interpretation

V938 confirms the lower-contract gap is now specifically below the repaired
runtime namespace and property-service surface. The actor can still reach
`/dev/esoc-0`, but it does not progress to `ks`, MHI pipe, WLFW, BDF, or
`wlan0`.

The evidence does not prove that the missing exact property-context entries are
the root cause. It proves they are co-present with the SDX50M queue/runtime
failure and should be classified before another eSoC trigger retry.

## Guardrails

- No service-manager start.
- No CNSS daemon start.
- No `/dev/subsys_esoc0` controller open attempt.
- No live eSoC ioctl.
- No `ks` start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP/route mutation.
- No external ping.

## Postflight

Manual postflight after V938:

- `bootstatus`: `BOOT OK`, `selftest fail=0`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `netservice status`: flag disabled, `ncm0` present, `tcpctl` stopped.

## Next

V939 should be a host-only classifier over V938 evidence. It should determine
whether the next minimal step is property-context materialization/override,
Android property-context recapture, or a different `mdm_helper` lower input
repair. Do not retry `/dev/subsys_esoc0`, `ESOC_NOTIFY`, Wi-Fi HAL, or
scan/connect until that classification is complete.
