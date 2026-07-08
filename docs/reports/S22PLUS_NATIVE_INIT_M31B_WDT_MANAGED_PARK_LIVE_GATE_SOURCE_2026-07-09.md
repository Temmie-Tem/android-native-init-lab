# S22+ M31B Watchdog-Managed Park Live Gate Source (2026-07-09)

## Verdict

HOST-ONLY LIVE-GATE SOURCE PASS / OFFLINE-CHECK PASS / DEFAULT DRY-RUN
FAIL-CLOSED ON MISSING `AGENTS.md` EXCEPTION.

No flash, reboot, Odin transfer, partition write, or device write was run in
this unit.

This adds the guarded helper for the already-built M31B watchdog-managed park
candidate. The helper is intentionally inert for live use until a fresh
M31B-only SHA-pinned boot-only `AGENTS.md` exception exists.

## Helper

`workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py`

Modes:

```text
--offline-check
  Verify candidate AP, manifest contract, Magisk rollback AP, stock fallback AP.
  No AGENTS exception check, no Android check, no Odin transfer.

default dry-run
  Verify artifacts, then require a fresh M31B AGENTS exception before Android
  preflight. This currently fails closed because no active M31B exception exists.

--live --ack S22PLUS-M31B-WDT-MANAGED-PARK-LIVE-GATE
  Future only. Requires AGENTS exception first.

--rollback-from-download --ack S22PLUS-M31B-WDT-MANAGED-PARK-ROLLBACK-FROM-DOWNLOAD
  Future recovery-only boot rollback from an attended Download-mode device.
```

## Pinned Candidate

```text
AP.tar.md5          06d1c149c7c09a284062826f21ac848220e99d552d6b91762abbfb80f3679527
boot.img            206fbb40df69a496f7fbe67e32cf862049d9258ef518db6949e1b5db2f4afdc4
/init               b01e52d3762e3cbdcba3501b00bb1dc9f9084899550ea23b92df43884bed23d0
module list         80da959311e4a0f6bedb40da3c6f74c7fd5918017e40e0787b3e17c153cfe937
source              32d85b4aeb64e5e1615b175b93fde166795598bfa0614934a9dcfb1bb165230d
kernel              bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
base Magisk boot    2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

AP member list:

```text
boot.img.lz4
```

Watchdog dependency closure:

```text
smem.ko
minidump.ko
qcom-scm.ko
qcom_wdt_core.ko
gh_virt_wdt.ko
```

Rollback APs:

```text
Magisk boot rollback AP   d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback AP    1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Helper Contract

The helper verifies:

- candidate AP SHA and exactly one `boot.img.lz4` tar member;
- manifest target is `SM-S906N/g0q/S906NKSS7FYG8`;
- manifest `live_flash_authorized=false`;
- manifest still requires a fresh SHA-pinned `AGENTS.md` exception;
- boot-only construction from known-booting Magisk boot;
- no reboot syscall intent, `reboot_request=null`;
- no Android/Magisk handoff;
- no persistent partition mount or block write;
- no USB/configfs/ACM path;
- no module binary injection into boot ramdisk;
- exactly one module-list text file in boot ramdisk;
- exact watchdog closure above;
- final `/init` has arm64 `__NR_finit_module` (273);
- final `/init` does not contain arm64 `__NR_reboot` (142).

## Live Interpretation Model

M31B is not counted by self-Download. It is a park candidate.

PASS for a future live:

- candidate leaves original Odin Download mode after flash;
- no ADB/Odin endpoint appears during the selected observation window;
- no operator-observed PMIC/RDX abnormal reset during that window;
- default observation window is 120 seconds, minimum allowed by helper is 60
  seconds;
- operator enters Download mode manually only after the helper asks for rollback;
- rollback restores the pinned Magisk boot baseline.

FAIL / NO-PROOF:

- original Odin endpoint never disconnects after candidate flash;
- Odin or ADB appears before the survival window finishes;
- PMIC/RDX abnormal reset appears before the survival window finishes;
- manual Download happens before the helper asks;
- rollback does not restore Android/Magisk baseline.

Manual Download is recovery-only. It is never reported as candidate
self-Download proof.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m31b_wdt_managed_park_live_gate \
  tests.test_s22plus_m31b_wdt_managed_park_build

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py
```

Results:

```text
py_compile: pass
unit tests: 8 tests pass
offline-check: pass; no device action
default dry-run: fail-closed; AGENTS.md missing M31B authorization markers
```

Offline-check private log:

`workspace/private/runs/s22plus_m31b_wdt_managed_park_live_gate_20260708T162231Z_01/s22plus_m31b_wdt_managed_park_live_gate.txt`

Default dry-run failed before Android preflight because `AGENTS.md` has no
M31B one-shot exception. That is the intended current state.

## Next

Do not live-flash from this report alone. The next unit, if the operator wants
to run M31B, is to add one fresh M31B-only SHA-pinned boot-only `AGENTS.md`
exception with the helper path, exact hashes, live ack token, rollback ack
token, observation semantics, and rollback requirements. Then rerun the default
dry-run; only a dry-run that passes Android/root/baseline checks should precede
the attended live command.
