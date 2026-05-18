# Native Init v240 Linker Namespace Gap Probe

## Summary

- Goal: classify the `cnss-daemon` dependency/namespace blocker left after v239
  cleared the bionic `/dev/null` early abort.
- Result: PASS / `android-linker-vndk-apex-version-alias-gap`.
- No PID1 boot image update, Android daemon execution, Wi-Fi scan/connect,
  rfkill write, credential handling, DHCP, routing, or Android partition write
  was used.

## Implementation

Added host probe:

```text
scripts/revalidation/wifi_linker_namespace_gap_probe.py
```

The tool combines:

- v239 real-linkerconfig linker-list evidence;
- v240 diagnostic minimal-vendor linkerconfig smoke evidence;
- captured Android `/linkerconfig/ld.config.txt` from v233;
- exported vendor/system library evidence from v226/v227;
- read-only live `stat` checks for VNDK/system/vendor library paths.

References used for interpretation:

- Android linker config format: https://android.googlesource.com/platform/bionic/+/master/linker/ld.config.format.md
- AOSP linker namespace overview: https://source.android.com/docs/core/architecture/vndk/linker-namespace

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_linker_namespace_gap_probe.py
python3 scripts/revalidation/wifi_linker_namespace_gap_probe.py analyze
```

Static/host-only result:

```text
decision=android-linker-real-namespace-policy-gap pass=True
```

Diagnostic minimal-vendor comparison:

```bash
python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v240-minimal-vendor-cnss-smoke \
  --null-device-mode dev-null \
  --linkerconfig-mode minimal-vendor \
  --target-profiles cnss-daemon \
  --env-modes clean \
  probe
```

Minimal-vendor result:

- `cnss-daemon` linker-list exits `0` under both `/system/bin/linker64` and the
  direct APEX linker path.
- It resolves `libcutils.so`, `liblog.so`, `libnl.so`, `libc++.so`, `libbase.so`,
  `libutils.so`, and related dependencies from `/system/lib64` while vendor
  QMI/CNSS libraries resolve from `/vendor/lib64`.

Live v240 command:

```bash
python3 scripts/revalidation/wifi_linker_namespace_gap_probe.py \
  --out-dir tmp/wifi/v240-linker-namespace-gap-live \
  probe
```

Live result:

```json
{
  "decision": "android-linker-vndk-apex-version-alias-gap",
  "pass": true,
  "reason": "real vendor namespace links libcutils.so through vndk, but linkerconfig points to com.android.vndk.v30 while the mounted system image exposes com.android.vndk.current"
}
```

Evidence directory:

```text
tmp/wifi/v240-linker-namespace-gap-live/
```

## Findings

Target classification:

- `/vendor/bin/cnss-daemon` matches `dir.vendor` and uses the `[vendor]` section.
- `[vendor] namespace.default.links` includes `system`, `vndk`, and
  `com_android_neuralnetworks`.
- `namespace.default.link.vndk.shared_libs` includes `libcutils.so`.
- `cnss-daemon` has direct `DT_NEEDED` entries including `libcutils.so`,
  `liblog.so`, `libqmi_cci.so`, `libqmi_common_so.so`, `libnl.so`,
  `libcld80211.so`, `libperipheral_client.so`, `libmdmdetect.so`,
  `libqmiservices.so`, `libc++.so`, `libc.so`, `libm.so`, and `libdl.so`.

Live path checks:

| path | exists |
| --- | --- |
| `/mnt/system/system/apex/com.android.vndk.v30/lib64/libcutils.so` | no |
| `/mnt/system/system/apex/com.android.vndk.v30/lib64` | no |
| `/mnt/system/system/apex/com.android.vndk.v30` | no |
| `/mnt/system/system/apex/com.android.vndk.current/lib64/libcutils.so` | yes |
| `/mnt/system/system/apex/com.android.vndk.current/lib64` | yes |
| `/mnt/system/system/apex/com.android.vndk.current` | yes |
| `/mnt/system/system/lib64/libcutils.so` | yes |
| `/mnt/system/vendor/lib64/libcutils.so` | no |
| `/vendor/lib64/libcutils.so` | no |

## Interpretation

The v239 blocker is not a missing generic `/system/lib64/libcutils.so`; that
file exists and system baseline targets can use it.  The real vendor namespace
tries to satisfy `libcutils.so` through the `vndk` linked namespace, but the
captured linkerconfig searches the versioned VNDK APEX path
`/apex/com.android.vndk.v30`.  The mounted system image available to the native
helper exposes `com.android.vndk.current` instead.

Therefore the current blocker is a private namespace APEX path/version alias
mismatch, not the earlier `/dev/null` early abort and not a generic linker
crash.

## Guardrails

- No `cnss-daemon` entrypoint execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No global bind mount or persistent Android partition write.
- Live captures are read-only `stat`/`ls` checks plus bounded `linker64 --list`
  evidence.

## Next Step

v241 should test private-only VNDK APEX alias/materialization inside the helper
namespace:

```text
/apex/com.android.vndk.v30 -> /apex/com.android.vndk.current
```

The first v241 acceptance target should remain linker-list only: prove whether
that private alias advances `cnss-daemon` dependency resolution beyond
`libcutils.so` without starting the daemon.
