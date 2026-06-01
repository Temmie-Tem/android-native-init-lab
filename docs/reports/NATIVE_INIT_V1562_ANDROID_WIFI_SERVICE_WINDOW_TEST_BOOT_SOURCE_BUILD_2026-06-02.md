# Native Init V1562 Android Wi-Fi Service-Window Test Boot Source Build

## Summary

- Cycle: `V1562`
- Type: source/build-only route selector and boot artifact build
- Decision: `v1562-android-wifi-service-window-test-boot-source-build-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1562-android-wifi-service-window-test-boot/manifest.json`

## Change

V1562 makes the v1393 Wi-Fi test boot route selectable at build time. The default
route remains `wifi-companion-post-pm-mdm-helper-esoc-observer`, while the new
service-window route compiles PID1 to launch:

```text
wifi-companion-android-wifi-service-window-start-only
--allow-android-wifi-service-window
```

The service-window route compiles out the post-PM observer flags from the PID1
argv, including direct PM observer, post-PM mdm-helper lower-trace, private
patched CNSS daemon, and forced RC1 enumerate flags.

## Built Artifact

| field | value |
| --- | --- |
| manifest | `tmp/wifi/v1562-android-wifi-service-window-test-boot/manifest.json` |
| boot image | `tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img` |
| helper mode | `android-service-window-start-only` |
| helper runtime mode | `wifi-companion-android-wifi-service-window-start-only` |
| init sha256 | `5638f696643bc1df74eea413c1aeb97b9939cd36666897bb8d23c854e1b15ace` |
| helper sha256 | `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411` |
| ramdisk sha256 | `6458f17cdd301f9f70be9c508b05a152aac27b29ee485a37bdb3f8c8b291fc4b` |
| boot sha256 | `3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d` |

## Backcompat Smoke

The default route was also rebuilt to verify the `post-pm-observer` branch still
compiles and packages:

| field | value |
| --- | --- |
| manifest | `tmp/wifi/v1562-post-pm-observer-backcompat-smoke/manifest.json` |
| helper runtime mode | `wifi-companion-post-pm-mdm-helper-esoc-observer` |
| boot sha256 | `4db35ad69ff1b101be749c5b2ec9ee5866f47190f28c134c9e049ab829d0e420` |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/build_native_init_wifi_test_boot_v1393.py
python3 scripts/revalidation/build_native_init_wifi_test_boot_v1393.py \
  --out-dir tmp/wifi/v1562-android-wifi-service-window-test-boot \
  --cycle V1562 \
  --decision v1562-android-wifi-service-window-test-boot-source-build-pass \
  --cycle-label v1562 \
  --init-build v1562-service-window \
  --wifi-test-klog-prefix A90v1562 \
  --wifi-test-helper-mode android-service-window-start-only \
  --wifi-test-supervise-helper \
  --wifi-test-watch-sec 45 \
  --wifi-test-supervisor-timeout-sec 45
python3 scripts/revalidation/build_native_init_wifi_test_boot_v1393.py \
  --out-dir tmp/wifi/v1562-post-pm-observer-backcompat-smoke \
  --cycle V1562 \
  --decision v1562-post-pm-observer-backcompat-source-build-pass \
  --cycle-label v1562-backcompat \
  --init-build v1562-backcompat
```

Additional checks:

- `verify_init_route_contract` confirmed the service-window PID1 binary contains
  `wifi-companion-android-wifi-service-window-start-only` and
  `--allow-android-wifi-service-window`.
- `verify_init_route_contract` confirmed the service-window PID1 binary does not
  contain the post-PM observer allow/PM observer route flags.
- Invalid service-window combinations with RC1/provider debug options are
  rejected before build.
- Generated artifacts passed static ELF checks, ramdisk entry checks, marker
  checks, boot image repack, and credential-byte scan.

## Safety Scope

V1562 is source/build-only. It performed no device command, reboot, flash,
partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external
ping, direct PMIC/GPIO/GDSC write, blind eSoC notify, global PCI rescan, or
platform bind/unbind.

The service-window helper mode does start bounded Android Wi-Fi service-window
actors in a future live test boot, but it still records:

- `scan_connect_credentials=false`
- `wifi_scan_connect=false`
- `credentials=false`
- `dhcp_routes_external_ping=false`

## Next Gate

V1563 should be a rollbackable live handoff using the V1562 service-window boot
artifact. The only success target for that gate is whether native init emits
`cnss-daemon wlfw_start` and `wlfw_service_request` under the Android
service-window route. Do not use credentials, scan/connect, DHCP/routes, or
external ping in V1563.
