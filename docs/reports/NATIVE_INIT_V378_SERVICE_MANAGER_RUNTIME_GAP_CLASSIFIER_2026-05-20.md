# V378 Service-Manager Runtime Gap Classifier Report

## Result

- regression decision: `service-manager-runtime-gap-classifier-regression-pass`
- live classify decision: `service-manager-runtime-gap-binder-devnode-required`
- Binder refresh decision: `binder-devnode-plan-ready`
- pass: `true`
- device_commands_executed: `false` for classifier
- device_mutations: `false`
- evidence:
  - `tmp/wifi/v378-service-manager-runtime-gap-classifier-regression-20260520-023043/`
  - `tmp/wifi/v378-service-manager-runtime-gap-classifier-live-20260520-023043/`
  - `tmp/wifi/v378-current-binder-devnode-feasibility-20260520-023057/`

## Verified

- Python compile PASS for `scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py`.
- Regression covers missing V376 manifest, not-needed, missing observations, Binder required, property required, and unsafe postflight cases.
- Live V376 evidence classified as `service-manager-runtime-gap-binder-devnode-required`.
- Both targets had `child_signal=6`, `postflight_safe=true`, and Binder driver open failure in stderr.
- Current read-only Binder metadata still matches:
  - `/dev/binder`: `10:81`
  - `/dev/hwbinder`: `10:80`
  - `/dev/vndbinder`: `10:79`
- No HAL, scan/connect, DHCP, routing, rfkill, firmware, or Android partition write was performed.

## Interpretation

The first hard blocker after V376 is not linker namespace, identity switching, or service-manager binary visibility. Those phases reached the child exec boundary. The child then aborted because Binder device nodes were absent inside the helper namespace.

`/dev/__properties__` and `/data` are also absent in the captured namespace, but the observed abort occurs at Binder driver open first. Therefore the next repair should start with private Binder devnode provisioning and preserve cleanup/postflight gates.

## Reference

- Kernel binderfs documentation describes private Binder device instances and dynamic Binder device allocation: https://www.kernel.org/doc/html/v5.1/filesystems/binderfs.html

## Next Step

- V379 should add helper-private Binder devnode provisioning for service-manager start-only mode.
- Preferred first repair is static private devnodes from current misc metadata (`10:81`, `10:80`, `10:79`) inside the helper temp root.
- Binderfs mount/allocation remains a separate, later option because it requires additional mount/ioctl policy.
- HAL start-only approval packet remains blocked until V376 no longer fails on Binder devnode absence.
