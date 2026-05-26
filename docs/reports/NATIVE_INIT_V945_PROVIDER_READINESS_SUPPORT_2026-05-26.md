# V945 Provider-Readiness Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build verifier | `tmp/wifi/v945-provider-readiness-support/manifest.json` | `v945-provider-readiness-support-pass` |

V945 adds provider-readiness diagnostics to the existing bounded
`mdm_helper` runtime-contract path. It does not start a new actor and does not
expand the live trigger surface.

## Implementation

- Advanced `a90_android_execns_probe` helper marker to `v157`.
- Added `mdm_helper_provider_readiness.*` snapshots at the same phases as the
  V943 queue-timing snapshots:
  - `before_property_shim`;
  - `after_per_mgr_settle`;
  - `after_mdm_helper_spawn`;
  - `window`;
  - `final`;
  - `after_cleanup`.
- Each snapshot records:
  - private binder node status for `binder`, `hwbinder`, and `vndbinder`;
  - private property-service socket status;
  - `servicemanager`, `hwservicemanager`, `vndservicemanager`, `pm-service`,
    `pm-proxy`, and `pm_proxy_helper` process counts;
  - `per_mgr` and `mdm_helper` fd matches for binder, hwbinder, and vndbinder.

## Guardrails

- Source/build-only verification.
- No device command.
- No actor, daemon, service-manager, CNSS, or Wi-Fi HAL start.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl, notify, or boot-done signal.
- No scan/connect/link-up, credential use, DHCP/route mutation, or external ping.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_provider_readiness_support_v945.py
python3 scripts/revalidation/native_wifi_provider_readiness_support_v945.py
```

Verifier result:

- decision: `v945-provider-readiness-support-pass`
- pass: `true`
- build artifact:
  `tmp/wifi/v945-execns-helper-v157-build/a90_android_execns_probe`
- build sha256:
  `308b0f37bfe1265874afdc141f07c8d0b638e6d80c5093af03641f54e96371c2`
- build rc: `0`

The verifier confirmed:

- helper version marker is `a90_android_execns_probe v157`;
- existing `wifi-companion-mdm-helper-runtime-contract-capture` mode remains
  present;
- provider-readiness path, process, and fd diagnostics are present;
- no new trigger or Wi-Fi bring-up markers were introduced;
- the helper artifact is statically linked.

## Next

V946 should deploy helper `v157` only. V947 should run the same bounded
runtime-contract live capture and classify whether `per_mgr`/provider readiness
is missing because binder/service-manager surfaces are absent, because
`pm-service` never opens provider fds, or because a later provider actor is
needed. Do not start `pm_proxy_helper`, open `/dev/subsys_esoc0`, or start
Wi-Fi HAL until that classification is available.
