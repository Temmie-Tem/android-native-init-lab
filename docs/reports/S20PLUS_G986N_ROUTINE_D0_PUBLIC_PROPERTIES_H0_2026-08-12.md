# S20+ G986N Routine D0 Public-Property Capability - H0 Review Record

Date: 2026-08-12

Status: **PASS_GO - ROUTINE D0 ACTIVATED**

## Objective

Add a reusable, proportionate D0 path for direct operator-requested public
property reads from the exact operator-owned `SM-G986N` / `y2q` /
`G986NKSS8IYC2` target. The first requested question is its Samsung CSC/OMC
sales code. This capability is intentionally separate from the consumed
one-shot onboarding inventory.

## Closure

- Runner:
  `workspace/public/src/scripts/revalidation/s20plus_g986n_routine_d0.py`
- Focused tests: `tests/test_s20plus_g986n_routine_d0.py`
- Exact target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`
- Fixed host tool: reviewed `/usr/bin/adb` canonical realpath and SHA-256 from
  the existing onboarding runner
- Per invocation: four bounded host commands, two exact-target reads, two
  inventories, and zero commands to S22+, A90, or another target
- Evidence: no-clobber private result/failure receipt; serials and USB topology
  only as SHA-256 digests

The snapshot reads only fixed public identity, boot-health, verified-boot, and
Samsung CSC/OMC properties. Carrier resolution preserves `NO_PROOF` and
`CONFLICT` rather than guessing. The runner has no arbitrary ADB path, command,
property, shell fragment, retry, write, root, reboot, mode transition, transfer,
partition, package-list, or `/efs` surface.

## Isolation From Consumed Onboarding

The original onboarding runner, result, and durable active-intent guard remain
unchanged and consumed. The routine process neither opens nor rotates that
guard. Routine failure closes only that read invocation; a later read requires
a new direct operator request and re-runs exact identity selection from the
start.

## H0 Validation

- `python3 -m py_compile` for the runner and focused test: PASS
- Initial independent review found that the first draft selected the model
  before requiring exact device/product metadata. The runner now rejects any
  partial, wrong, offline, duplicated, conflicting, or mixed plausible target
  row before its first selected-target command.
- `python3 -m unittest -v tests.test_s20plus_g986n_routine_d0`: 13/13 PASS
- Device, ADB, USB, reboot, transfer, and partition commands during H0: zero

## Activation Gate

Independent review initially found one High exact-selection defect: a wrong
device/product row sharing the expected model could receive selected-target
reads before rejection. The routine-specific selector and negative corpus
above remedied it. Re-review returned `PASS_GO` with no unresolved finding for
the runner, tests, contract, registry transition, and activation wording.

Reviewed routine runner SHA-256:
`2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c`.
The exact registry row and binding routine status are active. This qualifies
only fixed exact-target routine D0 public-property reads under a current direct
operator request; it grants no D1, F1, root, reboot, transfer, or partition
authority.

Independent reviewer device/ADB/USB commands, private-evidence reads, and file
modifications: zero.

## First Live Use

The first connected invocation after activation closed after its initial
global inventory because the exact healthy target row was unavailable. It sent
zero selected-target, S22+, A90, or other-target commands and made no device
change. Its private failure receipt SHA-256 is
`65dfcaf52ddbec2c71bbd52f79f694565f6cd1385d92a6af9c9843cb94f22363`.
It was not automatically retried.

After the operator reported the device reconnected, that new direct request
authorized a new routine invocation. It returned
`PASS_S20PLUS_G986N_ROUTINE_D0_READ_ONLY` for exact
`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2` with four bounded host
invocations: two global inventories, two selected S20+ reads, and zero S22+,
A90, or other-target commands. All write, root, reboot, mode-transition,
payload-transfer, and partition-access flags were false. Private result
SHA-256:
`5c1825b643f1745c6ed0c84b19cf4cce0246b20c4e3eb60cdb8e6047d03ba04f`.

The public properties have role-specific evidence:

- `boot_sales_code=KTC`
- `csc_sales_code=KTC`
- `omcnw_code=KTC`
- `omc_path=/optics/configs/carriers/KTC/conf`
- `omc_etcpath=/prism/etc/carriers/KTC`
- `carrier_id=KOO`

The runner therefore preserved its aggregate resolution as `CONFLICT` instead
of guessing one unqualified CSC. The narrower evidence supports current
sales/OMC configuration `KTC` and a distinct boot carrier ID `KOO`.
