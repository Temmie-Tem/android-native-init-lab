# V3427 S22+ Transition Selection Host Pass

## Verdict

`PASS; MANUAL RDX/DOWNLOAD + FIRST ROLLBACK BOOT SELECTED; POSITIVE CONTROL NEXT; NO LIVE`.

V3427 selected the least-confounded recoverable transition for the V3426
observer and corrected the negative-result interpretation before live work.

## Verified Inputs

```text
V3426 schema                         s22plus_v3426_phase_observer_design_v2
V3426 contract SHA256                cba82ce1bae23f56bcad57876f5d647e31a37a36d7bc9b477de57b1f85b3babf
V3427 transition SHA256              426aa2bb50f6e73e153f5f5dc9cde59ddf37ab315f46860c1dc0bd0b3e810734
Magisk boot-only rollback AP         exact SHA, one member PASS
stock boot-only fallback AP          exact SHA, one member PASS
Odin4 executable                     PASS
historical recovery reports          5/5 exact SHA and token PASS
```

The historical reports cover repeated manual Download rollback success and M29
Android-origin ring survival. They do not prove direct-PID1-origin survival.

## Independent Review

Claude Opus confirmed that absence must be `NO_PROOF`, because Stage A reach and
transition preservation are not independently observed. It accepted manual
RDX/Download as the least-confounded available transition and confirmed that an
exact fresh PRECHECK+FINAL pair remains conclusive positive evidence.

The review also required first-boot provenance, paired markers, bounded dwell,
quiet post-FINAL park, duplicate EOF reads, truncation handling, and a stock-
origin positive control through the same transition. All are now contract gates.

## Result

```text
V3426 + V3427 focused tests           34/34 PASS
both generated JSON --check           PASS
```

No candidate, helper, exception, device contact, module insertion, reboot, image,
or flash was created or performed. The next bounded unit is the host-only design
of the stock-origin same-transition positive control. Broad approval intent does
not substitute for its future exact SHA-pinned exception and acknowledgement.
