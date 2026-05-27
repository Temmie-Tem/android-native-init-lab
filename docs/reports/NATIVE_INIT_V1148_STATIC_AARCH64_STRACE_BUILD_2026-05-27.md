# Native Init V1148 Static AArch64 `strace` Build Report

Date: `2026-05-27`

## Result

- Decision: `v1148-static-aarch64-strace-built-and-scaffold-install-ready`
- Pass: `true`
- Build script: `scripts/revalidation/build_static_strace.sh`
- Source: `https://github.com/strace/strace/releases/download/v7.0/strace-7.0.tar.xz`
- Source SHA256: `6c92419be3f2ec560b31728a4652217c59864c8642ba7b1b3771b1b013ad074b`
- Artifact: `external_tools/userland/bin/strace-aarch64-static-7.0`
- Artifact SHA256: `67a363496763eb1ce62f54be0e813db59f368e47adb40c195534779bf2048c46`
- V1147 install-ready manifest: `tmp/wifi/v1147-android-mdm-helper-strace-module/manifest.json`

## Summary

V1148 builds `strace 7.0` as a static AArch64 binary using the existing
cross-toolchain pattern, then reruns the V1147 Magisk module scaffold with that
binary.

Resulting state:

```text
static aarch64 strace -> built
readelf INTERP        -> absent
readelf dynamic       -> absent
V1147 scaffold        -> install_ready=true
```

The generated module remains under ignored `tmp/` evidence and has not been
installed on the device.

## Build Verification

Observed artifact type:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

Dynamic-link checks:

```text
INTERP segment: absent
dynamic section: absent
```

The V1147 scaffold verifier classified the staged binary as:

```json
{
  "aarch64": true,
  "copied": true,
  "has_dynamic": false,
  "has_interp": false,
  "ok": true,
  "static_or_no_interp": true
}
```

## Commands

Executed:

```bash
bash scripts/revalidation/build_static_strace.sh
python3 scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  --strace-binary external_tools/userland/bin/strace-aarch64-static-7.0
```

V1147 rerun result:

```json
{"decision": "v1147-magisk-strace-module-install-ready", "install_ready": true, "pass": true}
```

## Safety

- Device commands executed: `false`
- Android boot executed: `false`
- Module install executed: `false`
- Native `/dev/subsys_esoc0` retry: `false`
- Native eSoC ioctl: `false`
- Wi-Fi HAL start: `false`
- Scan/connect/link-up: `false`
- Credential use: `false`
- DHCP/route: `false`
- External ping: `false`
- Boot image/partition write/flash: `false`

## Next

V1149 should package and install the generated Magisk module during an Android
handoff, capture `/data/local/tmp/a90-wifi/`, remove the module, and return to
native init. That live gate should still avoid credentials, scan/connect, DHCP,
routes, external ping, native eSoC retry, and direct vendor partition mutation.
