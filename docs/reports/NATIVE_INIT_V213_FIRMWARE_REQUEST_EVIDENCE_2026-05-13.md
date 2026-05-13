# Native Init v213 Firmware Request Evidence Report

## Summary

- status: PASS
- runtime device build: `A90 Linux init 0.9.59 (v159)`
- collector: `scripts/revalidation/native_firmware_request_probe.py`
- helper source: `stage3/linux_init/helpers/a90_icnssctl.c`
- helper builder: `scripts/revalidation/build_icnssctl_helper.sh`
- baseline evidence: `tmp/wifi/v213-firmware-request-evidence-baseline`
- path-only evidence: `tmp/wifi/v213-firmware-request-evidence`
- reprobe: not executed

v213 adds guarded firmware request evidence collection for the native Wi-Fi
bring-up path. The default mode is read-only. `--apply-path` temporarily mounts
vendor read-only, writes `firmware_class.path=/mnt/vendor/firmware` through the
fixed-target `a90_fwpathctl` helper, confirms request-name visibility, and then
rolls back to the original path. ICNSS unbind/bind remains opt-in and requires
both `--reprobe` and `--i-understand-icnss-reprobe`.

## Implementation

- Added `native_firmware_request_probe.py` with a command allowlist guard.
- Added fixed-target `a90_icnssctl` helper source for optional future ICNSS
  unbind/bind reprobe.
- Added `build_icnssctl_helper.sh` for static ARM64 helper builds.
- Added `.gitignore` entry for the built `a90_icnssctl` artifact.

The collector forbids active Wi-Fi bring-up operations: rfkill writes, WLAN
link-up, scan/connect, module load/unload, daemon/HAL/supplicant/hostapd start,
firmware copy, persistent mount, and shell redirection.

## Static Validation

```sh
python3 -m py_compile \
  scripts/revalidation/native_firmware_request_probe.py \
  scripts/revalidation/a90ctl.py \
  scripts/revalidation/native_init_flash.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_request_probe as p
p.validate_no_active_wifi_commands()
p.validate_command_guard()
print('v213 command guard PASS')
PY

scripts/revalidation/build_icnssctl_helper.sh
git diff --check
```

Results:

- Python compile: PASS
- command guard: PASS
- `a90_icnssctl` static ARM64 build: PASS
- `git diff --check`: PASS

Artifact hashes:

```text
6919a396aef4fab8a434deb1211c5fa2501870f48535bbe633e7b81c07716095  scripts/revalidation/native_firmware_request_probe.py
fabd59d935e48006e104c08830cc5e576b19b5cb4221793c335a3b74168d00d1  scripts/revalidation/build_icnssctl_helper.sh
45e745f11a7f9a3ace595cfdf87a5f68b5ae8a28f934f0cbc94abfbae3fc69f9  stage3/linux_init/helpers/a90_icnssctl.c
652b66cb9079b0e9dd194c871bee7aca8dde16577a53f1837be71bd25babf0d5  stage3/linux_init/helpers/a90_icnssctl
```

## Device Validation

Baseline command:

```sh
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v213-firmware-request-evidence-baseline
```

Baseline result:

- result: PASS
- decision: `baseline-only`
- reason: `read-only ICNSS firmware request baseline collected`
- captures: 24
- expected absent captures: `/proc/dynamic_debug/control`,
  `/sys/kernel/tracing/events`, `/sys/kernel/debug/tracing/events/firmware`
- manifest SHA256: `4ec982d385048e05078124f46a26a80ed9def439d454336652c8b2f8e621dbc6`
- summary SHA256: `80249d1e7551c1b93982feb5f8856538a67419d33d3774caac56109784bbd02c`

Path-only command:

```sh
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --apply-path \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v213-firmware-request-evidence
```

Path-only result:

- result: PASS
- decision: `path-only-pass`
- reason: `firmware path apply/readback/rollback passed without ICNSS reprobe`
- captures: 49
- original `firmware_class.path`: `/vendor/firmware_mnt/image`
- applied `firmware_class.path`: `/mnt/vendor/firmware`
- rolled back `firmware_class.path`: `/vendor/firmware_mnt/image`
- post-run `firmware_class.path`: `/vendor/firmware_mnt/image`
- request path visibility: all likely paths visible under `/mnt/vendor/firmware`
- request evidence: false, because ICNSS reprobe was not executed
- leftover `/mnt/vendor` mount: false
- leftover `/tmp/a90-v213-*` mount: false
- manifest SHA256: `b71bbc0518e3a6109574f4ccc443f15dff486ca2528f411a0d118bf66f430c81`
- summary SHA256: `44d5e11dd6b216d3e34d6e0edec4b62a9a97f9548cd1c6766640398b842a1234`

Post-run direct checks:

```text
firmware_class.path = /vendor/firmware_mnt/image
/mnt/vendor mount = absent
/tmp/a90-v213-* mount = absent
```

## Decision

v213 validates the safe parts of the firmware request evidence ladder:

1. read-only ICNSS/kernel baseline collection works;
2. temporary vendor `ro,noload` mount works;
3. `firmware_class.path` can be safely switched to `/mnt/vendor/firmware`;
4. likely firmware request paths resolve under that path;
5. rollback and cleanup work.

The next step is a deliberate decision point: either deploy `a90_icnssctl` and
run the opt-in ICNSS reprobe, or first add more device-side safety/observability
around driver unbind/bind. Do not jump directly to Wi-Fi scan/connect yet.
