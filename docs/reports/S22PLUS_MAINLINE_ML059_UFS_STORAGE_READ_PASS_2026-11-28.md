# ML059: first mainline UFS media reads (phase 2a complete)

ML059 ran the read-only storage stage with the response-byte fix (report
V16, v74 `c2dde46285`, capability-7). It closed
**`PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`** (`closed.json`
`67147152…`) in 194 s, with no physical action, no replug and no recovery.

**The storage stage completed (rc 0, step DONE).** For the first time, the
mainline kernel module read the phone's UFS media directly:
- **READ CAPACITY(16)** returned last LBA 62,305,279 with 4096-byte blocks,
  the expected LU0 geometry.
- **READ(10) of LBAs 1–3** returned the primary GPT. Its SHA-256 matches the
  live Android32 table (`a0de4421…`). The parsed entries leave the test block
  outside every partition and inside the last usable LBA.
- **READ(10) of LBA 62,305,152**, the test block in LU0's unallocated tail,
  returned 4096 zero bytes (SHA-256 `ad7facb2…`, the digest of 4096 zeros).

No write opcode was issued; none exists in the module.

## Run

The operator returned the exact approval for task `179e2678…` (1800 s, one
operation, attended). Readiness was refreshed just before dispatch, with zero
device controls, and the target-session lease was free.

| Journal event (from preflight) | Seconds |
| --- | ---: |
| N step start (`mainline-evidence`) | 19.7 |
| module permit (effect intent) | 106.8 |
| Download return intent | 113.3 |
| final rooted Android health complete | 194.5 |

Counts: 1 N, 1 original A and 3 controls, with no recovery. Final rooted
Android health passed.

## Link result

Result 0, HCS `0xf` (Device Present), the same as ML054 and ML056–ML058.

## Storage result (report V16 fields 38–54)

| Field | Value | Meaning |
| --- | --- | --- |
| rc / step | 0 / 10 | completed (`DONE`) |
| flags | `0xcfff` | every step flag, plus UNIT_ATTENTION, BLOCK_ZERO, TUR_REPEAT, TARGET_FAILURE |
| fDeviceInit polls | 1 | cleared at the first read |
| sense | `0x062900` | the first TUR's UNIT ATTENTION: key 6, ASC `0x29` (power on or reset) |
| last status | `0x21000000` | block READ: RESPONSE, GOOD, response 0, OCS 0 |
| capacity (low word) | 62,305,279 | last LBA |
| GPT word | `0xa0de4421` | the pinned live table |
| block digest | `ad7facb2…2ca7` | 4096 zero bytes |
| response header | 0 | no extra header, no data segment |

The first TEST UNIT READY after reset again returned CHECK CONDITION with
response Target Failure, as in ML057 and ML058. V16 accepted it and parsed
the sense: UNIT ATTENTION, power on or reset. It then took the one repeat,
which returned GOOD.

## What it took

| Run | Report | Stop |
| --- | --- | --- |
| ML057 | V14 | TUR: response `0x01` refused (first misread as an extra header) |
| ML058 | V15 | same; the new header word showed EHS 0, which exposed the response byte |
| ML059 | V16 | **completed** |

## Claims

A completed run can claim:
- the first direct UFS media reads from the mainline kernel on this phone:
  capacity, the primary GPT and one unallocated block;
- that the primary GPT on the device equals the live Android32 table that
  every partition plan here assumes;
- that the test block at LBA 62,305,152 holds zeros before any write, which
  is the baseline for phase 2b.

It does not claim:
- any write, persistence or stability;
- any LUN other than 0, or any block other than LBAs 1–3 and 62,305,152.

## Next

Roadmap step 2 continues with phase 2b: one FUA write of a known pattern to
LBA 62,305,152. It needs its own closed raw-block exception in the common
contract, operator approval, review and a new run approval. Phase 2c then
reads the block back after a reboot.
