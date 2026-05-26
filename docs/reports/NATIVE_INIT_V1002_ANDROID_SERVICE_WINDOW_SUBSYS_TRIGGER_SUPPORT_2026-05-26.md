# V1002 Android Service-window Subsystem Trigger Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper source/build | `tmp/wifi/v1002-execns-helper-v170-build/build.log` | `v1002-helper-v170-build-pass` |

V1002 adds helper `v170` support for a service-window-scoped
`/dev/subsys_esoc0` trigger capture. No live trigger was run in V1002.

## Implemented

- Bumped `a90_android_execns_probe` to `v170`.
- Added mode `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.
- Added explicit allow flag
  `--allow-android-wifi-service-window-subsys-trigger-capture`.
- Reused the Android Wi-Fi service-window actor order and added a narrow gate:
  trigger only after `mdm_helper` is observed holding `/dev/esoc-0`.
- Reused the existing `/dev/subsys_esoc0` trigger child, with service-window
  labels and post-trigger surface captures.
- Added trigger child cleanup accounting and final postflight safety checks.
- Preserved explicit no-scan/no-connect/no-credential/no-DHCP/no-external-ping
  transcript markers.

## Validation

Executed:

```bash
mkdir -p tmp/wifi/v1002-execns-helper-v170-build
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe \
  2>&1 | tee tmp/wifi/v1002-execns-helper-v170-build/build.log

git diff --check
strings tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v170|wifi-companion-android-wifi-service-window-subsys-trigger-capture|allow-android-wifi-service-window-subsys-trigger-capture|subsys-trigger-window-captured|subsys-trigger-start-failed|service-window-mdm-helper-esoc-fd'
```

Result:

```text
artifact: tmp/wifi/v1002-execns-helper-v170-build/a90_android_execns_probe
sha256: edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254
linkage: statically linked, no dynamic section
strings: v170 mode/flag/result/gate strings present
git diff --check: pass
```

## Guardrails

V1002 was source/build-only:

- no deploy;
- no device command;
- no actor start;
- no live `/dev/subsys_esoc0` open;
- no eSoC ioctl;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP, route mutation, external ping, boot image write, or partition write.

## Next

Use V1003 for deploy-only helper `v170` parity. Then use V1004 for a live
current-boot SELinux refresh plus the new service-window subsystem trigger
capture. V1004 must still block scan/connect, credentials, DHCP/routing, and
external ping.
