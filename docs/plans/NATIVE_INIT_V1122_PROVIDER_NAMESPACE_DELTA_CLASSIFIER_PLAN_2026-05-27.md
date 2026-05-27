# Native Init V1122 Provider Namespace Delta Classifier Plan

Date: `2026-05-27`

## Goal

Compare V1108 provider-positive evidence with V1121 firmware-mounted evidence
to identify the differentiator behind `pm-service` clean exit before provider
registration.

## Inputs

- `tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live/manifest.json`
- `tmp/wifi/v1121-firmware-mount-only-provider-live/manifest.json`

## Scope

- Host-only evidence comparison.
- No device command.
- No tracefs write.
- No daemon start.
- No Wi-Fi HAL, scan/connect, DHCP, credential use, route, or external ping.

## Success Criteria

- Confirm both gates used the no-pre-CNSS `per_proxy` contract.
- Confirm V1108 provider-positive + CNSS PM register/connect success.
- Confirm V1121 provider-missing + CNSS PM path not reached.
- Identify whether firmware mount/global `/vendor` surface is the remaining
  differentiator.
