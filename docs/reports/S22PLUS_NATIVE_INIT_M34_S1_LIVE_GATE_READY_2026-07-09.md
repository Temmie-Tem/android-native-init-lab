# S22+ M34 S1 Live Gate Ready

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

HOST READY / FAIL-CLOSED / NO LIVE AUTH.

The M34 S1 live gate helper is implemented and statically validated. It does
not authorize a live flash. `AGENTS.md` still has no active M34 S1 exception,
so default execution fails closed before Android or flash actions.

2026-07-09 04:19 KST update: the helper can now print a draft
SHA-pinned one-shot `AGENTS.md` exception for this exact S1 artifact with
`--print-agents-exception-draft`. The draft is not active authorization unless
the operator approves it and it is inserted into `AGENTS.md`.

## Helper

`workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py`

Default candidate:

`workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/S1/odin4/AP.tar.md5`

## Candidate Pins

- target: `SM-S906N/g0q/S906NKSS7FYG8`
- stage: `S1`
- marker: `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S1`
- AP.tar.md5 SHA256:
  `77e8858ea6becc3e988232d464f97827f55594f16ed6edebd23c3529c972d237`
- boot.img SHA256:
  `bb46233068890bb6849c63b4dab845ca48b65a9ffeac9e24ad08e81416b63f85`
- `/init` SHA256:
  `5339170f3138843a8f8da6cfd5f20f85696d3a9d18ae22bda439e21d0dd259cd`
- template source SHA256:
  `ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193`
- module-list SHA256:
  `2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`
- base Magisk boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Contract Checked

The helper verifies the v0.2 manifest and refuses drift:

- S1 only
- stock recipe report pointer present
- runtime steps exactly:
  `configfs_gadget=True`, `udc_none=True`,
  `max_speed_high_speed=False`, `usb_role_force=False`, `udc_bind=False`
- `UDC=none` and stock IDs are present
- `g1/max_speed=high-speed`, `/sys/class/usb_role`, and
  `UDC=a600000.dwc3` are absent from S1
- AP tar contains exactly `boot.img.lz4`
- boot-only, no reboot syscall, no Download beacon
- no Android/Magisk handoff
- no persistent mount or block write
- no module binary injection into boot ramdisk
- QMP and EUD remain excluded
- rollback APs are SHA-pinned
- generated exception draft must satisfy the same `policy_required_markers()`
  set as the live fail-closed gate

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest -q \
  tests/test_s22plus_m34_s1_runtime_gadget_live_gate.py \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s1_runtime_gadget_live_gate.py \
  --print-agents-exception-draft > /tmp/m34_s1_agents_exception_draft.txt
```

Results:

- helper `py_compile`: pass
- M34 S1 + M34 build tests: 9 passed
- offline check: pass; no device action
- explicit fail-closed check without active `AGENTS.md` exception: rc=1,
  refused before Android/flash actions
- combined M34 S1/M34/M33 regression tests: 20 passed
- exception draft generation: pass; 116-line draft, self-checked against
  `policy_required_markers()`, no device action

## Next

Next live step is M34 S1 only. It needs a fresh SHA-pinned `AGENTS.md`
one-shot exception and explicit operator approval for this exact S1 AP. S2/S3
remain host-only until S1 has a live result.
