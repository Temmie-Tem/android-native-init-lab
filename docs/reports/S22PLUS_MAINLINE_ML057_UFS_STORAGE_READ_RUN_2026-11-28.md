# ML057: read-only storage stage stopped at TEST UNIT READY

ML057 was the first run of the
[read-only storage stage](../operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md)
(phase 2a, report V14). It used the witness-floor route with the floor kernel
and the storage module. It closed **`PASS_MAINLINE_UFS_LINK` /
`ANDROID_CLOSED_HEALTHY`** (`closed.json` `6631a06c…`).

- **The link repeated ML056's exactly.** Every link field in the report
  equals ML056's. The only difference is the report tag, `0xd0000000` → `0xe0000000`
  (V13 → V14).
- **The storage stage stopped at its first SCSI command and touched no
  media.**
  - NOP OUT passed. The fDeviceInit flag was set, then read back clear after
    one poll.
  - TEST UNIT READY returned a well-formed RESPONSE UPIU: OCS 0, response
    0, SCSI status CHECK CONDITION.
  - The stage refused that response as `-EPROTO` and stopped before READ
    CAPACITY. No read was issued, the GPT and the test block were not read,
    and no command could write.
- **The session took 193 s.** No physical action, replug or host recovery
  step was needed.

## Run

The operator returned the exact approval for task `19048e48…` (1800 s, one
operation, attended). The first readiness record had aged out by dispatch, so
readiness was re-run with zero device controls. The target-session lease was
free, and the approved terminal dispatched once.

| Journal event (from preflight) | Seconds |
| --- | ---: |
| N step start (`mainline-evidence`) | 18.7 |
| module permit (effect intent) | 105.7 |
| Download return intent | 112.0 |
| final rooted Android health complete | 193.4 |

Counts: 1 N, 1 original A and 3 controls, with no recovery. Final rooted
Android health passed.

## Storage result (report V14 fields 38–53)

| Field | Value | Meaning |
| --- | --- | --- |
| rc | −71 | `-EPROTO` |
| step | 6 | `G0Q_ST_TUR` |
| flags | 15 | LIST, NOP, INIT_SET, INIT_CLEAR |
| fDeviceInit polls | 1 | cleared at the first read |
| sense | 0 | none recorded |
| last status | `0x21020000` | type RESPONSE `0x21`, SCSI status `0x02`, response 0, OCS 0 |
| capacity, GPT word, block digest | 0 | not reached |

`last_status` packs OCS, response (header byte 6), status (byte 7) and
type (byte 0) (`ufs_storage.c:123`). With type `0x21` and response 0, the
only `-EPROTO` return left in `scsi()`/`ring()` is the extra-header guard:
header byte 8 (Total EHS Length) was nonzero (`ufs_storage.c:128`). The
CHECK CONDITION path itself always returns `-EAGAIN`, and the sense parser
was never reached. The CHECK CONDITION is most likely the expected UNIT
ATTENTION after power-on and reset, which the stage was built to consume
once.

The guard was added in review round 9 because an extra header segment would
shift the data segment, where sense lives. Upstream `ufshcd` does not check
this byte on ordinary responses. The report does not carry header bytes
8–11, so the value of byte 8 and the data segment length are not known.

## Claims

A completed run can claim:
- a third completed mainline UFS link startup with Device Present, with
  every reported link field equal to ML056's;
- the first UTP exchanges on mainline after the link, all on LU 0 with no
  media access: NOP OUT/NOP IN, a set and read of fDeviceInit (cleared
  within one poll), and a TEST UNIT READY answered with CHECK CONDITION;
- an authenticated USB first response with no physical action.

It does not claim:
- READ CAPACITY, a GPT read or the test block read: none was issued;
- the sense key: the response was refused before sense parsing;
- stability or anything about writes.

## Next

Proposed next unit (needs operator choice), an H0 change to the storage stage:
1. carry header bytes 8–11 of the last response in the report;
2. accept a nonzero Total EHS Length on a RESPONSE UPIU by locating the
   data segment after the EHS, bounded by the response length;
3. re-run the read-only stage.

Both changes need review, adoption, a new capability and a new run approval.
