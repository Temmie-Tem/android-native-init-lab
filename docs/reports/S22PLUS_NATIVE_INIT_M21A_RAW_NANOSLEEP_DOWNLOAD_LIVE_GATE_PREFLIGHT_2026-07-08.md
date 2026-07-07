# S22+ M21A Raw Nanosleep-Download Live Gate Preflight (2026-07-08)

## Verdict

PREFLIGHT READY, NOT EXECUTED.

Codex added the SHA-pinned `AGENTS.md` exception and guarded helper for exactly
one M21 candidate:

`M21A_RAW_NANOSLEEP_DOWNLOAD`

No live flash, reboot, Odin candidate transfer, or rollback was run in this
unit.

## Helper

Path:

`workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py`

Live ack:

`S22PLUS-M21A-RAW-NANOSLEEP-DOWNLOAD-LIVE-GATE`

Rollback-only ack:

`S22PLUS-M21A-ROLLBACK-FROM-DOWNLOAD`

Default behavior is dry-run. `--offline-check`, `--live`, and
`--rollback-from-download` are mutually exclusive.

## Candidate Pins

```text
label               M21A_RAW_NANOSLEEP_DOWNLOAD
AP.tar.md5          d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79
boot.img            61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5
base_boot           2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel              bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
/init               10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30
source              300ed990c8ea476c3744e18327ae08277c0d27dc443e99245aeecba457968c4f
```

Rollback APs:

```text
Magisk boot-only AP  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
Stock boot-only AP   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

The candidate AP contains exactly one member:

```text
boot.img.lz4
```

## Runtime Shape

The helper verifies the host-built manifest before any live action:

```text
raw AArch64 PID1
no C runtime / libc / PT_INTERP
no fs setup
no marker write
no module load
no configfs / UDC binding / USB role force
no persistent partition mount
no block-device writes
pre_reboot_dwell_sec=90
pre_reboot_syscalls=["nanosleep"]
auto_reboot=download
on_reboot_syscall_return=infinite-park
```

The helper also verifies that `/init` has exactly two `svc #0` instructions and
loads arm64 syscall numbers 101 (`nanosleep`) and 142 (`reboot`).

## Timing Policy

This is the important behavioral change from M20A.

The helper does not treat a later Odin endpoint as a pass by itself. It records
monotonic elapsed time after the original post-flash Odin endpoint disconnects:

- Odin before the 90 second dwell threshold: no proof.
- Android/ADB return: no proof.
- No Odin within the post-dwell grace window: no proof; manual rollback
  required.
- Operator manual download-mode entry: recovery-only / no proof.
- PASS requires Odin/download mode only after the 90 second dwell and within
  the grace window, with no operator key intervention, followed by rollback to
  the pinned Magisk boot baseline.

Default live window:

```text
dwell_sec=90
dwell_grace_sec=30
```

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py
```

Results:

- `py_compile`: pass.
- `--offline-check`: pass; AGENTS exception, M21A AP/manifest, and rollback APs
  verified; no device action.
- Dry-run: pass; verified current Android identity, orange verified boot,
  `boot_recovery=0`, `boot_completed=1`, Magisk root, current boot SHA
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`, M21A
  AP/manifest, rollback APs, and dwell policy.

Private dry-run log:

`workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_gate_20260707T180008Z_01/s22plus_m21a_raw_nanosleep_download_live_gate.txt`

## Next

M21A live can now be run only with the explicit ack token:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --live --ack S22PLUS-M21A-RAW-NANOSLEEP-DOWNLOAD-LIVE-GATE
```

During the live window the operator must not press recovery/download keys until
the helper either completes the dwell+grace window or asks for manual rollback.
If manual recovery is needed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --rollback-from-download --ack S22PLUS-M21A-ROLLBACK-FROM-DOWNLOAD
```
