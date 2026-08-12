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

The device-independent output is not the two ports — it is the **method**.

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

Currently demonstrated on three maintainer-owned devices. The architecture and
validation methodology are developed around device-independent boundaries where
practical.

- **Galaxy A90 5G (`SM-A908N`)** — established recovery-safe baseline: custom
  native init, USB ACM/NCM, KMS/HUD, input, storage, network, and a minimal
  userspace.
- **Galaxy S22+ (`SM-S906N`, FYG8)** — active frontier: source-matched
  vendor-kernel rebuild and retained PID 1 witness work.
- **Galaxy S20+ 5G (`SM-G986N`)** — newly acquired: one-shot read-only D0
  onboarding is consumed; no active D1/F1 process yet.

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

Changes move through bounded units: host-side implementation and validation,
independent adversarial review, then — only where unavoidable — recovery-safe
device validation with a pre-declared rollback. Results and their evidence are
recorded in per-target ledgers under `docs/operations/`.

AI coding agents, including Codex, are used for implementation and analysis
inside those same boundaries. The contract is the authority, not the agent.

The test suite is host-only and touches no device:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

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
- [`docs/overview/PROJECT_STATUS.md`](docs/overview/PROJECT_STATUS.md) — device state and verification history
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
