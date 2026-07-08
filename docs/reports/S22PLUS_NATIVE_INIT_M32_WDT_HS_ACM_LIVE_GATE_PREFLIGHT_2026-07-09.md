# S22+ M32 Watchdog-Managed HS ACM Live Gate Preflight (2026-07-09)

## Verdict

M32 LIVE GATE PREFLIGHT PASS. The guarded helper, `AGENTS.md` one-shot
exception, exact candidate hashes, rollback APs, Android identity, Android
stability, current boot hash, and baseline ACM state were verified.

No live flash was run by this preflight report. The later live step requires
`--live --ack S22PLUS-M32-WDT-HS-ACM-LIVE-GATE`.

## Helper

`workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py`

Modes:

```text
--offline-check
  Verify candidate artifacts and rollback APs only. No device action.

default dry-run
  Verify artifacts, AGENTS exception, Android identity/stability/current boot,
  and that no baseline M32 ACM endpoint is already present.

--live --ack S22PLUS-M32-WDT-HS-ACM-LIVE-GATE
  Flash the M32 boot-only AP, observe for ACM plus survival, then require
  manual Download rollback.

--rollback-from-download --ack S22PLUS-M32-WDT-HS-ACM-ROLLBACK-FROM-DOWNLOAD
  Roll back from an already-entered Download mode using the pinned Magisk
  boot-only AP, with stock boot-only fallback.
```

## Pinned Artifacts

```text
candidate AP.tar.md5  b2dee88862cbbfa8e9da799978c10134a07f41e4d144c23b2db1d0b8e00adbd4
candidate boot.img    8001809f9f0d7b2d6615bdec97843680a0c20721d679dde74a76bbe6d95bb9ca
candidate /init       0595a0e932fa0ca7240192e2438d134ca8e4338a48e68a17edb8d9b023dc8f77
module list           2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c
generated source      ad1b94c144faa3ba3dd232110a07a7680ce5aa7c796061158e0cd75c3edd37b2
preserved kernel      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
base Magisk boot      2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
Magisk rollback AP    d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock fallback AP     1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Candidate AP member list:

```text
boot.img.lz4
```

## Policy

The `AGENTS.md` one-shot exception now includes the live token
`S22PLUS-M32-WDT-HS-ACM-LIVE-GATE`, rollback token
`S22PLUS-M32-WDT-HS-ACM-ROLLBACK-FROM-DOWNLOAD`, exact hashes, target identity,
module closure, excluded QMP/EUD policy, and rollback requirements.

The helper confirmed:

```text
agents_exception_missing=[]
```

This exception authorizes only one attended boot-only M32 live gate. It does not
authorize DTBO/vendor_boot/recovery/vbmeta/non-boot flash, repeat M31B, M28/M29,
F43, RDX PC dump retrieval, EUD writes, Magisk modules, raw host dd, fastboot,
format data, or any A90 action.

## Dry-Run Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py
```

Result:

```text
dry-run ok: M32 candidate, rollback APs, AGENTS exception, Android stability,
current boot hash, and ACM baseline verified
```

Run log:

`workspace/private/runs/s22plus_m32_wdt_hs_acm_live_gate_20260708T170112Z/s22plus_m32_wdt_hs_acm_live_gate.txt`

Key live preflight facts:

```text
target=SM-S906N/g0q/S906NKSS7FYG8
vbstate=orange
boot_completed=1
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
android_stability_result=ok samples=4
current boot hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
baseline ACM=/dev/ttyACM0, vendor=04e8, product=6860, model=SAMSUNG_Android
```

The baseline ACM endpoint is Android's current interface, not the M32 endpoint:
product `6860`, serial `<S22_SERIAL_REDACTED>`, model `SAMSUNG_Android`; it did not match
the expected M32 serial `S22M32WDTHS01` or model marker.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m32_wdt_hs_acm_live_gate \
  tests.test_s22plus_m32_wdt_hs_acm_build

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py
```

Results:

- `py_compile`: pass.
- M32 live/build unit tests: 10 tests pass.
- `--offline-check`: pass, no device action.
- Default dry-run: pass, Android/Magisk baseline verified.

## Live Procedure

If proceeding immediately under the active one-shot exception:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py \
  --live \
  --ack S22PLUS-M32-WDT-HS-ACM-LIVE-GATE
```

Expected operator role:

- Do not press keys during the observation window.
- If the helper reports ACM proof or timeout and asks for rollback, manually
  enter Download mode.
- If the device reaches RDX/PMIC abnormal reset or any unexpected stuck state,
  report the screen state before further action.

Success criteria:

- Candidate leaves original Download endpoint after flash.
- M32 ACM endpoint appears, ideally with marker-bearing banner.
- No PMIC/RDX reset and no ADB/Odin reappearance during the observation window.
- Manual Download rollback restores the Magisk boot baseline.

Failure / no-proof:

- PMIC/RDX abnormal reset before ACM survival proof.
- No ACM endpoint through the observation window.
- Unexpected Odin/ADB endpoint before the observation window completes.
- Rollback cannot restore Android/Magisk baseline.
