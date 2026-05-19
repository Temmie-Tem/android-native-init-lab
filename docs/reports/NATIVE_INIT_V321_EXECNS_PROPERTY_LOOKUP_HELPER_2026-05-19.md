# v321 Report: Execns Property Lookup Helper Support

- date: `2026-05-19`
- scope: static support for read-only private property lookup helper mode
- boot image change: none
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- result: `execns-property-lookup-helper-static-pass`

## Summary

v321 extends `stage3/linux_init/helpers/a90_android_execns_probe.c` so it can
support a future Android-linked read-only property lookup proof. The new mode is
not executed live in this step because v317 has not recorded
`private-property-namespace-proof-pass` and the v320 live approval gate remains
closed.

The helper now knows how to build the existing private Android execution
namespace, bind an allowlisted private property directory into that private root
as `/dev/__properties__`, and execute `/system/bin/getprop <key>` for a small
read-only property allowlist.

## Implementation

Changed helper marker:

```text
a90_android_execns_probe v11
```

New arguments:

```text
--mode property-lookup
--target-profile system-getprop
--property-root /mnt/sdext/a90/private-property-v317/.../dev/__properties__
--property-key <allowlisted ro.* key>
```

Property root guardrails:

- must be under `/mnt/sdext/a90/private-property-v317`;
- must end with `/dev/__properties__`;
- must not contain `..`;
- must not be a symlink;
- must be a directory;
- is mounted only inside the helper's private temporary root.

Initial property key allowlist:

- `ro.build.version.sdk`
- `ro.build.version.release`
- `ro.product.vendor.device`
- `ro.board.platform`
- `ro.product.name`
- `ro.hardware`
- `ro.vendor.build.version.sdk`

## Validation

Build:

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh /tmp/a90_android_execns_probe_v321
```

Result:

```text
artifact: /tmp/a90_android_execns_probe_v321
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
sha256: f40db33a2823662f64d7a2b3c6dca9ce174801208c14c4a83647a12db1ce636b
readelf: There is no dynamic section in this file.
```

Static checks:

```bash
strings /tmp/a90_android_execns_probe_v321 | rg "a90_android_execns_probe v11|property-lookup|system-getprop|property-root|property-key|getprop"
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
git diff --check
```

All static checks passed.

## Live Validation

Not executed in v321.

Reason: v321 is helper support only. Live private property lookup is still
blocked until:

1. v317 records `private-property-namespace-proof-pass`;
2. v317 workspace state is clean or explicitly refreshed;
3. v320 live approval phrase is provided;
4. the host runner is updated to call this helper mode after the above gates.

## Safety Result

- no boot partition write;
- no device flash;
- no global `/dev/__properties__` bind;
- no `/dev/socket/property_service` creation;
- no property mutation;
- no CNSS, Wi-Fi HAL, `wificond`, `supplicant`, `hostapd`, scan, connect,
  DHCP, routing, rfkill, module load, firmware mutation, or daemon start.

## Next Step

Recommended next step is to update `wifi_private_property_lookup_proof.py` so
its `run` path can invoke the new helper mode, but still only after v317 PASS
and exact v320 approval. The alternative is to pause and run v317 live proof only
after the exact v317 approval phrase.
