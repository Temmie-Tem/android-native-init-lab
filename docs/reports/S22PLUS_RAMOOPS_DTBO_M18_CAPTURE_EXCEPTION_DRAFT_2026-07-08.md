# S22+ Ramoops DTBO + M18 Capture Exception Draft (2026-07-08)

## Scope

Host-only policy-prep. No device action, no reboot, no flash, no partition
write, and no edit to `AGENTS.md`.

The active safety contract still does not authorize the `dtbo` write or the M18
capture live run. This unit prepares the exact exception text for operator
review without activating it.

## Added

`docs/operations/S22PLUS_RAMOOPS_DTBO_M18_CAPTURE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`

The draft is copyable into `AGENTS.md` only after explicit operator
authorization. It covers exactly:

- patched DTBO AP SHA
  `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`;
- stock DTBO rollback AP SHA
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`;
- patched raw DTBO SHA
  `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`;
- stock raw DTBO SHA
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- M18 AP SHA
  `9382f91bf2cd3235410368ca08208b9343d8584da48c29b25c46a931b1f42805`;
- M18 boot SHA
  `a99a09fa062d1aaa848a41037c649a43abc983f177714dfc24c39d0df4d84083`;
- known-booting Magisk base boot SHA
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- Magisk boot rollback and stock boot fallback APs;
- the three ack tokens used by the gate helper;
- the patched-DTBO AVB digest caveat under disabled-vbmeta/orange state;
- attended boot rollback, pstore collection, and stock DTBO restore.

## Validation

The draft was checked against the exact marker list required by
`s22plus_ramoops_dtbo_m18_capture_live_gate.py`.

```text
required_count=19
missing=[]
```

The capture helper remains fail-closed today: because `AGENTS.md` was not edited,
default dry-run/live still stops on missing authorization markers before Android
or device action.

## Next

Only after explicit operator authorization, copy the reviewed exception block
from the operations draft into `AGENTS.md`, then rerun the existing capture gate
default dry-run. It should progress past the policy marker check and into normal
Android preflight, without flashing unless `--live --ack
S22PLUS-RAMOOPS-DTBO-M18-CAPTURE-LIVE-GATE` is also supplied.
