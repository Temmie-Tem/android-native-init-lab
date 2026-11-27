# ML058: the storage stop is the response byte, not the extra header

ML058 ran the read-only storage stage with the response-header report
(V15, v73 `d927a15f7a`, capability-6). It closed
**`PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`** (`closed.json`
`a395514a…`) in 184 s, with no physical action and no recovery.

- **The link repeated ML056 and ML057.** Result 0, HCS `0xf`.
- **The storage stage stopped exactly as in ML057**, at TEST UNIT READY with
  `-EPROTO`, before any media command.
- **The new header word corrects ML057's diagnosis.** The Total EHS Length
  is 0. The refused byte is the response field: Target Failure (`0x01`),
  alongside CHECK CONDITION.

## Storage result (report V15 fields 38–54)

| Field | Value | Meaning |
| --- | --- | --- |
| rc | −71 | `-EPROTO` |
| step | 6 | TEST UNIT READY |
| flags | 15 | LIST, NOP, INIT_SET, INIT_CLEAR |
| fDeviceInit polls | 1 | cleared at the first read |
| sense | 0 | not parsed |
| last status | `0x21020100` | RESPONSE, status CHECK CONDITION, **response `0x01`**, OCS 0 |
| response header | `0x00000014` | EHS 0, device information 0, data segment 20 bytes |

`scsi()` refuses any RESPONSE UPIU whose response byte is nonzero
(`ufs_storage.c:186`). The device answers the first TEST UNIT READY after
reset with CHECK CONDITION and Target Failure. It also returns a 20-byte data
segment: the 2-byte length plus 18 bytes of fixed-format sense, presumably
the UNIT ATTENTION. Upstream `ufshcd_transfer_rsp_status()` takes only the
status byte for SCSI responses and ignores the response byte (`ufshcd.c`,
`UPIU_TRANSACTION_RESPONSE` case).

## Correction to ML057

ML057's status was the same `0x21020100`. Its report decoded the word as
`0x21020000`, read the response byte as 0, and attributed the stop to the
Total EHS Length check. That was a decoding error. V15's EHS handling is
harmless, but it did not address the real refusal. The ML057 report carries
a correction pointing here.

## Claims

A completed run can claim:
- a fourth completed mainline UFS link startup with Device Present;
- the UTP exchanges up to TEST UNIT READY, all on LU 0 with no media access;
- the device's first TEST UNIT READY answer: CHECK CONDITION, response
  Target Failure, no extra header, a 20-byte data segment.

It does not claim READ CAPACITY, a GPT read or the test block read, or the
sense key.

## Proposed next unit (operator choice)

For SCSI responses, accept response `0x01` only together with CHECK
CONDITION, as the upstream driver effectively does. Parse the sense as
before, so the one UNIT ATTENTION repeat applies. GOOD must still come with
response 0. This needs review, adoption, a new capability and a new run
approval.
