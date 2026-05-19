# v310 Plan: Property Serializer Compatibility Proof

- date: `2026-05-19`
- scope: host-only `property_info` / `prop_area` serializer-parser proof
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v309 identified the AOSP source facts for Android 12 property area and
serialized `property_info` formats. v310 converts those facts into a host-only
binary roundtrip proof.

This does not install generated files on the device. It writes only private
evidence artifacts under `tmp/wifi`.

## Key Changes

- Add `scripts/revalidation/wifi_property_serializer_proof.py`.
- Build a minimal serialized `property_info` binary:
  - header version `1`;
  - string tables for context/type;
  - trie nodes and exact matches for selected seed keys.
- Build a minimal `prop_area` binary:
  - magic `0x504f5250`;
  - version `0xfc6ed0ab`;
  - size `128 KiB`;
  - selected read-only seed properties.
- Parse both generated binaries with host-side parsers and verify roundtrip.

## Scope Limits

v310 uses one synthetic model context:

```text
u:object_r:default_prop:s0
```

That is enough to prove the serializer/parser mechanics, but not enough to
claim final Android-compatible context selection. v311 must map the selected
keys through real property context files before any runtime prototype.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_property_serializer_proof.py
python3 scripts/revalidation/wifi_property_serializer_proof.py \
  --out-dir tmp/wifi/v310-property-serializer-proof \
  run
git diff --check
```

Expected result:

```text
property-serializer-proof-ready
```

## Acceptance

- Host-only execution only.
- Generated binaries are evidence artifacts only.
- No device command, ADB command, `/dev` runtime file, property service socket,
  daemon start, or Wi-Fi bring-up action.
- The report states that real context mapping is still required.

