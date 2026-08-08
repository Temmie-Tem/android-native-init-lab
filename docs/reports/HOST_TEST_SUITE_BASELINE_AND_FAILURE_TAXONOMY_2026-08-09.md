# Host Test Suite Baseline And Failure Taxonomy

Date: `2026-08-09`
Tier: H0 (host only). No device was contacted. No device authority is claimed
or granted by this document.

## Why this is a report and not a ledger row

`AGENTS.md` restricts separate reports to a new capability, a new hazard class,
an incident, or an ambiguous device-safety result. This one records a **new
hazard class in host validation**: the suite's failure count is not a stable
measurement of the tree. 38 of 475 failures change identity depending on test
ordering, and 30 depend on host inputs that live in `/tmp`. Until that is
stated, any "N tests fail" number — including one used to gate a device action —
is being read as if it meant more than it does.

It belongs to no target campaign: it spans S22+ and A90 and touches neither.

## Measurement conditions

| | |
|---|---|
| Commit | `ebc5b6c7b5ee0ade8bbf405ab495a39b728c6abd` (working tree clean before and after) |
| Command | `python3 -m unittest discover -s tests -p "test_*.py"` from the repo root |
| Python | 3.14.4 |
| `umask` | `0002` — load-bearing, see F3 |
| Loop | stopped for the whole measurement |
| Wall time | 1749.7 s |

Result line, verbatim:

```
Ran 8509 tests in 1749.653s
FAILED (failures=309, errors=166, skipped=285)
```

## Headline

- **475 failure blocks**, across **471 distinct test ids**.
  The gap is real: 3 test ids are collected and run 2–3 times by discovery.
- 8509 collected tests is itself inflated: `unittest discover` turns a module it
  cannot import into one `_FailedTest`, so an unimportable module both removes
  its real tests and adds a fake one.

## Attribution

Every one of the 475 was re-run in isolation with `os.stat`, `os.lstat`,
`os.listdir` and `open` wrapped, recording each path touched and whether it
existed. Classification is from that observation, not from the exception label.

| | class | count |
|---|---|---|
| A | passes alone, fails in the suite (order-dependent) | 11 |
| B | module only imports because another test edited `sys.path` | 27 |
| C | a required input under `workspace/private/` is absent | 286 |
| D | a required host input staged under `/tmp/` is absent | 30 |
| E | some other absent path | 6 |
| F | nothing absent — code or expectation drift | 115 |
| | **total** | **475** |

C/D by input root (a test counts once per root it probed):

| tests | root |
|---:|---|
| 114 | `workspace/private/inputs/boot_images` |
| 85 | `workspace/private/builds/audio` |
| 45 | `workspace/private/inputs/toolchains` |
| 43 | `workspace/private/inputs/audio` |
| 29 | `workspace/private/backups/baseline_a_20260423_{025322,030309}` (the same 29 probe both) |
| 24 | `/tmp/a90-mesa-*` (three staging roots) |
| 21 | `workspace/private/runs/audio` |
| 17 | `workspace/private/outputs/s22plus_native_init` |

Class D counts only tests whose absent inputs were *exclusively* under `/tmp`.
A further 48 tests probe an absent `/tmp` path as well as an absent
`workspace/private/` one and are counted in C; 78 touch an absent `/tmp` path in
total.

## Findings

### F1 — the suite result depends on test ordering

**83 of 1199 test modules cannot be imported on their own** (78
`ModuleNotFoundError`, 5 `AttributeError`). They import inside the suite only
because a module that ran earlier put `workspace/public/src/scripts/revalidation`
on `sys.path`.

Measured directly, one fresh interpreter per module:

```
for f in tests/test_*.py; do PYTHONPATH=tests python3 -c "import $(basename $f .py)"; done
```

The consequence runs both ways:

- 27 failures are these modules; alone they fail with `ModuleNotFoundError`
  instead of whatever the suite reported.
- 11 failures across 5 modules **pass in isolation and fail in the suite** —
  `test_s22plus_fyg8_p286_change_freeze`,
  `test_native_audio_late_manifest_wait_live_v2808`,
  `test_native_doom_status_stub_live_handoff_v3001`,
  `test_native_doomgeneric_pageflip_presenter_source_v3077`,
  `test_native_doominput_keyboard_state_live_handoff_v2992`.
  That direction is contamination through shared state, not `sys.path`.

Nothing here is a new regression; it is the accumulated cost of three invocation
conventions coexisting (`_loader`, direct `sys.path` edits, neither).

### F2 — host inputs staged in `/tmp`

The GPU shader-verification cycles read their inputs from `/tmp`:

```
/tmp/a90-mesa-gpu-src/src/freedreno/registers/adreno/a6xx.xml
/tmp/a90-mesa-c1-fullnir-softpipe-v3300/src/freedreno/isa/ir3-disasm
/tmp/a90-mesa-gpu-src/a6xx_texture_blit_reference_v3304.txt
```

A reboot removes them and the tests fail permanently with a message-less
`assertTrue(False)`. The third file is a reference authored for V3304 — cloning
Mesa again does not restore it. Affected: V3299, V3300, V3302, V3304, V3305 plus
four non-GPU modules that stage under `/tmp` for other reasons.

`workspace/private/` is at least a declared and backed-up location. `/tmp` is
neither, and a test rooted there cannot state what it was verified against.

### F3 — `umask 002` breaks three exact-file contracts

`a90_phase2d_finalize_f1.regular_record()` rejects any input with
`st_mode & 0o022`. Git records only the executable bit, so under `umask 002`
a checkout produces `664`/`775` and the contract rejects its own review sources.

Of the 33 declared review sources, 28 are hardened to `644`/`755` and **5 are
not** — all of them added recently:

| file | added |
|---|---|
| `a90_v3403_absent_only_staging.py` | 2026-07-30 |
| `a90_phase3_network_ssh_keyed_rootfs_v1.py` | 2026-08-03 |
| `phase3_network_ssh_v1/{manifest.toml, a90_debian_network_ssh_v1.sh, a90_debian_return_arm_v1.sh}` | 2026-08-03 |

Verified by clearing the group/other write bits on those files, re-running, and
restoring every mode exactly:

```
before: FAILED (errors=3)
after : OK
modes restored exactly: True
```

Not a code defect — a convention that recent work did not follow, and that will
recur on every new file written into that closure. 140 tracked files in the tree
are currently mode `777`.

### F4 — `v2573.artifact_from_manifest` uses `Path()` as a null sentinel

`native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573.py:129`:

```python
path = ROOT / raw_path if raw_path else Path()   # Path() == Path('.')
```

`Path('.')` is truthy and `.exists()` is True, so a manifest entry with no
`path` passes both guards at `:133` and `:136` and reaches `open("rb")` on a
directory. All **20** `IsADirectoryError` failures pass through `:138` with
errno path `'.'`, from 18 modules and one caller.

The fix is the sentinel, not the guard — `path.is_file()` would suppress the
exception while still recording `"path": "."` and `"exists": True` for an entry
that has no path at all.

Measured with `else None` applied to a 12-test sample, then reverted:

| | before | after |
|---|---:|---:|
| `IsADirectoryError` | 7 | 0 |
| failing | 12 | 10 |

It converts crashes into correct fail-closed reports
(`{'ok': False, 'error': 'manifest missing: workspace/private/builds/audio/...'}`)
and clears 2. It does not clear the rest: those need the private build outputs.

### F5 — H2 first-boot tests were left behind by H3/H4

`tests/test_a90_h2_live_integration_v1.py` was last updated at `4fcb31d330`
(2026-08-05). `a90_resident_promotion_v1.py` and `a90_v3403_f1_orchestrator.py`
moved twice after that, on the same day and later. Four tests now fail:

- `validate_candidate_first_boot_contract()` gained required keyword-only
  `remote_final` and `rootfs_sha256`; the caller in the test was not updated.
- `_validate_candidate_first_boot_journal` reads `spec.candidate_build`; the
  test's `SimpleNamespace` fixture does not define it. (×2)
- The rejection message changed from `non-H2` to
  `non-auto resident journal has first-boot proof`; `assertRaisesRegex` still
  pins the old text.

This is the A90 resident promotion path, which is inside the A90 F1 execution
closure. The tests broke silently while the loop ran unattended.

### F6 — three tracked symlinks dangle into private space

```
workspace/public/archive/stage3/linux_init/init_v724
                                          /init_v725_fasttransport
                                          /init_v726_wifi_lifecycle
      -> ../../../../private/builds/native-init/v724/…
```

They are the only dangling tracked symlinks in the tree. A fresh clone gets
three broken links, and `workspace/public/archive/` is a runtime import path.

## What this does not establish

- **No claim that the 286 C-class failures are recoverable.** Each was observed
  probing an absent path; whether that input can be regenerated was not tested
  here, except that `workspace/private/inputs/audio/` is documented as host-only
  extractable in
  `docs/reports/NATIVE_INIT_V2506_AUDIO_ACDB_DEPENDENCY_CLOSURE_HOST_ONLY_2026-06-16.md`.
- **No claim about why any private input is absent.** Not measured.
- **F-class is 115 failures, not 115 bugs.** Several are correct fail-closed
  behaviour on consumed campaigns — `F1V2Error: manifest health profile or
  runner version mismatch` (21), expired capability gates, frozen preimage
  mismatches. Only F3/F4/F5 above were traced to a root.
- **`assertIn` failures are not mostly contract prose.** Of 98: 67 assert
  against generated runtime data, 15 against generated native C source, 7
  against other markdown, and only **8** against `AGENTS.md` or `GOAL*.md`.

## Instrument corrections made during this work

Recorded because both would have produced confident wrong numbers.

1. The first probe used `sys.addaudithook`. On Python 3.14 the `os.stat` audit
   event does not fire for `Path.exists()` / `os.path.exists()`, so it reported
   **zero** absent paths for 60 tests that demonstrably probe them. Caught only
   because it contradicted a directly observed `exists: false`. Replaced with
   wrapped `os.stat`/`os.lstat`/`open`, validated against a known-absent path
   before being trusted.
2. Paths were recorded verbatim and existence checked afterwards, which is wrong
   for any test that `chdir()`s. Fixed to resolve at record time and all 475
   were re-run: **0 rows changed class**. The correction was necessary to state;
   it did not change the result.

## Reproduction

```bash
# baseline
python3 -m unittest discover -s tests -p "test_*.py"

# F1: modules that cannot import alone
for f in tests/test_*.py; do
  m=$(basename "$f" .py)
  PYTHONPATH=tests python3 -c "import $m" >/dev/null 2>&1 || echo "$m"
done

# F3: the mode contract
python3 -c "
import os,sys; sys.path.insert(0,'workspace/public/src/scripts/server-distro')
import a90_phase2d_finalize_f1 as f
for p in sorted({q.resolve() for q in f.EXECUTION_REVIEW_SOURCES} |
                {q.resolve() for q in f.PHASE3_EXECUTION_REVIEW_SOURCES}):
    m = p.stat().st_mode & 0o777
    print(f'{m:04o}', p.name, '<-- rejected' if m & 0o022 else '')"

# F6: dangling tracked symlinks
git ls-files -z | xargs -0 -I{} sh -c '[ -L "{}" ] && [ ! -e "{}" ] && echo "{}"'
```

## Suggested order

1. **F3** — `chmod g-w,o-w` on 5 files. Minutes. Unblocks 3 failures and stops
   the recurrence in the A90 F1 closure.
2. **F5** — 4 stale tests in an execution-critical path. Small, and the longer
   it sits the less the H2 contract is actually being checked.
3. **F4** — one line, plus the 18 modules' failures become readable.
4. **F1** — the largest and the one that makes every future number trustworthy.
   No file edits are required to *measure* it; normalizing 1199 files is a
   separate decision.
5. **F2** — decide whether the GPU cycles' inputs move under `workspace/private/`
   or are declared unreproducible.
6. **F6** — three symlinks; decide whether the archive may reference private space.
