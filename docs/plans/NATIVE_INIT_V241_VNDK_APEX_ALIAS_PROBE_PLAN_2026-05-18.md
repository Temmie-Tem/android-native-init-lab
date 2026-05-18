# Native Init v241 VNDK APEX Alias Probe Plan

## Summary

- v241 continues from v240 without changing the PID1 boot image.
- Goal: test a private-only VNDK APEX alias inside the helper namespace:
  `/apex/com.android.vndk.v30 -> /apex/com.android.vndk.current`.
- Scope remains `linker64 --list` only.  No `cnss-daemon` entrypoint execution,
  Wi-Fi scan/connect, rfkill write, credential handling, DHCP, routing, or
  persistent partition write is allowed.

## Rationale

v240 classified the current blocker as `android-linker-vndk-apex-version-alias-gap`:
real linkerconfig links `libcutils.so` through the `vndk` namespace and expects
`/apex/com.android.vndk.v30`, while the mounted system image exposes
`/apex/com.android.vndk.current`.

The smallest safe closure test is a private namespace alias/materialization in
`a90_android_execns_probe`, then rerun the same `cnss-daemon` linker-list probe.

## Implementation

- Update `stage3/linux_init/helpers/a90_android_execns_probe.c` to v7.
- Add helper option:
  - `--vndk-apex-alias-mode none`: preserves v239 behavior.
  - `--vndk-apex-alias-mode v30-to-current`: creates a private `/apex` symlink
    farm pointing to `/system/apex/*`, plus an extra
    `com.android.vndk.v30 -> /system/apex/com.android.vndk.current` symlink.
- Keep the alias inside the temporary chroot root only.
- Extend `scripts/revalidation/wifi_linker_crash_capture_probe.py` with
  `--vndk-apex-alias-mode` and v241-specific classification.

## Test Plan

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_linker_crash_capture_probe.py \
  scripts/revalidation/wifi_linker_namespace_gap_probe.py
scripts/revalidation/build_android_execns_probe_helper.sh
python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v241-plan-smoke \
  --null-device-mode dev-null \
  --vndk-apex-alias-mode v30-to-current \
  --target-profiles cnss-daemon \
  --env-modes clean \
  plan
```

Device validation:

```bash
python3 scripts/revalidation/tcpctl_host.py \
  --device-binary /cache/bin/a90_android_execns_probe \
  --toybox /cache/bin/toybox \
  install \
  --local-binary stage3/linux_init/helpers/a90_android_execns_probe

python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v241-vndk-apex-alias-live \
  --null-device-mode dev-null \
  --vndk-apex-alias-mode v30-to-current \
  --target-profiles cnss-daemon \
  --env-modes clean \
  probe
```

## Acceptance

- PASS if `cnss-daemon` linker-list exits `0` under both allowlisted linker
  paths with no `SIGSEGV`, no `0xa1` fault, and no missing `libcutils.so`.
- Report must show `context.apex_vndk_v30` exists as a private symlink to
  `/system/apex/com.android.vndk.current`.
- Postflight `selftest` must remain `fail=0`.

## Next Step After PASS

- v242 can plan a controlled start-only runtime probe using the same private
  namespace requirements, short timeout, process-group cleanup, and explicit
  no-scan/no-connect guardrails.
- If start-only is considered too risky, v242 should first map runtime
  non-linker requirements such as sockets, properties, firmware path, and device
  nodes from the now-closed linker dependency context.
