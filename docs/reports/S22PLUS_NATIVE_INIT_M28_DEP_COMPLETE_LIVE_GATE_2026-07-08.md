# S22+ Native-Init M28 Dependency-Complete Live Gate (2026-07-08)

## Verdict

PRE-LIVE PASS / LIVE NOT EXECUTED: M28 dependency-complete batch policy is
SHA-pinned in `AGENTS.md`, statically validated, and dry-run verified against
the attached S22+ Android/Magisk baseline. No live flash, reboot, rollback,
partition write, or sysfs write was performed.

## Scope

Authorized M28 matrix:

- `S24`
- `S24,F43`

`S24` must run first. If `S24` fails, requires operator manual Download, or does
not cleanly roll back to Magisk boot, stop and do not run `F43`. Manual Download
during observation is contamination and must not be counted as clean
self-download proof.

The batch uses the pinned M25 DTBO high-speed cap, rolls boot back to the
Magisk baseline after each clean self-download hit, and requires stock DTBO
rollback at session end.

## Files

- Live helper:
  `workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py`
- Tests:
  `tests/test_s22plus_m28_dep_complete_live_gate.py`
- Host-build manifest:
  `workspace/private/outputs/s22plus_native_init/m28_dep_complete_download_v0_1/manifest.json`
- Source-stage report:
  `docs/reports/S22PLUS_NATIVE_INIT_M28_DEP_COMPLETE_LIVE_GATE_SOURCE_2026-07-08.md`
- Closure finding:
  `docs/reports/S22PLUS_MODULE_CLOSURE_DEP_INCOMPLETE_STOCK_MODULES_DEP_2026-07-08.md`

## Pinned Artifacts

Helper SHA256:

```text
83521d521c55ceda8c860a940f8eb334e66638561b785231c5a5b007ad791d3b
```

M28 top manifest SHA256:

```text
4986940e214dcb32916f5e06806f0cb2342479e82347abec0244edb2a09a250e
```

M25 DTBO context:

```text
M25 high-speed DTBO AP: 35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6
patched raw DTBO:       8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17
stock DTBO rollback AP: 6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
stock raw DTBO:         97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

M28 candidates:

| Label | Modules | Modules SHA256 | AP.tar.md5 SHA256 | boot.img SHA256 | /init SHA256 |
| --- | ---: | --- | --- | --- | --- |
| `S24` | 26 | `8c605e2c69aad74f80191bdbc1843b002539d22d49bcffa86bb85bbcb343e5e4` | `c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f` | `a1459931001bfd6e17593dd329fc682f00ab61f4841b6543791f5349dd012cd0` | `5c04a2023b2b56ef98746da6f7168121b62d7859cee81c756b80d1a382c1964e` |
| `F43` | 43 | `430050d648d85dd6c3fea459a6cd627a58fd234afe1b485820ccc1f2eb65f87b` | `003ea5760d9e33402750afd7a52b6b95727e4b4cff3f4d3cf66c559eabbb38d1` | `6453b8f2dd685757148056ba8767c2820b0547123f4e5e5e423c4adb0c70496c` | `68de58cd3f05fd77af00984027948ad5ab953ae128dc4133d336e0a521cd588f` |

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m28_dep_complete_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --serial RFCT519XWGK

git diff --check
```

Results:

- Unit tests passed: `Ran 9 tests ... OK`.
- Offline check passed for `S24/F43`, M25 DTBO cap, and rollback APs with no
  device action.
- Device dry-run passed with `agents_exception_missing=[]`.
- `git diff --check` passed.

## Dry-Run Baseline

Dry-run log:

```text
workspace/private/runs/s22plus_m28_dep_complete_live_gate_20260708T142842Z/s22plus_m28_dep_complete_live_gate.txt
```

Baseline observed:

- `boot_completed=1`
- `bootanim=stopped`
- `vbstate=orange`
- Magisk root: `uid=0(root)`
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- stock DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Live Commands

Recommended first live command, not executed by this report:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --serial RFCT519XWGK \
  --variant S24 \
  --live \
  --ack S22PLUS-M28-DEP-COMPLETE-LIVE-GATE
```

Only after a clean S24 self-download and Magisk boot rollback should `F43` be
considered:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --serial RFCT519XWGK \
  --variant S24 \
  --variant F43 \
  --live \
  --ack S22PLUS-M28-DEP-COMPLETE-LIVE-GATE
```

Rollback-only rescue command if a candidate leaves the phone in Download mode:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M28-DEP-COMPLETE-ROLLBACK-FROM-DOWNLOAD
```

Stock-DTBO-only rescue command if the boot candidate was not flashed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m28_dep_complete_live_gate.py \
  --restore-dtbo-from-download \
  --ack S22PLUS-M28-RESTORE-STOCK-DTBO
```
