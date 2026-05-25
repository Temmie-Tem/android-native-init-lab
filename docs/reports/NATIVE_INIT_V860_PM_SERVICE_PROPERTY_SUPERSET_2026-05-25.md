# Native Init V860 pm-service Property Superset Report

## Result

V860 passed as a bounded diagnostic/proof cycle.

| Unit | Evidence | Decision |
|---|---|---|
| host layout | `tmp/wifi/v860-pm-service-property-superset-runtime/manifest.json` | `v860-pm-service-property-superset-runtime-ready` |
| deploy plan | `tmp/wifi/v860-pm-service-property-superset-incremental-plan/manifest.json` | `v860-pm-service-property-superset-incremental-plan-ready` |
| deploy preflight | `tmp/wifi/v860-pm-service-property-superset-incremental-preflight/manifest.json` | `v860-pm-service-property-superset-incremental-preflight-ready` |
| deploy live | `tmp/wifi/v860-pm-service-property-superset-incremental-live/manifest.json` | `v860-pm-service-property-superset-incremental-deploy-pass` |
| replay live | `tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json` | `v860-property-clean-no-subsys-hold` |

## Layout

| Field | Value |
|---|---:|
| property count | `131` |
| context count | `21` |
| V858 target keys | `8` |
| V859 new keys | `8` |
| V677 regression keys | `20` |
| V860 superset keys | `28` |
| missing mappings | `0` |
| missing seeds | `0` |

V860 preserved the V858 `pm-service`/`pm-proxy` keys and added the V859
`vndservicemanager`, `ServiceManager`, and `PerMgrLib` keys. The V677 residual
set was included to avoid regressing older service-manager/Wi-Fi-HAL property
coverage.

## Live Replay

The bounded replay reused helper v132 and did not redeploy the helper. It
materialized and cleaned up Android-equivalent eSoC/subsys nodes, ran only the
`pm-service`/`pm-proxy` start-only path, and preserved the hard gates.

| Observation | Value |
|---|---|
| property denial total | `0` |
| property denial unique | `0` |
| V860 target remaining | `[]` |
| new after V860 | `[]` |
| `pm-service` observable | `1` |
| `pm-proxy` observable | `1` |
| `pm-service` holds `/dev/subsys_esoc0` | `false` |
| `pm-service` holds `/dev/subsys_modem` | `false` |
| helper deploy executed | `false` |
| `mdm_helper` / `ks` start executed | `false` |
| Wi-Fi HAL / bring-up executed | `false` |
| external ping executed | `false` |

## Device Health

Post-run selftest passed:

```text
selftest: pass=11 warn=1 fail=0 duration=40ms entries=12
```

## Interpretation

The active blocker is no longer private property coverage for the current
`pm-service`/`pm-proxy` path. The remaining gap is a lifetime/provider-input
gap: `pm-service` becomes observable under Android-equivalent node parity but
does not hold `/dev/subsys_esoc0` or `/dev/subsys_modem` in the capture window.

## Next Gate

V861 should classify the post-property-clean `pm-service` lifetime gap before
starting `mdm_helper` or `ks`. The useful target is now child lifetime,
provider registration, stdout/stderr, exit status, and fd timing versus Android
V853, not another property overlay unless new denial evidence appears.
