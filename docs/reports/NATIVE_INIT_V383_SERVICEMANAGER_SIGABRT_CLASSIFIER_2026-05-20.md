# V383 Service-Manager SIGABRT Runtime-Gap Classifier

## Summary

- Extended `scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py` to classify the V382 result without device mutation.
- New decision: `service-manager-runtime-gap-servicemanager-sigabrt-capture-required`.
- This applies when `system-servicemanager` exits with `SIGABRT`, Binder/property prerequisites are not the first blocker, and `system-hwservicemanager` survives the bounded start-only window.
- No bridge command, device command, daemon start, or Wi-Fi bring-up is performed by this classifier.

## Source Notes

- AOSP Android 11 `servicemanager` main path initializes Binder polling and uses fatal checks around Binder/Looper setup.
- AOSP Android 11 `servicemanager` access path uses SELinux service context handles and `CHECK`/fatal behavior for required SELinux setup.
- Device evidence showed `hwservicemanager` loaded `plat_hwservice_contexts` and `vendor_hwservice_contexts`, but `servicemanager` aborted before becoming observable.

References:

- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/main.cpp
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-gsi/cmds/servicemanager/servicemanager.rc

## Validation

Regression:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v383-classifier-regression \
  regression
```

Result:

- decision: `service-manager-runtime-gap-classifier-regression-pass`
- pass: `true`
- device_commands_executed: `false`
- device_mutations: `false`

V382 evidence classification:

```bash
python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v383-classify-v382 \
  --v376-manifest tmp/wifi/v382-executor-full-approved-20260520-035119/live/manifest.json \
  classify
```

Result:

- decision: `service-manager-runtime-gap-servicemanager-sigabrt-capture-required`
- pass: `true`
- reason: `servicemanager aborts with SIGABRT while hwservicemanager survives the bounded window`
- next_step: `add service-manager ptrace-lite/tombstone evidence capture before HAL work`
- device_commands_executed: `false`
- device_mutations: `false`

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py
git diff --check
```

## Interpretation

- V382 closed the helper-version blocker and advanced beyond the property-root blocker.
- The next blocker is not generic Binder absence and not generic property-runtime absence.
- The next actionable step is a bounded evidence-capture helper update, not Wi-Fi HAL start.

## Next Candidate

V384 should implement a local helper update that permits service-manager start-only `ptrace-lite` capture or equivalent early-crash evidence capture. Deployment and live execution must remain separately gated; Wi-Fi HAL/start/scan/connect remains blocked.
