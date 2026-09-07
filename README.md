# Android Native Init Lab

[![license](https://img.shields.io/github/license/Temmie-Tem/android-native-init-lab)](LICENSE)
[![repository boundary](https://github.com/Temmie-Tem/android-native-init-lab/actions/workflows/boundary.yml/badge.svg)](../../actions/workflows/boundary.yml)
[![last commit](https://img.shields.io/github/last-commit/Temmie-Tem/android-native-init-lab)](../../commits)

**English** · [한국어](README.ko.md)

**Building a minimal Linux-style userspace on Android vendor kernels — keeping
the device drivers, replacing everything above them.**

An Android phone that loses vendor support is still a capable computer: ARM64
SoC, RAM, flash, display, battery, Wi-Fi, USB. What ages out is the software
stack, not the silicon. The hard part of reusing that hardware is that its
drivers exist only inside its vendor kernel.

This repository researches a reproducible, recovery-safe way to keep that vendor
kernel and its device-specific drivers while replacing the Android userspace
entry point with a **custom static `/init` running as PID 1** and a minimal
native runtime.

It is not a distribution port and not a custom ROM.

<p align="center">
  <img src="docs/images/a90/01-debian-pid1-appliance.jpg" width="36%" alt="Debian 12.14 running as PID 1 on the A90">
  <img src="docs/images/a90/boot-sequence.gif" width="41%" alt="A90 native init booting on the stock Linux 4.14 vendor kernel">
</p>

<p align="center"><sub>
Two separate A90 runs, on different builds, recorded on the physical device.<br>
<b>Left</b> — Debian 12.14 with <code>/usr/sbin/init</code> as PID 1 on an ext4 root,
with Dropbear SSH on the local USB-NCM link and a loopback HTTP service also
reached through an outbound Cloudflare Quick Tunnel.<br>
<b>Right</b> — a native-init cold boot on the stock Samsung Linux 4.14 vendor
kernel, from the Samsung splash through the USB serial gadget coming up to the
HUD.<br>
<a href="docs/devices/A90_VISUAL_EVIDENCE.md">More A90 visual evidence and run references →</a>
</sub></p>

## Why this approach

For an unsupported Android device the usual options are:

| Path | Hardware support | Cost |
| --- | --- | --- |
| Keep stock Android | Good | The entire Android framework comes along |
| Custom ROM | Good | Still Android; still the framework |
| Mainline Linux port | Poor initially | Per-model GPU/display/USB/power bring-up |

This project explores the gap between them: **vendor kernel + native
Linux-style userspace**. Vendor drivers keep working, the Android framework is
gone, and control starts at PID 1.

```text
vendor bootloader
  -> stock or source-matched rebuilt Android vendor kernel
    -> custom static /init (PID 1)
      -> serial console / display HUD / input
      -> logging and runtime layer
      -> USB gadget, networking, server-oriented userspace
```

## Why it might matter beyond these devices

The device-independent output is not the individual device ports — it is the
**method**.

Bring-up work on locked-down hardware is normally ad hoc, undocumented, and
occasionally destructive. This repository is an attempt to make it auditable and
repeatable:

- a binding safety contract ([`AGENTS.md`](AGENTS.md)) that classifies every
  action by risk tier — host-only, connected read-only, transient control, and
  boot-only transfer;
- mandatory pre-declared rollback, no-replay rules, and target isolation, so a
  failed experiment cannot quietly brick a device or contaminate another target;
- reproducible candidate identity, evidence ledgers, and host-side validation
  that must pass before any device is touched.

See [`docs/operations/DEVICE_ACTION_RISK_TIERS.md`](docs/operations/DEVICE_ACTION_RISK_TIERS.md)
and [`docs/operations/DEVICE_ACTION_PROCESS_V2.md`](docs/operations/DEVICE_ACTION_PROCESS_V2.md).

## Current scope

Research currently spans three maintainer-owned devices. The architecture and
validation methodology are developed around device-independent boundaries where
practical. See the [device progress guide](docs/devices/README.md) for the
evidence-bounded overview.

- **Galaxy A90 5G (`SM-A908N`)** — custom native PID 1, ACM/NCM, native Wi-Fi
  and audio, plus bounded Debian PID 1/SSH/display results. The current unit is
  H41 rollback/health closure; the isolated-Debian server work is paused.
- **Galaxy S22+ (`SM-S906N`, FYG8)** — the authenticated native-PID1 USB path
  now supports bounded read-only shell work through P348. The P353-P361 display
  series then reached repeated cached-buffer framebuffer selection with clean
  output observed by the operator and corroborated by photographs and clips;
  authenticated dispatch and exact rollback are proved separately from the
  visual observation. P363 and P364 moved to native reboot/Download control but
  both closed `NO_PROOF_OBSERVER`; that control path remains unproved. P365 is
  the current implementation/qualification unit. The P349 RAM-workspace/hour-witness
  unit remains host-qualified and paused.
- **Galaxy S20+ 5G (`SM-G986N`)** — exact onboarding, resident Magisk root, and
  retained T2 TWRP recovery are established. The P0 V3 native-PID1 attempt
  ended with no exact ACM banner and healthy Magisk rollback. Native PID 1
  remains unproved; current work investigates an early-boot observation path.

The S22+ entry was checked on 2026-09-08; other entries retain their 2026-09-05 snapshot. The device pages link
the accepted results; each target's GOAL and contract govern its changing
frontier and execution requirements.

Target-specific source, helpers, reports, rollback identities, and safety gates
stay explicitly separated. A result on one target never authorizes a device
action on another.

## What this is not

- Not a completed Debian/Ubuntu/Red Hat port.
- Not a project to restore the Android framework, apps, SurfaceFlinger, or Zygote.
- Not a mainline kernel port or a general-purpose custom ROM.
- Not an environment that immediately supports camera, modem, or GPU
  acceleration, which depend on Android vendor userspace.
- Not a rooting, bypass, or exploit-practice project. Nothing here is a method
  for reaching devices, services, accounts, or networks belonging to anyone else.

## How work is validated

Changes move through bounded units with an explicit completion criterion.
Start with available evidence and focused host checks; reuse unchanged build
and validation results. Independent review applies to the contract, execution,
and safety changes named in [`AGENTS.md`](AGENTS.md#review-rules).
Use device validation when the question requires it, under the selected
target's recovery and approval rules. Results and their evidence are recorded
in per-target ledgers under `docs/operations/`.

AI coding agents, including Codex, are used for implementation and analysis
inside those same boundaries. The contract is the authority, not the agent.

The test suite is host-only and touches no device. Run tests for the changed
area first, expanding coverage when the change or a failure requires it;
see [test guidance](CONTRIBUTING.md#running-the-tests). Documentation-only
edits normally need content, link, and diff checks rather than image builds.

One check runs continuously. The **Repository boundary** badge asserts exactly one
thing: the public tree satisfies the identifier boundary in
[`docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md).
It is not a test-suite status — the full suite depends on maintainer-private
fixtures and is not run in CI.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Documentation index, project status, per-cycle reports |
| `docs/operations/` | Risk tiers, device-action process, per-target contracts, campaign ledgers |
| `workspace/public/src/native-init/` | Native init source closure |
| `workspace/public/src/scripts/` | Analyzers, validators, build and revalidation helpers |
| `workspace/public/archive/` | Historical script and native-init provenance |
| `workspace/private/` | Local private inputs, images, build outputs, raw logs (not published) |
| `tests/` | Host-only regression suite |

## Key documents

- [`GOAL.md`](GOAL.md) / [`GOAL_A90.md`](GOAL_A90.md) / [`GOAL_S20PLUS.md`](GOAL_S20PLUS.md) — current frontier and next bounded unit per target
- [`AGENTS.md`](AGENTS.md) — binding safety contract and absolute device boundaries
- [`docs/README.md`](docs/README.md) — full documentation index
- [`docs/devices/README.md`](docs/devices/README.md) — per-device progress, established results, and open boundaries
- [`docs/overview/PROJECT_HISTORY.md`](docs/overview/PROJECT_HISTORY.md) — how the project got here, era by era (narrative; not evidence)
- [`CHANGELOG.md`](CHANGELOG.md) — native init and boot image version history
- [`README.ko.md`](README.ko.md) — Korean documentation, including the detailed working rules

## Safety, scope, and ethics

This work is performed only on local devices that the repository owner
personally owns and maintains a recovery path for. Nothing here should be read
as a method for accessing third-party devices, services, accounts, or networks.

This repository may reference real flashable binaries and vendor-specific
images. Before any experiment, confirm the current boot/recovery/vbmeta state
and a recoverable known-good image.

Device serials and other private identifiers are not published; see
[`docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md).

## Contributing

Most of the useful work here needs no device — analyzers, validators, tests, and
documentation are all host-only. See [`CONTRIBUTING.md`](CONTRIBUTING.md), and
[`SECURITY.md`](SECURITY.md) for reporting security-relevant findings.

## License

Original documentation, scripts, and source in this repository are MIT licensed —
see [`LICENSE`](LICENSE).

Vendor firmware, kernel sources, patched AP/TWRP images, and other proprietary
components are **not** covered by that license, are not distributed here, and
remain under their own terms. Third-party components vendored into the published
tree (such as AOSP `mkbootimg`) keep their own licenses. See [`NOTICE`](NOTICE).

## A note on the repository name

This repository was originally named `A90_5G_rooting`, when the Galaxy A90 5G was
its only target. It was renamed after the research expanded to the Galaxy S22+
and to a reusable, device-independent native PID 1 method. Historical paths and
target-specific `a90_*` identifiers are retained where they remain technically or
historically meaningful.
