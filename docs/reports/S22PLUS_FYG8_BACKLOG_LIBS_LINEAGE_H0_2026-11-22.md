# S22+ backlog library lineage, FYG8 → GYJ1 (H0)

Date: 2026-11-22
Target: Samsung Galaxy S22+ `SM-S906N`. `S906NKSS7FYG8` (Android 15, SPL
2025-08-01) against `S906NKSU7GYJ1` (Android 16, SPL 2025-10-01).
Scope: H0 static lineage and patch-diff summary. Host-only, read-only, no
device contact. No reproduction, no proof of concept, no exploit work, and no
instruction-level reconstruction of any fix.
Serves: the [CVE backlog](../plans/S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md).
Uses the same inputs and method as the
[Quram DNG patch diff](S22PLUS_FYG8_QURAM_DNG_PATCH_DIFF_H0_2026-11-22.md).

## Inputs

Both sides come from the AVB-bound images described in the Quram report: same
signing key, hashtrees verified. Only the `/system/lib64` copies were compared.
The `/vendor` copies of `libsavsvc.so` and `libpadm.so` were not.

| Library | FYG8 size, sha256 | GYJ1 size, sha256 |
|---|---|---|
| `libsavsvc.so` | 1,268,504, `748024e4…2295` | 1,268,544, `9c2f42e8…02e5` |
| `libpadm.so` | 117,608, `6d4b1b53…11f7` | 121,696, `7cf9f278…c843` |
| `libsecuibc.so` | 273,848, `5174984f…dca5` | 277,888, `793a5541…883b` |
| `extractors/libsmkvextractor.so` | 145,432, `bb168209…3167` | 149,456, `76244696…a362` |

FYG8 hashes equal the [component inventory](S22PLUS_FYG8_COMPONENT_INVENTORY_H0_2026-11-22.md).

## Which advisories this pair can test

| Library | Advisories | Fixed in | Role of this pair |
|---|---|---|---|
| `libsavsvc.so` | CVE-2025-21034 | Sep-2025 | pre-fix → first fixed |
| `libpadm.so` | CVE-2025-21051/21052/21053/21054 | Oct-2025 | pre-fix → first fixed |
| `libsecuibc.so` | CVE-2026-21153/21154 | Nov-2026 | both pre-fix (**control**) |
| `libsmkvextractor.so` | CVE-2026-21114/21116/21156 | Oct/Nov-2026 | both pre-fix (**control**) |

The two control libraries show what the Android 15 → 16 rebuild alone does to
a binary. That gives a noise baseline for the two libraries that did receive a
fix in GYJ1.

## Method

`libdiff.py` (private) uses binutils only: `nm -D -S` (exported function
sizes), `readelf -S` (section sizes), `strings -n 6` (string set difference)
and `c++filt`. For the two largest `libpadm` deltas, `objdump` counted
instructions, compare instructions, conditional branches and call targets.
Running it on `libimagecodec.quram.so` reproduces the Quram report's counts
(2,761 common, 7 added, 72 size-changed), which checks the script.

## Result

| Library | Exported functions (FYG8/GYJ1) | Added / removed | Size-changed | `.text` delta |
|---|---|---|---|---|
| `libsavsvc.so` | 917 / 917 | 0 / 0 | 302 (net −3,968 B) | +316 B |
| `libpadm.so` | 120 / 120 | 0 / 0 | 46 (net +5,164 B) | +5,384 B |
| `libsecuibc.so` (control) | 174 / 174 | 0 / 0 | 40 (net +312 B) | +388 B |
| `libsmkvextractor.so` (control) | 2 / 2 | 0 / 0 | 1 | +3,224 B |

### Rebuild noise (controls)

- **`libsecuibc.so`.** Changes are small: ±8–164 B per function. A
  `.note.gnu.property` section appears and `.plt` grows, which are
  toolchain-level changes. String changes are limited to symbol and binary
  noise (`_ZdlPv` → `_ZdlPvm`, sized delete). There are no new messages.
- **`libsmkvextractor.so`.** This is an Android 16 platform API port, not a
  security change. The `libsavscmn.so` and `libextmediaformatdef.so`
  dependencies are gone (`scmn_fcc2mt*` → `android::FourCCToMime`). The
  `AMEDIAFORMAT_KEY_*` symbols became string literals. `CHECK` line numbers
  in `smkv_extractor.cpp` shift by +4 at first, then by about −100 near the
  end of the file (1587 → 1488). The fixes for this library come from later
  SMRs, so none of this is attributable to an advisory.

The baseline: an Android 16 rebuild of an unchanged-source library moves
function sizes by tens of bytes. A platform port can move them by kilobytes
and rewrite strings. Function-size churn alone is not evidence of a fix.

### `libsavsvc.so` (CVE-2025-21034)

- The export set is identical (917/917). The code family is continuous.
- Churn runs both ways and across many codecs. Examples:
  - `eco_mv_inter_b` 2,692 → 1,064 B;
  - `arac_it_32x32` 2,832 → 4,260 B;
  - `svp8d_dec_coeff` 5,724 → 4,400 B;
  - `s264d_get_pic_out_from_dpb_bp` 356 → 8 B.
- That pattern looks like inlining and optimisation changes, not targeted
  checks.
- There is one new meaningful string, `bit_depth_luma : %d, reset_bd_chfmt :
  %d`. It sits next to the growth of `aracd_set_ppi_by_bit_depth` (824 →
  1,368 B, in the `arac` HEVC decoder path).
- **The delta could not be localised at summary level.** The fix is likely in
  there, but rebuild churn hides it.

### `libpadm.so` (CVE-2025-21051–21054)

- The export set is identical (120/120). The code family is continuous.
- Two functions account for most of the `.text` growth (+4,900 of +5,384 B).

| Function | FYG8 | GYJ1 | Comment |
|---|---|---|---|
| `padme_init_q_tbl` | 186 insn, 4 cmp, 3 cond. branches | 1,045 insn, 2 cmp, 1 cond. branch | grew 5.6×, with *fewer* branches; looks like loop unrolling, not checks |
| `padme_get_qt` | 1,694 insn, 38 cmp, 34 cond. branches | 2,060 insn, 64 cmp, 67 cond. branches | same call targets; compares and branches roughly double; **candidate hardening delta** |

- Decoder-side (`padmd_*`) functions change by only ±40–130 B. That is at the
  noise level.
- No new diagnostic strings.
- Both large deltas are in the quantisation-table path on the *encoder* side
  (`padme_*`). The advisories say only "JPEG path". Whether these deltas are
  the fixes is not established.

## State change

- **CVE-2025-21034 (`libsavsvc.so`): `PUBLISHED` → `PRESENT`.** Component and
  pre-fix lineage are observed on FYG8. The delta is unlocalised.
- **CVE-2025-21051/21052/21053/21054 (`libpadm.so`): `PUBLISHED` →
  `PRESENT`.** Component and pre-fix lineage are observed. There is one
  candidate delta (`padme_get_qt`), but per-CVE attribution is open.
- **`libsecuibc.so` and `libsmkvextractor.so` rows stay `PUBLISHED`.** The
  library family is continuous through GYJ1. Lineage *against the fixed code*
  needs the Oct/Nov-2026 builds, and this pair cannot provide that.
- Rows for these libraries from later SMRs need later builds:
  - CVE-2026-21049 (`libpadm.so`);
  - CVE-2026-21069/21071/21072 (`libsavsvc.so`).

Follow-up: the [GYJ1 → GZH3 diff](S22PLUS_GYJ1_GZH3_LIBS_DIFF_H0_2026-11-22.md)
covers the Jul/Aug-2026 rows with the latest FUS build (SPL 2026-08-05).

## Limits

- Only exported symbols are sized. Static functions are folded into the
  `.text` totals.
- A size or branch-count change is a pointer, not a proof of a fix.
- Android 16 toolchain changes confound every delta here. The controls bound
  that noise but do not remove it.

## Private outputs

Analysis `s22plus-gyj1-compare.oxhg0V7q` holds:
- `libdiff.py` and `libdiff.json` (per library: sections, export sets,
  size-changed functions, added and removed strings);
- the `fyg8/` and `gyj1/` library copies.

The 10 GB GYJ1 `super.img` intermediate was deleted. `extract.sh` regenerates
it from the retained FUS package. The AVB-verified `system.img` and
`vendor.img` were kept.
