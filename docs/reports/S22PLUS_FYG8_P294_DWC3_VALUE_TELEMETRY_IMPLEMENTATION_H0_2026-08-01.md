# P2.94 DWC3 value telemetry implementation H0

Date: 2026-08-01

Verdict: `PASS_P294_DWC3_VALUE_TELEMETRY_IMPLEMENTATION_HOST_ONLY`

P2.94 implements the closed two-slot successor design without changing the
45-byte retained record ABI or its two-slot capacity. Generation 106 is the
16-value USBLNKST progress record and generation 107 is the adjacent terminal
record. The terminal record has 132 conditional UDC-state/speed, COREIDLE, and
SUSPHY values. Fifteen exact fixed-precondition masks and two contradiction
details preserve noncanonical RUN_STOP, DEVCTRLHLT, PRTCAP, VBUS-valid, UDC,
and CONNECTSPD evidence.

The normal path spends no terminal tuple capacity on the already-proven power
helper and direct-run-stop values. Deviations from those preconditions fail
before final sampling. The generated runtime publishes the A/B pair through
one helper with no intervening publication call. Its source adjacency audit,
repository-module API audit, and the runtime C classifier versus Python SoT
closure all pass.

Host evidence:

- 103 Tier-1 source keys are selected; verifier, decoder, tests, and reports
  remain outside payload identity and are approval-bundle inputs.
- the generated candidate patch changes exactly five pinned source files and
  cleanly applies to the exact P2.90 source reference;
- two independent AArch64 userspace links are byte-identical;
- the C classifier and Python SoT agree over all 64,512 raw register states and
  produce exactly 149 terminal details;
- the production linked-validator harness checks 7,077,888
  generation/stage/item pairs and accepts exactly the declared 107 positions;
- the generated patch SHA256 is
  `e9a607e8e9e8b35fcbb9ea21e9145418efd1e2544c8101a55f481a8d23b7da5e`.

The gate set is closed for this successor. A new gate is not added unless at
least two actual occurrences of the same failure class are cited; otherwise
implementation proceeds. P2.94 has not derived an intent, run Full-LTO,
created a candidate or manifest, contacted a device, or received live
authority.
