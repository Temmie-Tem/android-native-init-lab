# V381 Execns Service Property Runtime Report

## Result

- decision: `execns-helper-v14-service-property-runtime-local-pass`
- pass: `true`
- device build: `A90 Linux init 0.9.61 (v319)`
- helper version: `a90_android_execns_probe v14`
- scope: local helper source/build only
- device deploy: `false`
- daemon start: `false`
- Wi-Fi bring-up: `false`

## Artifact

| item | value |
| --- | --- |
| local artifact | `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe` |
| sha256 | `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7` |
| file | `ELF 64-bit LSB executable, ARM aarch64, statically linked` |
| dynamic section | none |

## Changes

- Bumped `EXECNS_VERSION` to `a90_android_execns_probe v14`.
- Allowed `--property-root` in `service-manager-start-only` mode.
- Kept `--property-key` restricted to `property-lookup` mode.
- Extended private property materialization to service-manager start-only only when all are true:
  - `--mode service-manager-start-only`
  - `--allow-service-manager-start-only`
  - `--property-root` is supplied and allowlisted
- Preserved the existing V317 allowlist: property root must stay under `/mnt/sdext/a90/private-property-v317` and end in `/dev/__properties__`.

## Validation

- static ARM64 build: PASS
- required strings: PASS
- no dynamic section: PASS
- `git diff --check`: PASS

## Interpretation

V381 prepares the smallest repair for the V380 runtime gap. It does not prove that service-manager survives yet; it only enables the next live smoke to present a private read-only property area and minimal private `/data` tree to the service-manager namespace without touching global native paths.

## References

- AOSP property service serializes property info to `/dev/__properties__/property_info` and initializes the property area during `PropertyInit`.
- AOSP property service creates the property service socket separately; V381 deliberately does not emulate mutable property service socket behavior.

## Next

- V382: deploy v14 to `/cache/bin/a90_android_execns_probe` and rerun bounded service-manager start-only with private property root and `private-empty` data mode.
- Continue blocking Wi-Fi HAL/start/bring-up until service-manager start-only is stable and postflight-clean.
