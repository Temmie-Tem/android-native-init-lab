# Native Init v310 Property Serializer Proof Report

- date: `2026-05-19`
- scope: host-only `property_info` / `prop_area` serializer-parser proof
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_serializer_proof.py`

## Summary

v310 generated host-only binary evidence for serialized `property_info`,
`properties_serial`, and a per-context `prop_area`, then parsed the generated
files back to verify selected Android-backed seed keys.

The proof passed, but it intentionally uses a synthetic single context. Real
property context mapping remains the next gate.

## Evidence

| item | path | result |
| --- | --- | --- |
| serializer proof | `tmp/wifi/v310-property-serializer-proof/` | `property-serializer-proof-ready` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_property_serializer_proof.py
python3 scripts/revalidation/wifi_property_serializer_proof.py \
  --out-dir tmp/wifi/v310-property-serializer-proof \
  run
git diff --check
```

Result: PASS.

## Roundtrip

| key | result |
| --- | --- |
| `ro.build.version.sdk` | context/type/value roundtrip PASS |
| `ro.product.name` | context/type/value roundtrip PASS |
| `ro.hardware` | context/type/value roundtrip PASS |
| `ro.vendor.build.version.sdk` | context/type/value roundtrip PASS |

## Binary Facts

| item | value |
| --- | --- |
| `property_info` size | `620` bytes |
| `prop_area` size | `131072` bytes |
| `prop_area` magic | `0x504f5250` |
| `prop_area` version | `0xfc6ed0ab` |
| `prop_area` bytes_used | `876` |
| model context | `u:object_r:default_prop:s0` |

## Decision

- decision: `property-serializer-proof-ready`
- reason: host-only `property_info` and `prop_area` roundtrip passed.
- next step: v311 context-aware `property_contexts` mapping proof.

## Safety

- No device command execution.
- No ADB command execution.
- No runtime property file installation.
- No property service socket creation.
- No service-manager/HAL/Wi-Fi daemon execution.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.

