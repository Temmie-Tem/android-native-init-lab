# S22+ FYG8 P2.50 E2 F1 GCC pass, SSUSB timeout

Date: 2026-07-24 KST
Tier: F1 boot-only candidate plus mandatory rollback
Status: `CLOSED`
Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Result

One fresh exact Process v2 approval was supplied for the prepared P2.49
binding. The runner transferred the exact boot-only candidate once, completed
the bounded observation, transferred the preapproved exact Magisk rollback
once, and verified final health. The operator observed a successful candidate
boot with no boot loop.

The two retained reads are byte-identical and contain one exact E2 record:

| Generation | Stage | Item | Gate | Outcome |
|---:|---:|---:|---|---|
| 76 | `0x83` | 8 | `gcc-waipio` | success |
| 77 | `0x84` | 9 | `ssusb` | failure, `ETIMEDOUT` (110) |

The record has no CRC, delimiter, transition, foreign-family, partial-record,
fallback, or A/B adjacency issue. It proves that the corrected descriptor-
derived validator accepted the first formerly unreachable stage and that the
runtime observed the GCC bind before waiting for SSUSB.

## Transaction

- candidate transfer: completed exactly once;
- candidate observation: closed;
- rollback transfer: completed exactly once;
- final Android boot and boot-animation completion: passed;
- root and orange verified-boot state: passed;
- boot, `vendor_boot`, DTBO, and recovery identities: passed;
- Odin endpoint absence after rollback: passed;
- canonical eight-event timeline: passed; and
- durable state: `CLOSED`, 19 journal records.

Private raw evidence remains under:

```text
workspace/private/runs/device-action-f1-live-v2/p249-20260724-2/
```

## Interpretation

This is a successful diagnostic rung but not terminal E2 success. P2.46 had
only reached `apps-rpmh-mxlvl` at `0x82`; P2.50 proves `gcc-waipio` at `0x83`
and moves the first observed failure to `a600000.ssusb` at `0x84`.

The formal acceptance requires terminal stage `0x8f`, so the runner correctly
returns no-proof despite the useful intermediate record. The result does not
prove SSUSB, DWC3 core, UDC publication, or USB enumeration.

## Next Unit

P2.51 is H0 focused analysis of `a600000.ssusb` probe dependencies and the
exact source/DT/module state already carried by P2.49. Do not repeat F1 until
that analysis identifies a bounded discriminator or correction.
