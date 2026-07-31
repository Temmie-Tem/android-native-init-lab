# A90 Observation Pipeline Phase 0 H0

Date: 2026-07-31
Decision: `A90_OBSERVATION_PIPELINE_PHASE0_H0_PASS`

Independent verdict: GO
Unresolved CRITICAL: 0
Unresolved HIGH: 0
Unresolved MEDIUM: 0
Device actions: none
Review decision: `GO_A90_OBSERVATION_PIPELINE_PHASE0`

## Result

The active A90 observation path now uses one byte-aware implementation for
line decoding, A90P1 framing, display marker validation, and independent fact
classification. The implementation preserves LF/CRLF and byte offsets,
rejects invalid UTF-8, bare CR, NUL, unterminated BEGIN/END, noncanonical field
sets or order, duplicate fields, mismatched sequence/command/flags, and
noncanonical rc/errno/status combinations.

Successful `switch-root-to-distro` remains the one explicit no-END protocol
transition. The caller must opt in to that command; ordinary nested BEGIN and
unfinished frames remain errors. Historical private raw logs replay as 18/18
PASS with 230 complete frames and two explicit one-way transitions.

`a90ctl.py` now consumes the shared strict parser instead of selecting the last
regex-shaped END line. Strict UTF-8 decoding occurs at the bridge byte boundary.
The structural trust grade `A90P1_V1_STRUCTURAL_ONLY` survives through the
server-distro command wrapper. This does not claim authenticity against an
exact F016 frame forgery; it makes that protocol-v1 limit machine-visible.

The Phase 2 display observer now classifies native release, Debian PID 1,
Dropbear, and display acquisition independently. A malformed, ambiguous, or
timed-out display marker no longer erases valid PID1, Dropbear, or native
release facts. D3 marker and Dropbear evidence require exact unique lines.
Atomic display PASS still requires every required fact; partial evidence
remains `NO_PROOF` and cannot preempt rollback.

The finalizer no longer accepts an unrelated historical GO report. It requires
one exact, noncontradictory GO status block and exact unique current hashes for
all nine execution-review sources below.

## Reviewed execution sources

- `workspace/public/src/scripts/revalidation/a90_observation_pipeline.py`: `4e43d16e3dc5b2ef7509fa0432e1bebc9629ab77099206d95138af54dcbd7e08`
- `workspace/public/src/scripts/revalidation/a90ctl.py`: `11c567c5ec4d7b95dfbe0409af1759a90087eb937e47ce627b21511316d5766d`
- `workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py`: `9cc66229526217b162cb4be112a13f708b7ffb6ea435d008c77c777f011de933`
- `workspace/public/src/scripts/server-distro/a90_phase2c_display_packet.py`: `7061ae1d354fe972edae2b9b616754618a1f2d843e0c93a08134e0509b947a47`
- `workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py`: `6b9720ca2e53f0fbed6efe9208b54739fa7f57df84c7a72ab61940f104ff7744`
- `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`: `2a25b07c83018fc576980b6c28f4be05b022c6a7a8826c007a7905e4048ba323`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`: `5e839d1b5d8c461e39400502a870e28164d3b387ea2b3550e1b2d1cc23e738ac`
- `workspace/public/src/scripts/server-distro/phase2c_display_packet_v1/contract.toml`: `1a5720ee410850f9550ff1b13fa20235541176a30c6b5f905de395b21c80fe2c`
- `workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py`: `54674590b336880567b59c6b8186aff21b3f67e5f8d717c89835ec225fc44352`

## Validation

- focused A90 host regression: 185/185 PASS
- current strict private replay: 18/18 PASS, 230 frames, two one-way transitions
- redacted V3406 CRLF fixture: PASS
- touched Python `py_compile`: PASS
- tracked diff whitespace: PASS
- independent safety review: GO, no unresolved Critical, High, or Medium

The private corpus catalog remains mode 0600 under `workspace/private/runs/`.
The tracked fixture contains allowlisted mechanical fields only; no target
identifier, address, credential, or raw private log is included.

## Remaining bounded work

The next H0 unit is return-channel and presenter diagnosis. The three preserved
V3404-V3406 observations reached the same missing-END boundary after roughly
220-228 seconds. Source inspection shows the attended return observer can see
the still-present USB bridge during Debian, immediately start one long native
menu command, and abort on its missing END. Therefore those records do not
prove a supervisor or global-sync delay. That observer must distinguish bridge
presence from a valid native A90P1 epoch before another F1.

Presenter attempt 3 still records only generic rc=1. The presenter source has
multiple rc=1 exits and does not read backlight state, so the black screen does
not identify DRM-master, connector, SETCRTC, or panel/backlight failure. The
next rootfs observation contract must retain the exact presenter log and
read-only DRM/backlight/connector inventory before selecting a fix.

Nonblocking Low follow-up remains monotonic receive-chunk persistence and
per-fact byte spans. Neither item grants live authority.

## Authority

This was H0 only. No device was contacted, no rootfs was staged, no boot image
was transferred, and no approval was created or consumed. S22+ sources and
devices were outside this unit.
