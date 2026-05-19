# v321 Plan: Execns Property Lookup Helper Support

- date: `2026-05-19`
- scope: static/helper support for read-only private property lookup
- boot image change: none planned
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- status: implementation planned / live execution blocked until v317 PASS

## Summary

v320 added a fail-closed host runner for private Android property lookup. The
remaining gap is that `a90_android_execns_probe` does not yet have a safe helper
mode for running Android-linked `/system/bin/getprop` against a private
`/dev/__properties__` tree.

v321 adds only helper support and static validation. It does not run the live
property lookup, start daemons, bind over global `/dev/__properties__`, or bring
up Wi-Fi. Live execution remains blocked until v317 records
`private-property-namespace-proof-pass` and the later v320 approval gate is
satisfied.

## Technical Basis

The proof should use Android's own property reader path, not a custom parser.
AOSP `getprop` calls Android property APIs, and bionic's property implementation
loads serialized property contexts from the property area. Therefore the helper
needs to expose a private property tree only inside its temporary namespace and
then execute an allowlisted `getprop` query inside that namespace.

References:

- AOSP `getprop`: <https://android.googlesource.com/platform/system/core/+/master/toolbox/getprop.cpp>
- Bionic system properties: <https://android.googlesource.com/platform/bionic/+/master/libc/system_properties/system_properties.cpp>

## Key Changes

- Extend `stage3/linux_init/helpers/a90_android_execns_probe.c`:
  - bump helper marker to `a90_android_execns_probe v11`;
  - add `--mode property-lookup`;
  - add `--target-profile system-getprop` mapped to `/system/bin/getprop`;
  - add `--property-root <path>` and `--property-key <key>`;
  - bind the host/device private property directory only into the helper's
    private root at `/dev/__properties__`;
  - execute `/system/bin/getprop <property-key>` inside the private chroot;
  - capture stdout, stderr, child exit code, signal, and timeout using the same
    bounded capture style as existing execns modes.
- Keep the allowlist narrow:
  - property root must be under `/mnt/sdext/a90/private-property-v317/`;
  - property key must be one of the initial v320 lookup keys:
    `ro.build.version.sdk`, `ro.build.version.release`,
    `ro.product.vendor.device`, `ro.board.platform`, `ro.product.name`,
    `ro.hardware`, `ro.vendor.build.version.sdk`.
- Do not modify `wifi_private_property_lookup_proof.py` live behavior in this
  step. It remains fail-closed until v317 PASS evidence exists.

## Explicitly Forbidden

- Global bind mount over `/dev/__properties__`.
- `/dev/socket/property_service` creation.
- Property mutation, `setprop`, or property-service writes.
- CNSS, Wi-Fi HAL, `wificond`, `supplicant`, `hostapd`, or daemon start.
- Wi-Fi scan/connect/link-up, rfkill write, firmware mutation, or partition
  write.
- Live execution before v317 PASS and v320 approval gates.

## Validation

Static-only for v321:

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh /tmp/a90_android_execns_probe_v321
strings /tmp/a90_android_execns_probe_v321 | rg "property-lookup|system-getprop|property-root|property-key"
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
git diff --check
```

Optional argument-validation checks, only on device or an ARM64 runner:

```bash
/tmp/a90_android_execns_probe_v321 \
  --system-root /mnt/system/system \
  --vendor-block /dev/block/sda29 \
  --vendor-fstype ext4 \
  --target-profile system-getprop \
  --mode property-lookup \
  --property-root /tmp/not-allowed \
  --property-key ro.build.version.sdk
```

Expected result: rejected by argument allowlist before any namespace setup.

## Acceptance

- Helper builds statically with `-Wall -Wextra`.
- Help text documents the new mode/profile/options.
- Invalid property root/key combinations fail before namespace setup.
- Live property lookup is still blocked by v320/v317 gates.
- No boot image or native init version change is made.

## Next Step

After v321 static support is committed, either:

1. wait for exact v317 approval and run the v317 private property namespace
   proof, or
2. update the v320 host runner to call the new helper only after v317 PASS
   evidence is present.
