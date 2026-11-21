# S22+ Quram DNG patch diff, FYG8 → GYJ1 (H0)

Date: 2026-11-22
Target: Samsung Galaxy S22+ `SM-S906N`. Pre-fix `S906NKSS7FYG8` (Android 15,
SPL 2025-08-01). First fixed `S906NKSU7GYJ1` (Android 16, SPL 2025-10-01).
Scope: H0 static patch diff. Host-only, read-only, no device contact. No
reproduction, no proof of concept, no exploit work.
Serves: Candidate A of the
[security side track](../plans/S22PLUS_FYG8_SECURITY_SIDE_TRACK_CANDIDATES_2026-09-16.md)
and the [CVE backlog](../plans/S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md).

## Inputs and provenance

| | FYG8 (pre-fix) | GYJ1 (first fixed) |
|---|---|---|
| Source | SamFW ZIP, policy-pinned (`f831e5fb…a2c8`) | Samsung FUS (official server, `samloader download` of `S906NKSU7GYJ1/S906NOKR7GYJ1/S906NKSU7GYI7/S906NKSU7GYJ1`), ZIP sha256 `a520dc593a3dab6eab9131bc8b57d8b0e3bf18a0d8f7cce320b09779212da224` |
| AP tar sha256 | `7934579f…0bb2` (equals policy) | `cf6182963079d9c88712b4a04074381c9eb44fe75baf33b0279b0c7eba8cf39b` |
| vbmeta / vbmeta_system | `1031323a…` / `6d19a37e…` | `4930e66d…94b0b4` / `b0184be6…1698` |
| AVB | signatures valid; 6 logical hashtrees verified | signatures valid, **same key** (sha1 `e03300ab66600a17e63d91ad7f2357380a46a65c`); `system` and `vendor` hashtrees verified |
| `/system/lib64/libimagecodec.quram.so` | 2,701,280 B, sha256 `926b1fd1…3a1a`, build-id `616cea83…8e97` | 2,716,072 B |

Update history (Samsung doc page and FUS list) shows no build between FYG8 and
GYJ1. FYG8 is the last Android 15 build. GYJ1 therefore carries both the
Sep-2025 and the Oct-2025 SMR fixes. That includes CVE-2025-21043 (Sep) and
CVE-2025-21055 (Oct), both in `libimagecodec.quram.so`.

## Method

- Exported dynamic symbols carry the DNG C++ classes: 2,761 functions in FYG8
  and 2,768 in GYJ1. This allowed a per-function comparison with
  `aarch64-linux-gnu-nm -D -S` and `objdump` only.
- For string references, `adrp`/`add` pairs were resolved through the `LOAD`
  segments.
- radare2 6.2.4 was downloaded and sha256-verified for deeper work but was not
  used. Running it needs operator permission.

## Result

| Measure | Value |
|---|---|
| Functions present in both | 2,761 |
| Added in GYJ1 | 7 (none removed) |
| Size-changed functions | 72 |

Added functions:
- `SafeInt32Add`, `SafeInt64Add`, `SafeInt64Mult`
- `getColorSpcaeID` (sic)
- three `WINKJ_*NullConvert*` functions

GYJ1 adds these DNG hardening deltas (new error strings in parentheses):

1. **`QuramDngOpcodeList::parse`** (408 → 624 B).
   - **Opcode count cap.** The 32-bit count read from the stream is now
     compared with `0xF4240` (1,000,000) before the loop ("Invalid opcode
     count: %u (max: %u)"). FYG8 has no cap.
   - **Opcode creation check.** FYG8 dereferences the return value of
     `QuramDngDecoder::makeDngOpcode` without a null check
     (`ldr w8, [x0, #8]`). GYJ1 adds `cbz x0`, then throws ("Failed to create
     opcode %u").
   - The existing end-position check now logs its operands ("Error parsing
     opcode list: %zu != %zu + %zu").
2. **`QuramDngOpcodeList::doApply`** (148 → 220 B). Adds "NULL opcode at
   index %u".
3. **`QuramDngOpcodeUnknown::initialize`** (140 → 208 B). The opcode payload
   size is now capped at `0x3200000` (50 MiB) ("Invalid size: %u (max: %u)").
   FYG8 has no check.
4. **`QuramDngDecoder::makeTmpStage2Image`** (1,340 → 1,924 B). It contains 60
   call sites to the new `SafeInt64Mult`/`SafeInt64Add`, so its buffer-size
   arithmetic became overflow-checked.
5. **`QuramDngPixelBuffer::getInternalPixel`** is new in the export table
   (260 B, multiple bounds comparisons, "Out-of-range pixel access"). Other
   larger deltas: `QuramDngReadImage::readTile` +728 B,
   `QuramDngPixelBuffer::RepeatSubArea` +224 B, several
   `QuramDngOpcode*::processArea` ±40–170 B. These were not yet read
   instruction by instruction.

Non-DNG deltas, recorded but not analyzed: `TransformICC`/`checkColorXform`
(ICC colour-space handling), the `initJpegCaptureOTF*` logging change, and
JPEG upsampler/null-convert additions.

## Interpretation (hypothesis, not proof)

- **Code lineage is confirmed.** The FYG8 library is the same code family as
  the first fixed build, minus the guards above. FYG8 is pre-fix for the
  Sep/Oct-2025 Quram DNG hardening.
- **The root cause is consistent with public accounts.** The opcode-list
  delta (an untrusted 32-bit count with no cap, and a 1,000,000 cap added in
  the fix) matches the public secondary account of CVE-2025-21043's opcode-count
  handling. The fix also hardens per-opcode payload size, null opcode objects,
  stage-2 image size arithmetic and pixel access. That is broader than a
  single check.
- **Attribution is still open.** GYJ1 bundles two Quram CVEs
  (CVE-2025-21043, CVE-2025-21055) and possibly undisclosed SVE items. Without
  vendor detail, no delta can be pinned to a single CVE ID.
- **Memory corruption is not proven here.** An uncapped count or a missing null
  check is enough for resource exhaustion or a crash. The OOB-write mechanism
  named in the advisory most plausibly lies in the size and offset arithmetic
  deltas (items 3–5). That remains a hypothesis until those functions are read.

## State change

- **CVE-2025-21043, CVE-2025-21055: `PUBLISHED` → `PRESENT`.** The component
  and pre-fix lineage are observed on FYG8. Candidate `DIFFED` deltas are
  identified above, but the per-CVE attribution is open.
- The other Quram rows are later SMRs and need the respective later builds.

## Private outputs

Analysis `s22plus-gyj1-compare.oxhg0V7q` holds:
- `extract.sh`, `verify_avb.py` and `avb-verified.json`;
- `fyg8/` and `gyj1/` library copies;
- `parse.{fyg8,gyj1}.s` and `full.gyj1.s`.

The GYJ1 package is at `workspace/private/inputs/firmware/S906NKSU7GYJ1_SKC/`.

## Next

- Read `readTile`, `makeTmpStage2Image`, `RepeatSubArea` and the opcode
  `processArea` deltas instruction by instruction. radare2 function-level diff
  needs permission; objdump suffices for the exported functions.
- Repeat the method for `libsavsvc.so`, `libpadm.so`, `libsecuibc.so` and
  `libsmkvextractor.so`. All differ between FYG8 and GYJ1. Only the
  Sep/Oct-2025 advisories apply to this pair.
