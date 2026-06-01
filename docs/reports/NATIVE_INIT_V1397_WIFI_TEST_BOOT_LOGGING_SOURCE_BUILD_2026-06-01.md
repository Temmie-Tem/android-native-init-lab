# Native Init V1397 Wi-Fi Test Boot Logging Source Build

## Summary

- Cycle: `V1397`
- Type: source/build-only Wi-Fi test boot observability update
- Decision: `v1397-wifi-test-boot-logging-source-build-pass`
- Result: PASS
- Artifact: `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`
- Boot SHA256: `8bb427c1567b1e4d466b17d5db72db3184132e7087ba0c6d2e5682f00ddeb376`

V1397 keeps the separate rollbackable Wi-Fi test boot path, but changes the
PID1 hook so each test boot gets a fresh per-boot log and a delayed summary
watcher. This is specifically to close the V1396 observability gap where the
helper reached the lower provider path but the `/cache` log only contained the
spawn records.

## Implementation

- PID1 hook now truncates the Wi-Fi test boot log at boot before spawning the
  helper.
- PID1 hook initializes a summary file and starts a non-blocking watcher child.
- The watcher samples helper liveness, helper `wchan`, helper `/proc` status,
  `wlan0` presence, and log size after `35s`.
- V1397 build uses distinct `/cache` paths so old V1393/V1395/V1396 evidence
  cannot pollute the next run.
- The handoff runner now accepts an expected test version plus configurable log,
  summary, and dmesg pattern arguments for later V1397/V1398 live gates.

## Artifact

| Item | Path | SHA256 |
|---|---|---|
| PID1 | `tmp/wifi/v1397-wifi-test-boot/init_v1397_wifi_test` | `afb31d692f94f03361046cba1a38d8e89f88ac739b9705f32d8f1e43988f3c4b` |
| helper | `tmp/wifi/v1397-wifi-test-boot/a90_android_execns_probe_v286` | `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f` |
| ramdisk | `tmp/wifi/v1397-wifi-test-boot/ramdisk_v1397_wifi_test.cpio` | `5477aa795cf889e67ddc03083bb908e866e6bb9b4243b1744a58c76632d25393` |
| boot image | `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img` | `8bb427c1567b1e4d466b17d5db72db3184132e7087ba0c6d2e5682f00ddeb376` |

## V1397 Runtime Paths

- Log: `/cache/native-init-wifi-test-boot-v1397.log`
- Summary: `/cache/native-init-wifi-test-boot-v1397.summary`
- PID file: `/cache/native-init-wifi-test-boot-v1397.pid`
- Watcher PID file: `/cache/native-init-wifi-test-boot-v1397-watcher.pid`
- Watch delay: `35s`

## Validation

- `python3 -m py_compile` passed for the modified build and handoff scripts.
- V1397 builder produced static aarch64 PID1/helper binaries.
- Boot image marker verification passed for `A90 Linux init 0.9.70 (v1397-wifitest)`,
  `a90_android_execns_probe v286`, `A90v1397`, and the V1397 `/cache` paths.
- Builder verified forbidden credential-like byte patterns were absent from the
  PID1, helper, ramdisk, and boot image artifacts.
- No device command, flash, reboot, partition write, Wi-Fi scan/connect,
  credentials, DHCP/routes, or external ping occurred in V1397.

## Next

V1398 should run local artifact sanity for the exact V1397 manifest and boot
image. The first live handoff after that should flash only
`tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`, expect `A90 Linux init 0.9.70 (v1397-wifitest)`, collect
`/cache/native-init-wifi-test-boot-v1397.log` and `/cache/native-init-wifi-test-boot-v1397.summary`, then roll back to
`stage3/boot_linux_v724.img`.
