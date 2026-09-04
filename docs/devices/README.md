# Device progress guide

**English** · [한국어](README.ko.md)

This directory is an external-reader map of the three devices in this
repository. It does not replace the binding target contracts, current GOAL
files, campaign ledgers, or run reports. Those records remain authoritative.

## Evidence vocabulary

- **PROVED** — accepted by the named evidence contract in one bounded run or
  by a reproducible host-side proof for the stated scope.
- **observed** — directly seen, but not sufficient for the stronger claim
  nearby.
- **designed** — implemented or documented host-side; not demonstrated at
  runtime unless explicitly stated.
- **unproved** — the repository has no accepted evidence for the claim.

These labels are deliberately local. Evidence from different runs is not
combined into a new end-to-end success.

## At a glance

Snapshot of records checked on 2026-09-05; follow each GOAL for later changes.

| Device | SoC / kernel | Established result | Current frontier | Important unproved boundary |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.md) (`SM-A908N`) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED:** native PID 1, ACM/NCM, native Wi-Fi/audio, and bounded Debian PID 1/SSH/display results | H41 rollback/health closure; isolated-Debian server work paused | One persistent run integrating the selected isolated-Debian architecture; H41 playback and recovery closure |
| [Galaxy S22+](S22PLUS.md) (`SM-S906N`, FYG8) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED:** rebuilt-kernel Android boot; native-PID1 ACM, bidirectional fixed commands, authentication, and bounded multiple sessions with healthy rollback | Initial OPEN failure capture and session reliability | Reliable long-idle/reopen, general shell/persistent service, and detailed USB/Max77705 causality |
| [Galaxy S20+ 5G](S20PLUS.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED:** onboarding, resident Magisk, retained T2 TWRP, and P0 V3 transfer/healthy rollback | Early-boot pstore/PMSG observation after P0 V3 NO_PROOF | Custom native PID 1, live early-boot retention, and autonomous F1 |

## Reading order

Start with the device page above. For current state, follow its GOAL link; for
device authority, follow the target contract; for historical outcomes, follow
the ledger and specific reports. A host-side `PASS_GO` qualifies only the
named capability and is not proof of a live result or standing device
authority.
