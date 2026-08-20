# A90 boot-only F1 owner reuse hardening context

> **HISTORICAL 2026-08-20.** This evidence describes the retired sealed-package
> owner. The active H0 replacement is
> `docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md`.

Analysis date: 2026-08-20
Target revision: `2a5ec435dc3203fd78a55b3ab33440bedd785590`
Scope: A90 public host-only owner, contract, observation, helper, and policy
Device/private/USB/network/other-target contact: 0

The evidence collection is framed as the concatenation of
`path NUL decimal-size NUL lowercase-sha256 LF` in the order below.
Collection SHA256:
`4e0f73012dbb9b92fefca94780ab4c7f1660a0ad9ff0cb54d42e8e483f57692c`.

| ID | Reader-facing evidence | Bytes | SHA256 |
| --- | --- | ---: | --- |
| E01 | Repository F1 invariants (`AGENTS.md`) | 17,014 | `6cd7e24235396089baab844b0e568a93fb82528bf7fc6cb6c5cfc62d83ef0793` |
| E02 | A90 current goal (`GOAL_A90.md`) | 33,404 | `1dd57bc42b6a93f1bbba33c36a6ceb78e8c6beb13f7673ca3e1e508c73b04fb7` |
| E03 | A90 binding target contract | 89,405 | `ed9f51212db33bd822dc96ecf12feeda05ce255d088c402c4742851d173fad51` |
| E04 | Current reusable-owner structural design | 41,746 | `fc060503d110be5d3025308c05a5a6ae6c296fd5139e6b0dd7d4bf1f8479d94a` |
| E05 | Current owner implementation | 62,330 | `90ed3c6b129660d05e19ae82f111d690176cb970be678bfe9c8a8c79f1670970` |
| E06 | Owner contract implementation | 41,787 | `4b79728d72f97fdfeb0efaba694653769419b708718bc5e349fb38f5a9f184d4` |
| E07 | Serial observation implementation | 17,467 | `d9debb1eb1ff738f3e2f0fe1eb485f3a3d47588cfdcdbfdd1dc5226a2d54d7c3` |
| E08 | Host runtime qualification generator | 16,892 | `684d2b9a012da656a069c9771a1836491a92c9886bbdb5fd4b543db3e0ca0817` |
| E09 | Stored runtime qualification | 49,587 | `b28cf3c16c056a6fba2db104327d57aee9667d2a2bdb89801e523db0473a5aed` |
| E10 | Owner focused tests | 63,951 | `efc1bb3b815188d8469405631f1d9804fd2300190c113bc770d345512d6c92a6` |
| E11 | Four-command bootstrap | 6,283 | `8234a2589c75cf466a359fbd9738d5b1c27c8ccdf700a8ed1822904dba45c590` |
| E12 | Existing native-to-recovery flash helper | 43,118 | `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53` |

## Source-backed observations

- E01 requires a known healthy start, exact candidate and rollback, a fresh
  journal, candidate no-replay, immediate rollback, and bounded final health.
  It does not require tests, reports, or the complete host stdlib tree to be
  part of the execution closure.
- E05 includes `tests/test_a90_boot_only_f1_owner_v1.py` in
  `owner_source_closure()`. E06 additionally binds resident, recovery, runtime,
  and hazard qualifications to the owner closure.
- E05 implements a persistent ten-source staging tree and four fresh command
  subprocesses. E12 already owns the A90-specific device flow: serial recovery
  request, recovery ADB wait, push/hash/boot write/readback, reboot, and serial
  native-init verification.
- On 2026-08-20 the two focused owner modules ran 76 tests with one failure.
  The owner closure matched the stored receipt, but regenerated Python runtime
  qualification differed in `runtimeRoots`, `dynamicLibraries`, and its
  aggregate digest. This is measured host-runtime drift, not a device result.

This focused run is evidence `E13` — **Owner runtime qualification drift
fixture**. It is derived from E09 (stored runtime qualification) and E10
(focused tests); it created no repository artifact and is not an additional
collection member.

## Threat and reliability boundary

The design must resist wrong-target selection, stale or substituted artifacts,
malformed candidate data, host interruption, duplicate dispatch, and lost
reporting after a device effect. Root and a malicious concurrent process under
the same invoking UID remain outside this lane; attempting to isolate from
that actor with more same-UID Python files does not create a new trust boundary.

## Limitation

This is a host-only structural analysis. It does not validate a live recovery
ADB serial, perform an F1, qualify a candidate, or prove performance. Timing and
resource effects are therefore source-derived or hypothetical unless explicitly
identified as the focused-test result above.
