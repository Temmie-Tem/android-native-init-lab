# INERT DRAFT - S22+ V3437 Ramoops Intentional-Panic Exception

This is an inert policy draft. Its presence does not authorize a device action.
It becomes active only if an operator explicitly approves promotion and the
exact clause is added to `AGENTS.md` as a narrow active exception.

Proposed scope:

- proposed active marker: `S22+ V3437 ramoops intentional-panic live gate`;
- active-only sentinel: `S22PLUS_V3437_PANIC_POLICY_STATE=ACTIVE`;
- target: Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8`;
- helper:
  `workspace/public/src/scripts/revalidation/s22plus_v3437_ramoops_positive_control_live_gate.py`;
- independent acknowledgement token:
  `S22PLUS-V3437-RAMOOPS-INTENTIONAL-PANIC`;
- V3436 contract SHA256
  `f9ff86aa346023f8a168c98cd04bee57e1d69f913c9b4592f40ecfdc9133fec5`;
- candidate raw DTBO SHA256
  `3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281`;
- exactly one `S22RPC1` run-bound marker sequence;
- marker sinks are `/dev/kmsg` and `/dev/pmsg0` only;
- exactly one write of `1` to `/proc/sys/kernel/sysrq` and one write of `c` to
  `/proc/sysrq-trigger` (`sysrq-trigger-c`);
- independent acknowledgement token must be supplied only after patched live
  DT sizes, ramoops module parameters, pstore mount, and backend registration
  have all passed;
- after panic, collect pstore under the still-patched DTBO before stock DTBO
  rollback;
- no repeated panic, no additional sysfs/procfs write, no module insertion,
  no PMIC/GPIO/regulator/GDSC write, no persistent filesystem marker, and no
  A90 action;
- this exception authorizes no partition write; candidate and rollback DTBO
  writes require the separate V3437 DTBO maintenance exception.

The panic exception is one-shot. A failed or returned panic trigger does not
authorize a retry. Manual recovery may be required.
