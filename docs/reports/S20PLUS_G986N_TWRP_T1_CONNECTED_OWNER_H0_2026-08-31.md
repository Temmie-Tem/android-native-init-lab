# S20+ G986N TWRP T1 connected-owner H0 record

Date: 2026-08-31
Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`
Status: **BINDING ACTIVE AFTER DORMANT AND ACTIVATION-DIFF REVIEW**

## Predecessor evidence

The live T0 terminal is
`NO_PROOF_T0_RETURNED_STOCK_RECOVERY_HEALTHY`. It proves one candidate and one
exact-stock recovery-only Odin transfer, later healthy rooted Android, and the
exact final stock recovery SHA-256
`dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.
It does not prove recovery ADB or TWRP. The consumed T0 candidate is not reused.
The T1 owner mechanically revalidates that complete journal plus the exact
2,188-byte terminal SHA-256
`94a7edbf5607f60cb19eeb3c7f09795682ccecb26a4dc807bed2485263b9e67a`,
pins the T0 owner and H0 base sources, and requires current serial continuity.
Only a sanitized predecessor summary enters host output.

## Exact T1 closure

The candidate is the deterministic IYC2-stock-substrate/AstroForge-V2-ramdisk
recovery-only AP:

- AP: 52,111,401 bytes, SHA-256
  `3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f`;
- sole `recovery.img.lz4`: 52,100,173 bytes, SHA-256
  `f4ccd3fbcd683b5597cf20b028b1230cfb0dd8f4f3c93d3db27c5314834ace7a`;
- decoded recovery: 82,694,144 bytes, SHA-256
  `48406883b1f631c4dfa1b157708f2e320e70b744967024bad6cb50b08cd06cb2`.

The sole rollback is the demonstrated exact-stock recovery-only AP, 36,608,041
bytes at SHA-256
`ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157`.
Neither AP contains another partition member. Donor source reproduction remains
unproved; the exact downloaded bytes and sanitized port are pinned.

## Qualified implementation

The profile
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t1_profile_h0.py`
is 12,843 bytes at SHA-256
`c495deaac141fbbbee8fa9d13501f0e593306fa40127618640615f6a498de5e1`.
It validates the artifact/manifest closure and freezes a root-ADB observer for
TWRP `3.7.1_12-AstroForge_v2`, its donor incremental, ADB-only state, fresh boot
ID, and marker SHA-256
`9e772d73d58740e09abe7f75f30e99c66cda04547287189d859ed457b9c2c6c5`.

The connected owner
`workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t1_f2.py` is
161,745 bytes at SHA-256
`756289617ee4837457a5d1c0357d6a8b78d10d86f4b6822d30a86ed24a174fd0`;
its activation-normalized SHA-256 is
`6ed9fe2ff0cf23f7ff28a2f3cc036cebc97ff48c37228fbac67d3c87cb72ee7a`.
`T1_F2_ACTIVE=true`. The 60,027-byte focused test is SHA-256
`270cea73c3aa943a4ffd49703452644bf8ad32666d9094c7555aca5c9f63720e`.

The owner inherits the reviewed T0 exact-target binding, raw capture, cgroup
quiescence, no-clobber typed journal, one-shot Download/Odin classification,
global candidate claim, physical rollback, and final stock-health machinery.
It changes the candidate/profile namespace and successful terminal: only a
raw-derived completed candidate plus same-serial/topology fresh TWRP marker
observation may publish `PROVED_T1_RECOVERY_RETAINED`. That terminal records one
candidate transfer, zero rollback transfers, and releases the shared guard with
TWRP intentionally retained. It grants no recovery UI action.

Absent/malformed ADB, Android arrival, transfer uncertainty, or endpoint drift
cannot retain by proof and cannot replay the candidate. Those branches converge
only on the attended physical prebound exact-stock rollback and later exact
stock digest. A clean retained terminal closes its run and rollback approval;
later stock restoration requires separately reviewed fresh exact-stock
authority.

## Validation and authority

The focused owner corpus passes 51/51 after adding exact TWRP profile and
retained-terminal tests. Together with the 14/14 deterministic T1 builder suite,
the current T1 corpus passes 65/65. `py_compile`, active render/host validation,
and `git diff --check` pass.

The dormant closure and activation-only diff each received independent
`PASS_GO` before their commits. Activation creates no run or standing approval.
The first permitted live step is a fresh attended `--prepare`; no T1 transfer is
possible until its exact emitted approval is returned before expiry. No T1
prepare, approval, Download entry, Odin invocation, recovery write, or device
command occurred during qualification or activation.
