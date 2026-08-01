# A90 Resident Install V2 H0 Closure

Date: 2026-08-02

Status: **H0 PASS / LIVE NOT AUTHORIZED**

## Outcome

The reviewed A90 F1 whole-owner path now supports an exact
`a90-resident-install-v2` manifest.  It reuses the existing absent-only rootfs
stager, checked `native_init_flash.py` boot-only transfer, durable F1 journal,
and exact V2321 rollback recovery.

After the first candidate boot, the new tail verifies exact candidate identity
and self-test, clean read-only pstore, the manifest-bound rootfs source, and the
exact USB-local NCM path.  It then closes:

`PASS_A90_RESIDENT_INSTALLED / RESIDENT_HEALTHY`

The install mode performs zero resident reboots.  The legacy
`a90-resident-promotion-v1` second-boot path remains unchanged.

## Exact Terminal

The successful install result fixes the following values:

- candidate transfer count: `1`;
- candidate replay: `false`;
- candidate health check count: `1`;
- resident reboot count: `0`;
- rollback transfer count: `0`;
- rollback required: `false`; and
- device safety state: `RESIDENT_HEALTHY`.

Terminal repair accepts only the exact eleven-action success journal from
preflight through candidate health and close.  It rejects a terminal-only
journal, a missing health record, any rollback action in the success sequence,
boolean values substituted for integer counts, incomplete health evidence, or
a rootfs receipt whose command is not the canonical manifest-bound preflight
script.  A crash after the terminal journal but before `result.json`
publication repairs only the result and never rolls back a proven resident.

Before the terminal exists, failures retain the existing pre-authorized exact
rollback path and never retry the candidate.

## Changed Execution Closure

- `a90_v3403_absent_only_staging.py`: mode-specific resident schema selection;
- `a90_v3403_f1_orchestrator.py`: one pure canonical rootfs-preflight script
  builder shared by runtime execution and durable repair validation;
- `a90_resident_promotion_v1.py`: install schema validation, first-health
  terminal, exact result repair, and legacy promotion preservation; and
- `a90_resident_manifest_builder_v1.py`: explicit `--resident-install-v2`
  structural conversion before production-loader validation.

No new flash implementation, transport, retry loop, or device effect was
added.

## Validation

Fifteen related A90 modules were executed in separate Python processes to
avoid the repository's known duplicate-module test-loader identity problem.
The result was `331/331 PASS`.

The execution-critical focused set passed `194/194`:

- absent-only staging: `44/44`;
- F1 orchestrator: `118/118`;
- resident install/promotion: `28/28`; and
- resident manifest builder: `4/4`.

`py_compile` and scoped `git diff --check` passed.  Independent safety review
returned **PASS / GO** after its two Medium findings were fixed.  No review
finding remains.

Reviewed source SHA256 values:

- staging: `d822b09110ca8aa2c73bf95e983b05d5a1511d54f44c297f2ff8fbd0ebc61221`;
- orchestrator: `7c7dbda2f817228e7a044179fe545282388ce11a446abf44b85d66ea6b020451`;
- resident runner: `843ff6d0afde3fc40fa1ef19a3795318f5e16de0a7071f5d087459208a8c6929`;
  and
- manifest builder: `d3e43c4f87a85d98c48729c748b166cc21c1160e16f27f618668d37f84453836`.

## Host-Only Next-Run Preparation

Fresh run `a90-v3406-debian-display-f1-20260802-01` has a new-inode 2 GiB
rootfs and a fresh single-run observer key.  Its clean-base audit, read-only
ext4 check, key ownership/mode check, runtime-path absence checks, and
new-inode check passed.  This preparation contacted no device and grants no
F1 authority.

## Remaining Gates

The next live steps are deliberately not included in this H0 result:

1. exact connected A90 D0 and path-absence preflight;
2. final resident-install-v2 manifest publication from the committed source
   closure;
3. host-only approval receipt preparation; and
4. one fresh exact A90 F1 approval.

Every older resident manifest and approval is stale.  S22+ was untouched.
