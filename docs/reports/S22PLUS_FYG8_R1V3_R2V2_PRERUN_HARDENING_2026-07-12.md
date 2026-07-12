# S22+ FYG8 R1 v3 / R2 v2 Pre-run Hardening

Date: 2026-07-12 KST  
Scope: host-only implementation and static validation; no SSH, build, image,
device, USB, or flash action

## Result

The FX-8300 clean reproduction is no longer exposed to the three confirmed
pre-run failures found by the independent review:

1. Stock kernel banners now use one canonical extractor in baseline generation,
   R1, and R2. It returns exact ASCII bytes before the first LF or NUL and does
   not strip or normalize whitespace.
2. R1 now requires the pinned stock baseline during preflight and compares one
   exact contiguous banner. Its marker checks remain as diagnostics. R2 uses the
   same extractor and separately requires the PREEMPT marker.
3. The Samsung `_setup_env.sh` timestamp override is patched and restored with
   atomic replacement. Raw-byte hashes, original mode, and original timestamps
   are recorded; the real source file's `0444` mode is supported and restored.
4. The remote runbook now transfers and hashes the shared extractor, stock
   baseline, stock IKCONFIG, and all four module-map inputs before reconstruction
   or build.

## Exact Evidence

- Real FYG8 stock kernel: banner terminator is `LF NUL`; canonical banner length
  is 398 bytes.
- Baseline regeneration remained byte-identical to the pinned file, SHA256
  `3041f6a50c5ac77631c747dc3d21e5fd0ad68a520ffc9a2052b1c0b5976db092`.
- Real source `_setup_env.sh`: mode `0444`, parent directory writable, timestamp
  control preflight verified.
- Runbook's four tool pins and six R2 data pins all passed `sha256sum --check
  --strict` locally.
- All 64 `test_s22plus_fyg8*.py` tests passed.
- `py_compile` passed for the shared extractor, baseline generator, R1 wrapper,
  and R2 auditor; `git diff --check` passed.

`ruff` was not installed on this workstation, so no Ruff result is claimed.

## Remaining Gate

No Full-LTO build was run in this unit. The next bounded action remains the
SHA-pinned FX-8300 clean R1 v3 build followed by R2 v2 only after R1 PASS. No
kernel packaging or device action is authorized.
