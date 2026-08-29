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

| Device | SoC / kernel | Established result | Current frontier | Important unproved boundary |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.md) (`SM-A908N`) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED:** custom native PID 1; ACM/NCM; native Wi-Fi and internal-speaker paths; bounded runs proving Debian PID 1, SSH, and display | Reproduce a stock-shaped self-built kernel with public MPGen/RTIC metadata, then qualify any future canary separately | One persistent isolated-Debian run simultaneously closing PID 1, final Wi-Fi, authenticated SSH, minimal `/dev`, isolation, and terminal health |
| [Galaxy S22+](S22PLUS.md) (`SM-S906N`, FYG8) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED:** source-matched rebuilt kernel boots Android; a direct native candidate reached accepted `/init` exec while current was PID 1 | USB chain: SSUSB parent → DWC3 child → UDC → transport; obtain the missing fresh baseline before any later live qualification | First native userspace instruction and candidate-runtime SSUSB/DWC3/UDC/host transport |
| [Galaxy S20+ 5G](S20PLUS.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED:** exact onboarding, boot-only Magisk bootstrap/rollback, persistent rooted Android, and bounded native-canary transaction/recovery results | Integrate and activate, only after review, the N3-U0 ACM path and the separately dormant autonomous-research infrastructure | Native PID 1 and N3-U0 runtime; autonomous connected authority is not active |

## Reading order

Start with the device page above. For current state, follow its GOAL link; for
device authority, follow the target contract; for historical outcomes, follow
the ledger and specific reports. A host-side `PASS_GO` qualifies only the
named capability and is not proof of a live result or standing device
authority.
