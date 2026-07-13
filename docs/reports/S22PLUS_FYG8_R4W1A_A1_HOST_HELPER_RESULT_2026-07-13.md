# S22+ FYG8 R4W1-A A1 Host Helper Result

Date: 2026-07-13 KST
Scope: host-only implementation and static validation
Device contact: none
Flash or device write: none

## Verdict

`PASS_R4W1A_LIVE_HELPER_OFFLINE_CHECK`

The R4W1-A A1 live helper is implemented and passes its complete offline
artifact gate. It is ready for a separate independent source/policy review and,
after fresh approval, the connected read-only identity dry-run. It is not
live-ready: binding `AGENTS.md` contains neither the oracle-dry nor candidate
ACTIVE sentinel, no connected dry-run occurred, the real FYG8 streamed ZIP
shape remains unverified, and no device action is authorized by this result.

## Implemented Modes

The new helper
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py`
separates five modes:

| Mode | Device effect | Current state |
| --- | --- | --- |
| `--offline-check` | none | implemented and PASS |
| `--connected-dry-run` | read-only | implemented; fresh acknowledgement required; not run |
| `--oracle-dry-run` | one temporary `/bugreports` ZIP plus exact cleanup | implemented; policy inactive |
| `--live` | one boot-only candidate plus mandatory rollback | implemented; policy inactive |
| `--rollback-from-download` | boot-only recovery for an already-started run | implemented; policy inactive |

The connected mode has a separate acknowledgement so an accidental invocation
cannot contact the device. Oracle and candidate modes require distinct exact
whole-line ACTIVE sentinels in binding policy and exact source pins before any
device contact.

## Artifact And Dependency Pins

| Item | SHA256 |
| --- | --- |
| helper | `6dcf003c2c0ef186e4001af44da8cc526014d1704c8b25d7ba04788afd9ca577` |
| focused tests | `c6b650024db29ad97919e3896d19693efca365bb05f5da27031518e2e73e78dd` |
| inactive policy draft | `a444cfd23c51cf237c8e05ee1c427b51f484bb5b808549222dcb3fd08c8b262e` |
| candidate raw boot | `a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133` |
| candidate AP | `cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895` |
| R4W1 Image | `9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c` |
| static checker | `cb2fb233370463135d6f8a26c2fbd93fb3404c973aa5b326a94c6ec149c2f711` |
| exact checker result | `fc528ba9c8acce18a636d398a13add42a7882e7bfd505e82d63ff861e0963a0b` |
| marker oracle | `bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462` |
| oracle audit | `f243191c985caf918a2a4504be349fdaa133c10b75caab973c71b1e31c1610dd` |
| reviewed R3 common source | `f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4` |
| reviewed Odin primitive source | `1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305` |

The offline helper reran the independent three-reproduction static checker.
The 29.73-second rerun used 927,796 KiB maximum RSS and reproduced the exact
existing result SHA256 above with verdict
`PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`.

## Oracle Side-Effect Contract

The implementation does not treat `bugreportz -s` as read-only. It inventories
all direct `/bugreports` entries through non-root shell before and after the
single capture. Preexisting entries must remain byte-identity metadata stable.
Exactly one strict regular file must appear, and its size and SHA256 must equal
the complete bounded host stream before deletion is permitted.

Cleanup rechecks the exact path, non-symlink regular-file state, device/inode/
size/mtime/mode tuple, and SHA256. It never uses a wildcard, recursive delete,
or root. Parser failure after an exact content match still permits exact
cleanup. Multiple, unsafe, changed, or host/remote-mismatched files are not
deleted and force non-PASS.

The candidate parser remains load-bearing. The first rollback
`/proc/last_kmsg` double read is recorded only as corroboration; byte mismatch
does not override a valid candidate streamed marker proof.

Promotion order is executable policy, not documentation alone. Connected PASS
creates a helper/result-SHA-bound record required by oracle policy. Oracle
capture start creates a separate one-shot consumed record; only exact shape and
cleanup PASS creates the promotion record required by candidate policy. The
helper refuses ACTIVE text that does not name the exact prerequisite record
hashes.

## Validation

- 22 focused live-helper tests passed;
- Python bytecode compilation passed;
- exact static checker rerun matched the pinned result byte-for-byte;
- full helper `--offline-check` returned
  `PASS_R4W1A_LIVE_HELPER_OFFLINE_CHECK` with `device_contact=false`,
  `device_write=false`, and `flash=false`;
- real binding policy reports both oracle and candidate ACTIVE states false;
- `git diff --check` passed before documentation close.

No device was enumerated or contacted in this unit.

## Remaining Gates

1. independent read-only review of helper, tests, artifacts, and inactive policy;
2. fresh attended acknowledgement for one connected read-only identity dry-run;
3. durable connected dry-run PASS with exact Magisk/observer baseline;
4. separate review and activation of only the zero-flash oracle dry-run clause;
5. fresh attended oracle acknowledgement and one exact `bugreportz` rehearsal;
6. only after oracle PASS, re-pin and independently review the candidate clause;
7. fresh one-shot candidate approval.

The next executable device unit is therefore the connected read-only identity
dry-run, not the oracle write and not the candidate flash.
