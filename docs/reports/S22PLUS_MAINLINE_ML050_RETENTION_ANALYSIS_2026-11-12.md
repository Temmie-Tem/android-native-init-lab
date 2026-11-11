# Why ML050 returned no UDC record

The complete FYG8 Android snapshot establishes that no intact ML050 record
reached the reader. The existing evidence does **not** decide whether the
late writer ever committed a record. It does narrow the loss mechanisms
and gives a concrete reason to investigate what the bootloader restored.
This analysis used existing S22+ captures, firmware analysis and host
fixtures. No new device action was taken.

## The returned bytes

The host received no candidate USB response. After the new Download device
appeared at N+590.227 seconds, original Android returned healthy. The earlier
properties prefix and final health contained the same observed Android boot
ID. The fixed log read succeeded between two health brackets on that boot.
The stored copy is 2,097,136 bytes, the entire Samsung ring payload. Both
the equality and wrapped branches of the stock reader can produce this
length. The immediate invalid-magic reset to zero would produce an empty
snapshot. The producer header itself is excluded.

A search spanning the end/start seam found neither the eight-byte format
magic nor the fresh 16-byte candidate ID. The independent candidate/HMAC
scan also found no valid body under an invalidated prefix. An incorrect
linear search position, rotation alone, post-snapshot Android logging,
and a simple USB-enumeration failure do not explain the missing bytes.
The same kernel produced an authenticated UDC-absent record in a VM.
[Physical run](S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)
and [Samsung reader analysis](S22PLUS_MAINLINE_RETAINED_LOG_FEASIBILITY_H0_2026-10-29.md).

## Two compatible histories

* **No commit.** The exact packaged DT satisfies the static board and no-map
  reservation checks. ML050 has no contemporaneous physical evidence of
  live mapping eligibility, LOGM magic, index or header stability. The worker
  skips expired sampling slots and only reschedules after successful
  publication. One early guard or mapping failure can therefore eliminate
  all later samples even when Debian and its independent timer run. UDC
  absence and failed binding themselves are recordable outcomes.
* **Commit followed by loss.** The payload contains an Android shutdown
  request for Download followed by four consecutive XBL labels saying
  “restored from storage”. Two alternating firmware sections record a
  completed boot-partition write. Earlier analysis of the same FYG8
  SecEnvDxe identified a storage read into this very LOGM region. Restoring
  an older copy there could discard a committed RAM-only record in a single
  step. All four actual-instruction success/failure and valid/invalid header
  fixtures produced that label, so the string cannot establish the read's
  result. The six KlogOffset-zero messages do not measure the guest ring
  cursor. [FYG8 firmware path and instruction fixtures](S22PLUS_MAINLINE_ML003_RESET_PROVENANCE_H0_2026-10-30.md#what-the-restore-label-actually-establishes).

Ordinary forward logging is a weaker specific explanation. Only 356,319
bytes follow the start of the first banner, and 178,187 bytes from the third.
In a continuously advancing ring, reaching a slot immediately behind
the writer cursor requires roughly 2 MiB of forward appends, even in the
tail-placement case. Using a verified ML050 VM frame and the stock snapshot
model, 178,187 forward bytes preserved that frame at four representative
cursor positions. Those suffix lengths measure surviving text, not total
physical writes since a hypothetical commit. The final snapshot cannot
authenticate a continuous cursor or assign each section to a particular
boot. The two Odin sections both report the same 96 MiB uncompressed size.
The two transfer-and-boot pairs have different lengths (178,132 and
178,187 bytes) and differ in content. They do not show a byte-identical
replay of either complete pair.

## Historical controls and discussion

Across the 24 available, receipt-checked snapshots for ML003–ML025 and ML050,
the association is descriptive, with different instruments and reset paths.

| Firmware text in the returned snapshot | Candidate record present | No candidate record |
| --- | ---: | ---: |
| Includes warm reset, valid magic | 10 | 1 |
| Restored-from-storage labels only | 0 | 13 |

ML017 is the warm-label exception. ML021–ML023 had authenticated userspace or
USB evidence despite returning no early markers. LA002 verified an actual
write, immediate readback and snapshot on its candidate vendor Android boot,
before the subsequent original-A restoration. None supplies ML050's missing
write-time evidence. [ML021 USB result](S22PLUS_MAINLINE_ML021_RUN_2026-11-04.md)
and [LA002 calibration](S22PLUS_LOADER_LOGM_LA002_RUN_2026-11-03.md#logm-observations).

Claude Mythos 5.2 and Gemini 4 Argon High each assessed the evidence and
then received the other's first response and the firmware/corpus findings
for a second round. The firmware evidence gives old-copy replacement more
support than ordinary short forward append as a loss mechanism. It supplies
no probability of loss versus non-publication for this run. A same-boot
acknowledgment that independently read back a committed slot before Download
would distinguish a successful commit from subsequent loss. ML050 has no
such observation.

Private reproducibility materials and provider usage records for the
discussion are under
`workspace/private/outputs/s22plus-ml050-retention-discussion-h0-20261112-1/`.
