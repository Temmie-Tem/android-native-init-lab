# S22+ FYG8 R1 v3 / R2 v2 Clean Reproduction

Date: 2026-07-12 KST  
Remote: Debian 13 FX-8300, `<BUILD_HOST>`  
Scope: host-only clean Full-LTO build and static audit; no image packaging,
USB, device contact, or flash action

## Verdict

`PASS_R1V3_FULL_LTO_REPRODUCIBLE_AND_R2V2_STATIC_CLOSED`

The separately reconstructed `source-clean-final` tree passed the R1 v3
preflight, completed one Full-LTO build without incremental repair, and passed
R2 v2 with the exact FYG8 Linux banner and complete module-consumer CRC closure.

## R1 v3

- Result JSON: 680,172 bytes, SHA256
  `448f024b9c0d99fcac02cbc6a858a227ca5cb290a44f0616621542994b329c6f`.
- Source overlay: 166,037 members, exact resident match.
- Build return: `0`; `r1_buildability_pass=true`.
- Exact canonical banner: 398 bytes, full pinned FYG8 equality PASS.
- Unpatched `Image`: 41,490,944 bytes, SHA256
  `9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d`.
- Required outputs: 8/8; generated modules: 2,397; symvers paths: 15.
- `dataipa` and `datarmnet_shs` provider closures: PASS.
- Timestamp control: applied once, patched content unchanged, original bytes
  and mode `0444` restored.
- Elapsed: 33:47.58; peak RSS: 24,252,508 KiB; swaps: 0.

## R2 v2

- Result JSON: 6,756 bytes, SHA256
  `ee935a523270b45c93d2db3e1f21d32b2bf49f3a96965efe5d8df66515964392`.
- `r2_static_pass=true`; blockers: 0.
- Exact banner, release, compiler, PREEMPT marker, Full-LTO config: PASS.
- Config delta: one allowlisted absolute
  `CONFIG_UNUSED_KSYMS_WHITELIST` path only.
- Requirement rows: 25,864/25,864 matched over 4,619 required symbols.
- Provider symbols: 10,511; missing: 0; mismatched: 0; conflicts: 0.
- Vendor-ramdisk shape: 441; complete on-disk corpus: 491; PASS.
- Stock boot-capacity gate: PASS.

## Evidence Return

The complete R1/R2 records and logs were copied to:

- `workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/remote-fx8300-r1-v3-clean/`
- `workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/remote-fx8300-r2-v2-clean/`

The R3-operational set was copied with all 15 symvers path identities preserved:

- `workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/remote-fx8300-r1-v3-operational/`

All remote/local evidence-file SHA maps matched. All 19 operational file
identities matched the size and SHA256 values pinned in the R1 result.

R2 v2 was then rerun locally with the returned `Image`, `.config`, and all 15
explicit local symvers paths. It passed with blocker 0 and matched every
load-bearing remote result value. The path-remapped local result is 8,430 bytes,
SHA256
`34702b79cdf87e9d708ea72772355859c0590f51e4b8924c4aa2c2fcb82568a7`,
under `remote-fx8300-r2-v2-local-reaudit/result.json`.

## Boundary

This closes the host R1/R2 prerequisite only. No boot image, Odin AP, candidate,
or live authorization was created. R3 still requires the separately reviewed
artifact/static checker, exact artifact pins, a narrow `AGENTS.md` exception,
and fresh attended operator approval before any device action.
