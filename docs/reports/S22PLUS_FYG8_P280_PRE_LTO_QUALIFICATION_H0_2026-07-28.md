# S22+ FYG8 P2.80 Pre-LTO Qualification H0

Date: 2026-07-28 KST

## Scope

Host-only. This unit did not start Full LTO, build a boot image, package an
Odin AP, contact a device, create live authority, reboot, transfer, or write.

## Problem

The build runbook required four gates before Full LTO:

1. exact two-link userspace plus source-contract-specific ELF entrypoints;
2. exact source-contract safety dictionary;
3. generic E3 configfs/libcomposite/ACM QEMU execution; and
4. P2.80 Kprobe ABI plus shared four-plus-six event lifecycle execution.

The gates existed, but `s22plus_fyg8_p234_build.py` did not consume their
receipts. Their order was an operator convention. A build could therefore
start after a missing or stale gate, which is the same late-check class that
previously caused avoidable Full-LTO rebuilds.

The historical P2.60 QEMU result also omitted QEMU identity. Its kernel and
module substrate needed an external pin before it could qualify P2.80.

## Decision

Add one P2.80-specific qualification assembler and verifier. Do not generalize
the complete build substrate in this unit.

The private qualification receipt is accepted only when all of the following
are current and exact:

- selected P2.80 intent, patch, run ID, profile, and source-contract ID;
- deterministic P2.80 implementation and complete source receipts;
- exact userspace result and binary receipts;
- independently derived static ELF entrypoints for `/init` and child;
- complete P2.80 safety dictionary, including tracefs/Kprobe authority;
- exact P2.60 generic E3 QEMU result;
- exact P2.80 one-pair Kprobe QEMU result;
- at least five successful P2.80 shared lifecycle cold runs;
- pinned guest kernel/config and QEMU binary/version;
- pinned compressed and decompressed bytes for all nine generic USB modules;
- qualification, build-wrapper, gate-executor, userspace-builder,
  safety-builder, and entrypoint-closure sources.

Receipt consumption is not a `verified=true` or hash-shape check. The build
wrapper reopens the exact selected intent and patch, recomputes the P2.80
implementation, reopens all four portable gate JSON files, and re-runs their
argv, pin, timing, digest, source-receipt, output-shape, safety, and ELF
entrypoint semantics. Large QEMU material files are verified while assembling
the qualification. Build-host consumption binds the exact accepted gate JSON
receipts and current public executors without requiring the QEMU substrate to
be copied to the build host.

## Build Enforcement

When the selected source contract is P2.80:

- `--pre-lto-qualification` is mandatory;
- an absolute or missing qualification path is rejected;
- stale candidate, source, gate, tool, kernel, module, or implementation
  material is rejected;
- the accepted qualification summary and gate-result receipts are added to
  build provenance; and
- A and B must carry the same normalized qualification identity;
- the reproducibility result carries that identity to candidate packaging; and
- `build_allowed` remains false unless qualification is verified.

Historical source contracts do not require the new argument and retain their
prior path.

## Evidence

- Current run ID: `568abdddae4a0320e14c95aad8bf1e9c`.
- Current patch SHA256:
  `23e2febdd57388efbbca1aa0935f102e06dab165b1f855ca525c5b1a6f2d81b9`.
- Current qualification SHA256:
  `00a7132b5fea8d8f4f0a3b7314d36ca92a272fcc9d96c0bb417b033b77bd9479`.
- Exact userspace two-build verdict:
  `PASS_P280_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY`.
- P2.80 implementation verdict:
  `PASS_P280_DISCRIMINATOR_IMPLEMENTATION_HOST_ONLY`.
- Shared lifecycle result: 5/5 cold QEMU boots passed.
- Shared role phase: about 0.55-0.61 seconds.
- Shared bind phase: about 0.67-0.75 seconds.
- Qualification verdict:
  `PASS_P280_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY`.
- Direct qualification reopening and semantic revalidation passed.
- Wrapper tests prove exact acceptance and missing/stale refusal.
- A/B and candidate-builder tests reject absent or differing provenance.
- Focused implementation, registration, build, and qualification tests:
  178 passed.
- Standalone import ordering, Python compilation, pinned `ruff@0.6.9`, and
  `git diff --check` passed.

The first independent review returned NO-GO because the consumer trusted gate
shapes, QEMU command/timing semantics were incomplete, A/B and packaging did
not require provenance, and executor sources were not bound. All four findings
were reproduced, fixed, and pinned by mutation tests before this evidence was
recorded. A separate circular-import failure was then found by standalone
module loading and removed by deferring the safety-builder import.

The second independent review returned NO-GO because QEMU `command[0]` was not
required to match the pinned identity, an unauthenticated duplicate
`materials` field remained in the receipt, and A/B plus packaging compared a
normalized summary without reopening the selected qualification file. The
command/identity equality is now exact, the duplicate field is absent, and
both downstream consumers reopen and fully revalidate the repository-relative
qualification against the current intent, patch, sources, gates, and safety
contract. Mutation tests cover all three bypasses.

A final re-review found two residual bypasses and one provenance warning:
build-host verification skipped the current QEMU file when large material
verification was disabled, qualification and stored gate objects accepted
extra fields, and downstream selection paths came from the qualification
instead of the caller. The verifier now always opens the canonical pinned
QEMU binary, all qualification and portable-gate roots are closed schemas, and
A/B plus packaging supply and compare the caller-selected repository-relative
intent and patch. The resulting v5 receipt supersedes all earlier receipts.
The closing independent review reran the former passing mutations, six import
orders, and 82 focused tests. It found no remaining MUST-FIX or WARN item and
returned GO for this H0 qualification/provenance closure only.

Generic QEMU proves only the covered generic trace/configfs/gadget mechanics.
It does not prove Qualcomm DWC3-MSM targets, S22+ SCS/PAC behavior, PHY/VBUS,
physical USB enumeration, or live P2.80 evidence.

## Remaining

The duplicated generic QEMU substrate helpers are a maintainability issue, not
a blocker for this exact candidate. Extracting one reusable pinned substrate
is deferred to P2.81 and must not invalidate this candidate during Full-LTO.

After independent review and a scoped commit, the next host-only step is two
clean same-path Full-LTO builds with the exact qualification receipt supplied
to both preflight and build. D0 and F1 remain separate and unauthorized.
