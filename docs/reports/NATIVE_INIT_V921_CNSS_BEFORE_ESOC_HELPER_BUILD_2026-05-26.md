# V921 CNSS-before-eSoC Helper Build

- generated: `2026-05-25T21:16:00+00:00`
- decision: `v921-mdm-helper-cnss-before-esoc-support-pass`
- pass: `True`
- reason: helper `v152` adds a CNSS/WLFW-precondition-gated `/dev/subsys_esoc0` path with explicit fail-closed no-open outputs.
- next_step: deploy helper `v152` only, then run the bounded live V923 precondition gate.

## Scope

V921 is source/build-only. It does not contact the device, deploy the helper,
start actors, open `/dev/subsys_esoc0`, boot Android, use credentials, scan,
associate, mutate DHCP/routes, ping externally, or write boot/partition/firmware
state.

The Android dmesg/GPIO/IRQ direction remains useful as fallback evidence, but
V919 already closed the immediate need for a new Magisk module or Android
recapture. V921 therefore implements the next native fail-closed gate instead
of adding another Android collection path.

## Added Helper Contract

New helper mode:

```text
wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture
```

Required opt-in flag:

```text
--allow-mdm-helper-cnss-before-subsys-trigger-capture
```

Required fail-closed outputs:

```text
cnss_before_esoc.wlfw_precondition_observed=0|1
cnss_before_esoc.subsys_esoc0_open_gate=cnss-wlfw-precondition
cnss_before_esoc.subsys_esoc0_open_attempted=0|1
```

## Execution Design

The new mode materializes the same private Android runtime surfaces used by the
existing `mdm_helper` runtime gates, then runs this bounded order:

1. property shim;
2. `per_mgr_light`;
3. `/vendor/bin/mdm_helper`;
4. wait for `mdm_helper` to expose `/dev/esoc-0`;
5. start `/vendor/bin/cnss_diag`;
6. start `/vendor/bin/cnss-daemon -n -l`;
7. poll for a WLFW precondition marker;
8. open `/dev/subsys_esoc0` only if the marker is observed;
9. capture blocker/wifi/subsys surfaces and cleanup actors.

## Static Verification

| check | value |
| --- | --- |
| helper version | `a90_android_execns_probe v152` |
| mode string | present |
| allow flag | present |
| predicate and dispatch | present |
| actor order tokens | present |
| WLFW marker detection | present |
| missing-allow no-open output | present |
| `/dev/subsys_esoc0` open isolated to gated child | present |
| open after WLFW gate | present |
| fake notify/boot-done spoofing | absent |
| service-manager/HAL/scan/connect/DHCP/external ping counters | forced `0` |
| blocker and Wi-Fi surface observability | present |
| cleanup/reboot-required contract | present |

## Build Artifact

| field | value |
| --- | --- |
| path | `tmp/wifi/v921-execns-helper-v152-build/a90_android_execns_probe` |
| sha256 | `cdaa1adde9774e90e1d1e9f5f4eca43be4643b7ff0be2c8a0a08da5bf3e52105` |
| file | `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped` |
| dynamic section | none |

## Evidence

- `tmp/wifi/v921-execns-helper-v152-build/build.log`
- `tmp/wifi/v921-mdm-helper-cnss-before-esoc-support/manifest.json`
- `tmp/wifi/v921-mdm-helper-cnss-before-esoc-support/summary.md`

## Decision

V921 passes as a local source/build unit. The next safe unit is deploy-only
helper `v152` parity, followed by a bounded live V923 run. The live run must
still avoid service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, fake `ESOC_NOTIFY`, fake `ESOC_BOOT_DONE`, direct GPIO writes,
and boot/partition/firmware mutation.
