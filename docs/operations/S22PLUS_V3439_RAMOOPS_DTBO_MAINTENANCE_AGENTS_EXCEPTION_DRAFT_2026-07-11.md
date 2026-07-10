# INERT DRAFT - S22+ V3439 Corrected Ramoops DTBO Maintenance Exception

This is an inert policy draft. Its presence does not authorize a device action.
The operator approved a future V3439 live run, but this clause becomes active
only after the exact helper is committed and the active text is promoted to
`AGENTS.md`.

Proposed scope:

- proposed active marker: `S22+ V3439 ramoops DTBO maintenance live gate`;
- active-only sentinel: `S22PLUS_V3439_DTBO_POLICY_STATE=ACTIVE`;
- target: Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8`;
- helper:
  `workspace/public/src/scripts/revalidation/s22plus_v3439_ramoops_positive_control_live_gate.py`;
- V3438 postmortem SHA256
  `f5c12e50e01d9b7938a2482f4990a0620f9d7e7cb0fb6837350357af009ec5a4`;
- independent acknowledgement token:
  `S22PLUS-V3439-RAMOOPS-DTBO-MAINTENANCE`;
- exactly one candidate DTBO flash using AP.tar.md5 SHA256
  `622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264`;
- candidate raw DTBO SHA256
  `3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281`;
- exactly one stock DTBO rollback using AP.tar.md5 SHA256
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`;
- stock raw DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- both APs contain exactly one member, `dtbo.img.lz4`;
- known Magisk boot raw SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- required restore acknowledgement token:
  `S22PLUS-V3439-RAMOOPS-STOCK-DTBO-RESTORE`;
- candidate flash is allowed only from verified stock DTBO and normal rooted
  Android;
- the pre-panic gate must require exact parameters,
  `/sys/module/pstore/parameters/backend=ramoops`, and exactly one bound ramoops
  platform device with compatible `ramoops` and status `okay`;
- early dmesg strings are corroborative only and cannot be a hard gate;
- stock rollback remains available from exactly one Android or Odin transport;
- no boot, vendor_boot, recovery, vbmeta, BL, CP, CSC, super, userdata, EFS,
  sec_efs, RPMB, keymaster, modem, bootloader, or other partition write;
- no raw host `dd`, fastboot, Magisk module, multidisabler, or format data;
- no panic, sysrq write, PMIC/GPIO/regulator/GDSC write, or A90 action under
  this exception.

The DTBO maintenance exception alone cannot authorize the intentional panic.
The separate V3439 panic exception must also be active before `--live-session`.
