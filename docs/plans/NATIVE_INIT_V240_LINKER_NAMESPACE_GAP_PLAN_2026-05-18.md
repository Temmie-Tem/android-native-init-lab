# Native Init v240 Linker Namespace Gap Plan

## Summary

- v240 continues from v239 without changing the PID1 boot image.
- Goal: classify why `linker64 --list /vendor/bin/cnss-daemon` cannot resolve
  `libcutils.so` after the private `/dev/null` early-abort blocker was cleared.
- Scope is read-only evidence and host-side analysis: no `cnss-daemon`
  entrypoint execution, no Wi-Fi scan/connect, and no persistent partition write.
- Expected output is a precise next blocker label for the Android linker
  namespace/search-path gap.

## Rationale

v239 proved the generic `SIGSEGV(11)`/`0xa1` early abort was a missing
null-device context.  The remaining failure is no longer a crash:

```text
library "libcutils.so" not found: needed by main executable
```

The real Android linkerconfig maps `/vendor/bin/cnss-daemon` into the `vendor`
section.  In that section, `namespace.default.links` includes `vndk`, and the
`vndk` link allowlist includes `libcutils.so`.  Therefore the next question is
whether the linked namespace search paths actually exist in the private root.

Relevant references:

- Android linker config format: https://android.googlesource.com/platform/bionic/+/master/linker/ld.config.format.md
- AOSP linker namespace overview: https://source.android.com/docs/core/architecture/vndk/linker-namespace

## Implementation

- Add `scripts/revalidation/wifi_linker_namespace_gap_probe.py`.
- Inputs:
  - v239 real linkerconfig manifest: `tmp/wifi/v239-devnull-linker-capture-live/manifest.json`
  - minimal-vendor comparison manifest: `tmp/wifi/v240-minimal-vendor-cnss-smoke/manifest.json`
  - real linkerconfig: `tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__ld.config.txt`
  - exported vendor root: `tmp/wifi/v226-vendor-root-live-export/vendor-source`
  - exported system core libs: `tmp/wifi/v227-android-core-system-library-evidence/system-root/system`
- Parse the linkerconfig enough to identify:
  - `dir.vendor` target classification for `/vendor/bin/cnss-daemon`
  - `namespace.default.search.paths`
  - `namespace.default.links`
  - `namespace.default.link.<ns>.shared_libs`
  - linked namespace search paths
- Extract unresolved libraries from v239 linker-list stderr.
- Compare real linkerconfig behavior with the diagnostic `minimal-vendor`
  linkerconfig smoke run.
- Live read-only checks:
  - `/mnt/system/system/apex/com.android.vndk.v30/lib64/libcutils.so`
  - `/mnt/system/system/apex/com.android.vndk.current/lib64/libcutils.so`
  - `/mnt/system/system/lib64/libcutils.so`
  - `/mnt/system/vendor/lib64/libcutils.so`
  - `/vendor/lib64/libcutils.so`

## Test Plan

```bash
python3 -m py_compile scripts/revalidation/wifi_linker_namespace_gap_probe.py
python3 scripts/revalidation/wifi_linker_namespace_gap_probe.py analyze
```

Optional minimal-vendor comparison, when not already present:

```bash
python3 scripts/revalidation/wifi_linker_crash_capture_probe.py \
  --out-dir tmp/wifi/v240-minimal-vendor-cnss-smoke \
  --null-device-mode dev-null \
  --linkerconfig-mode minimal-vendor \
  --target-profiles cnss-daemon \
  --env-modes clean \
  probe
```

Device validation:

```bash
python3 scripts/revalidation/wifi_linker_namespace_gap_probe.py \
  --out-dir tmp/wifi/v240-linker-namespace-gap-live \
  probe
```

## Acceptance

- PASS if the tool can distinguish a real linker namespace/search-path problem
  from the already-fixed `/dev/null` early abort.
- Preferred PASS label:
  `android-linker-vndk-apex-version-alias-gap`.
- The report must show whether `com.android.vndk.v30` or
  `com.android.vndk.current` exists on the mounted system image.
- The report must keep daemon start and Wi-Fi operations blocked.

## Next Step After PASS

- v241 should test a private-only VNDK APEX alias/materialization strategy, such
  as mapping `/apex/com.android.vndk.v30` to the mounted
  `/apex/com.android.vndk.current` inside the helper namespace only.
- The test must remain `linker64 --list` only until the dependency graph is
  closed.
