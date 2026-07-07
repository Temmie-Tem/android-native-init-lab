# S22+ Native-Init M21 Floor Discriminator Redesign (2026-07-08)

## Verdict

HOST-ONLY REDESIGN. No build, flash, or device write was run in this unit.

M20A invalidates the old helper-only inference:

`later Odin endpoint == automatic self-download proof`

The helper can observe a later download-mode endpoint after the operator has
manually forced download mode during a bootloop. Therefore any future floor
probe must make the candidate state externally distinguishable before download
mode appears. Plain `reboot(..., "download")` timing is not enough.

## Evidence Reclassification

M4T2 remains the strongest positive native-init floor proof.

- It used a raw AArch64 `/init`.
- It had no libc, loader, filesystem setup, marker write, module loading,
  configfs, or reboot syscall.
- It immediately entered an infinite `wfe; b` park loop.
- The proof was not a transport timing inference. The operator visually
  confirmed the device stopped/parked and did not continue the prior fast
  bootloop.

M4T3 is downgraded from a hard raw-reboot PASS to a timing-ambiguous result.

- The candidate was raw assembly and first-action
  `reboot(..., "download")`.
- The helper saw a later Odin endpoint about 44 seconds after the original
  post-flash endpoint disconnected.
- The operator observed a bootloop-like sequence.
- There was no manual-download correction recorded at that time, so the result
  remains useful, but after M20A it must not be used as a standalone hard proof
  that the raw reboot syscall self-entered download mode.

M19 C000 and M20A both now share the same failure interpretation:

- candidate flash succeeded;
- helper later saw an Odin endpoint;
- operator reported bootloop behavior and manual download-mode entry;
- rollback succeeded;
- automatic self-download proof failed.

M20B, M20C, M19 C129+, and wider module paths remain parked.

## Failure In The Old Discriminator

The old detector conflated at least four cases:

1. Candidate raw PID1 calls `reboot(..., "download")` successfully.
2. Candidate crashes or exits and the platform eventually falls to a visible
   bootloop.
3. Bootloader or recovery policy re-enters a mode that later exposes Odin.
4. Operator manually enters download mode to recover.

The host can see the endpoint, but without an intentional pre-download dwell or
another independent marker it cannot prove which case happened.

## M21 Requirements

The next live-capable discriminator must satisfy all of these before it is
considered for a SHA-pinned `AGENTS.md` exception:

- boot partition only, Odin AP with exactly `boot.img.lz4`;
- raw AArch64 PID1 only: no C runtime, libc, dynamic loader, filesystem setup,
  kmsg/pstore marker, modules, configfs, USB role force, or Android handoff;
- candidate must enter a visible or time-distinct state before requesting
  download mode;
- helper must record monotonic timestamps for flash completion, original Odin
  disconnect, dwell start, expected earliest self-download, actual Odin
  reappearance, rollback start, and rollback done;
- helper must treat any Odin endpoint before the dwell threshold as
  `no-proof/manual-or-bootloader-artifact`, not as self-download;
- operator instruction must be explicit: do not press recovery/download keys
  until the helper either reaches dwell+grace timeout or asks for manual
  rollback;
- if the operator intervenes manually at any point, the result is recovery-only
  and no automatic proof.

## Proposed Next Candidate

Preferred first candidate:

`M21A_RAW_NANOSLEEP_DOWNLOAD`

Shape:

```text
_start:
  raw nanosleep(75-90s)
  raw reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
             LINUX_REBOOT_CMD_RESTART2, "download")
  infinite wfe park if the syscall returns
```

This adds one raw syscall before reboot, so it is not a pure reboot-only
candidate. That is intentional: the wall-clock dwell is the proof separator.
It keeps the runtime shape below C/libc/fs/module/configfs while making manual
intervention and early bootloader artifacts distinguishable.

Rejected as primary:

- Pure first-action raw reboot again: repeats the ambiguous M20A/M4T3 proof
  shape.
- Busy-loop calibrated delay: avoids `nanosleep`, but wall time depends on CPU
  frequency and boot-time scheduling.
- Marker-before-reboot: adds filesystem/logging surfaces before the floor is
  repaired.

Optional control:

`M21P_RAW_PARK_RERUN` can re-anchor the M4T2 visual park under current helper
timing, but it requires manual download-mode rollback by design and does not
answer whether raw self-download can be made unambiguous.

## Live Interpretation Policy

For a future M21A live run:

- PASS:
  - candidate flash succeeds;
  - the device does not visibly fast-loop before the dwell threshold;
  - no operator key intervention occurs;
  - Odin/download mode appears only after dwell+grace;
  - rollback restores the pinned Magisk boot baseline.

- FAIL, below-or-at floor:
  - visible fast loop before the dwell threshold;
  - Odin endpoint appears before the dwell threshold;
  - Android/ADB returns unexpectedly;
  - no download mode appears after dwell+grace and the candidate cannot prove
    the reboot syscall.

- RECOVERY ONLY / NO PROOF:
  - operator manually enters download mode before the helper declares the
    automatic window complete.

## Next

Implement host-only M21A build tooling and static validation first. Do not live
flash until the candidate AP SHA256, boot SHA256, `/init` SHA256, helper, ack
tokens, dry-run output, rollback preconditions, and the exact M21A-only
`AGENTS.md` boot-partition exception are committed.
