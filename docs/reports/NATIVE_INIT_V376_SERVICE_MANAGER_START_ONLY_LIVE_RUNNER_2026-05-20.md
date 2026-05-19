# V376 Service-Manager Start-Only Live Runner Report

## Result

- initial preflight decision: `service-manager-start-only-live-preflight-ready`
- no-approval decision: `service-manager-start-only-live-approval-required`
- approved live decision: `service-manager-start-only-live-runtime-gap`
- pass: `true`
- daemon_start_executed: `true`
- wifi_bringup_executed: `false`
- evidence:
  - `tmp/wifi/v376-plan-20260520-021643/`
  - `tmp/wifi/v376-preflight-20260520-021643/`
  - `tmp/wifi/v376-refusal-20260520-021651/`
  - `tmp/wifi/v376-preflight-refresh-20260520-021959/`
  - `tmp/wifi/v376-approved-run-20260520-022612/`

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
- exact approval phrase was received and approved live run executed only service-manager start-only helper calls.
- `system-servicemanager` and `system-hwservicemanager` both returned `start-only-runtime-gap`.
- both child processes started and then exited with `SIGABRT` before the observe window.
- postflight cleanup remained safe: `manager_processes=0`, `wifi_links=0`.
- post-run native `status` and `selftest` remained clean with `fail=0`.

## Runtime Gap

Both targets reached `exec_attempted=1` and `child_started=1`, then aborted before becoming observable.

- `servicemanager`: `Binder driver '/dev/binder' could not be opened.  Terminating.` followed by `SIGABRT`.
- `hwservicemanager`: `Binder driver could not be opened. Terminating.` followed by `SIGABRT`.
- `context.dev_properties.exists=0` and `/data` paths are also absent, but the first hard runtime blocker in this run is missing private Binder devnodes.

## Next Step

- Classify the V376 runtime gap before any HAL start-only approval packet.
- Likely next implementation target: helper private Binder devnode provisioning inside the service-manager namespace, preserving cleanup and scope gates.
- Wi-Fi HAL start, scan/connect/link-up, credential, DHCP, routing remain blocked.
