# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: get_intermediate_timeout

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-get_intermediate_timeout-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-get-intermediate-timeout-20260701T052423Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-get-intermediate-timeout-20260701T052423Z/timeline.json`

## Target

`get_intermediate_timeout(void)` was selected as a post-saturation state
getter rather than another generic lib/time helper. The explicit
source-backed advisory sweep found it as a no-argument scalar getter in the
NCM/Knox networking header, while nearby apparent candidates stayed parked:

- `get_debug_reset_header`: allocates, reads a debug partition, prints, and frees.
- `get_empty_filp`: allocates a `struct file` and reaches credential/security/RCU paths.
- `get_dump_page`: reaches `__get_user_pages`.

Trusted contract:

- No arguments.
- The function reads NCM intermediate-timeout global state and returns an
  `unsigned int`.
- Valid proof results are stable across the short repeat and in
  `0..0xffffffff`.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `get_intermediate_timeout=0xffffff80099a5ff4`.
- Resolution: `export-recovery`, C1 verified; map agrees with recovered export.
- Source declaration: `extern unsigned int get_intermediate_timeout(void)` at
  `include/net/ncm.h:140`.
- ABI: no pointer arguments.
- C1 safety tier after seeding: `SAFE-SCALAR`, no required pointer args.
- Direct BL xrefs: `4`.
- Next-symbol boundary: `knox_collect_conntrack_data` at `+0x10`.
- Static word checks pinned the complete leaf body plus guard:
  `0x90010268`, `0xb9495100`, `0xd65f03c0`, `0x00be7bad`.

## Live Run

Flash gate:

- Fallback images `v2237` and `v48`, v2321 rollback image, and TWRP recovery
  artifacts were present before flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py --from-native`; pushed-image SHA
  and boot readback SHA both matched the candidate SHA.
- Candidate helper `version/status` verification passed after reboot.

Observed public values:

| Case | Return | Result |
| --- | ---: | --- |
| read 1 | `0x0` | PASS |
| read 2 | `0x0` | PASS |

Both reads were stable and in the `unsigned int` timeout range. The target
returned normally through the REPL, and the proof path kept raw runtime
pointers and the KASLR slide in private evidence only.

Health and rollback:

- Initial candidate explicit `hide` overlapped with the live proof because of
  a host-side parallel command mistake and hit serial `AT` framing noise;
  `selftest` still passed.
- Post-proof health was rerun sequentially and passed:
  `hide=0`, `selftest=0`, `status=0`; status reported `selftest pass=11
  warn=1 fail=0` and `pstore entries=0`.
- Rollback to `boot_linux_v2321_usb_clean_identity_rodata.img` used
  `native_init_flash.py --from-native`; pushed-image SHA and boot readback SHA
  matched the v2321 SHA.
- Final explicit health first hit serial `ATAT` framing noise on `version`,
  while `selftest/status` passed. A `hide` plus short settle retry then passed
  `version/selftest/status`, with resident
  `v2321-usb-clean-identity-rodata` and `selftest pass=11 warn=1 fail=0`.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-get-intermediate-timeout-20260701T052423Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `65.532s` |
| candidate flash start to boot ready | `66s` |
| candidate explicit health initial | `14s` |
| live call-proof | `14s` |
| post-proof candidate health | `4s` |
| rollback flash helper total | `64.278s` |
| rollback flash start to boot ready | `64s` |
| final health initial | `11s` |
| final health retry | `4s` |
| candidate start to final health done | `211s` |

Notes:

- The candidate explicit health initial phase and live proof overlapped due to
  host-side parallel command dispatch. The trusted health gate is the later
  sequential post-proof health pass plus clean rollback/final health.
- No post-proof `busybox dmesg` log probe was run; normal REPL return, clean
  selftest/status, pstore inventory, and rollback are the side-effect/oops
  gates for this proof.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map get_intermediate_timeout --no-objdump`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.CallSafetyClassificationTests`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_intermediate_timeout_passes_with_no_arg_timeout_contract`

Results:

- `py_compile`: PASS.
- Static classifier: `get_intermediate_timeout` is `SAFE-SCALAR`,
  `export-recovery`, `0xffffff80099a5ff4`.
- `CallSafetyClassificationTests`: `Ran 13 tests`, `OK`.
- Focused fake-live proof test: `Ran 1 test`, `OK`.

## Function Map Entry

`get_intermediate_timeout` is live-proven under exactly this contract:

- No arguments.
- The current image body is the pinned `adrp; ldr w0; ret` leaf global-load.
- The return value is a stable `unsigned int` in `0..0xffffffff`; this run
  observed `0x0` twice.

This proof does not authorize neighboring NCM/Knox helpers, debug partition
readers, file allocators, user-page walkers, mass calls, or relaxing the C1
fail-closed identity/safety gate.
