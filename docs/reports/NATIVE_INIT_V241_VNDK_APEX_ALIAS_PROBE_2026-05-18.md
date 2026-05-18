# Native Init v241 VNDK APEX Alias Probe

## Summary

- Goal: close the v240 VNDK APEX alias blocker by testing a private-only
  `/apex/com.android.vndk.v30 -> /apex/com.android.vndk.current` alias.
- Result: PASS / `android-linker-vndk-apex-alias-cnss-list-pass`.
- No PID1 boot image update, Android daemon execution, Wi-Fi scan/connect,
  rfkill write, credential handling, DHCP, routing, or Android partition write
  was used.

## Implementation

Updated helper:

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
- version: `a90_android_execns_probe v7`
- SHA-256: `d6bd192b46cdeea93e8d0581335393d7101b3731a28cd441a1081e773329b2a4`

New helper option:

```text
--vndk-apex-alias-mode none|v30-to-current
```

Behavior:

- `none`: preserves v239/v240 behavior and bind-mounts `/apex` from the system
  image.
- `v30-to-current`: creates a private `/apex` symlink farm inside the temporary
  chroot root, then adds
  `com.android.vndk.v30 -> /system/apex/com.android.vndk.current`.

Updated host probe:

- `scripts/revalidation/wifi_linker_crash_capture_probe.py`
- passes `--vndk-apex-alias-mode` to the helper;
- records `missing_libs` per matrix row;
- classifies clean `cnss-daemon` linker-list resolution as
  `android-linker-vndk-apex-alias-cnss-list-pass`.

## Validation

Local validation:

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
git diff --check
```

Helper deploy used existing NCM transfer path:

```text
/cache/bin/a90_android_execns_probe
sha256=d6bd192b46cdeea93e8d0581335393d7101b3731a28cd441a1081e773329b2a4
```

Live probe command:

```bash
python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v241-vndk-apex-alias-live-final \
  --null-device-mode dev-null \
  --vndk-apex-alias-mode v30-to-current \
  --target-profiles cnss-daemon \
  --env-modes clean \
  probe
```

Live result:

```json
{
  "decision": "android-linker-vndk-apex-alias-cnss-list-pass",
  "pass": true,
  "reason": "private VNDK APEX alias allowed cnss-daemon linker-list dependency resolution to complete"
}
```

Evidence directory:

```text
tmp/wifi/v241-vndk-apex-alias-live-final/
```

Postflight:

```text
selftest: pass=11 warn=1 fail=0 duration=36ms entries=12
```

## Matrix Result

| linker | target | signal | exit | missing libs | conclusion |
| --- | --- | ---: | ---: | --- | --- |
| `system-linker` | `cnss-daemon` | `0` | `0` | none | linker-list passed |
| `apex-linker` | `cnss-daemon` | `0` | `0` | none | linker-list passed |

## Key Evidence

Both matrix rows reported:

```text
vndk_apex_alias_mode=v30-to-current
apex_mount_source=<private-symlink-farm>
context.apex_vndk_v30.exists=1
context.apex_vndk_v30.type=symlink
context.apex_vndk_v30.readlink=/system/apex/com.android.vndk.current
context.apex_vndk_v30_libcutils.exists=1
```

The resolved linker-list includes VNDK libraries from the current APEX through
that alias, for example:

```text
libcutils.so => /system/apex/com.android.vndk.current/lib64/libcutils.so
libnl.so => /system/apex/com.android.vndk.current/lib64/libnl.so
libc++.so => /system/apex/com.android.vndk.current/lib64/libc++.so
```

Vendor-side libraries still resolve from `/vendor/lib64`, for example:

```text
libqmi_cci.so => /vendor/lib64/libqmi_cci.so
libqmi_common_so.so => /vendor/lib64/libqmi_common_so.so
libcld80211.so => /vendor/lib64/libcld80211.so
```

## Interpretation

v241 closes the v240 blocker.  The real linkerconfig was usable once the private
namespace provided the versioned VNDK APEX name expected by that config.  This
means the current Android linker dependency path for `cnss-daemon` can be made
namespace-complete without global mounts or persistent filesystem changes.

This is still not Wi-Fi bring-up.  It only proves the bounded `linker64 --list`
dependency graph can complete.  Starting `cnss-daemon` may still fail on runtime
requirements such as sockets, properties, firmware path assumptions, device
nodes, capabilities, SELinux behavior, or service ordering.

## Guardrails

- No `cnss-daemon` entrypoint execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No global bind mount or persistent Android partition write.
- Alias exists only inside the helper's temporary private namespace.

## Next Step

v242 should choose between:

1. controlled start-only runtime probe with short timeout, process-group cleanup,
   and no scan/connect guardrails; or
2. a runtime requirement inventory that maps sockets/properties/device nodes
   before any daemon entrypoint execution.

Given linker dependency closure now passes, the more direct next step is a
strictly bounded start-only probe, but it should remain opt-in and abort on any
unsafe preflight failure.
