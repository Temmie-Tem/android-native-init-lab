# Native Init v392 Handoff And Framechain Analyzer

## Summary

V390 approval phrases were rechecked against the committed V390 live result. No duplicate V390 live run was performed because V390 already deployed helper v20 and captured the service-manager PC/LR crash map rows.

V392 remains the active next execution target. This update adds a guarded live handoff document and a host-only frame-chain analyzer for the V392 backchain evidence that will be produced by helper v21.

This update does not deploy helper v21, does not start service-manager daemons, and does not attempt Wi-Fi bring-up.

## V390 Recheck

- report: `docs/reports/NATIVE_INIT_V390_APPROVED_LIVE_RESULT_2026-05-20.md`
- evidence: `tmp/wifi/v390-approved-full-20260520-063910/`
- decision: `v390-deploy-live-executor-full-service-manager-runtime-gap-servicemanager-sigabrt-captured`
- pass: `True`
- helper v20 deploy: PASS
- service-manager crash map capture: PASS
- Wi-Fi bring-up: `False`

V390 confirmed:

- `hwservicemanager`: `start-only-pass`
- `servicemanager`: `start-only-runtime-gap`
- PC: `libc.so + 0x8bebc`
- LR: `libc.so + 0x8be90`

## Added Handoff

- handoff: `docs/archive/legacy/operations/WIFI_V392_BACKCHAIN_LIVE_HANDOFF.md`

The handoff records:

- hard boundaries for V392 helper v21 deploy and service-manager start-only capture
- exact V392 approval phrases
- one-shot executor command
- preflight, deploy-only, live-only, post-run analyzer, and rollback commands
- explicit block on Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, driver bind/unbind, firmware mutation, and Android partition writes

Older V390 approval phrases are intentionally insufficient for V392 execution.

## Added Analyzer

- tool: `scripts/revalidation/wifi_service_manager_framechain_analyze.py`
- executor integration: `docs/reports/NATIVE_INIT_V392_EXECUTOR_FRAMECHAIN_INTEGRATION_2026-05-20.md`

The analyzer is host-only. It parses V392 live logs for:

- `capture.crash.framechain.count`
- `capture.crash.framechain.N.fp`
- `capture.crash.framechain.N.next_fp`
- `capture.crash.framechain.N.return_addr`
- `capture.crash.maprow.frameN_ra.*`

When a matching ELF root is provided, it also symbolicates frame return addresses through `addr2line`.

Decision labels:

- `service-manager-framechain-symbolization-pass`
- `service-manager-framechain-maprow-ready`
- `service-manager-framechain-no-maprow`
- `service-manager-framechain-needs-v392-live`

## Validation

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_framechain_analyze.py
git diff --check
```

Result: PASS.

Negative parser validation against V390 live evidence:

```text
python3 scripts/revalidation/wifi_service_manager_framechain_analyze.py \
  --out-dir tmp/wifi/v392-framechain-negative-v390 \
  --run-log tmp/wifi/v390-approved-full-20260520-063910/live/native/run-system-servicemanager.txt \
  analyze
```

Result:

```text
decision: service-manager-framechain-needs-v392-live
pass: True
framechain_present: False
maprows_present: False
symbols_present: False
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Evidence:

- `tmp/wifi/v392-framechain-negative-v390/`

## Current Execution State

V392 is still blocked until exact V392 approval is provided:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Once approved, run the V392 one-shot executor from the handoff document and then parse the new live log with `wifi_service_manager_framechain_analyze.py`.

After the executor integration update, the one-shot executor runs that frame-chain parse automatically for runtime-gap live results. Manual parsing remains useful for ad-hoc or copied evidence.
