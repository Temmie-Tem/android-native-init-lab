# V949 Matrix Provider-Readiness Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build verifier | `tmp/wifi/v949-matrix-provider-readiness-support/manifest.json` | `v949-matrix-provider-readiness-support-pass` |

V949 extends the existing CNSS/service-manager matrix path with the same
`mdm_helper_provider_readiness.*` diagnostics proven in V947. This is
source/build-only work; no device command was executed by the verifier.

## Implementation

- Advanced `a90_android_execns_probe` helper marker to `v158`.
- Changed provider-readiness snapshot marker to `snapshot_only=1`, so it can be
  used in both actor-free and actor-running contexts without implying that the
  surrounding mode did not start actors.
- Added provider-readiness snapshots to the matrix path:
  - `cnss_before_esoc_before`;
  - `cnss_before_esoc_after_service_manager_start`;
  - `cnss_before_esoc_after_per_mgr_settle`;
  - `cnss_before_esoc_after_mdm_helper_spawn`;
  - `cnss_before_esoc_after_cnss_daemon_start`;
  - `cnss_before_esoc_final`;
  - `cnss_before_esoc_after_cleanup`.

## Guardrails

- Source/build-only verification.
- No device command.
- No actor, daemon, service-manager, CNSS, or Wi-Fi HAL start by the verifier.
- No `/dev/subsys_esoc0` open.
- No eSoC ioctl, notify, or boot-done signal.
- No scan/connect/link-up, credential use, DHCP/route mutation, or external ping.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_matrix_provider_readiness_support_v949.py
python3 scripts/revalidation/native_wifi_matrix_provider_readiness_support_v949.py
```

Verifier result:

- decision: `v949-matrix-provider-readiness-support-pass`
- pass: `true`
- build artifact:
  `tmp/wifi/v949-execns-helper-v158-build/a90_android_execns_probe`
- build sha256:
  `dfd70d5bb7cdfeb52ea5843da3ff01560c4cd1d890d9cd7e65269a287c2e724d`
- build rc: `0`

The verifier confirmed:

- helper version marker is `a90_android_execns_probe v158`;
- provider-readiness snapshots are pure observer snapshots;
- the existing runtime-contract path remains instrumented;
- the CNSS/service-manager matrix path now records provider-readiness phases;
- matrix guardrails still block Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, eSoC notify, and boot-done;
- the matrix path still does not start `pm_proxy_helper`.

## Next

V950 should deploy helper `v158` only. V951 should run one bounded
CNSS/service-manager matrix order with provider-readiness capture, preferably
the prior best comparator `before-cnss`, while keeping `pm_proxy_helper`,
`/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and
external ping blocked.
