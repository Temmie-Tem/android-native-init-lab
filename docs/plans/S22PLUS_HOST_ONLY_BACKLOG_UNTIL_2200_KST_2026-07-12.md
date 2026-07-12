# S22+ Host-Only Backlog Until 22:00 KST

Date: 2026-07-12 KST  
Planning window: approximately 17:55-22:00 KST  
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`

## Scope

This is the ranked work list for the operator-away window. It permits only
host-side inspection, documentation, deterministic rebuilds, and static
validation. It does not authorize device contact, boot-image packaging,
ramdisk replacement, AP generation, flashing, rebooting, or live testing.

Current baseline:

- R0 reproducible environment: PASS.
- R1 unchanged Full-LTO buildability: PASS.
- R2 static stock-equivalence: PASS.
- R3 unpatched rebuilt-kernel viability: pending artifact design, fresh policy,
  and explicit operator approval.
- Lane W reboot-reason producer control: host design complete; implementation
  remains outside the current authorization.

## Ranked Backlog

| Rank | Work unit | Estimate | Unattended | Deliverable and exit condition |
|---|---|---:|---|---|
| P0 | Final-wrapper clean one-shot R1/R2 reproduction on the FX-8300 host | 45-70 min | Yes | Start from the pinned reconstructed source and an empty generated output directory. Run the final committed wrapper without the incremental repair sequence, then run R2 with no ad-hoc arguments. PASS only if the R1/R2 schema, release, config, provider closure, output set, and hashes agree with the canonical close or any difference is fully explained. |
| P0 | Minimal evidence-retention audit | 30-45 min | Yes | Produce a SHA256 manifest and retention table for `Image`, `Image.lz4`, `System.map`, generated `.config`, 15 symvers files, result JSON, preflight, timing, and provider logs. Record what remains remote-only. Do not copy the full approximately 8 GiB output tree or delete anything. |
| P0 | R3 host-only artifact and policy design packet | 60-90 min | Yes, design only | Select and pin the unpatched R2 kernel input and stock-userspace carrier; document exact future repack parameters, partition-size checks, stale copied-vbmeta caveat, boot-only AP membership rule, health milestones, mandatory rollback pins, timeline schema, and fail-closed classifications. No image or AP may be generated. |
| P1 | R3 independent pre-live static gate contract | 30-45 min | Yes, design only | Specify a checker that will later prove exact kernel/config/release hashes, carrier provenance, boot-size bounds, one-member `boot.img.lz4` AP policy, stock DTBO/recovery preservation, rollback availability, and the eight-event timeline. Stop before implementing a live helper or activating an `AGENTS.md` exception. |
| P1 | Build phase and ETA instrumentation design | 30-45 min | Yes | Map the wrapper into GKI compile, Full-LTO link, vendor/external module, dist-refresh, and R2 phases. Define machine-readable phase timestamps, peak RSS/swap, object/module counts, and ETA based on the completed FX-8300 run. This is host tooling only. |
| P1 | Remote build storage and cleanup policy | 15-25 min | Yes, read-only | Inventory the approximately 8 GiB remote `source/out` tree and failed/intermediate outputs. Classify canonical evidence, reproducible cache, and disposable output. Do not delete until the operator approves the proposed set. |
| P2 | Lane W 15-module static readiness cross-check | 60-120 min | Partially | Re-check module hashes, dependency ordering, provider barriers, bindings, and readiness predicates against the R1/R2 outputs and exact FYG8 source. A review report is allowed. Source implementation, payload build, ramdisk work, and candidate generation require a separately opened unit. |
| P2 | Split compile/link feasibility note | 45-60 min | Yes | Compare a faster-host compile plus FX-8300 Full-LTO-link workflow against the measured 33-minute clean build. Cover absolute path parity, toolchain identity, generated-file ordering, mtimes, transport cost, and reproducibility. Default conclusion should remain one-host build unless the expected saving justifies the added state transfer. |
| P3 | R3B DEFEX/PROCA locator-only audit | 45-75 min | Yes, deferred | Locate the two known Magisk patch ranges in the rebuilt kernel and test uniqueness without changing bytes. This cannot promote R3B and should run only after higher-priority R3 work because R3B remains contingent on R3 and demonstrated need. |
| P3 | Retained-witness and bootloader residual-unknown review | 90-180 min | Yes, low priority | Narrow dynamic ramoops base/header validity and reset-path preservation unknowns from existing stock images and logs. Record only evidence-backed hypotheses; do not let this displace the R3 viability path. |

## Recommended Four-Hour Sequence

1. Correct active-frontier documentation and pin this backlog: 15-25 minutes.
2. Run the clean one-shot final-wrapper R1/R2 reproduction: 45-70 minutes.
3. Audit and manifest the minimal retained evidence: 30-45 minutes.
4. Write the R3 artifact/policy design packet: 60-90 minutes.
5. Use remaining time for either ETA instrumentation or the Lane W static
   cross-check, then commit host-only results: 30-60 minutes.

This order first removes the residual reproducibility caveat, then preserves the
proof compactly, and only then advances toward the next live rung.

## Operator-Return Decisions

The following decisions should wait for the operator:

1. Whether a successful clean one-shot run replaces the current R1/R2 result as
   the canonical evidence set.
2. Whether to retain or copy the large remote `vmlinux` and full generated
   module tree, rather than only the minimal pinned evidence.
3. Whether to authorize R3 artifact implementation and boot-only packaging
   after reviewing the host-only design packet.
4. Whether to open Lane W source implementation as a separate bounded unit.
5. Which of R3 or Lane W receives the next fresh one-shot live-policy design.

## Hard Stops

- No S22+ or A90 device contact.
- No candidate kernel modification, ramdisk replacement, boot image, LZ4 boot
  member, Odin AP, or flash helper generation.
- No `AGENTS.md` live exception activation while the operator is away.
- No deletion of remote or local build evidence.
- No security-config change, R3B patch application, or witness patch.
- Any unexpected R1/R2 hash or schema difference is evidence to investigate,
  not permission to normalize or overwrite the canonical result.

