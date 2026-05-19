# V376 Service-Manager Start-Only Live Runner Report

## Result

- decision: `service-manager-start-only-live-preflight-ready`
- no-approval decision: `service-manager-start-only-live-approval-required`
- pass: `true`
- daemon_start_executed: `false`
- wifi_bringup_executed: `false`
- evidence:
  - `tmp/wifi/v376-plan-20260520-021643/`
  - `tmp/wifi/v376-preflight-20260520-021643/`
  - `tmp/wifi/v376-refusal-20260520-021651/`

## Verified

- Python compile PASS for `scripts/revalidation/wifi_service_manager_start_only_live_runner.py`.
- plan mode emits target/helper command plan without native execution.
- preflight mode checks native state through the bridge and does not start daemons.
- native version matched `A90 Linux init 0.9.61 (v319)`.
- native `status` and `selftest` were clean with `fail=0`.
- remote helper SHA matched `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`.
- remote helper usage includes `service-manager-start-only` and `--allow-service-manager-start-only`.
- `servicemanager` and `hwservicemanager` binaries are visible.
- linkerconfig and apex libraries runtime inputs are visible.
- `sda29` sysfs device metadata is visible.
- service-manager process surface is clean.
- Wi-Fi link surface is clean.
- temporary Binder nodes are not present before helper execution.
- no-approval run refused before any bridge/native command.

## Current Gate

Generic approval text is not accepted for live daemon start. The runner requires this exact phrase with `--apply --assume-yes`:

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

- If operator accepts the bounded daemon-start risk, run the approved V376 command with the exact V373 phrase.
- The approved command may start only `servicemanager` and `hwservicemanager` in helper `service-manager-start-only` mode.
- Wi-Fi HAL start, scan/connect/link-up, credential, DHCP, routing remain blocked.
