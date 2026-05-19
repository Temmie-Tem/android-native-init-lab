# V381 Execns Service Property Runtime Plan

## Summary

- Baseline native build remains `A90 Linux init 0.9.61 (v319)`.
- Target helper version: `a90_android_execns_probe v14`.
- V381 is helper support only: allow service-manager start-only mode to receive a private read-only property area and a minimal private `/data` tree.
- No helper deploy, no daemon start, no Wi-Fi HAL start, and no Wi-Fi bring-up are part of V381.

## Background

V380 proved that private Binder nodes now work in the helper namespace. The next classifier result is `service-manager-runtime-gap-property-runtime-required`:

- `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` are present in the helper namespace.
- `/dev/__properties__` is absent.
- `/data` is absent.
- `servicemanager` still aborts while `hwservicemanager` can stay observable until timeout.

AOSP property service creates `/dev/__properties__`, writes serialized property metadata at `/dev/__properties__/property_info`, initializes property areas, and then loads boot/default properties. Bionic clients read from this property runtime. Our earlier V317/V320 proofs already built and verified a private read-only property area under `/mnt/sdext/a90/private-property-v317/dev/__properties__`.

## Design

- Keep global native `/dev/__properties__` untouched.
- Reuse the existing private V317 property root:
  - `/mnt/sdext/a90/private-property-v317/dev/__properties__`
- Extend `a90_android_execns_probe` validation so `--property-root` is valid in:
  - `property-lookup`
  - `service-manager-start-only`
- Keep `--property-key` valid only in `property-lookup`.
- Extend namespace setup so private properties are bind-mounted when:
  - mode is `property-lookup`, or
  - mode is `service-manager-start-only`, `--allow-service-manager-start-only` is present, and `--property-root` is supplied.
- Use existing `--data-wifi-mode private-empty` support for a minimal private `/data/vendor/wifi/sockets` tree in the helper temp root.

## Guardrails

- No persistent `/data` write.
- No global `/dev/__properties__` bind.
- No property service socket creation.
- No Android service-manager start in V381.
- No Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, scan/connect, DHCP, routing, rfkill, firmware, or credential actions.

## Validation

- Build static ARM64 helper:
  - `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -o tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe stage3/linux_init/helpers/a90_android_execns_probe.c`
- Confirm artifact marker/strings:
  - `a90_android_execns_probe v14`
  - `service-manager-start-only`
  - `--allow-service-manager-start-only`
  - `--property-root`
  - `--data-wifi-mode`
- Confirm static artifact has no dynamic section.
- Run `git diff --check`.

## Next

- V382 should deploy v14 and run service-manager start-only with:
  - `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`
  - `--data-wifi-mode private-empty`
- V382 remains no Wi-Fi HAL and no Wi-Fi bring-up.
