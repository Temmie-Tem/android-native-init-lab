# Contributing

Thanks for looking. This is a research repository, so contribution works a
little differently from a typical library: **most of the value can be
contributed without owning any of the target devices.**

Everything here is governed by [`AGENTS.md`](AGENTS.md), the binding safety
contract, and by the risk tiers in
[`docs/operations/DEVICE_ACTION_RISK_TIERS.md`](docs/operations/DEVICE_ACTION_RISK_TIERS.md).
Please skim both before opening a substantial pull request.

## Host-only contributions (no device required)

This is the largest and most useful surface. Everything here is verifiable on an
ordinary Linux host, touches no phone, and corresponds to the **H0** tier:

- **Analyzers and parsers** under `workspace/public/src/scripts/` — decoders,
  evidence validators, contract checkers.
- **Tests** under `tests/` — the suite is host-only by design.
- **Build and packaging tooling.**
- **Documentation** — including corrections to the operational docs under
  `docs/operations/`.
- **Bug reports against host-side code**, ideally with a failing test.

If you are looking for a place to start, a failing or missing test for an
existing analyzer is always welcome.

## Device-backed contributions

Anything that touches real hardware is only acceptable on a device **you
personally own and can recover**, and must follow the tier rules:

| Tier | What it is | Requirement |
| --- | --- | --- |
| `D0` | Connected, read-only observation | Exact target resolution; no writes |
| `D1` | One transient, no-payload control action | Pre-declared recovery; operator present |
| `F1` | Boot-only image transfer | Mandatory exact rollback; attended; never replayed |

Device-backed work must arrive with its evidence: what was run, what was
observed, the rollback that was performed, and the verified final health of the
device. Please open an issue to discuss before doing device work — the contract
requires the target and the recovery path to be settled *before* anything is
sent to hardware.

Adding a **new device target** additionally requires a target contract and a
rollback identity of its own; the existing ones under
[`docs/operations/targets/`](docs/operations/targets/) are the reference.

## Not accepted

- Any action against a device you do not own and control.
- Destructive experimentation without a pre-declared, tested recovery path.
- Writes to forbidden partitions or use of forbidden primitives (see
  `AGENTS.md` — this includes bootloader, modem, EFS, RPMB, and similar).
- Changes aimed at credential capture, stealth, persistence, or evading device
  or platform protections.
- Commits containing device serials, PARTUUIDs, MAC/BSSID/IP values, firmware
  blobs, boot images, or raw device logs. Keep private inputs and run evidence
  under `workspace/private/`, which is not published. See
  [`docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md);
  a boundary check enforces this.

## Running the tests

The suite is pure host-side and touches no device. Run it through `discover`,
which is the supported invocation:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

The full suite is large and slow; when working on one area, narrow the pattern:

```bash
python3 -m unittest discover -s tests -p "test_s22plus_fyg8_p30*.py"
```

Before opening a pull request, confirm the repository boundary check is clean:

```bash
python3 workspace/public/src/scripts/security/repository_boundary_check.py
```

Some tests depend on private fixtures or a cross-toolchain that are not part of
the public tree; those are expected to be skipped or excluded rather than run.

## Pull requests

- Keep changes bounded — one logical unit per PR.
- Include the host validation you ran.
- Do not modify a target contract or the safety boundaries in `AGENTS.md`
  casually; changes there require independent review.
- Documentation-only fixes are welcome and do not need ceremony.
