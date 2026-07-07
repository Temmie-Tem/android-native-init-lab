# S22+ — Ramoops DTBO + M13 Capture Gate Source (2026-07-08)

## Scope

Host-only source/gate work. No device action, no reboot, no flash, and no
partition write.

This follows the DTBO status-only live pass. The direct vendor_boot-only
positive-control path is retired; the new path must enable the live ramoops node
through patched DTBO before flashing M13.

## Added Helper

`workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py`

Modes:

- `--offline-check`: verify all DTBO/M13 packages, manifests, and rollback APs;
  no device action; no `AGENTS.md` live exception required.
- default dry-run: verify packages, then require a future SHA-pinned
  `AGENTS.md` exception before touching Android state.
- `--live`: once separately authorized, intended flow is patched DTBO flash,
  Android/root return, live `ramoops_region/status=okay` proof, M13 boot flash,
  host observation, Magisk boot rollback, pstore collection, and stock DTBO
  restore.
- `--rollback-boot-from-download`: attended recovery/capture mode if M13 parks
  and the operator manually enters Download mode; it rolls boot back, collects
  pstore, then restores stock DTBO.
- `--restore-dtbo-from-download` / `--restore-dtbo-from-android`: explicit stock
  DTBO restore paths.

## Required Pinned Artifacts

```text
dtbo candidate AP.tar.md5 4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00
dtbo rollback AP.tar.md5  6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
patched raw dtbo          1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab
stock raw dtbo            97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
M13 AP.tar.md5            5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
M13 boot.img              21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
M13 base Magisk boot      2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
M13 kernel                bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
M13 init                  6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
M13 source                4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
Magisk rollback AP        d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback AP    1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Required tar members:

```text
DTBO APs: dtbo.img.lz4
M13/boot rollback APs: boot.img.lz4
```

Ack tokens reserved by the helper:

```text
S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE
S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD
S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO
```

## Policy Draft

An inert copyable draft was added:

`docs/operations/S22PLUS_RAMOOPS_DTBO_M13_CAPTURE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`

It is not active policy. `AGENTS.md` was not edited by this unit.

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py
```

Results:

```text
py_compile: pass
offline-check: pass; verified DTBO/M13 candidates and rollback APs; no device action
default dry-run: blocked before Android/device action because AGENTS.md has no
  ramoops DTBO + M13 authorization markers; rc=1
```

The default blocker is intentional. The current live contract does not yet
authorize the combined DTBO+M13 run.

## Next Gate

If the operator chooses to run this live, first promote the inert exception
draft into `AGENTS.md`, then re-run the helper default dry-run. Only after the
dry-run proves Android/root baseline, stock DTBO hash, and live disabled status
should the attended `--live --ack S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE`
mode be considered.
