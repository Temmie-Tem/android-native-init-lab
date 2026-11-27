# S22+ mainline UFS read/write and persistence: design proposal (H0)

Status: **proposal, not adopted**. It grants no device authority. It is step 2
of the operator's UFS roadmap (shorter wait, then read/write and persistence,
then stability, then the upstream driver). Step 1 closed with ML056: link
startup at the 60-second floor, Device Present
([run](S22PLUS_MAINLINE_ML056_UFS_BOOT_FLOOR_RUN_2026-11-27.md)).

## Goal

After the link starts, the fixed module reads and writes one fixed 4096-byte
block on the UFS device through its own minimal UTP path. The block must keep
its contents across a reboot. Both the stock Android kernel and the next
mainline boot must read back the same bytes.

## Write target: one block in LU0's unallocated tail

| Item | LBA (4096-byte blocks) |
| --- | ---: |
| `native_data` (entry 41) last block | 62,305,023 |
| **Unallocated tail gap** | **62,305,024 – 62,305,270** (247 blocks, 1,011,712 bytes) |
| GPT last usable | 62,305,270 |
| Backup GPT entries | 62,305,271 – 62,305,272 |
| Backup GPT header (last LBA) | 62,305,279 |
| **Proposed test block** | **62,305,152** |

Source: the live Android32 primary GPT (the retained P398 proposed table;
44 entries, first usable 6, last usable 62,305,270).

Why this block:
- **No partition covers it**, so no filesystem, Android or native code reads it.
- **It sits 128 blocks after `native_data`'s end and 118 blocks before the
  backup GPT.** A small offset error cannot reach either.
- **It is not near the primary GPT.** The other unallocated gap, LBAs 6–264,
  sits right after the primary entry array.

Rejected alternatives:
- **A block inside `native_data`.** The partition holds the live ext4 root
  with the Debian install (8,969 entries). A raw write there lands in a
  filesystem.
- **A new dedicated partition.** This would need another G2 GPT mutation.
- **Other LUs.** Boot, RPMB and persist-type LUs are forbidden or recovery
  critical.

## Fixed command sequence

The module adds a minimal single-slot UTP engine after the existing link
startup. Every command is compiled in with fixed fields; nothing comes from the
host or the observer.

1. Set the UTP transfer request list base (one slot), enable list run-stop.
   Crypto stays disabled (HCE crypto-general-enable clear), so the inline
   crypto engine is bypassed and data is plaintext.
2. **NOP OUT → NOP IN.** Confirms the UTP transport.
3. **Query: set flag `fDeviceInit`**, then read the flag until it clears
   (bounded poll inside the existing 15-second budget).
4. **TEST UNIT READY**, LUN 0. One REQUEST SENSE and one repeat are allowed for
   the expected power-on UNIT ATTENTION.
5. **READ CAPACITY(16)**, LUN 0. The result must be exactly 62,305,280 blocks
   of 4096 bytes.
6. **READ(10) LBAs 1–3.** These are the primary GPT header and entries. The
   bytes must equal the retained live table. The module also parses them and
   confirms that no entry covers the test block.
7. **READ(10) the test block.** This is the baseline, or the previous run's
   pattern.
8. *(phase 2b only)* **WRITE(10) with FUA**, one block, the test LBA only. The
   pattern is derived from the run's authenticated nonce.
9. *(phase 2b only)* **READ(10) the test block** again. It must equal the
   pattern.

Excluded: every other SCSI opcode (UNMAP, FORMAT UNIT, WRITE BUFFER, MODE
SELECT, SECURITY PROTOCOL, START STOP UNIT and the rest), every query write
other than `fDeviceInit`, attribute and descriptor writes, `fPurgeEnable`,
boot-LU or write-protect changes, the RPMB and other well-known LUNs, power
mode changes and the generic UFS, SCSI and block drivers. The existing V13
link scope, predicates and single link attempt are unchanged.

## Guards before the one write

The module issues the WRITE only if all of these hold on this boot:
- link completed, with Device Present;
- `fDeviceInit` cleared within its bound;
- capacity is exact;
- the GPT bytes are exact and no entry covers the block;
- the baseline read succeeded;
- the remaining budget covers the write and its readback.

Any failure skips the write and reports why.

The LBA appears in three places:
- a compile-time constant;
- a range check against the GPT parsed at run time (`native_end < LBA ≤ last_usable`);
- the host's check of the authenticated report.

## Phases

| Phase | Device effect | Proves |
| --- | --- | --- |
| **2a, read-only** (ML057) | Steps 1–7; no write | UTP data path; mainline reads match the retained GPT; the gap's baseline contents |
| **2b, one write** (ML058) | Steps 1–9 | One persistent write with readback in the same boot |
| **2c, persistence** | Rooted Android reads the block after the Download → Android return; the next mainline run reads it at step 7 | Survival across a reboot, read by two different storage stacks |

Phase 2a comes first because it makes the target's state visible without
writing. If the gap's baseline is not all zeros (or a recognizable pattern),
the design stops for review before any write.

Stability (step 3) would chain runs. Each run reads the previous run's
pattern, writes its own new one and reads it back.

## Host verification and report

- A new report version adds these fields:
  - the NOP result;
  - the `fDeviceInit` poll count;
  - the TEST UNIT READY sense;
  - capacity;
  - the GPT match;
  - baseline and readback digests;
  - the write status;
  - the skip reason.
- The host checks every field and binds the pattern to the run's nonce.
- A new fixed Android D0 read takes the SHA-256 of that one block from the
  whole-LU node as root, read-only. Final health takes it after the return.

## Contract changes needed

- **Common contract.** Permanent boundary 2 forbids raw block writes outside
  closed exceptions (today the G2 GPT and native ext4 exceptions). Phase 2b
  needs a new closed exception: one WRITE(10) of one block at one fixed LBA in
  LU0's unallocated tail, by the fixed mainline module, under its guards.
  Phase 2a needs a narrower delegation: fixed reads and the fixed
  initialization commands after link startup. Both need the operator's
  explicit approval.
- **Target contract.** Adopt both. Add the fixed Android read of the test block.
- **Code.** A new module report version and the UTP engine in the module
  (estimated 400–600 lines of C). Host parsing and verification. A fake-HCI
  test harness for the UTP sequence. The kernel, DT, route observer and
  witness floor are unchanged.

## Hazards

- **Wrong LBA.** Mitigated by the three LBA checks above and the 118- and
  128-block margins.
- **Unknown vendor use of the gap.** Phase 2a records the baseline first, and
  any unexpected content stops the design.
- **`fDeviceInit` and UTP state at handoff.** The device stays initialized
  when the Download reboot follows. The bootloader re-initializes UFS. The
  ordinary Download and original-A path is unchanged.
- **Write cache.** FUA forces the write to media before completion.
- **Inline crypto.** Crypto stays disabled. A request without a crypto
  configuration passes in plaintext, which Android's raw read also sees. If
  phase 2a shows otherwise, the design stops.
- **Hang or power loss.** Only the one block is at risk. The 15-second module
  budget, timer child, Download attempt and physical fallback stay.

## Open questions for the operator

1. Is the test block LBA 62,305,152 in LU0's unallocated tail acceptable?
2. Split into 2a (read-only) and 2b (one write), as recommended, or combine
   them?
3. Add the rooted Android read of the block for the independent persistence
   check (recommended)?
