# S22+ FYG8 R4W1-B Live NO_PROOF / Magisk Recovery PASS

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

## Outcome

The one-shot candidate AP transferred successfully, but no post-candidate
retained observer was captured. Direct PID1 execution is therefore `NO_PROOF`.
The separately approved recovery-only path restored and verified the exact
Magisk baseline.

```text
live run          workspace/private/runs/s22plus-r4w1b-live-20260719T144807Z
live verdict      FAIL_R4W1B_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED
live result SHA   f59cba9ab1bbc91784327f360abaa91e1680774c994d01c0bc869a07a3cc2ccc
live timeline SHA 2b2b4d9fd3abc42010aa648eb63a9e40934c05e0cc105c81e9b281bcc9245a90
candidate transfer true

recovery run      workspace/private/runs/s22plus-r4w1b-rollback-20260719T145137Z
recovery verdict  PASS_R4W1B_MAGISK_ROLLBACK_FROM_DOWNLOAD
recovery result   8276daece2f5bcf82ef9449ec0a2bcd314667ddb866b3d08be55295be3adfea9
recovery timeline d89c254b374db857e1a62bb6ad70a4fd153c69bec8ab0bec93b3629915a7673f
consumed state    bf38e7794625af386cd4adbba3242c2fe677df87b944e4985c54168dd7d8dbe8
```

## Live Sequence

1. Exact connected PASS and complete offline artifact gates passed.
2. The helper durably created the one-shot consumed state.
3. Exact candidate boot-only AP transfer completed successfully.
4. The first strict disconnect check saw `/dev/bus/usb/002/007` in Odin output
   after the path had disappeared. It classified that endpoint as stale and
   refused raw park.
5. The helper continued to mandatory rollback and polled for normal Download.
6. `/dev/bus/usb/002/008` appeared at the end of the 120-second transition
   window. No confirmation time remained, so no rollback transfer was attempted
   by the live run.

The live timeline contains all canonical eight events with explicit no-action
semantics for rollback. No marker observer exists for the candidate, so neither
candidate boot nor direct PID1 exec is proven.

## Recovery Sequence

After fresh recovery approval, the helper required the valid consumed state and
one Odin endpoint. At the fresh TTY prompt the operator confirmed normal Samsung
Download. The helper re-enumerated the same `/dev/bus/usb/002/008` endpoint and
immediately transferred the exact Magisk boot-only AP.

Odin returned rc=0 and transferred only `boot.img.lz4`. Final health proved:

- exact `SM-S906N/g0q/S906NKSS7FYG8` Android with boot complete and boot animation stopped;
- Magisk `uid=0(root)` and known boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock `vendor_boot`, DTBO, and recovery identities;
- orange verified-boot state;
- no Odin endpoint.

## Interpretation

The candidate write and recovery mechanism worked. The evidence failure was in
host endpoint-transition handling and the shared 120-second wait/confirmation
budget, not a proven candidate boot failure. It also cannot be used as evidence
that the candidate booted or that `/init` executed.

## Policy

```text
S22PLUS_FYG8_R4W1B_POLICY_STATE=RETIRED
candidate consumed=true
candidate rerun authorized=false
live policy_active=false
```

The connected policy remains present for evidence validation, but its preflight
rejects the consumed candidate state. No further R4W1-B device action is
authorized.
