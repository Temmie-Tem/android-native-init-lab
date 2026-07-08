# S22+ M33 P28 Live Gate Preflight

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

GO for the already approved one-shot M33 P28 live gate.

The run remains boot-only and policy-bounded. `AGENTS.md` now contains the
fresh SHA-pinned M33 P28 exception and the helper dry-run verifies
`agents_exception_missing=[]`.

## Target

- Device: `SM-S906N/g0q/S906NKSS7FYG8`
- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py`
- Live ack: `S22PLUS-M33-P28-WDT-PREFIX-PARK-LIVE-GATE`
- Rollback-from-Download ack:
  `S22PLUS-M33-P28-WDT-PREFIX-PARK-ROLLBACK-FROM-DOWNLOAD`

## Candidate Pins

- Candidate AP SHA256:
  `4c76ef4df814356a7acfa9ce9a00c2fe003208ff8289c2874535e26b7e1c3f07`
- Candidate boot SHA256:
  `3bc59d6df58b5c7130e6ca531a6a6cd3a4d35e14ff7fd6667da72e2bd40e9e29`
- Candidate `/init` SHA256:
  `2ef661b9e5a1496674b6cc457c9b0e84c60ae7af01914c2403db602c6ebe84b1`
- Module-list SHA256:
  `ef57a00fbef4b9c89936b30fc5c001974fbe9c2ece590c6a6984cb4695318a8f`
- Generated source SHA256:
  `8d752ade0ee5100b5f91cb7fb15c09d24652a97e03721fb8c4d784d1f419f289`
- Known booting Magisk boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Scope

P28 adds `dwc3-msm.ko` and monitor gadget dependencies while still excluding
`usb_f_ss_acm.ko`, runtime configfs, runtime ACM setup, and QMP/EUD. It is a
park-only discriminator:

- no ACM function
- no runtime USB/configfs/ACM
- no reboot syscall
- no Download beacon
- no Android/Magisk handoff
- no persistent mount
- no block write

Survival means the candidate remains parked through the 60-90 second window
with no returned host ADB/Odin endpoint. PMIC/RDX abnormal reset before that
window is a fail. Manual Download rollback is recovery-only after the helper
asks for it.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m33_p28_wdt_prefix_park_live_gate.py \
  tests/test_s22plus_m33_wdt_prefix_park_build.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py
```

Results:

- `py_compile`: pass
- unit tests: 9 tests OK
- dry-run: pass
- `agents_exception_missing=[]`
- Android baseline: `boot_completed=1`, `vbstate=orange`
- Magisk root: `uid=0(root) ... context=u:r:magisk:s0`
- current boot partition SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Dry-run log:

`workspace/private/runs/s22plus_m33_p28_wdt_prefix_park_live_gate_20260708T181621Z/s22plus_m33_p28_wdt_prefix_park_live_gate.txt`

## Immediate Command

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m33_p28_wdt_prefix_park_live_gate.py \
  --live --ack S22PLUS-M33-P28-WDT-PREFIX-PARK-LIVE-GATE
```
