# Device progress guide

**English** · [한국어](README.ko.md)

This directory is an external-reader map of the three devices in this
repository. It does not replace the binding target contracts, current GOAL
files, campaign ledgers, or run reports. Those records remain authoritative.

## Evidence vocabulary

- **PROVED** — accepted by the named evidence contract in one bounded run or
  by a reproducible host-side proof for the stated scope.
- **OBSERVED** — direct observation that has not been elevated to PROVED;
  prose may use "observed" grammatically.
- **designed** — implemented or documented host-side; not demonstrated at
  runtime unless explicitly stated.
- **unproved** — the repository has no accepted evidence for the claim.

These labels are deliberately local. Evidence from different runs is not
combined into a new end-to-end success.

## At a glance

The S22+ row was checked on 2026-09-12; the other rows retain their 2026-09-05 snapshot. Follow each GOAL for later changes.

| Device | SoC / kernel | Established result | Current frontier | Important unproved boundary |
| --- | --- | --- | --- | --- |
| [Galaxy A90 5G](A90.md) (`SM-A908N`)<br>[visual evidence](A90_VISUAL_EVIDENCE.md) | Qualcomm SM8150 / vendor Linux 4.14.190 | **PROVED:** native PID 1, ACM/NCM, native Wi-Fi/audio, and bounded Debian PID 1/SSH/display results | Parked at last-tracked H41 Native; exact V2321 rollback/health closure remains pending; isolated-Debian server work paused | One persistent run integrating the selected isolated-Debian architecture; H41 playback and recovery closure |
| [Galaxy S22+](S22PLUS.md) (`SM-S906N`, FYG8)<br>[display visual evidence](S22PLUS_DISPLAY_VISUAL_EVIDENCE.md)<br>[boot HUD visual evidence](S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.md) | Qualcomm SM8450 / vendor Linux 5.10.226 | **PROVED:** rebuilt-kernel Android boot, native-PID1 ACM, authenticated bounded read-only shell and healthy rollback through P348; P353-P361 **PROVED** display dispatch/rollback and **OBSERVED** clean cached-buffer output, including repeated framebuffer selection; work since P375 **PROVED** an authenticated root command console and a native PID1 status HUD carrying uptime, console state, memory, CPU and battery fields, with **OBSERVED** on-panel output; P384 **PROVED** a complete attended native roundtrip — install, authenticated health, timely exact Download, same-N restoration on a fresh kernel boot identity, and exact Android cleanup — and P385 **PROVED** the first admitted native baseline, with same-boot reentry across two boots | Each completed scope closes with exact rollback and final health, and leaves no native session or replay authority; the exact current functional version and next bounded unit are canonical in `GOAL.md` | device-backed P349 hour witness, standing/unrestricted root shell, pixel readback, the WC/CACHED corruption cause, native normal reboot, software-causal Download attribution, unattended operation, resident native operation, and PID1/kernel-stall recovery |
| [Galaxy S20+ 5G](S20PLUS.md) (`SM-G986N`) | Qualcomm SM8250 / vendor Linux 4.19.113 | **PROVED:** onboarding, resident Magisk, retained T2 TWRP, and P0 V3 transfer/healthy rollback | Early-boot pstore/PMSG observation after P0 V3 NO_PROOF | Custom native PID 1, live early-boot retention, and autonomous F1 |

## Reading order

Start with the device page above. For current state, follow its GOAL link; for
device authority, follow the target contract; for historical outcomes, follow
the ledger and specific reports. A host-side `PASS_GO` qualifies only the
named capability and is not proof of a live result or standing device
authority.
